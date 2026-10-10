"""Tests for the synthetic roll generator: determinism, schema, normal booths and planted anomalies."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from rapidfuzz import fuzz

from app.synth.generate import generate
from app.synth.names import COLUMNS

FILES = ("draft_roll.csv", "final_roll.csv", "asdd.csv", "truth.json", "demo_voters.json")
SEED = 42
PLANTED_REMOVAL_BOOTHS = [17, 42, 25]


class Synth:
    """Loaded synthetic output shared by the tests."""

    def __init__(self, out: Path) -> None:
        self.out = out
        self.draft = pd.read_csv(out / "draft_roll.csv", dtype={"house_no": str})
        self.final = pd.read_csv(out / "final_roll.csv", dtype={"house_no": str})
        self.asdd = pd.read_csv(out / "asdd.csv", keep_default_na=False)
        self.truth = json.loads((out / "truth.json").read_text(encoding="utf-8"))
        self.demo = json.loads((out / "demo_voters.json").read_text(encoding="utf-8"))
        self.removed = self.draft[~self.draft["epic_no"].isin(self.final["epic_no"])]
        self.added = self.final[~self.final["epic_no"].isin(self.draft["epic_no"])]
        # Reason per removed voter, from asdd.csv; NaN where asdd has no row (P6).
        self.reason = self.removed["epic_no"].map(self.asdd.set_index("epic_no")["reason"])

    def booth_removed(self, part: int) -> pd.DataFrame:
        return self.removed[self.removed["part_no"] == part]

    def anomaly(self, anomaly_id: str) -> dict[str, Any]:
        return next(a for a in self.truth["anomalies"] if a["id"] == anomaly_id)


def _hashes(out: Path) -> dict[str, str]:
    return {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in FILES}


@pytest.fixture(scope="module")
def syn(tmp_path_factory: pytest.TempPathFactory) -> Synth:
    out = tmp_path_factory.mktemp("synthetic")
    generate(out, SEED)
    return Synth(out)


def test_creates_five_files(syn: Synth) -> None:
    for name in FILES:
        assert (syn.out / name).is_file()


def test_deterministic_same_seed_same_bytes(tmp_path: Path, syn: Synth) -> None:
    generate(tmp_path / "again", SEED)
    assert _hashes(tmp_path / "again") == _hashes(syn.out)


def test_different_seed_changes_output(tmp_path: Path, syn: Synth) -> None:
    generate(tmp_path / "other", SEED + 1)
    assert _hashes(tmp_path / "other")["draft_roll.csv"] != _hashes(syn.out)["draft_roll.csv"]


def test_csv_columns_exact(syn: Synth) -> None:
    expected = "epic_no,ac_no,part_no,serial_no,name,relative_name,relation_type,house_no,age,gender"
    for name in ("draft_roll.csv", "final_roll.csv"):
        assert (syn.out / name).read_text(encoding="utf-8").splitlines()[0] == expected
    assert list(syn.draft.columns) == COLUMNS
    assert (syn.out / "asdd.csv").read_text(encoding="utf-8").splitlines()[0] == "epic_no,part_no,reason,remark"


def test_constituency_and_booth_sizes(syn: Synth) -> None:
    assert set(syn.draft["ac_no"]) == {999}
    assert sorted(syn.draft["part_no"].unique()) == list(range(1, 61))
    sizes = syn.draft.groupby("part_no").size()
    assert sizes.min() >= 700 and sizes.max() <= 900
    assert syn.truth["ac_no"] == 999 and syn.truth["ac_name"] == "Demo Nagar (Synthetic)"


def test_enums_and_formats(syn: Synth) -> None:
    for roll in (syn.draft, syn.final):
        assert set(roll["gender"]) <= {"M", "F", "O"}
        assert set(roll["relation_type"]) <= {"FATHER", "HUSBAND", "MOTHER", "OTHER"}
        assert roll["epic_no"].str.fullmatch(r"VGX\d{7}").all()
        assert roll["house_no"].str.fullmatch(r"\d+(-[A-Z]|/\d)?").all()
    assert set(syn.asdd["reason"]) <= {"ABSENT", "SHIFTED", "DEAD", "DUPLICATE"}
    assert 0 < (syn.draft["gender"] == "O").mean() < 0.01
    assert syn.draft["house_no"].str.contains("-").any() and syn.draft["house_no"].str.contains("/").any()
    assert syn.draft["age"].between(18, 95).all()


def test_epic_unique(syn: Synth) -> None:
    assert syn.draft["epic_no"].is_unique
    assert syn.final["epic_no"].is_unique
    assert syn.asdd["epic_no"].is_unique


def test_serials_are_sequential_per_booth(syn: Synth) -> None:
    for roll in (syn.draft, syn.final):
        for _, group in roll.groupby("part_no"):
            assert list(group["serial_no"]) == list(range(1, len(group) + 1))


def test_normal_booth_removal_additions_and_reason_mix(syn: Synth) -> None:
    draft_n = syn.draft.groupby("part_no").size()
    rate = syn.removed.groupby("part_no").size().reindex(draft_n.index, fill_value=0) / draft_n
    assert rate.drop(index=PLANTED_REMOVAL_BOOTHS).between(0.029, 0.061).all()
    add_rate = syn.added.groupby("part_no").size().reindex(draft_n.index, fill_value=0) / draft_n
    ordinary = [p for p in draft_n.index if p not in (33, 51)]
    assert add_rate[ordinary].between(0.009, 0.031).all()
    mix = syn.reason[~syn.removed["part_no"].isin(PLANTED_REMOVAL_BOOTHS)].value_counts(normalize=True)
    assert mix["DEAD"] == pytest.approx(0.35, abs=0.05)
    assert mix["SHIFTED"] == pytest.approx(0.40, abs=0.05)
    assert mix["ABSENT"] == pytest.approx(0.15, abs=0.05)
    assert mix["DUPLICATE"] == pytest.approx(0.10, abs=0.05)


def test_normal_removals_age_gender_and_additions(syn: Synth) -> None:
    normal = syn.removed[~syn.removed["part_no"].isin(PLANTED_REMOVAL_BOOTHS)]
    reasons = syn.reason[normal.index]
    assert (normal[reasons == "DEAD"]["age"] >= 60).mean() > 0.6
    assert (normal[reasons != "DEAD"]["age"] >= 60).mean() < 0.4
    draft_f = (syn.draft[~syn.draft["part_no"].isin(PLANTED_REMOVAL_BOOTHS)]["gender"] == "F").mean()
    assert (normal["gender"] == "F").mean() == pytest.approx(draft_f, abs=0.03)
    ordinary_added = syn.added[~syn.added["part_no"].isin([33, 51])]
    assert (ordinary_added["age"] <= 25).mean() > 0.55  # young skew
    assert (ordinary_added["age"] <= 40).all()


def test_removed_voters_are_in_asdd_except_p6(syn: Synth) -> None:
    missing = set(syn.removed[syn.reason.isna()]["epic_no"])
    assert missing == set(syn.anomaly("P6")["details"]["missing_asdd_epics"])
    assert set(syn.asdd["epic_no"]) <= set(syn.removed["epic_no"])


def test_p1_booth_17(syn: Synth) -> None:
    removed = syn.booth_removed(17)
    rate = len(removed) / (syn.draft["part_no"] == 17).sum()
    all_rates = syn.removed.groupby("part_no").size() / syn.draft.groupby("part_no").size()
    assert 0.20 <= rate <= 0.24
    assert rate > 4 * all_rates.median()
    assert (syn.reason[removed.index] == "SHIFTED").mean() == pytest.approx(0.82, abs=0.02)
    assert (removed["gender"] == "F").mean() == pytest.approx(0.71, abs=0.02)


def test_p2_booth_42(syn: Synth) -> None:
    removed = syn.booth_removed(42)
    assert 0.12 <= len(removed) / (syn.draft["part_no"] == 42).sum() <= 0.16
    assert (syn.reason[removed.index] == "ABSENT").mean() >= 0.85


def test_p3_booth_33_house_cluster(syn: Synth) -> None:
    final_33 = syn.final[syn.final["part_no"] == 33]
    cluster = final_33[final_33["house_no"] == "12-B"]
    assert len(cluster) == 45  # exactly the planted voters; no ordinary household shares the number
    assert cluster["epic_no"].isin(syn.added["epic_no"]).all()
    assert (syn.draft["house_no"][syn.draft["part_no"] == 33] == "12-B").sum() == 0
    assert len(syn.added[syn.added["part_no"] == 33]) > 45
    assert syn.anomaly("P3")["counts"]["added_same_house"] == 45



def _is_near_copy(src: pd.Series, copy: pd.Series) -> bool:
    return bool(
        src["gender"] == copy["gender"]
        and abs(int(src["age"]) - int(copy["age"])) <= 1
        and src["epic_no"] != copy["epic_no"]
        and fuzz.ratio(src["name"], copy["name"]) >= 80
        and fuzz.ratio(src["relative_name"], copy["relative_name"]) >= 80
    )


def test_p4_near_copies_of_booth_8_in_booth_51(syn: Synth) -> None:
    pairs = syn.anomaly("P4")["details"]["pairs"]
    assert len(pairs) == 25
    draft = syn.draft.set_index("epic_no", drop=False)
    final = syn.final.set_index("epic_no", drop=False)
    for pair in pairs:
        src, copy = draft.loc[pair["source_epic"]], final.loc[pair["copy_epic"]]
        assert src["part_no"] == 8 and copy["part_no"] == 51
        assert pair["copy_epic"] not in draft.index  # different EPIC, present only in the final roll
        assert (src["name"], src["relative_name"]) != (copy["name"], copy["relative_name"])
        assert _is_near_copy(src, copy)
    assert len(syn.added[syn.added["part_no"] == 51]) >= 25


def test_p5_booth_25_dead_removals_of_young_voters(syn: Synth) -> None:
    removed = syn.booth_removed(25)
    young_dead = removed[(syn.reason[removed.index] == "DEAD") & removed["age"].between(18, 30)]
    assert len(young_dead) >= 30
    elsewhere = syn.removed[(syn.removed["part_no"] != 25) & (syn.reason == "DEAD")]
    assert (elsewhere["age"] <= 30).sum() == 0  # normal booths record none, so P5 stands out


def test_p6_bad_ages_and_missing_asdd(syn: Synth) -> None:
    bad = syn.final[(syn.final["age"] < 18) | (syn.final["age"] > 110)]
    assert len(bad) == 6
    assert set(bad["part_no"]) == {3, 9}
    assert (bad["age"] > 110).any() and (bad["age"] < 18).any()
    missing = syn.removed[syn.reason.isna()]
    assert len(missing) == 8
    assert set(missing["part_no"]) == {3, 9}
    assert syn.anomaly("P6")["counts"] == {"final_age_out_of_range": 6, "removed_missing_from_asdd": 8}


def test_truth_lists_all_anomalies(syn: Synth) -> None:
    anomalies = syn.truth["anomalies"]
    assert [a["id"] for a in anomalies] == ["P1", "P2", "P3", "P4", "P5", "P6"]
    for a in anomalies:
        assert a["description"] and a["part_nos"] and a["counts"]
    assert syn.anomaly("P4")["part_nos"] == [8, 51]
    assert syn.anomaly("P1")["counts"]["removed"] == len(syn.booth_removed(17))


def test_demo_voters_exist_with_stated_status(syn: Synth) -> None:
    removed, present, added = (syn.demo[k] for k in ("removed", "present", "added"))
    assert (removed["name"], removed["relative_name"], removed["relation_type"]) == (
        "Sunita Devi", "Ramesh Kumar", "HUSBAND")
    assert (removed["part_no"], removed["age"], removed["gender"], removed["reason"]) == (17, 34, "F", "SHIFTED")
    in_draft, in_final = set(syn.draft["epic_no"]), set(syn.final["epic_no"])
    assert removed["epic_no"] in in_draft and removed["epic_no"] not in in_final
    assert syn.asdd.set_index("epic_no").loc[removed["epic_no"], "reason"] == "SHIFTED"
    assert present["epic_no"] in in_draft and present["epic_no"] in in_final
    assert added["epic_no"] not in in_draft and added["epic_no"] in in_final
    both = pd.concat([syn.draft, syn.final]).drop_duplicates("epic_no").set_index("epic_no")
    for voter in (removed, present, added):
        row = both.loc[voter["epic_no"]]
        assert (row["name"], int(row["age"]), int(row["part_no"])) == (voter["name"], voter["age"], voter["part_no"])
        assert (both["name"] == voter["name"]).sum() == 1  # unique name, so a name lookup is unambiguous


def test_no_blocked_words_in_text_outputs(syn: Synth) -> None:
    blocked = re.compile(r"fraud|illegal|rigging|ineligible|foreigner|infiltrator|wrongly deleted", re.I)
    for name in ("truth.json", "demo_voters.json", "asdd.csv"):
        assert not blocked.search((syn.out / name).read_text(encoding="utf-8"))

