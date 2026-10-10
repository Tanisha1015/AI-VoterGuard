"""Planted anomalies P1-P6 for the synthetic roll, plus the truth entries that describe them.

Everything here is synthetic test data. The wording is deliberately neutral: the anomalies are
*unusual patterns worth verifying*, used to check that the detectors can surface them.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.synth.names import Row, draw_ages, make_people, spelling_variant

P1_BOOTH, P2_BOOTH, P3_BOOTH, P5_BOOTH = 17, 42, 33, 25
P4_SOURCE_BOOTH, P4_TARGET_BOOTH = 8, 51
P6_BOOTHS = (3, 9)
P3_HOUSE = "12-B"
P3_COUNT, P4_COUNT, P5_COUNT = 45, 25, 30
P6_BAD_AGES_PER_BOOTH, P6_MISSING_ASDD_PER_BOOTH = 3, 4

REASONS = ("ABSENT", "SHIFTED", "DEAD", "DUPLICATE")
NORMAL_MIX = {"DEAD": 0.35, "SHIFTED": 0.40, "ABSENT": 0.15, "DUPLICATE": 0.10}


@dataclass
class Booth:
    """Mutable state for one booth while the rolls are being built."""

    part_no: int
    female_share: float
    draft: list[Row]
    removed: dict[int, str] = field(default_factory=dict)  # draft index -> reason
    additions: list[Row] = field(default_factory=list)  # appear only in the final roll
    final: list[Row] = field(default_factory=list)  # survivors first, then additions
    missing_asdd: set[int] = field(default_factory=set)  # removed draft indexes with no asdd row


@dataclass(frozen=True)
class RemovalPlan:
    """How many voters to remove from a booth, with which reasons and gender mix."""

    rate: float
    reason_mix: dict[str, float]
    female_share: float | None  # None = proportional to the booth's own gender mix


def plan_for(part_no: int, rng: np.random.Generator) -> RemovalPlan:
    """Return the removal plan for a booth (P1 and P2 are planted; all others are normal)."""
    if part_no == P1_BOOTH:
        return RemovalPlan(0.22, {"SHIFTED": 0.82, "ABSENT": 0.10, "DEAD": 0.05, "DUPLICATE": 0.03}, 0.71)
    if part_no == P2_BOOTH:
        return RemovalPlan(0.14, {"ABSENT": 0.90, "SHIFTED": 0.06, "DEAD": 0.03, "DUPLICATE": 0.01}, None)
    raw = {r: NORMAL_MIX[r] * float(rng.uniform(0.85, 1.15)) for r in REASONS}
    total = sum(raw.values())
    return RemovalPlan(float(rng.uniform(0.03, 0.06)), {r: v / total for r, v in raw.items()}, None)


def sanitize_houses(booth: Booth) -> None:
    """Keep the P3 house number out of booth 33's ordinary households and additions."""
    if booth.part_no != P3_BOOTH:
        return
    for row in booth.draft + booth.additions:
        if row["house_no"] == P3_HOUSE:
            row["house_no"] = "12-C"


def plant_p3(booth: Booth, rng: np.random.Generator, epics: Iterator[str], surnames: tuple[str, ...]) -> dict[str, Any]:
    """P3: 45 added voters (varied names and ages) sharing one house number in booth 33."""
    sur = [surnames[int(i)] for i in rng.integers(0, len(surnames), P3_COUNT)]
    rows = make_people(rng, epics, booth.part_no, draw_ages(rng, P3_COUNT), booth.female_share,
                       [P3_HOUSE] * P3_COUNT, sur)
    booth.additions.extend(rows)
    return {
        "id": "P3", "part_nos": [P3_BOOTH],
        "description": f"Unusual cluster: {P3_COUNT} added voters share house_no \"{P3_HOUSE}\" in one booth; "
                       "worth a field check.",
        "counts": {"added_same_house": P3_COUNT},
        "details": {"house_no": P3_HOUSE},
    }


