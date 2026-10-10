"""Constants shared by the comparison and aggregation engine (see contracts/CONTRACT.md)."""

from __future__ import annotations

import math

# Enums from CONTRACT.md 6.1.
REASONS: tuple[str, ...] = ("ABSENT", "SHIFTED", "DEAD", "DUPLICATE")
GENDERS: tuple[str, ...] = ("M", "F", "O")

# CSV schemas from CONTRACT.md 6.2.
ROLL_COLUMNS: tuple[str, ...] = (
    "epic_no", "ac_no", "part_no", "serial_no", "name",
    "relative_name", "relation_type", "house_no", "age", "gender",
)
ASDD_COLUMNS: tuple[str, ...] = ("epic_no", "part_no", "reason", "remark")
ROLL_INT_COLUMNS: tuple[str, ...] = ("ac_no", "part_no", "serial_no", "age")

# Fields whose difference makes a voter "modified" (same epic_no in draft and final).
COMPARE_FIELDS: tuple[str, ...] = ("name", "relative_name", "house_no", "age", "gender", "part_no")

# Age bands: label -> [lower, upper) in years. The last band is open-ended, so "80+" means 81 and over.
AGE_BAND_LABELS: tuple[str, ...] = ("18-25", "26-35", "36-45", "46-60", "61-80", "80+")
AGE_BAND_EDGES: tuple[float, ...] = (18, 26, 36, 46, 61, 81, math.inf)
YOUNG_BAND = "18-25"  # the band behind young_share_draft

# Plausible age range for a roll entry; ages outside it are reported as a data-quality issue.
MIN_VALID_AGE = 18
MAX_VALID_AGE = 110

# A removal recorded as DEAD for a voter younger than this is counted in dead_under_40.
DEAD_YOUNG_AGE = 40

# data_quality issue types.
REMOVED_WITHOUT_ASDD = "REMOVED_WITHOUT_ASDD"
ASDD_NOT_IN_DRAFT = "ASDD_NOT_IN_DRAFT"
AGE_OUT_OF_RANGE = "AGE_OUT_OF_RANGE"
DUPLICATE_EPIC = "DUPLICATE_EPIC"
DQ_COLUMNS: tuple[str, ...] = ("part_no", "issue_type", "epic_no", "detail")
