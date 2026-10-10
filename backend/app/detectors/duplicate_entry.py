"""DUPLICATE_ENTRY: near-identical records in different booths of the final roll.

Records are blocked by (gender, age bucket, first letters of the normalised name) so only small groups
are compared; there is never an all-pairs comparison over the whole roll. Only name, relative name, gender
and age are used. A pair is a pattern worth verifying, not a conclusion about either voter.
"""

from __future__ import annotations

import re
from itertools import combinations

import pandas as pd
from rapidfuzz import fuzz

from app.detectors.base import DetectorContext, DetectorType, Flag, make_flag, severity_for
from app.detectors.config import THRESHOLDS

PAIR_COLUMNS: tuple[str, str] = ("part_a", "part_b")
_NON_LETTERS = re.compile(r"[^a-z ]+")


def normalise_name(name: str) -> str:
    """Lower-case, drop everything except letters and spaces, and collapse repeated spaces."""
    return " ".join(_NON_LETTERS.sub(" ", str(name).lower()).split())


def _block_keys(final: pd.DataFrame) -> pd.DataFrame:
    """Copy of the columns needed for matching plus a ``block`` key; the roll itself is not modified."""
    t = THRESHOLDS["DUPLICATE_ENTRY"]
    out = pd.DataFrame({
        "epic_no": final["epic_no"].to_numpy(),
        "part_no": final["part_no"].to_numpy(),
        "age": final["age"].to_numpy(),
        "name": final["name"].map(normalise_name).to_numpy(),
        "relative_name": final["relative_name"].map(normalise_name).to_numpy(),
    })
    prefix = out["name"].str.replace(" ", "", regex=False).str[: t["name_prefix_len"]]
    bucket = (out["age"] // t["age_bucket_width"]).astype(str)
    out["block"] = final["gender"].to_numpy() + "|" + bucket.to_numpy() + "|" + prefix.to_numpy()
    return out


def _is_pair(a: tuple, b: tuple) -> bool:
    """Compare two (epic, part, age, name, relative_name) records against the pair rules."""
    t = THRESHOLDS["DUPLICATE_ENTRY"]
    if a[1] == b[1] or a[0] == b[0] or abs(a[2] - b[2]) > t["max_age_diff"]:
        return False
    return (fuzz.token_set_ratio(a[3], b[3]) >= t["name_score_min"]
            and fuzz.token_set_ratio(a[4], b[4]) >= t["name_score_min"])


def find_duplicate_pairs(final: pd.DataFrame) -> pd.DataFrame:
    """Return one row (part_a, part_b) per matching pair of final-roll records in different booths."""
    keyed = _block_keys(final)
    sizes = keyed["block"].map(keyed["block"].value_counts())
    pairs: list[tuple[int, int]] = []
    for _, block in keyed[sizes > 1].groupby("block", sort=True):
        records = list(zip(block["epic_no"], block["part_no"], block["age"], block["name"],
                           block["relative_name"]))
        pairs.extend((int(a[1]), int(b[1])) for a, b in combinations(records, 2) if _is_pair(a, b))
    return pd.DataFrame(pairs, columns=list(PAIR_COLUMNS), dtype="int64")


def pairs_per_booth(pairs: pd.DataFrame) -> pd.Series:
    """Pairs per booth, counting each pair for both of its booths (index: part_no)."""
    both = pd.concat([pairs["part_a"], pairs["part_b"]])
    return both.value_counts().sort_index().astype("int64")


def partner_booths(pairs: pd.DataFrame, part_no: int) -> dict[str, int]:
    """For one booth, how many pairs it has with each other booth (keys are strings for JSON)."""
    mine = pd.concat([pairs.loc[pairs["part_a"] == part_no, "part_b"],
                      pairs.loc[pairs["part_b"] == part_no, "part_a"]])
    counts = mine.value_counts().sort_index()
    return {str(int(k)): int(v) for k, v in counts.items()}


class DuplicateEntryDetector:
    """Fires when a booth has enough near-identical record pairs with other booths."""

    name = DetectorType.DUPLICATE_ENTRY

    def detect(self, ctx: DetectorContext) -> list[Flag]:
        t = THRESHOLDS["DUPLICATE_ENTRY"]
        pairs = ctx.duplicate_pairs if ctx.duplicate_pairs is not None else find_duplicate_pairs(ctx.final)
        counts = pairs_per_booth(pairs)
        baseline = float(counts.reindex(ctx.booth_df["part_no"], fill_value=0).median()) if len(ctx.booth_df) else 0.0
        flags: list[Flag] = []
        for part_no, n in counts.items():
            if n >= t["pairs_min"]:
                flags.append(make_flag(part_no, self.name, severity_for(n, t["pairs_high"]), "duplicate_pairs",
                                       n, baseline, {"partner_booths": partner_booths(pairs, int(part_no))}))
        return flags
