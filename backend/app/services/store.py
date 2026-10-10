"""Read side of the database: turn stored rows into the contract objects (see app.models)."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlmodel import Session, select

from app import db
from app.errors import ApiError
from app.models import (
    AuditSummary, Baseline, BoothDetail, BoothSummary, Flag, Metric, Review, SnapshotHashes, Totals,
)
from app.services.pipeline import booth_summary


def get_audit(session: Session, audit_id: str) -> db.AuditRow:
    """The audit row, or a 404 with the standard error body."""
    audit = session.get(db.AuditRow, audit_id)
    if audit is None:
        raise ApiError(404, "AUDIT_NOT_FOUND", f"Audit {audit_id} was not found.")
    return audit


def flag_from_row(row: db.FlagRow) -> Flag:
    """Build the contract Flag from a stored row."""
    return Flag(
        flag_id=row.flag_id, part_no=row.part_no, detector=row.detector,  # type: ignore[arg-type]
        severity=row.severity,  # type: ignore[arg-type]
        metric=Metric(name=row.metric_name, value=row.metric_value, baseline=row.metric_baseline),
        explanation={"en": row.explanation_en, "hi": row.explanation_hi},  # type: ignore[arg-type]
        recommended_checks=json.loads(row.checks_json),
        explanation_source=row.explanation_source,  # type: ignore[arg-type]
        review=Review(status=row.review_status, note=row.review_note,  # type: ignore[arg-type]
                      reviewed_at=row.reviewed_at),
    )


def list_flags(
    session: Session, audit_id: str, part_no: Optional[int] = None,
    severity: Optional[str] = None, detector: Optional[str] = None,
) -> list[Flag]:
    """Flags of an audit in detector order, optionally filtered by part_no, severity and detector."""
    query = select(db.FlagRow).where(db.FlagRow.audit_id == audit_id).order_by(db.FlagRow.seq)
    if part_no is not None:
        query = query.where(db.FlagRow.part_no == part_no)
    if severity is not None:
        query = query.where(db.FlagRow.severity == severity)
    if detector is not None:
        query = query.where(db.FlagRow.detector == detector)
    return [flag_from_row(row) for row in session.exec(query).all()]


def booth_records(audit: db.AuditRow) -> list[dict[str, Any]]:
    """The stored booth records of an audit, highest risk_score first (ties: lowest part_no)."""
    records: list[dict[str, Any]] = json.loads(audit.booths_json)
    return sorted(records, key=lambda b: (-b["risk_score"], b["part_no"]))


def booth_summaries(audit: db.AuditRow) -> list[BoothSummary]:
    return [BoothSummary(**booth_summary(b)) for b in booth_records(audit)]


def booth_detail(session: Session, audit: db.AuditRow, part_no: int) -> BoothDetail:
    """One booth with its gender_removed, age_band_removed_share and flags; 404 for an unknown booth."""
    for record in booth_records(audit):
        if record["part_no"] == part_no:
            flags = list_flags(session, audit.audit_id, part_no=part_no)
            return BoothDetail(**record, flags=flags)
    raise ApiError(404, "BOOTH_NOT_FOUND", f"Booth {part_no} was not found in audit {audit.audit_id}.")


def pending_reviews(session: Session, audit_id: str) -> int:
    """Number of flags whose review is still PENDING."""
    rows = session.exec(select(db.FlagRow.review_status).where(db.FlagRow.audit_id == audit_id)).all()
    return sum(1 for status in rows if status == "PENDING")


def totals(session: Session, audit: db.AuditRow) -> Totals:
    """The summary totals; pending_reviews is always read live from the flag rows."""
    stored = json.loads(audit.summary_json)["totals"]
    return Totals(**stored, pending_reviews=pending_reviews(session, audit.audit_id))


def baseline(audit: db.AuditRow) -> Baseline:
    """The contract constituency_baseline (the stored baseline also holds extra fields)."""
    stored = json.loads(audit.baseline_json)
    return Baseline(deletion_rate=stored["deletion_rate"], deletion_rate_mad=stored["deletion_rate_mad"])


def hashes(audit: db.AuditRow) -> SnapshotHashes:
    return SnapshotHashes(draft=audit.draft_hash, final=audit.final_hash, asdd=audit.asdd_hash)


def summary(session: Session, audit: db.AuditRow) -> AuditSummary:
    """GET /api/audits/{id}/summary."""
    return AuditSummary(
        audit_id=audit.audit_id, ac_no=audit.ac_no, ac_name=audit.ac_name, created_at=audit.created_at,
        snapshot_hashes=hashes(audit), totals=totals(session, audit),
        constituency_baseline=baseline(audit),
        reason_mix=json.loads(audit.summary_json)["reason_mix"],
    )
