"""REASON_DOMINANCE: one ASDD reason accounts for almost all removals in a booth."""

from __future__ import annotations

from app.detectors.base import DetectorContext, DetectorType, Flag, Severity, make_flag, severity_for
from app.detectors.config import THRESHOLDS
from app.engine import config as cfg


class ReasonDominanceDetector:
    """Fires when the largest-share reason has a high share and enough voters were removed."""

    name = DetectorType.REASON_DOMINANCE

    def detect(self, ctx: DetectorContext) -> list[Flag]:
        t = THRESHOLDS["REASON_DOMINANCE"]
        constituency_mix = ctx.baseline["reason_mix"]
        flags: list[Flag] = []
        for row in ctx.booth_df.to_dict("records"):
            if row["removed"] < t["min_removed"]:
                continue
            mix = row["reason_mix"]
            reason = max(cfg.REASONS, key=lambda r: mix[r])  # ties resolve in contract order
            share = float(mix[reason])
            if share >= t["share_min"]:
                severity = severity_for(share, t["share_high"])
                details = {"reason": reason, "removed": int(row["removed"])}
                flags.append(make_flag(row["part_no"], self.name, severity, "reason_share",
                                       share, constituency_mix[reason], details))
        return flags
