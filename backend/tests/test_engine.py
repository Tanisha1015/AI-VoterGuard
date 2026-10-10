"""Tests for the comparison and aggregation engine, using small hand-made rolls plus the synthetic data."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.engine import config as cfg
from app.engine.aggregate import aggregate_booths, constituency_baseline
from app.engine.compare import CompareResult, compare, load_rolls
from app.engine.hashing import sha256_file
from app.synth.generate import generate

ROLL_HEADER = ",".join(cfg.ROLL_COLUMNS)


def roll(*rows: dict[str, Any]) -> pd.DataFrame:
    """Build a roll DataFrame; unspecified fields get defaults. Each row needs at least epic_no."""
    defaults: dict[str, Any] = {
        "ac_no": 999, "part_no": 1, "serial_no": 1, "name": "A One", "relative_name": "B One",
        "relation_type": "FATHER", "house_no": "1", "age": 30, "gender": "M",
    }
    df = pd.DataFrame([{**defaults, **r} for r in rows], columns=list(cfg.ROLL_COLUMNS))
    return df.astype({c: "int64" for c in cfg.ROLL_INT_COLUMNS})


def asdd_df(*rows: tuple[str, int, str]) -> pd.DataFrame:
    """Build an ASDD DataFrame from (epic_no, part_no, reason) tuples."""
    df = pd.DataFrame(list(rows), columns=["epic_no", "part_no", "reason"])
    df["remark"] = ""
    return df[list(cfg.ASDD_COLUMNS)].astype({"part_no": "int64"})


def write_csvs(tmp: Path, draft: str, final: str, asdd: str) -> tuple[Path, Path, Path]:
    """Write three CSV texts to tmp and return their paths."""
    paths = (tmp / "draft.csv", tmp / "final.csv", tmp / "asdd.csv")
    for path, text in zip(paths, (draft, final, asdd)):
        path.write_text(text, encoding="utf-8")
    return paths


# --------------------------------------------------------------------------- hashing


def test_sha256_file_matches_hashlib_and_format(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    payload = b"epic_no,age\r\nVGX1,30\n\xe0\xa4\x85"
    path.write_bytes(payload)
    got = sha256_file(path)
    assert got == "0x" + hashlib.sha256(payload).hexdigest()
    assert len(got) == 66 and got == got.lower()


def test_sha256_file_changes_with_one_byte(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    path.write_bytes(b"abc")
    before = sha256_file(path)
    path.write_bytes(b"abc ")
    assert sha256_file(path) != before


def test_sha256_file_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty"
    path.write_bytes(b"")
    assert sha256_file(path) == "0x" + hashlib.sha256(b"").hexdigest()


# --------------------------------------------------------------------------- load_rolls

GOOD_ROLL = ROLL_HEADER + "\nVGX1,999,1,1,A One,B One,FATHER,12-B,30,M\nVGX2,999,1,2,C Two,D Two,HUSBAND,007,45,F\n"
GOOD_ASDD = "epic_no,part_no,reason,remark\nVGX2,1,SHIFTED,\n"


def test_load_rolls_returns_typed_frames(tmp_path: Path) -> None:
    d, f, a = load_rolls(*write_csvs(tmp_path, GOOD_ROLL, GOOD_ROLL, GOOD_ASDD))
    assert list(d.columns) == list(cfg.ROLL_COLUMNS) and list(a.columns) == list(cfg.ASDD_COLUMNS)
    assert all(str(d[c].dtype) == "int64" for c in cfg.ROLL_INT_COLUMNS)
    assert str(a["part_no"].dtype) == "int64"
    assert list(d["house_no"]) == ["12-B", "007"]  # kept as text, leading zeros intact
    assert list(a["remark"]) == [""]  # empty remark stays an empty string, not NaN
    assert len(f) == 2


def test_load_rolls_missing_roll_column(tmp_path: Path) -> None:
    bad = GOOD_ROLL.replace("house_no", "house")
    with pytest.raises(ValueError, match=r"draft roll: missing required column.*house_no"):
        load_rolls(*write_csvs(tmp_path, bad, GOOD_ROLL, GOOD_ASDD))


def test_load_rolls_missing_asdd_column(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"asdd: missing required column.*reason"):
        load_rolls(*write_csvs(tmp_path, GOOD_ROLL, GOOD_ROLL, "epic_no,part_no,remark\nVGX2,1,\n"))


def test_load_rolls_unknown_reason(tmp_path: Path) -> None:
    bad = "epic_no,part_no,reason,remark\nVGX2,1,MOVED,\n"
    with pytest.raises(ValueError, match=r"unknown reason.*MOVED"):
        load_rolls(*write_csvs(tmp_path, GOOD_ROLL, GOOD_ROLL, bad))


def test_load_rolls_unknown_gender_and_bad_number(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"final roll: unknown gender"):
        load_rolls(*write_csvs(tmp_path, GOOD_ROLL, GOOD_ROLL.replace(",30,M", ",30,X"), GOOD_ASDD))
    with pytest.raises(ValueError, match=r"column 'age' must contain whole numbers"):
        load_rolls(*write_csvs(tmp_path, GOOD_ROLL.replace(",30,M", ",abc,M"), GOOD_ROLL, GOOD_ASDD))


# --------------------------------------------------------------------------- compare

DRAFT = roll(
    {"epic_no": "VGX1", "part_no": 1}, {"epic_no": "VGX2", "part_no": 1, "gender": "F"},
    {"epic_no": "VGX3", "part_no": 1, "age": 35}, {"epic_no": "VGX4", "part_no": 2},
)


def test_added_and_removed_with_reason_and_null_reason() -> None:
    final = roll({"epic_no": "VGX1", "part_no": 1}, {"epic_no": "VGX4", "part_no": 2},
                 {"epic_no": "VGX9", "part_no": 2})
    res = compare(DRAFT, final, asdd_df(("VGX2", 1, "SHIFTED")))
    assert list(res.added["epic_no"]) == ["VGX9"]
    removed = res.removed.set_index("epic_no")
    assert set(removed.index) == {"VGX2", "VGX3"}
    assert removed.loc["VGX2", "reason"] == "SHIFTED"
    assert pd.isna(removed.loc["VGX3", "reason"])
    assert res.modified.empty


def test_modified_lists_changed_fields() -> None:
    final = roll(
        {"epic_no": "VGX1", "part_no": 1, "name": "A Renamed", "age": 31},
        {"epic_no": "VGX2", "part_no": 1, "gender": "F"},  # unchanged
        {"epic_no": "VGX3", "part_no": 1, "age": 35, "house_no": "9"},
        {"epic_no": "VGX4", "part_no": 3},  # booth changed
    )
    res = compare(DRAFT, final, asdd_df())
    mod = res.modified.set_index("epic_no")
    assert set(mod.index) == {"VGX1", "VGX3", "VGX4"}
    assert mod.loc["VGX1", "changed_fields"] == ["name", "age"]
    assert mod.loc["VGX3", "changed_fields"] == ["house_no"]
    assert mod.loc["VGX4", "changed_fields"] == ["part_no"]
    assert mod.loc["VGX1", "name_draft"] == "A One" and mod.loc["VGX1", "name_final"] == "A Renamed"
    assert res.added.empty and res.removed.empty


def test_serial_no_change_is_not_a_modification() -> None:
    final = DRAFT.copy()
    final["serial_no"] = 99
    assert compare(DRAFT, final, asdd_df()).modified.empty


def test_data_quality_issue_types() -> None:
    final = roll(
        {"epic_no": "VGX1", "part_no": 1, "age": 17}, {"epic_no": "VGX4", "part_no": 2, "age": 111},
        {"epic_no": "VGX5", "part_no": 2, "age": 18}, {"epic_no": "VGX6", "part_no": 2, "age": 110},
        {"epic_no": "VGX6", "part_no": 2, "age": 110},  # repeated epic_no in the final roll
    )
    asdd = asdd_df(("VGX2", 1, "DEAD"), ("VGX77", 2, "ABSENT"))
    dq = compare(DRAFT, final, asdd).data_quality
    assert list(dq.columns) == list(cfg.DQ_COLUMNS)
    found = {(r.part_no, r.issue_type, r.epic_no) for r in dq.itertuples()}
    assert found == {
        (1, cfg.REMOVED_WITHOUT_ASDD, "VGX3"),  # VGX2 has an ASDD row, VGX3 does not
        (2, cfg.ASDD_NOT_IN_DRAFT, "VGX77"),
        (1, cfg.AGE_OUT_OF_RANGE, "VGX1"),
        (2, cfg.AGE_OUT_OF_RANGE, "VGX4"),
        (2, cfg.DUPLICATE_EPIC, "VGX6"),
    }  # ages 18 and 110 are in range
    assert dq["detail"].str.len().gt(0).all()


def test_data_quality_empty_has_columns_and_is_clean() -> None:
    res = compare(DRAFT, DRAFT.copy(), asdd_df())
    assert res.data_quality.empty and list(res.data_quality.columns) == list(cfg.DQ_COLUMNS)
    assert res.added.empty and res.removed.empty and res.modified.empty


def test_duplicate_epic_flagged_once_per_extra_row() -> None:
    draft = roll({"epic_no": "VGX1"}, {"epic_no": "VGX1"}, {"epic_no": "VGX1"})
    dq = compare(draft, draft.copy(), asdd_df()).data_quality
    assert list(dq["issue_type"]) == [cfg.DUPLICATE_EPIC] * 4  # 2 extra rows in each roll


def test_compare_does_not_modify_inputs() -> None:
    final = roll({"epic_no": "VGX1", "part_no": 1, "age": 99})
    before = (DRAFT.copy(), final.copy())
    compare(DRAFT, final, asdd_df())
    pd.testing.assert_frame_equal(DRAFT, before[0])
    pd.testing.assert_frame_equal(final, before[1])



# --------------------------------------------------------------------------- aggregate_booths


def booth_scenario() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Booth 1: 10 draft voters, 5 removed, 3 added. Booth 2: unchanged. Booth 3: only an addition."""
    spec = [  # epic, gender, age, house
        ("E1", "F", 20, "H1"), ("E2", "F", 30, "H1"), ("E3", "M", 40, "H1"), ("E4", "M", 50, "H1"),
        ("E5", "F", 70, "H1"), ("E6", "M", 85, "H2"), ("E7", "F", 22, "H2"), ("E8", "M", 35, "H2"),
        ("E9", "F", 55, "H2"), ("E10", "M", 65, "H2"),
    ]
    booth1 = [{"epic_no": e, "part_no": 1, "gender": g, "age": a, "house_no": h} for e, g, a, h in spec]
    booth2 = [{"epic_no": e, "part_no": 2, "age": 30} for e in ("E11", "E12")]
    draft = roll(*booth1, *booth2)
    survivors = [r for r in booth1 if r["epic_no"] in {"E5", "E7", "E8", "E9", "E10"}]
    added = [
        {"epic_no": "A1", "part_no": 1, "house_no": "H9", "age": 25},
        {"epic_no": "A2", "part_no": 1, "house_no": "H9", "age": 30},
        {"epic_no": "A3", "part_no": 1, "house_no": "H8", "age": 17},  # out of range -> dq issue
        {"epic_no": "A4", "part_no": 3, "house_no": "H1", "age": 40},
    ]
    final = roll(*survivors, *booth2, *added)
    asdd = asdd_df(("E1", 1, "DEAD"), ("E2", 1, "SHIFTED"), ("E3", 1, "SHIFTED"),
                   ("E4", 1, "DUPLICATE"), ("E6", 1, "ABSENT"))
    return draft, final, asdd


