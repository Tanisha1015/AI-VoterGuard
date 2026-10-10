"""Tests for the anomaly detectors and the booth risk score.

Small hand-made booths check each rule's boundaries; the synthetic roll (data/synthetic, seed 42) with
truth.json checks that every planted pattern is found and that ordinary booths are mostly left alone.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.detectors.age_skew import AgeSkewDetector
from app.detectors.base import DetectorContext, DetectorType, Flag, Severity
from app.detectors.config import THRESHOLDS
from app.detectors.data_quality import DataQualityDetector
from app.detectors.deletion_rate import DeletionRateDetector
from app.detectors.duplicate_entry import DuplicateEntryDetector, find_duplicate_pairs, pairs_per_booth
from app.detectors.gender_skew import GenderSkewDetector
from app.detectors.house_cluster import HouseClusterDetector
from app.detectors.reason_dominance import ReasonDominanceDetector
from app.detectors.registry import number_flags, run_all
from app.detectors.risk import FEATURE_NAMES, feature_matrix, severity_component
from app.engine import config as cfg
from app.engine.aggregate import aggregate_booths, constituency_baseline
from app.engine.compare import CompareResult, compare, load_rolls
from app.synth.generate import generate

D = DetectorType
ZERO_MIX = {r: 0.0 for r in cfg.REASONS}
BASELINE: dict[str, Any] = {
    "deletion_rate": 0.05, "deletion_rate_mad": 0.01,
    "reason_mix": {"ABSENT": 0.2, "SHIFTED": 0.4, "DEAD": 0.35, "DUPLICATE": 0.05},
    "female_share_removed": 0.5,
}


# --------------------------------------------------------------------------- helpers


def booth_row(part_no: int = 1, **over: Any) -> dict[str, Any]:
    """A quiet booth row with every aggregate column; override fields as needed."""
    row: dict[str, Any] = {
        "part_no": part_no, "draft_count": 500, "final_count": 500, "removed": 0, "added": 0,
        "deletion_rate": 0.05, "reason_mix": dict(ZERO_MIX), "gender_removed": {"M": 0, "F": 0, "O": 0},
        "female_removed_share": 0.0, "female_share_draft": 0.5,
        "age_band_removed_share": {b: 0.0 for b in cfg.AGE_BAND_LABELS}, "young_share_draft": 0.15,
        "addition_rate": 0.0, "max_house_additions": 0, "max_house_voters": 5, "dead_under_40": 0,
        "dq_count": 0,
    }
    row.update(over)
    return row


def empty_result(dq: pd.DataFrame | None = None, added: pd.DataFrame | None = None) -> CompareResult:
    """A CompareResult with no differences, optionally with data-quality rows or added voters."""
    empty = pd.DataFrame()
    dq_df = dq if dq is not None else pd.DataFrame({c: [] for c in cfg.DQ_COLUMNS})
    return CompareResult(added if added is not None else empty, empty, empty, dq_df)


def ctx_for(rows: list[dict[str, Any]], **kw: Any) -> DetectorContext:
    """Build a DetectorContext from booth rows; draft, final, result and baseline are optional."""
    empty = pd.DataFrame(columns=list(cfg.ROLL_COLUMNS))
    return DetectorContext(
        booth_df=pd.DataFrame(rows), draft=kw.get("draft", empty), final=kw.get("final", empty),
        result=kw.get("result", empty_result()), baseline=kw.get("baseline", BASELINE),
    )


def person(epic: str, part: int, name: str, rel: str, age: int, gender: str = "M",
           house: str = "1") -> dict[str, Any]:
    """One synthetic roll row."""
    return {"epic_no": epic, "ac_no": 999, "part_no": part, "serial_no": 1, "name": name,
            "relative_name": rel, "relation_type": "FATHER", "house_no": house, "age": age,
            "gender": gender}


def only(flags: list[Flag]) -> Flag:
    """The single flag in a list (fails when there are none or several)."""
    assert len(flags) == 1, flags
    return flags[0]


# --------------------------------------------------------------------------- config / dataclass


def test_thresholds_cover_every_detector_and_are_json_exportable() -> None:
    assert {d.value for d in DetectorType} <= set(THRESHOLDS)
    assert json.loads(json.dumps(THRESHOLDS)) == THRESHOLDS


def test_detector_enum_matches_contract() -> None:
    assert [d.value for d in DetectorType] == [
        "DELETION_RATE", "REASON_DOMINANCE", "GENDER_SKEW", "AGE_SKEW", "HOUSE_CLUSTER",
        "DUPLICATE_ENTRY", "DATA_QUALITY"]
    assert [s.value for s in Severity] == ["LOW", "MEDIUM", "HIGH"]


# --------------------------------------------------------------------------- DELETION_RATE


@pytest.mark.parametrize(("z", "removed", "expected"), [
    (3.4, 50, None),                 # z just under 3.5
    (3.6, 50, Severity.MEDIUM),
    (5.9, 50, Severity.MEDIUM),
    (6.1, 50, Severity.HIGH),
    (9.0, 14, None),                 # high z but fewer than 15 removed
])
def test_deletion_rate_boundaries(z: float, removed: int, expected: Severity | None) -> None:
    rate = 0.05 + z * 1.4826 * 0.01
    flags = DeletionRateDetector().detect(ctx_for([booth_row(deletion_rate=rate, removed=removed)]))
    if expected is None:
        assert flags == []
    else:
        flag = only(flags)
        assert (flag.detector, flag.severity, flag.metric_name) == (D.DELETION_RATE, expected, "deletion_rate")
        assert flag.metric_value == pytest.approx(rate) and flag.baseline == 0.05


def test_deletion_rate_zero_mad_is_quiet() -> None:
    base = {**BASELINE, "deletion_rate_mad": 0.0}
    assert DeletionRateDetector().detect(ctx_for([booth_row(deletion_rate=0.9, removed=99)], baseline=base)) == []


# --------------------------------------------------------------------------- REASON_DOMINANCE


@pytest.mark.parametrize(("share", "removed", "expected"), [
    (0.79, 100, None), (0.80, 100, Severity.MEDIUM), (0.89, 100, Severity.MEDIUM),
    (0.90, 100, Severity.HIGH), (0.95, 19, None),
])
def test_reason_dominance_boundaries(share: float, removed: int, expected: Severity | None) -> None:
    mix = {"ABSENT": 0.0, "SHIFTED": share, "DEAD": 1 - share, "DUPLICATE": 0.0}
    flags = ReasonDominanceDetector().detect(ctx_for([booth_row(removed=removed, reason_mix=mix)]))
    if expected is None:
        assert flags == []
    else:
        flag = only(flags)
        assert flag.severity == expected and flag.details["reason"] == "SHIFTED"
        assert flag.metric_value == pytest.approx(share) and flag.baseline == 0.4


# --------------------------------------------------------------------------- GENDER_SKEW


def gender_ctx(female_removed: int, removed: int = 100) -> DetectorContext:
    """A booth whose draft roll is 50% female, with ``female_removed`` of ``removed`` removals female."""
    row = booth_row(removed=removed, gender_removed={"M": removed - female_removed, "F": female_removed, "O": 0})
    draft = pd.DataFrame([person(f"E{i}", 1, "A B", "C D", 30, "F" if i < 50 else "M") for i in range(100)])
    return ctx_for([row], draft=draft)


@pytest.mark.parametrize(("female_removed", "expected"), [
    (64, None), (65, Severity.MEDIUM), (74, Severity.MEDIUM), (75, Severity.HIGH),
])
def test_gender_skew_boundaries_female(female_removed: int, expected: Severity | None) -> None:
    flags = GenderSkewDetector().detect(gender_ctx(female_removed))
    if expected is None:
        assert flags == []
    else:
        flag = only(flags)
        assert (flag.severity, flag.details["gender"], flag.metric_name) == (expected, "F", "f_removed_share")
        assert flag.metric_value == pytest.approx(female_removed / 100) and flag.baseline == pytest.approx(0.5)


def test_gender_skew_male_and_small_booth() -> None:
    flag = only(GenderSkewDetector().detect(gender_ctx(20)))  # 80 male removed vs 50% in the draft
    assert flag.details["gender"] == "M" and flag.severity == Severity.HIGH
    assert GenderSkewDetector().detect(gender_ctx(5, removed=29)) == []


# --------------------------------------------------------------------------- AGE_SKEW


def test_age_skew_dead_under_40() -> None:
    assert AgeSkewDetector().detect(ctx_for([booth_row(dead_under_40=9)])) == []
    flag = only(AgeSkewDetector().detect(ctx_for([booth_row(dead_under_40=10)])))
    assert flag.details["kind"] == "DEAD_UNDER_40" and flag.metric_name == "dead_under_40"
    assert flag.metric_value == 10


def young_row(young_share: float, removed: int = 40) -> dict[str, Any]:
    bands = {b: 0.0 for b in cfg.AGE_BAND_LABELS} | {"18-25": young_share}
    return booth_row(removed=removed, age_band_removed_share=bands, young_share_draft=0.15)


@pytest.mark.parametrize(("share", "removed", "fires"), [(0.29, 40, False), (0.31, 40, True), (0.50, 29, False)])
def test_age_skew_young_removed(share: float, removed: int, fires: bool) -> None:
    flags = AgeSkewDetector().detect(ctx_for([young_row(share, removed)]))
    if fires:
        flag = only(flags)
        assert flag.details["kind"] == "YOUNG_REMOVED" and flag.baseline == pytest.approx(0.15)
    else:
        assert flags == []



# --------------------------------------------------------------------------- HOUSE_CLUSTER


def house_frame(part: int, house: str, n: int) -> pd.DataFrame:
    """n voters in one house of one booth."""
    return pd.DataFrame([person(f"A{part}_{house}_{i}", part, "X Y", "Z Y", 30, house=house) for i in range(n)])


@pytest.mark.parametrize(("n", "expected"), [
    (9, None), (10, Severity.MEDIUM), (29, Severity.MEDIUM), (30, Severity.HIGH),
])
def test_house_cluster_additions(n: int, expected: Severity | None) -> None:
    added = house_frame(1, "12-B", n)
    ctx = ctx_for([booth_row(max_house_additions=n, max_house_voters=min(n, 14))],
                  result=empty_result(added=added), final=added)
    flags = HouseClusterDetector().detect(ctx)
    if expected is None:
        assert flags == []
    else:
        flag = only(flags)
        assert flag.severity == expected and flag.details["house_no"] == "12-B"
        assert flag.metric_name == "max_house_additions"


def test_house_cluster_crowded_house_uses_floor_and_percentile() -> None:
    final = pd.concat([house_frame(2, "7", 16), house_frame(1, "1", 5), house_frame(3, "1", 5)], ignore_index=True)
    rows = [booth_row(1, max_house_voters=5), booth_row(2, max_house_voters=16), booth_row(3, max_house_voters=5)]
    flag = only(HouseClusterDetector().detect(ctx_for(rows, final=final)))
    assert flag.part_no == 2 and flag.details["house_no"] == "7" and flag.metric_name == "max_house_voters"
    # Below the floor of 15 nothing fires, even for the booth at the 99th percentile.
    assert HouseClusterDetector().detect(ctx_for([booth_row(1, max_house_voters=14)], final=house_frame(1, "7", 14))) == []


# --------------------------------------------------------------------------- DUPLICATE_ENTRY

STEMS = ["Aaron", "Bimal", "Chetan", "Deepak", "Eshan", "Farhan", "Girish", "Harish", "Imran", "Jatin",
         "Kabir", "Lalit", "Manoj", "Nitin", "Omkar", "Pavan", "Qadir", "Rohit"]


def copies(n: int, src: int, dst: int) -> list[dict[str, Any]]:
    """n (original in ``src``, spelling-variant copy in ``dst``) pairs, with a distinct name per pair."""
    rows: list[dict[str, Any]] = []
    for i in range(n):
        rows.append(person(f"S{src}_{i}", src, f"{STEMS[i]} Kumar", "Ramesh Singh", 40))
        rows.append(person(f"C{dst}_{i}", dst, f"{STEMS[i]}  Kumar.", "Ramesh Singh", 40))
    return rows


@pytest.mark.parametrize(("n", "expected"), [
    (4, None), (5, Severity.MEDIUM), (14, Severity.MEDIUM), (15, Severity.HIGH),
])
def test_duplicate_entry_thresholds_count_both_booths(n: int, expected: Severity | None) -> None:
    final = pd.DataFrame(copies(n, 1, 2))
    assert dict(pairs_per_booth(find_duplicate_pairs(final))) == {1: n, 2: n}
    flags = DuplicateEntryDetector().detect(ctx_for([booth_row(1), booth_row(2)], final=final))
    if expected is None:
        assert flags == []
    else:
        assert sorted(f.part_no for f in flags) == [1, 2]
        assert all(f.severity == expected and f.metric_value == n for f in flags)
        assert flags[0].details["partner_booths"] == {"2": n}


def test_duplicate_entry_rules_exclude_non_matches() -> None:
    base = copies(1, 1, 2)[0]
    twin = {**base, "epic_no": "T1", "part_no": 2}
    cases = {
        "same booth": {**twin, "part_no": 1},
        "same epic": {**twin, "epic_no": base["epic_no"]},
        "age gap 2": {**twin, "age": base["age"] + 2},
        "other gender": {**twin, "gender": "F"},
        "other relative": {**twin, "relative_name": "Zubin Mehra"},
        "other name": {**twin, "name": "Vikram Kumar"},
    }
    for label, other in cases.items():
        assert find_duplicate_pairs(pd.DataFrame([base, other])).empty, label
    assert len(find_duplicate_pairs(pd.DataFrame([base, twin]))) == 1
    assert len(find_duplicate_pairs(pd.DataFrame([base, {**twin, "age": base["age"] + 1}]))) == 1


def test_duplicate_entry_does_not_modify_input_and_handles_empty() -> None:
    final = pd.DataFrame(copies(3, 1, 2))
    before = final.copy()
    find_duplicate_pairs(final)
    pd.testing.assert_frame_equal(final, before)
    assert find_duplicate_pairs(final.iloc[0:0]).empty


# --------------------------------------------------------------------------- DATA_QUALITY


def test_data_quality_thresholds_and_details() -> None:
    dq = pd.DataFrame({
        "part_no": [1] * 8 + [2] * 3 + [3] * 2,
        "issue_type": ["AGE_OUT_OF_RANGE"] * 5 + ["REMOVED_WITHOUT_ASDD"] * 8,
        "epic_no": [f"E{i}" for i in range(13)], "detail": "",
    })
    rows = [booth_row(1, dq_count=8), booth_row(2, dq_count=3), booth_row(3, dq_count=2)]
    flags = DataQualityDetector().detect(ctx_for(rows, result=empty_result(dq=dq)))
    assert [(f.part_no, f.severity) for f in flags] == [(1, Severity.HIGH), (2, Severity.MEDIUM)]
    assert flags[0].details["issue_counts"] == {"AGE_OUT_OF_RANGE": 5, "REMOVED_WITHOUT_ASDD": 3}
    assert flags[1].details["issue_counts"] == {"REMOVED_WITHOUT_ASDD": 3}
    assert flags[0].metric_name == "dq_count" and flags[0].metric_value == 8



# --------------------------------------------------------------------------- risk + registry units


def test_severity_component_caps_at_one() -> None:
    def flag(part: int, sev: Severity) -> Flag:
        return Flag(part, D.AGE_SKEW, sev, "m", 1.0, 0.0)

    flags = [flag(1, Severity.LOW), flag(2, Severity.HIGH), flag(2, Severity.HIGH), flag(2, Severity.MEDIUM),
             flag(3, Severity.MEDIUM), flag(3, Severity.LOW)]
    out = severity_component(flags, pd.Series([1, 2, 3, 4]))
    assert list(out) == pytest.approx([0.15, 1.0, 0.45, 0.0])


def test_feature_matrix_columns_and_values() -> None:
    mix = {"ABSENT": 0.1, "SHIFTED": 0.7, "DEAD": 0.2, "DUPLICATE": 0.0}
    row = booth_row(7, deletion_rate=0.2, removed=100, reason_mix=mix, female_removed_share=0.7,
                    max_house_additions=12, dq_count=4)
    feats = feature_matrix(pd.DataFrame([row]), pd.Series({7: 6}))
    assert list(feats.columns) == list(FEATURE_NAMES)
    assert feats.iloc[0].to_dict() == pytest.approx({
        "deletion_rate": 0.2, "shifted_share": 0.7, "absent_share": 0.1, "dead_share": 0.2, "female_gap": 0.2,
        "young_removed_gap": -0.15, "addition_rate": 0.0, "max_house_additions": 12.0, "duplicate_pairs": 6.0,
        "dq_count": 4.0})


def test_number_flags_is_stable_per_booth() -> None:
    raw = [Flag(5, D.GENDER_SKEW, Severity.LOW, "m", 1, 0), Flag(2, D.DELETION_RATE, Severity.LOW, "m", 1, 0),
           Flag(5, D.DATA_QUALITY, Severity.LOW, "m", 1, 0)]
    assert [(f.flag_id, f.detector) for f in number_flags(raw)] == [
        ("f_2_1", D.DELETION_RATE), ("f_5_1", D.GENDER_SKEW), ("f_5_2", D.DATA_QUALITY)]


# --------------------------------------------------------------------------- synthetic data


@pytest.fixture(scope="module")
def synthetic_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Use data/synthetic when present, otherwise generate it (seed 42) into a temp folder."""
    existing = Path(__file__).resolve().parents[1] / "data" / "synthetic"
    if all((existing / n).is_file() for n in ("draft_roll.csv", "final_roll.csv", "asdd.csv", "truth.json")):
        return existing
    out = tmp_path_factory.mktemp("synthetic")
    generate(out, 42)
    return out


