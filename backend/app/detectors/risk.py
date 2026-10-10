"""Booth risk score: an IsolationForest anomaly score blended with the severity of the booth's flags.

The score ranks booths by how unusual they look so reviewers can decide where to look first. It is a
priority order for human verification, not a finding about any booth or voter.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.detectors.base import Flag
from app.detectors.config import THRESHOLDS
from app.engine import config as cfg

FEATURE_NAMES: tuple[str, ...] = (
    "deletion_rate", "shifted_share", "absent_share", "dead_share", "female_gap", "young_removed_gap",
    "addition_rate", "max_house_additions", "duplicate_pairs", "dq_count",
)


def feature_matrix(booth_df: pd.DataFrame, duplicate_pairs: pd.Series) -> pd.DataFrame:
    """One row per booth (same order as ``booth_df``) with the columns in ``FEATURE_NAMES``.

    ``duplicate_pairs`` maps part_no to its pair count; booths without an entry get 0.
    """
    mix = booth_df["reason_mix"]
    bands = booth_df["age_band_removed_share"]
    return pd.DataFrame({
        "deletion_rate": booth_df["deletion_rate"],
        "shifted_share": mix.map(lambda m: m["SHIFTED"]),
        "absent_share": mix.map(lambda m: m["ABSENT"]),
        "dead_share": mix.map(lambda m: m["DEAD"]),
        "female_gap": booth_df["female_removed_share"] - booth_df["female_share_draft"],
        "young_removed_gap": bands.map(lambda b: b[cfg.YOUNG_BAND]) - booth_df["young_share_draft"],
        "addition_rate": booth_df["addition_rate"],
        "max_house_additions": booth_df["max_house_additions"],
        "duplicate_pairs": booth_df["part_no"].map(duplicate_pairs).fillna(0),
        "dq_count": booth_df["dq_count"],
    }, index=booth_df.index).astype(float)


def isolation_scores(features: pd.DataFrame) -> np.ndarray:
    """Anomaly score in 0..1 per row (higher = more unusual), min-max scaled from decision_function."""
    if len(features) < 2:
        return np.zeros(len(features))
    t = THRESHOLDS["RISK"]
    forest = IsolationForest(n_estimators=t["n_estimators"], contamination="auto",
                             random_state=t["random_state"])
    forest.fit(features.to_numpy())
    raw = -forest.decision_function(features.to_numpy())  # decision_function: lower = more abnormal
    span = raw.max() - raw.min()
    return (raw - raw.min()) / span if span > 0 else np.zeros(len(raw))


def severity_component(flags: list[Flag], part_nos: pd.Series) -> pd.Series:
    """min(1, sum of severity weights / 2) per booth (0 for a booth without flags)."""
    t = THRESHOLDS["RISK"]
    totals: dict[int, float] = {}
    for flag in flags:
        totals[flag.part_no] = totals.get(flag.part_no, 0.0) + t["severity_points"][flag.severity.value]
    values = part_nos.map(lambda p: min(1.0, totals.get(int(p), 0.0) / t["severity_cap"]))
    return values.astype(float)


def score_booths(booth_df: pd.DataFrame, flags: list[Flag], duplicate_pairs: pd.Series) -> pd.DataFrame:
    """Return a copy of ``booth_df`` with ``risk_score`` (int 0..100) and ``flagged`` (bool) added.

    risk_score = round(100 * (0.6 * isolation + 0.4 * severity)); flagged = booth has at least one flag.
    """
    t = THRESHOLDS["RISK"]
    out = booth_df.copy()
    iso = isolation_scores(feature_matrix(out, duplicate_pairs))
    sev = severity_component(flags, out["part_no"]).to_numpy()
    out["risk_score"] = np.round(100 * (t["iso_weight"] * iso + t["severity_weight"] * sev)).astype("int64")
    flagged = {f.part_no for f in flags}
    out["flagged"] = out["part_no"].map(lambda p: int(p) in flagged).astype(bool)
    return out