@pytest.fixture(scope="module")
def scenario() -> tuple[pd.DataFrame, pd.DataFrame, CompareResult, pd.DataFrame]:
    draft, final, asdd = booth_scenario()
    res = compare(draft, final, asdd)
    return draft, final, res, aggregate_booths(res, draft, final)


def test_one_row_per_booth_with_all_columns(scenario: Any) -> None:
    booths = scenario[3]
    assert list(booths["part_no"]) == [1, 2, 3]
    assert list(booths.columns) == [
        "part_no", "draft_count", "final_count", "removed", "added", "deletion_rate", "reason_mix",
        "gender_removed", "female_removed_share", "female_share_draft", "age_band_removed_share",
        "young_share_draft", "addition_rate", "max_house_additions", "max_house_voters",
        "dead_under_40", "dq_count",
    ]


def test_counts_and_rates(scenario: Any) -> None:
    b1 = scenario[3].set_index("part_no").loc[1]
    assert (b1["draft_count"], b1["final_count"], b1["removed"], b1["added"]) == (10, 8, 5, 3)
    assert b1["deletion_rate"] == pytest.approx(0.5)
    assert b1["addition_rate"] == pytest.approx(0.3)


def test_reason_mix_includes_zero_reasons(scenario: Any) -> None:
    booths = scenario[3].set_index("part_no")
    assert booths.loc[1, "reason_mix"] == pytest.approx(
        {"ABSENT": 0.2, "SHIFTED": 0.4, "DEAD": 0.2, "DUPLICATE": 0.2})
    assert booths.loc[2, "reason_mix"] == {"ABSENT": 0.0, "SHIFTED": 0.0, "DEAD": 0.0, "DUPLICATE": 0.0}


