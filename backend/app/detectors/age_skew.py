"""AGE_SKEW: unusual age patterns among removals. Only age bands are analysed."""

from __future__ import annotations

from app.detectors.base import DetectorContext, DetectorType, Flag, make_flag, severity_for
from app.detectors.config import THRESHOLDS
from app.engine import config as cfg


class AgeSkewDetector:
    """Two kinds of flag, ``details.kind``:

    * DEAD_UNDER_40: many removals recorded with reason DEAD for voters under 40.
    * YOUNG_REMOVED: the 18-25 share among removed exceeds the booth's 18-25 draft share by a margin.
    """

    name = DetectorType.AGE_SKEW

    def detect(self, ctx: DetectorContext) -> list[Flag]:
        t = THRESHOLDS["AGE_SKEW"]
        dead_baseline = float(ctx.booth_df["dead_under_40"].median()) if len(ctx.booth_df) else 0.0
        flags: list[Flag] = []
        for row in ctx.booth_df.to_dict("records"):
            if row["dead_under_40"] >= t["dead_under_40_min"]:
                flags.append(make_flag(
                    row["part_no"], self.name, severity_for(row["dead_under_40"], t["dead_under_40_high"]),
                    "dead_under_40", row["dead_under_40"], dead_baseline,
                    {"kind": "DEAD_UNDER_40", "removed": int(row["removed"])}))
            if row["removed"] >= t["min_removed"]:
                young = float(row["age_band_removed_share"][cfg.YOUNG_BAND])
                gap = young - float(row["young_share_draft"])
                if gap >= t["young_gap_min"]:
                    flags.append(make_flag(
                        row["part_no"], self.name, severity_for(gap, t["young_gap_high"]),
                        "young_removed_share", young, row["young_share_draft"],
                        {"kind": "YOUNG_REMOVED", "gap": round(gap, 4), "removed": int(row["removed"])}))
        return flags