@pytest.fixture(scope="module")
def synthetic_run(synthetic_dir: Path) -> dict[str, Any]:
    """Run the whole pipeline once (engine + detectors + risk) and keep what the tests need."""
    start = time.perf_counter()
    draft, final, asdd = load_rolls(synthetic_dir / "draft_roll.csv", synthetic_dir / "final_roll.csv",
                                    synthetic_dir / "asdd.csv")
    result = compare(draft, final, asdd)
    booths = aggregate_booths(result, draft, final)
    flags, scored = run_all(booths, draft, final, result, constituency_baseline(booths))
    elapsed = time.perf_counter() - start
    truth = json.loads((synthetic_dir / "truth.json").read_text())
    return {"flags": flags, "booths": scored, "elapsed": elapsed, "truth": truth, "input": booths,
            "frames": (draft, final, result)}


def find(run: dict[str, Any], part_no: int, detector: DetectorType) -> Flag:
    """The first flag of ``detector`` for ``part_no`` (fails if there is none)."""
    matches = [f for f in run["flags"] if f.part_no == part_no and f.detector == detector]
    assert matches, f"no {detector.value} flag for booth {part_no}"
    return matches[0]



def test_p1_booth_17(synthetic_run: dict[str, Any]) -> None:
    assert find(synthetic_run, 17, D.DELETION_RATE).severity == Severity.HIGH
    assert find(synthetic_run, 17, D.REASON_DOMINANCE).details["reason"] == "SHIFTED"
    assert find(synthetic_run, 17, D.GENDER_SKEW).details["gender"] == "F"