def plant_p4(booths: dict[int, Booth], rng: np.random.Generator, epics: Iterator[str]) -> dict[str, Any]:
    """P4: 25 final-roll records in booth 51 that are near-copies of booth 8 draft voters."""
    src, dst = booths[P4_SOURCE_BOOTH], booths[P4_TARGET_BOOTH]
    survivors = [i for i in range(len(src.draft)) if i not in src.removed]
    pairs: list[dict[str, str]] = []
    for pick in rng.choice(survivors, size=P4_COUNT, replace=False):
        base = src.draft[int(pick)]
        copy: Row = dict(base)
        copy.update({
            "epic_no": next(epics), "part_no": P4_TARGET_BOOTH, "serial_no": 0,
            "name": spelling_variant(base["name"], rng),
            "relative_name": spelling_variant(base["relative_name"], rng),
            "age": int(min(95, max(18, base["age"] + int(rng.integers(-1, 2))))),
        })
        dst.additions.append(copy)
        pairs.append({"source_epic": base["epic_no"], "copy_epic": copy["epic_no"]})
    return {
        "id": "P4", "part_nos": [P4_SOURCE_BOOTH, P4_TARGET_BOOTH],
        "description": "Possible repeated entries: records in the target booth's final roll closely resemble "
                       "voters in the source booth (spelling variants, same gender, age within 1); worth verifying.",
        "counts": {"copied_records": P4_COUNT},
        "details": {"source_part_no": P4_SOURCE_BOOTH, "target_part_no": P4_TARGET_BOOTH, "pairs": pairs},
    }


def plant_p5(booth: Booth, rng: np.random.Generator) -> dict[str, Any]:
    """P5: 30 extra removals in booth 25 with reason DEAD where the voter's age is 18-30."""
    young = [i for i, r in enumerate(booth.draft) if r["age"] <= 30 and i not in booth.removed]
    for pick in rng.choice(young, size=P5_COUNT, replace=False):
        booth.removed[int(pick)] = "DEAD"
    return {
        "id": "P5", "part_nos": [P5_BOOTH],
        "description": "Unusual age pattern: removals recorded with reason DEAD for voters aged 18-30; "
                       "worth verifying against source records.",
        "counts": {"dead_removals_age_18_30": P5_COUNT},
    }


def plant_p6(booths: dict[int, Booth], rng: np.random.Generator) -> dict[str, Any]:
    """P6: out-of-range ages in the final roll and removed voters missing from asdd (booths 3 and 9).

    Must run after each booth's final roll has been built.
    """
    bad: list[dict[str, Any]] = []
    missing: list[str] = []
    for part in P6_BOOTHS:
        booth = booths[part]
        survivors = len(booth.final) - len(booth.additions)
        for pick in rng.choice(survivors, size=P6_BAD_AGES_PER_BOOTH, replace=False):
            row = booth.final[int(pick)]
            old = row["age"]
            row["age"] = int(rng.integers(112, 131)) if len(bad) % 3 == 2 else int(rng.integers(5, 18))
            bad.append({"epic_no": row["epic_no"], "part_no": part, "draft_age": old, "final_age": row["age"]})
        removed_ids = sorted(booth.removed)
        for pick in rng.choice(len(removed_ids), size=P6_MISSING_ASDD_PER_BOOTH, replace=False):
            idx = removed_ids[int(pick)]
            booth.missing_asdd.add(idx)
            missing.append(booth.draft[idx]["epic_no"])
    return {
        "id": "P6", "part_nos": list(P6_BOOTHS),
        "description": "Data-quality issues: final-roll records with age under 18 or over 110, and removed voters "
                       "with no matching row in asdd.csv; worth verifying against source records.",
        "counts": {"final_age_out_of_range": len(bad), "removed_missing_from_asdd": len(missing)},
        "details": {"age_records": bad, "missing_asdd_epics": missing},
    }


def removal_truth(booth: Booth, anomaly_id: str, description: str) -> dict[str, Any]:
    """Describe a planted removal pattern (P1 or P2) using the booth's actual counts."""
    reasons = list(booth.removed.values())
    female = sum(1 for i in booth.removed if booth.draft[i]["gender"] == "F")
    return {
        "id": anomaly_id, "part_nos": [booth.part_no], "description": description,
        "counts": {
            "draft_count": len(booth.draft), "removed": len(reasons),
            "removal_rate": round(len(reasons) / len(booth.draft), 4),
            **{reason.lower(): reasons.count(reason) for reason in REASONS},
            "female_removed": female,
        },
    }

