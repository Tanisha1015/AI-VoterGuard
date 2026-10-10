"""All detector and risk-score thresholds in one place, so they can be exported and reviewed.

Every value here only decides which booth-level patterns are worth a human look; none of them
decides anything about a voter. Detector keys match the ``detector`` enum in contracts/CONTRACT.md.
"""

from __future__ import annotations

from typing import Any

THRESHOLDS: dict[str, dict[str, Any]] = {
    # Robust z = (rate - median) / (mad_scale * MAD) across booths.
    "DELETION_RATE": {
        "z_min": 3.5, "z_high": 6.0, "min_removed": 15, "mad_scale": 1.4826,
    },
    # Share of the largest removal reason within a booth.
    "REASON_DOMINANCE": {
        "share_min": 0.80, "share_high": 0.90, "min_removed": 20,
    },
    # gap = share of a gender among removed - share of that gender in the booth's draft roll.
    "GENDER_SKEW": {
        "gap_min": 0.15, "gap_high": 0.25, "min_removed": 30,
    },
    # DEAD_UNDER_40 and YOUNG_REMOVED (18-25 share among removed vs the booth's draft share).
    "AGE_SKEW": {
        "dead_under_40_min": 10, "dead_under_40_high": 25,
        "young_gap_min": 0.15, "young_gap_high": 0.30, "min_removed": 30,
    },
    # Many additions at one house number, or an unusually crowded house in the final roll.
    "HOUSE_CLUSTER": {
        "additions_min": 10, "additions_high": 30,
        "voters_floor": 15, "voters_percentile": 99, "voters_only_severity": "LOW",
    },
    # Near-identical records in different booths of the final roll.
    "DUPLICATE_ENTRY": {
        "name_score_min": 92, "age_bucket_width": 3, "max_age_diff": 1, "name_prefix_len": 3,
        "pairs_min": 5, "pairs_high": 15,
    },
    # Count of data-quality issues recorded for the booth.
    "DATA_QUALITY": {
        "count_min": 3, "count_high": 8,
    },
    # Booth risk score = round(100 * (iso_weight * isolation + severity_weight * severity)).
    "RISK": {
        "n_estimators": 200, "random_state": 42,
        "iso_weight": 0.6, "severity_weight": 0.4, "severity_cap": 2.0,
        "severity_points": {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 1.0},
    },
}