def test_p2_booth_42_absent_dominance(synthetic_run: dict[str, Any]) -> None:
    flag = find(synthetic_run, 42, D.REASON_DOMINANCE)
    assert flag.details["reason"] == "ABSENT" and flag.severity == Severity.HIGH


def test_p3_booth_33_house_cluster(synthetic_run: dict[str, Any]) -> None:
    flag = find(synthetic_run, 33, D.HOUSE_CLUSTER)
    assert flag.details["house_no"] == "12-B" and flag.severity == Severity.HIGH


def test_p4_booth_51_duplicate_entry(synthetic_run: dict[str, Any]) -> None:
    flag = find(synthetic_run, 51, D.DUPLICATE_ENTRY)
    assert flag.metric_value >= 5 and "8" in flag.details["partner_booths"]


def test_p5_booth_25_age_skew(synthetic_run: dict[str, Any]) -> None:
    assert find(synthetic_run, 25, D.AGE_SKEW).details["kind"] == "DEAD_UNDER_40"


def test_p6_booths_3_and_9_data_quality(synthetic_run: dict[str, Any]) -> None:
    for part in (3, 9):
        assert find(synthetic_run, part, D.DATA_QUALITY).metric_value >= 3


def test_few_non_planted_booths_flagged(synthetic_run: dict[str, Any]) -> None:
    planted = {p for a in synthetic_run["truth"]["anomalies"] for p in a["part_nos"]}
    booths = synthetic_run["booths"]
    others = booths[~booths["part_no"].isin(planted)]
    assert len(others) > 0 and others["flagged"].sum() <= 0.10 * len(others)


