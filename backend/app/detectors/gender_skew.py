"""GENDER_SKEW: one gender is over-represented among removals compared with the booth's draft roll."""

from __future__ import annotations

import pandas as pd

from app.detectors.base import DetectorContext, DetectorType, Flag, make_flag, severity_for
from app.detectors.config import THRESHOLDS

GENDERS_CHECKED: tuple[str, ...] = ("F", "M")


def draft_gender_shares(draft: pd.DataFrame) -> pd.DataFrame:
    """Share of each gender among a booth's draft voters (rows: part_no, columns: gender)."""
    return pd.crosstab(draft["part_no"], draft["gender"], normalize="index")


class GenderSkewDetector:
    """Fires when gap = removed share of gender g - draft share of g is large and removals are many."""

    name = DetectorType.GENDER_SKEW

    def detect(self, ctx: DetectorContext) -> list[Flag]:
        t = THRESHOLDS["GENDER_SKEW"]
        shares = draft_gender_shares(ctx.draft)
        flags: list[Flag] = []
        for row in ctx.booth_df.to_dict("records"):
            if row["removed"] < t["min_removed"] or row["part_no"] not in shares.index:
                continue
            for gender in GENDERS_CHECKED:
                draft_share = float(shares.at[row["part_no"], gender]) if gender in shares.columns else 0.0
                removed_share = row["gender_removed"][gender] / row["removed"]
                gap = removed_share - draft_share
                if gap >= t["gap_min"]:
                    details = {"gender": gender, "gap": round(float(gap), 4), "removed": int(row["removed"])}
                    flags.append(make_flag(row["part_no"], self.name, severity_for(gap, t["gap_high"]),
                                           f"{gender.lower()}_removed_share", removed_share, draft_share,
                                           details))
        return flags
