"""Booth-level aggregation of a CompareResult, plus the constituency baseline.

Pure, vectorised Pandas: no file access and no loops over voter rows. All figures are descriptive
counts and shares computed deterministically; they highlight patterns that may be worth verifying
and say nothing about any individual voter. Only gender and age bands are analysed.

Conventions:
* A booth row exists for every part_no found in the draft or the final roll.
* Rates and shares whose denominator is zero are 0.0.
* removed counts belong to the voter's draft booth; added counts to the final booth.
* reason_mix, gender_removed and age_band_removed_share are shares (gender: counts) of ``removed``.
  Removals with no ASDD reason (or an age outside every band) are in ``removed`` but in none of the
  dict entries, so a mix can add up to less than 1.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.engine import config as cfg
from app.engine.compare import CompareResult


def _count_table(
    part_no: pd.Series, labels: pd.Series, index: pd.Index, columns: tuple[str, ...]
) -> pd.DataFrame:
    """Count rows per (part_no, label); every booth and every label is present, missing ones are 0."""
    table = pd.crosstab(part_no, labels.astype(object))
    return table.reindex(index=index, columns=list(columns), fill_value=0).astype("int64")


def _shares(counts: pd.DataFrame, totals: pd.Series) -> pd.DataFrame:
    """Divide each row of ``counts`` by its booth total; a zero total gives zeros."""
    return counts.div(totals.where(totals > 0), axis=0).fillna(0.0)


def _as_dicts(table: pd.DataFrame) -> pd.Series:
    """Turn each row of a wide table into a {column: value} dict, keeping the booth index."""
    return pd.Series(table.to_dict("records"), index=table.index, dtype=object)


def _per_booth(values: pd.Series, index: pd.Index) -> pd.Series:
    """Align a part_no-indexed count series to every booth (0 where a booth has no rows)."""
    return values.reindex(index, fill_value=0).astype("int64")


def _max_house(roll: pd.DataFrame, index: pd.Index) -> pd.Series:
    """Largest number of rows sharing one house_no within each booth (0 for a booth with no rows)."""
    sizes = roll.groupby(["part_no", "house_no"]).size()
    return _per_booth(sizes.groupby(level="part_no").max(), index)


def _age_band(age: pd.Series) -> pd.Series:
    """Label ages with the contract age bands; ages below 18 get no band (NaN)."""
    return pd.cut(age, bins=list(cfg.AGE_BAND_EDGES), labels=list(cfg.AGE_BAND_LABELS), right=False)


def aggregate_booths(result: CompareResult, draft: pd.DataFrame, final: pd.DataFrame) -> pd.DataFrame:
    """Return one row per part_no summarising removals, additions and data quality.

    Columns: part_no, draft_count, final_count, removed, added, deletion_rate (removed / draft_count),
    reason_mix, gender_removed, female_removed_share, female_share_draft, age_band_removed_share,
    young_share_draft (draft voters aged 18-25), addition_rate (added / draft_count),
    max_house_additions, max_house_voters, dead_under_40 and dq_count. Rows are sorted by part_no.
    """
    index = pd.Index(sorted(set(draft["part_no"]) | set(final["part_no"])), name="part_no", dtype="int64")
    rem, add = result.removed, result.added

    draft_count = _per_booth(draft.groupby("part_no").size(), index)
    final_count = _per_booth(final.groupby("part_no").size(), index)
    removed = _per_booth(rem.groupby("part_no").size(), index)
    added = _per_booth(add.groupby("part_no").size(), index)
    base = draft_count.where(draft_count > 0)  # NaN for a booth with no draft voters -> rate 0.0

    reasons = _count_table(rem["part_no"], rem["reason"], index, cfg.REASONS)
    genders = _count_table(rem["part_no"], rem["gender"], index, cfg.GENDERS)
    bands = _count_table(rem["part_no"], _age_band(rem["age"]), index, cfg.AGE_BAND_LABELS)
    draft_genders = _count_table(draft["part_no"], draft["gender"], index, cfg.GENDERS)
    draft_bands = _count_table(draft["part_no"], _age_band(draft["age"]), index, cfg.AGE_BAND_LABELS)
    dead_young = rem[(rem["reason"] == "DEAD") & (rem["age"] < cfg.DEAD_YOUNG_AGE)]

    out = pd.DataFrame({
        "part_no": index.to_numpy(),
        "draft_count": draft_count,
        "final_count": final_count,
        "removed": removed,
        "added": added,
    }, index=index)
    out["deletion_rate"] = (removed / base).fillna(0.0)
    out["reason_mix"] = _as_dicts(_shares(reasons, removed))
    out["gender_removed"] = _as_dicts(genders)
    out["female_removed_share"] = _shares(genders, removed)["F"]
    out["female_share_draft"] = (draft_genders["F"] / base).fillna(0.0)
    out["age_band_removed_share"] = _as_dicts(_shares(bands, removed))
    out["young_share_draft"] = (draft_bands[cfg.YOUNG_BAND] / base).fillna(0.0)
    out["addition_rate"] = (added / base).fillna(0.0)
    out["max_house_additions"] = _max_house(add, index)
    out["max_house_voters"] = _max_house(final, index)
    out["dead_under_40"] = _per_booth(dead_young.groupby("part_no").size(), index)
    out["dq_count"] = _per_booth(result.data_quality.groupby("part_no").size(), index)
    return out.reset_index(drop=True)


def _median_abs_deviation(values: pd.Series) -> float:
    """Raw (unscaled) median absolute deviation: median(|x - median(x)|)."""
    return float((values - values.median()).abs().median())


def _share(part: float, total: int) -> float:
    """part / total, or 0.0 when total is 0."""
    return float(part / total) if total > 0 else 0.0


def constituency_baseline(booth_df: pd.DataFrame) -> dict[str, Any]:
    """Summarise what is typical across booths, to compare each booth against.

    Returns deletion_rate (median of booth deletion rates), deletion_rate_mad (raw median absolute
    deviation of those rates), reason_mix (reason -> share of all removals in the constituency) and
    female_share_removed (female share of all removals). An empty ``booth_df`` gives zeros.
    """
    total = int(booth_df["removed"].sum())
    rates = booth_df["deletion_rate"]
    mix = pd.DataFrame(list(booth_df["reason_mix"]), columns=list(cfg.REASONS), index=booth_df.index)
    reason_counts = mix.mul(booth_df["removed"], axis=0).sum()
    female = sum(g["F"] for g in booth_df["gender_removed"])
    return {
        "deletion_rate": float(rates.median()) if not rates.empty else 0.0,
        "deletion_rate_mad": _median_abs_deviation(rates) if not rates.empty else 0.0,
        "reason_mix": {r: _share(reason_counts[r], total) for r in cfg.REASONS},
        "female_share_removed": _share(female, total),
    }