def test_gender_and_female_shares(scenario: Any) -> None:
    b1 = scenario[3].set_index("part_no").loc[1]
    assert b1["gender_removed"] == {"M": 3, "F": 2, "O": 0}
    assert b1["female_removed_share"] == pytest.approx(0.4)
    assert b1["female_share_draft"] == pytest.approx(0.5)


def test_age_bands_and_young_share(scenario: Any) -> None:
    b1 = scenario[3].set_index("part_no").loc[1]
    assert list(b1["age_band_removed_share"]) == list(cfg.AGE_BAND_LABELS)
    assert b1["age_band_removed_share"] == pytest.approx(
        {"18-25": 0.2, "26-35": 0.2, "36-45": 0.2, "46-60": 0.2, "61-80": 0.0, "80+": 0.2})
    assert b1["young_share_draft"] == pytest.approx(0.2)  # ages 20 and 22


def test_age_band_edges() -> None:
    draft = roll(*({"epic_no": f"E{a}", "age": a} for a in (18, 25, 26, 35, 36, 45, 46, 60, 61, 80, 81)))
    final = roll({"epic_no": "KEEP"})
    res = compare(draft, final, asdd_df())
    shares = aggregate_booths(res, draft, final).iloc[0]["age_band_removed_share"]
    assert shares == pytest.approx({"18-25": 2 / 11, "26-35": 2 / 11, "36-45": 2 / 11,
                                    "46-60": 2 / 11, "61-80": 2 / 11, "80+": 1 / 11})