def test_booth_17_ranks_in_top_three(synthetic_run: dict[str, Any]) -> None:
    top = synthetic_run["booths"].sort_values("risk_score", ascending=False, kind="stable")
    assert 17 in list(top["part_no"].head(3))


def test_scored_booth_table_shape(synthetic_run: dict[str, Any]) -> None:
    out, original = synthetic_run["booths"], synthetic_run["input"]
    assert list(out.columns) == [*original.columns, "risk_score", "flagged"]
    assert out["risk_score"].between(0, 100).all() and out["risk_score"].dtype.kind == "i"
    assert out["flagged"].dtype == bool
    assert "risk_score" not in original.columns  # the input table is not modified
    assert set(out.loc[out["flagged"], "part_no"]) == {f.part_no for f in synthetic_run["flags"]}


def test_flag_ids_and_fields(synthetic_run: dict[str, Any]) -> None:
    flags: list[Flag] = synthetic_run["flags"]
    assert len({f.flag_id for f in flags}) == len(flags)
    for part in {f.part_no for f in flags}:
        ids = [f.flag_id for f in flags if f.part_no == part]
        assert ids == [f"f_{part}_{n}" for n in range(1, len(ids) + 1)]
    assert all(isinstance(f.part_no, int) and isinstance(f.metric_value, float) for f in flags)
    json.dumps([f.details for f in flags])  # details must be JSON-serialisable


def test_run_is_fast_and_deterministic(synthetic_run: dict[str, Any]) -> None:
    assert synthetic_run["elapsed"] < 10.0, f"took {synthetic_run['elapsed']:.2f}s"
    draft, final, result = synthetic_run["frames"]
    booths = synthetic_run["input"]
    flags2, scored2 = run_all(booths, draft, final, result, constituency_baseline(booths))
    assert flags2 == synthetic_run["flags"]
    pd.testing.assert_frame_equal(scored2, synthetic_run["booths"])

