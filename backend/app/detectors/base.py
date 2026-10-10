"""Shared types for the detectors: enums, the Flag record, the input context and the Detector protocol.

A Flag is a purely numeric finding about one booth (no prose). Explanations are phrased later and may
only restate the numbers computed here. Flags say a pattern is unusual and worth verifying; they never
conclude anything about a voter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

import pandas as pd

from app.engine.compare import CompareResult


class DetectorType(StrEnum):
    """The ``detector`` enum from contracts/CONTRACT.md, in contract order."""

    DELETION_RATE = "DELETION_RATE"
    REASON_DOMINANCE = "REASON_DOMINANCE"
    GENDER_SKEW = "GENDER_SKEW"
    AGE_SKEW = "AGE_SKEW"
    HOUSE_CLUSTER = "HOUSE_CLUSTER"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    DATA_QUALITY = "DATA_QUALITY"


class Severity(StrEnum):
    """The ``severity`` enum from contracts/CONTRACT.md."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class Flag:
    """One unusual booth-level pattern. ``flag_id`` is assigned by ``registry.run_all``."""

    part_no: int
    detector: DetectorType
    severity: Severity
    metric_name: str
    metric_value: float
    baseline: float
    details: dict[str, Any] = field(default_factory=dict)
    flag_id: str = ""


@dataclass(frozen=True)
class DetectorContext:
    """Everything a detector may look at (read-only).

    ``duplicate_pairs`` is the table from ``duplicate_entry.find_duplicate_pairs`` (columns part_a,
    part_b); when it is None the duplicate detector computes it itself.
    """

    booth_df: pd.DataFrame
    draft: pd.DataFrame
    final: pd.DataFrame
    result: CompareResult
    baseline: dict[str, Any]
    duplicate_pairs: pd.DataFrame | None = None


class Detector(Protocol):
    """A detector turns a DetectorContext into zero or more Flags."""

    name: DetectorType

    def detect(self, ctx: DetectorContext) -> list[Flag]:
        """Return the flags for every booth where this detector fires."""
        ...


def make_flag(
    part_no: Any,
    detector: DetectorType,
    severity: Severity,
    metric_name: str,
    metric_value: Any,
    baseline: Any,
    details: dict[str, Any] | None = None,
) -> Flag:
    """Build a Flag with plain Python numbers (so it serialises to JSON without surprises)."""
    return Flag(
        int(part_no), detector, severity, metric_name,
        float(metric_value), float(baseline), dict(details or {}),
    )


def severity_for(value: float, high_at: float, base: Severity = Severity.MEDIUM) -> Severity:
    """HIGH when ``value`` reaches ``high_at``, otherwise ``base``."""
    return Severity.HIGH if value >= high_at else base
