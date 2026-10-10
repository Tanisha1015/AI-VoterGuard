"""Compare a draft roll with a final roll and the ASDD (absent/shifted/dead/duplicate) list.

``load_rolls`` is the only function here that reads files. ``compare`` and the helpers below it are
pure: DataFrames in, DataFrames out, vectorised, inputs never modified. Everything computed here is
deterministic; the output only describes differences and data-quality issues that are worth
verifying, and never decides anything about any voter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from app.engine import config as cfg


@dataclass(frozen=True)
class CompareResult:
    """Outcome of comparing draft, final and ASDD.

    added: final rows whose epic_no is not in the draft.
    removed: draft rows whose epic_no is not in the final, plus a ``reason`` column taken from the
        ASDD (null when the ASDD has no record for that epic_no).
    modified: voters present in both rolls with a different value in any of
        ``config.COMPARE_FIELDS``. Columns: epic_no, part_no (the draft booth), ``<field>_draft`` and
        ``<field>_final`` for every compared field, and changed_fields (list of field names).
    data_quality: one row per issue with columns part_no, issue_type, epic_no, detail.
    """

    added: pd.DataFrame
    removed: pd.DataFrame
    modified: pd.DataFrame
    data_quality: pd.DataFrame


# --------------------------------------------------------------------------- loading


def _read_csv(path: str | Path, label: str, columns: tuple[str, ...]) -> pd.DataFrame:
    """Read a CSV as text (no NA guessing) and check that every required column is present."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label}: missing required column(s) {missing}; found columns {list(df.columns)}"
        )
    return df[list(columns)].copy()


def _to_int_columns(df: pd.DataFrame, label: str, columns: tuple[str, ...]) -> pd.DataFrame:
    """Convert text columns to int64, raising a clear ValueError on the first non-integer value."""
    for col in columns:
        numbers = pd.to_numeric(df[col], errors="coerce")
        bad = numbers.isna() | (numbers % 1 != 0)
        if bad.any():
            first = int(np.flatnonzero(bad.to_numpy())[0])
            raise ValueError(
                f"{label}: column '{col}' must contain whole numbers; "
                f"found {df[col].iloc[first]!r} at data row {first + 1}"
            )
        df[col] = numbers.astype("int64")
    return df


def _check_values(df: pd.DataFrame, label: str, column: str, allowed: tuple[str, ...]) -> None:
    """Raise ValueError if ``column`` holds any value outside ``allowed``."""
    unknown = sorted(set(df.loc[~df[column].isin(allowed), column]))
    if unknown:
        raise ValueError(f"{label}: unknown {column} value(s) {unknown}; allowed values are {list(allowed)}")


def _load_roll(path: str | Path, label: str) -> pd.DataFrame:
    """Load and validate one roll CSV (draft or final)."""
    df = _read_csv(path, label, cfg.ROLL_COLUMNS)
    df = _to_int_columns(df, label, cfg.ROLL_INT_COLUMNS)
    _check_values(df, label, "gender", cfg.GENDERS)
    return df


