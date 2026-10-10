"""HOUSE_CLUSTER: many additions at one house number, or an unusually crowded house in the final roll."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.detectors.base import DetectorContext, DetectorType, Flag, Severity, make_flag, severity_for
from app.detectors.config import THRESHOLDS


def top_house(roll: pd.DataFrame) -> dict[int, tuple[str, int]]:
    """For each booth, the house_no with the most rows and that row count (ties: smallest house_no)."""
    if roll.empty:
        return {}
    sizes = roll.groupby(["part_no", "house_no"]).size().rename("n").reset_index()
    sizes = sizes.sort_values(["part_no", "n", "house_no"], ascending=[True, False, True], kind="stable")
    top = sizes.drop_duplicates("part_no")
    return {int(p): (str(h), int(n)) for p, h, n in zip(top["part_no"], top["house_no"], top["n"])}


class HouseClusterDetector:
    """One flag per booth at most.

    * Additions rule (checked first): max_house_additions >= 10 -> MEDIUM, HIGH from 30.
    * Crowding rule: max_house_voters >= max(15, p99 across booths) -> weaker signal, severity from
      THRESHOLDS (LOW), used only when the additions rule did not fire.
    ``details.house_no`` is the house behind the metric. House numbers are not personal data.
    """

    name = DetectorType.HOUSE_CLUSTER

    def detect(self, ctx: DetectorContext) -> list[Flag]:
        t = THRESHOLDS["HOUSE_CLUSTER"]
        booths = ctx.booth_df
        if booths.empty:
            return []
        added_top, final_top = top_house(ctx.result.added), top_house(ctx.final)
        cutoff = max(t["voters_floor"], float(np.percentile(booths["max_house_voters"], t["voters_percentile"])))
        add_base = float(booths["max_house_additions"].median())
        voters_base = float(booths["max_house_voters"].median())
        flags: list[Flag] = []
        for row in booths.to_dict("records"):
            part = row["part_no"]
            extra = {"max_house_voters": int(row["max_house_voters"])}
            if row["max_house_additions"] >= t["additions_min"]:
                house = added_top.get(part, ("", 0))[0]
                severity = severity_for(row["max_house_additions"], t["additions_high"])
                flags.append(make_flag(part, self.name, severity, "max_house_additions",
                                       row["max_house_additions"], add_base,
                                       {"kind": "HOUSE_ADDITIONS", "house_no": house, **extra}))
            elif row["max_house_voters"] >= cutoff:
                house = final_top.get(part, ("", 0))[0]
                flags.append(make_flag(part, self.name, Severity(t["voters_only_severity"]),
                                       "max_house_voters", row["max_house_voters"], voters_base,
                                       {"kind": "HOUSE_CROWDED", "house_no": house,
                                        "voters_cutoff": float(cutoff)}))
        return flags