def test_house_clusters_and_dead_under_40(scenario: Any) -> None:
    booths = scenario[3].set_index("part_no")
    assert booths.loc[1, "max_house_additions"] == 2  # two added voters at H9
    assert booths.loc[1, "max_house_voters"] == 4  # H2 holds E7, E8, E9, E10 in the final roll
    assert booths.loc[1, "dead_under_40"] == 1  # E1: DEAD at age 20 (E3 is SHIFTED at 40)
    assert booths.loc[2, "max_house_additions"] == 0


def test_data_quality_count_per_booth(scenario: Any) -> None:
    assert list(scenario[3]["dq_count"]) == [1, 0, 0]  # only A3's age 17 in booth 1


def test_zero_denominators_give_zero_not_nan(scenario: Any) -> None:
    b3 = scenario[3].set_index("part_no").loc[3]  # booth with no draft voters
    assert (b3["draft_count"], b3["final_count"], b3["added"]) == (0, 1, 1)
    assert b3["deletion_rate"] == 0.0 and b3["addition_rate"] == 0.0
    assert b3["female_removed_share"] == 0.0 and b3["female_share_draft"] == 0.0
    assert b3["young_share_draft"] == 0.0


def test_removed_without_reason_counts_but_not_in_mix() -> None:
    draft = roll({"epic_no": "E1"}, {"epic_no": "E2"}, {"epic_no": "E3"})
    final = roll({"epic_no": "E3"})
    res = compare(draft, final, asdd_df(("E1", 1, "ABSENT")))
    b = aggregate_booths(res, draft, final).iloc[0]
    assert b["removed"] == 2 and b["reason_mix"]["ABSENT"] == pytest.approx(0.5)
    assert b["dq_count"] == 1  # E2 has no ASDD record


