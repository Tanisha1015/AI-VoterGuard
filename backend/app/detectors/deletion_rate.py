"""DELETION_RATE: booths whose removal rate is far above the constituency median (robust z-score)."""

from __future__ import annotations

from app.detectors.base import DetectorContext, DetectorType, Flag, Severity, make_flag
from app.detectors.config import THRESHOLDS


class DeletionRateDetector:
    """Fires when robust z = (rate - median) / (1.4826 * MAD) is high and enough voters were removed.

    The median and MAD come from ``ctx.baseline``. When the MAD is 0 there is no spread to measure
    against, so the detector stays quiet rather than dividing by zero.
    """

    name = DetectorType.DELETION_RATE

    def detect(self, ctx: DetectorContext) -> list[Flag]:
        t = THRESHOLDS["DELETION_RATE"]
        median = float(ctx.baseline["deletion_rate"])
        scale = t["mad_scale"] * float(ctx.baseline["deletion_rate_mad"])
        if scale <= 0:
            return []
        flags: list[Flag] = []
        for row in ctx.booth_df.to_dict("records"):
            z = (row["deletion_rate"] - median) / scale
            if z >= t["z_min"] and row["removed"] >= t["min_removed"]:
                severity = Severity.HIGH if z >= t["z_high"] else Severity.MEDIUM
                details = {"robust_z": round(float(z), 2), "removed": int(row["removed"]),
                           "draft_count": int(row["draft_count"])}
                flags.append(make_flag(row["part_no"], self.name, severity, "deletion_rate",
                                       row["deletion_rate"], median, details))
        return flags
