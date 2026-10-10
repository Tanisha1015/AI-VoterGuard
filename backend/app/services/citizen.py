"""Citizen lookup: find one entry in the latest audit's rolls and report its status, masked.

Privacy rules: only the masked EPIC, "first name + last initial" and an age band are returned;
when several entries match equally well NOTHING about them is returned (AMBIGUOUS gives a message
only); nothing typed by the citizen is logged. Only name text is compared; religion, caste or
citizenship are never inferred. This module never decides eligibility: it only reports whether an
entry appears in the draft roll, the final roll, or both.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from rapidfuzz import fuzz

from app.engine import config as cfg
from app.errors import ApiError
from app.models import CitizenRecord, CitizenRequest, CitizenResponse
from app.services import templates

HONORIFICS = frozenset({"shri", "smt", "mr", "mrs", "ms", "km", "dr", "kumari"})
MATCH_MIN = 90.0  # minimum combined score for any match
UNIQUE_GAP = 5.0  # a unique match must beat the runner-up by at least this many points
NAME_WEIGHT, RELATIVE_WEIGHT = 0.6, 0.4

_PUNCTUATION = re.compile(r"[^\w\s\u0900-\u097F]|_")  # keeps Devanagari letters and vowel signs
_DOUBLE_LETTER = re.compile(r"(.)\1+")
_PHONETIC_FOLDS = (("ee", "i"), ("oo", "u"), ("aa", "a"), ("ph", "f"), ("w", "v"))


# ------------------------------------------------------------------ normalisation


def _fold_token(token: str) -> str:
    """Fold simple spelling variants: ee->i, oo->u, aa->a, ph->f, w->v, double letters -> single."""
    for old, new in _PHONETIC_FOLDS:
        token = token.replace(old, new)
    return _DOUBLE_LETTER.sub(r"\1", token)


def normalise_name(name: str) -> str:
    """Lower-case, drop punctuation and honorifics, and fold simple phonetic variants.

    If removing honorifics would leave nothing (for example the name is just "Kumari") they are kept.
    """
    tokens = _PUNCTUATION.sub(" ", str(name).lower()).split()
    kept = [t for t in tokens if t not in HONORIFICS] or tokens
    return " ".join(_fold_token(t) for t in kept)


# ------------------------------------------------------------------ masking


def mask_epic(epic_no: str) -> str:
    """VGX8433051 -> VGX****051."""
    return f"{epic_no[:3]}****{epic_no[-3:]}"


def display_name(name: str) -> str:
    """"Sunita Devi" -> "Sunita D."; a single word is returned unchanged."""
    parts = str(name).split()
    if len(parts) < 2:
        return parts[0] if parts else ""
    return f"{parts[0]} {parts[-1][0].upper()}."


def age_band(age: int) -> Optional[str]:
    """The contract age band for an age (None below 18)."""
    for label, low, high in zip(cfg.AGE_BAND_LABELS, cfg.AGE_BAND_EDGES, cfg.AGE_BAND_EDGES[1:]):
        if low <= age < high:
            return label
    return None


# ------------------------------------------------------------------ roll index (cached per audit)


@dataclass(frozen=True)
class RollIndex:
    """Searchable view of one audit's rolls.

    ``rows`` has one row per distinct (epic_no, booth, name, relative name) in draft union final, with
    columns epic_no, part_no, name, age, norm_name, norm_relative, in_draft, in_final. ``reasons`` maps
    epic_no to its ASDD reason.
    """

    rows: pd.DataFrame
    reasons: dict[str, str]


_INDEX_CACHE: dict[str, RollIndex] = {}
_ROLL_COLUMNS = ["epic_no", "part_no", "name", "relative_name", "age"]


def clear_cache() -> None:
    """Forget cached indexes (tests, or after audit files change)."""
    _INDEX_CACHE.clear()


def _read_roll(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, usecols=_ROLL_COLUMNS)
    df["part_no"] = df["part_no"].astype("int64")
    df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(-1).astype("int64")
    return df


def build_index(directory: Path) -> RollIndex:
    """Load draft_roll.csv, final_roll.csv and asdd.csv from ``directory``."""
    draft = _read_roll(directory / "draft_roll.csv")
    final = _read_roll(directory / "final_roll.csv")
    asdd = pd.read_csv(directory / "asdd.csv", dtype=str, keep_default_na=False)
    rows = pd.concat([draft, final], ignore_index=True)
    rows = rows.drop_duplicates(["epic_no", "part_no", "name", "relative_name"], keep="last")
    rows = rows.reset_index(drop=True)
    rows["in_draft"] = rows["epic_no"].isin(set(draft["epic_no"]))
    rows["in_final"] = rows["epic_no"].isin(set(final["epic_no"]))
    rows["norm_name"] = rows["name"].map(normalise_name)
    rows["norm_relative"] = rows["relative_name"].map(normalise_name)
    reasons = asdd.drop_duplicates("epic_no").set_index("epic_no")["reason"].to_dict()
    return RollIndex(rows, reasons)


def get_index(directory: Path) -> RollIndex:
    """Cached ``build_index``."""
    key = str(directory)
    if key not in _INDEX_CACHE:
        _INDEX_CACHE[key] = build_index(directory)
    return _INDEX_CACHE[key]


# ------------------------------------------------------------------ matching


def _score(row_name: str, row_relative: str, name: str, relative: str) -> float:
    """0.6 * token_set_ratio(name) + 0.4 * token_set_ratio(relative_name), on normalised text."""
    return (NAME_WEIGHT * fuzz.token_set_ratio(row_name, name)
            + RELATIVE_WEIGHT * fuzz.token_set_ratio(row_relative, relative))


def _best_per_epic(rows: pd.DataFrame, name: str, relative: str) -> list[tuple[float, int]]:
    """(best score, row position) for each distinct EPIC in ``rows``, highest score first."""
    best: dict[str, tuple[float, int]] = {}
    for pos, (epic, n, r) in enumerate(zip(rows["epic_no"], rows["norm_name"], rows["norm_relative"])):
        score = _score(n, r, name, relative)
        if epic not in best or score > best[epic][0]:
            best[epic] = (score, pos)
    return sorted(best.values(), key=lambda item: -item[0])


def classify(scores: list[float]) -> str:
    """Apply the match rules to scores sorted high to low.

    Returns "UNIQUE" (best >= 90 and at least 5 points ahead of the second), "AMBIGUOUS" (several
    scores >= 90 within 5 points of each other) or "NOT_FOUND".
    """
    if not scores or scores[0] < MATCH_MIN:
        return "NOT_FOUND"
    second = scores[1] if len(scores) > 1 else None
    if second is None or scores[0] - second >= UNIQUE_GAP:
        return "UNIQUE"
    return "AMBIGUOUS" if second >= MATCH_MIN else "NOT_FOUND"


def _status(in_draft: bool, in_final: bool) -> str:
    """In both rolls -> PRESENT; draft only -> REMOVED; final only -> ADDED."""
    if in_draft and in_final:
        return "PRESENT"
    return "REMOVED" if in_draft else "ADDED"


# ------------------------------------------------------------------ response building


def _not_found() -> CitizenResponse:
    return CitizenResponse(status="NOT_FOUND", match_confidence=0.0)


def _ambiguous(confidence: float) -> CitizenResponse:
    """Message only: the matching entries are never listed or described."""
    return CitizenResponse(
        status="AMBIGUOUS", match_confidence=confidence,
        message=templates.AMBIGUOUS_MESSAGE,  # type: ignore[arg-type]
    )


def _found(row: pd.Series, index: RollIndex, confidence: float, deadline: Optional[str]) -> CitizenResponse:
    """Build the masked response for one matched entry."""
    status = _status(bool(row["in_draft"]), bool(row["in_final"]))
    record = CitizenRecord(
        epic_masked=mask_epic(str(row["epic_no"])), part_no=int(row["part_no"]),
        name_display=display_name(str(row["name"])), age_band=age_band(int(row["age"])),
    )
    reason = index.reasons.get(str(row["epic_no"])) if status == "REMOVED" else None
    step: Any = templates.next_step(deadline) if status == "REMOVED" else None
    return CitizenResponse(
        status=status, match_confidence=confidence, record=record,  # type: ignore[arg-type]
        reason=reason or None, next_step=step,
    )


# ------------------------------------------------------------------ public API


def validate(request: CitizenRequest) -> tuple[Optional[str], str, str, int]:
    """Check the request has epic_no, or name + relative_name + part_no; else raise a 422 ApiError.

    Returns (epic_no or None, normalised name, normalised relative name, part_no).
    """
    epic = (request.epic_no or "").strip().upper()
    if epic:
        return epic, "", "", request.part_no or 0
    name = normalise_name(request.name or "")
    relative = normalise_name(request.relative_name or "")
    if not name or not relative or request.part_no is None:
        raise ApiError(
            422, "VALIDATION_ERROR",
            "Provide epic_no, or name, relative_name and part_no together.",
        )
    return None, name, relative, request.part_no


def lookup(request: CitizenRequest, directory: Path, deadline: Optional[str]) -> CitizenResponse:
    """Look the citizen up in the rolls stored in ``directory`` (see module docstring for the rules)."""
    epic, name, relative, part_no = validate(request)
    index = get_index(directory)
    if epic:
        hits = index.rows[index.rows["epic_no"].str.upper() == epic]
        if hits.empty:
            return _not_found()
        return _found(hits.iloc[-1], index, 1.0, deadline)

    booth = index.rows[index.rows["part_no"] == part_no].reset_index(drop=True)
    ranked = _best_per_epic(booth, name, relative)
    scores = [score for score, _ in ranked]
    verdict = classify(scores)
    if verdict == "NOT_FOUND":
        return _not_found()
    confidence = round(scores[0] / 100, 2)
    if verdict == "AMBIGUOUS":
        return _ambiguous(confidence)
    return _found(booth.iloc[ranked[0][1]], index, confidence, deadline)