def load_rolls(
    draft_path: str | Path, final_path: str | Path, asdd_path: str | Path
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load draft, final and ASDD CSVs into validated DataFrames.

    Roll columns are epic_no, ac_no, part_no, serial_no, name, relative_name, relation_type,
    house_no, age, gender (ints for ac_no, part_no, serial_no, age; everything else text, so house
    numbers like "12-B" or "007" are never altered). ASDD columns are epic_no, part_no (int), reason,
    remark.

    Raises:
        ValueError: a required column is missing, a numeric column holds a non-integer, a gender is
            not M/F/O, or an ASDD reason is not one of ABSENT, SHIFTED, DEAD, DUPLICATE.
    """
    draft = _load_roll(draft_path, "draft roll")
    final = _load_roll(final_path, "final roll")
    asdd = _read_csv(asdd_path, "asdd", cfg.ASDD_COLUMNS)
    asdd = _to_int_columns(asdd, "asdd", ("part_no",))
    _check_values(asdd, "asdd", "reason", cfg.REASONS)
    return draft, final, asdd


# --------------------------------------------------------------------------- comparison


def _find_removed(draft: pd.DataFrame, final: pd.DataFrame, asdd: pd.DataFrame) -> pd.DataFrame:
    """Draft rows missing from the final roll, with the ASDD reason (null when there is no record)."""
    removed = draft[~draft["epic_no"].isin(final["epic_no"])].copy()
    reason_by_epic = asdd.drop_duplicates("epic_no").set_index("epic_no")["reason"]
    removed["reason"] = removed["epic_no"].map(reason_by_epic)
    return removed.reset_index(drop=True)


def _find_modified(draft: pd.DataFrame, final: pd.DataFrame) -> pd.DataFrame:
    """Voters in both rolls whose compared fields differ, with the list of changed field names."""
    cols = ["epic_no", *cfg.COMPARE_FIELDS]
    merged = draft[cols].drop_duplicates("epic_no").merge(
        final[cols].drop_duplicates("epic_no"), on="epic_no", suffixes=("_draft", "_final")
    )
    joined = pd.Series("", index=merged.index)
    for field in cfg.COMPARE_FIELDS:
        differs = (merged[f"{field}_draft"] != merged[f"{field}_final"]).to_numpy()
        joined = joined + pd.Series(np.where(differs, field + ",", ""), index=merged.index)
    changed = joined != ""
    modified = merged[changed].copy()
    modified["changed_fields"] = joined[changed].str.rstrip(",").str.split(",")
    modified["part_no"] = modified["part_no_draft"]
    ordered = ["epic_no", "part_no"]
    ordered += [f"{f}_{side}" for f in cfg.COMPARE_FIELDS for side in ("draft", "final")]
    return modified[[*ordered, "changed_fields"]].reset_index(drop=True)


def _issues(rows: pd.DataFrame, issue_type: str, detail: pd.Series | str) -> pd.DataFrame:
    """Build data-quality rows (one per row of ``rows``) with the standard columns."""
    out = pd.DataFrame({
        "part_no": rows["part_no"].astype("int64").to_numpy(),
        "issue_type": issue_type,
        "epic_no": rows["epic_no"].to_numpy(),
        "detail": detail.to_numpy() if isinstance(detail, pd.Series) else detail,
    })
    return out[list(cfg.DQ_COLUMNS)]


def _duplicate_issues(roll: pd.DataFrame, label: str) -> pd.DataFrame:
    """One DUPLICATE_EPIC issue for every extra occurrence of an epic_no within one roll."""
    extra = roll[roll["epic_no"].duplicated(keep="first")]
    times = extra["epic_no"].map(roll["epic_no"].value_counts()).astype(str)
    detail = "epic_no appears " + times + " times in the " + label + " roll; worth verifying"
    return _issues(extra, cfg.DUPLICATE_EPIC, detail)


def _data_quality(
    draft: pd.DataFrame, final: pd.DataFrame, asdd: pd.DataFrame, removed: pd.DataFrame
) -> pd.DataFrame:
    """Collect data-quality issues into one DataFrame sorted by part_no, issue_type, epic_no."""
    no_record = removed[removed["reason"].isna()]
    asdd_extra = asdd[~asdd["epic_no"].isin(draft["epic_no"])]
    bad_age = final[(final["age"] < cfg.MIN_VALID_AGE) | (final["age"] > cfg.MAX_VALID_AGE)]
    age_detail = (
        "age " + bad_age["age"].astype(str) + " in the final roll is outside "
        + f"{cfg.MIN_VALID_AGE}-{cfg.MAX_VALID_AGE}; worth verifying"
    )
    parts = [
        _issues(no_record, cfg.REMOVED_WITHOUT_ASDD,
                "removed from the roll but no ASDD record found; worth verifying"),
        _issues(asdd_extra, cfg.ASDD_NOT_IN_DRAFT,
                "ASDD record has no matching voter in the draft roll; worth verifying"),
        _issues(bad_age, cfg.AGE_OUT_OF_RANGE, age_detail),
        _duplicate_issues(draft, "draft"),
        _duplicate_issues(final, "final"),
    ]
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame({
            c: pd.Series(dtype="int64" if c == "part_no" else "object") for c in cfg.DQ_COLUMNS
        })
    out = pd.concat(parts, ignore_index=True)
    return out.sort_values(["part_no", "issue_type", "epic_no"], kind="stable").reset_index(drop=True)


def compare(draft: pd.DataFrame, final: pd.DataFrame, asdd: pd.DataFrame) -> CompareResult:
    """Compare the rolls and return added, removed, modified and data-quality findings.

    Rows are matched on ``epic_no`` only. Inputs are not modified.
    """
    added = final[~final["epic_no"].isin(draft["epic_no"])].reset_index(drop=True)
    removed = _find_removed(draft, final, asdd)
    modified = _find_modified(draft, final)
    return CompareResult(added, removed, modified, _data_quality(draft, final, asdd, removed))