def test_no_changes_gives_zero_rows() -> None:
    draft = roll({"epic_no": "E1"}, {"epic_no": "E2", "part_no": 2})
    res = compare(draft, draft.copy(), asdd_df())
    b = aggregate_booths(res, draft, draft.copy())
    assert list(b["removed"]) == [0, 0] and list(b["deletion_rate"]) == [0.0, 0.0]
    assert list(b["max_house_additions"]) == [0, 0] and list(b["max_house_voters"]) == [1, 1]


# --------------------------------------------------------------------------- constituency_baseline


def test_baseline_median_mad_and_overall_shares(scenario: Any) -> None:
    base = constituency_baseline(scenario[3])
    # booth deletion rates are 0.5, 0.0, 0.0 -> median 0, MAD = median(0.5, 0, 0) = 0
    assert base["deletion_rate"] == 0.0 and base["deletion_rate_mad"] == 0.0
    assert base["reason_mix"] == pytest.approx({"ABSENT": 0.2, "SHIFTED": 0.4, "DEAD": 0.2, "DUPLICATE": 0.2})
    assert base["female_share_removed"] == pytest.approx(0.4)


def test_baseline_known_median_and_mad() -> None:
    booths = pd.DataFrame({
        "deletion_rate": [0.02, 0.04, 0.05, 0.06, 0.30],
        "removed": [2, 4, 5, 6, 30],
        "reason_mix": [{"ABSENT": 0.0, "SHIFTED": 1.0, "DEAD": 0.0, "DUPLICATE": 0.0}] * 5,
        "gender_removed": [{"M": 1, "F": 1, "O": 0}] * 5,
    })
    base = constituency_baseline(booths)
    assert base["deletion_rate"] == pytest.approx(0.05)
    assert base["deletion_rate_mad"] == pytest.approx(0.01)  # |x-0.05| = .03 .01 0 .01 .25 -> median .01
    assert base["reason_mix"]["SHIFTED"] == pytest.approx(1.0)
    assert base["female_share_removed"] == pytest.approx(5 / 47)


def test_baseline_with_no_removals_is_zero() -> None:
    draft = roll({"epic_no": "E1"})
    res = compare(draft, draft.copy(), asdd_df())
    base = constituency_baseline(aggregate_booths(res, draft, draft.copy()))
    assert base["deletion_rate"] == 0.0 and base["female_share_removed"] == 0.0
    assert base["reason_mix"] == {r: 0.0 for r in cfg.REASONS}



# --------------------------------------------------------------------------- synthetic data


@pytest.fixture(scope="module")
def synthetic_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Use data/synthetic when present, otherwise generate it (seed 42) into a temp folder."""
    existing = Path(__file__).resolve().parents[1] / "data" / "synthetic"
    if all((existing / n).is_file() for n in ("draft_roll.csv", "final_roll.csv", "asdd.csv")):
        return existing
    out = tmp_path_factory.mktemp("synthetic")
    generate(out, 42)
    return out


def test_synthetic_booth_17_and_runtime(synthetic_dir: Path) -> None:
    draft, final, asdd = load_rolls(
        synthetic_dir / "draft_roll.csv", synthetic_dir / "final_roll.csv", synthetic_dir / "asdd.csv")
    start = time.perf_counter()
    res = compare(draft, final, asdd)
    booths = aggregate_booths(res, draft, final)
    baseline = constituency_baseline(booths)
    elapsed = time.perf_counter() - start
    assert elapsed < 3.0, f"engine took {elapsed:.2f}s"

    by_booth = booths.set_index("part_no")
    assert by_booth.loc[17, "deletion_rate"] > 0.2
    assert by_booth.loc[17, "reason_mix"]["SHIFTED"] > 0.75
    assert len(booths) == 60 and baseline["deletion_rate"] < 0.1
    assert by_booth.loc[33, "max_house_additions"] >= 40
    assert by_booth.loc[25, "dead_under_40"] >= 30
    assert set(res.data_quality["issue_type"]) == {cfg.REMOVED_WITHOUT_ASDD, cfg.AGE_OUT_OF_RANGE}
    assert booths["draft_count"].sum() == len(draft) and booths["final_count"].sum() == len(final)

