"""Run every detector, number the flags and score the booths."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pandas as pd

from app.detectors.age_skew import AgeSkewDetector
from app.detectors.base import Detector, DetectorContext, Flag
from app.detectors.data_quality import DataQualityDetector
from app.detectors.deletion_rate import DeletionRateDetector
from app.detectors.duplicate_entry import DuplicateEntryDetector, find_duplicate_pairs, pairs_per_booth
from app.detectors.gender_skew import GenderSkewDetector
from app.detectors.house_cluster import HouseClusterDetector
from app.detectors.reason_dominance import ReasonDominanceDetector
from app.detectors.risk import score_booths
from app.engine.compare import CompareResult

DETECTORS: tuple[Detector, ...] = (
    DeletionRateDetector(), ReasonDominanceDetector(), GenderSkewDetector(), AgeSkewDetector(),
    HouseClusterDetector(), DuplicateEntryDetector(), DataQualityDetector(),
)


def number_flags(flags: list[Flag]) -> list[Flag]:
    """Sort flags by booth (detector order is kept within a booth) and set flag_id = f_{part_no}_{n}."""
    ordered = sorted(flags, key=lambda f: f.part_no)  # sorted() is stable
    counters: dict[int, int] = {}
    numbered: list[Flag] = []
    for flag in ordered:
        counters[flag.part_no] = counters.get(flag.part_no, 0) + 1
        numbered.append(replace(flag, flag_id=f"f_{flag.part_no}_{counters[flag.part_no]}"))
    return numbered


def run_all(
    booth_df: pd.DataFrame,
    draft: pd.DataFrame,
    final: pd.DataFrame,
    result: CompareResult,
    baseline: dict[str, Any],
) -> tuple[list[Flag], pd.DataFrame]:
    """Run all seven detectors; return (flags, booth_df with risk_score and flagged).

    Inputs are not modified. The expensive duplicate search runs once and is shared with the risk score.
    """
    pairs = find_duplicate_pairs(final)
    ctx = DetectorContext(booth_df, draft, final, result, baseline, pairs)
    flags = number_flags([flag for detector in DETECTORS for flag in detector.detect(ctx)])
    return flags, score_booths(booth_df, flags, pairs_per_booth(pairs))
