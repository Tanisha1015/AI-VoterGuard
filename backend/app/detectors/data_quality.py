"""DATA_QUALITY: a booth with several data-quality issues (missing ASDD rows, odd ages, repeated EPICs)."""

from __future__ import annotations

from app.detectors.base import DetectorContext, DetectorType, Flag, Severity, make_flag, severity_for
from app.detectors.config import THRESHOLDS


class DataQualityDetector:
    """Fires when dq_count reaches the threshold; details hold the count per issue_type."""

    name = DetectorType.DATA_QUALITY

    def detect(self, ctx: DetectorContext) -> list[Flag]:
        t = THRESHOLDS["DATA_QUALITY"]
        booths = ctx.booth_df
        if booths.empty:
            return []
        baseline = float(booths["dq_count"].median())
        issues: dict[int, dict[str, int]] = {}
        for (part_no, issue_type), n in ctx.result.data_quality.groupby(["part_no", "issue_type"]).size().items():
            issues.setdefault(int(part_no), {})[str(issue_type)] = int(n)
        flags: list[Flag] = []
        for row in booths.to_dict("records"):
            if row["dq_count"] >= t["count_min"]:
                severity = severity_for(row["dq_count"], t["count_high"], Severity.MEDIUM)
                flags.append(make_flag(row["part_no"], self.name, severity, "dq_count", row["dq_count"],
                                       baseline, {"issue_counts": issues.get(int(row["part_no"]), {})}))
        return flags
