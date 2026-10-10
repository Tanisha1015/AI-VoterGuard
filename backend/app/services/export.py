"""GET /api/audits/{audit_id}/export: the payload the trust service turns into a signed report."""

from __future__ import annotations

from sqlmodel import Session

from app import db
from app.detectors.config import THRESHOLDS
from app.detectors.registry import DETECTORS
from app.models import AuditExport, Bilingual, ExportSummary, FlaggedBooth, Methodology
from app.services import store, templates

METHODOLOGY_VERSION = "0.1"


def build_export(session: Session, audit: db.AuditRow) -> AuditExport:
    """Build the export object: hashes, summary, flagged booths with their flags and reviews."""
    all_flags = store.list_flags(session, audit.audit_id)
    flagged = [
        FlaggedBooth(booth=booth, flags=[f for f in all_flags if f.part_no == booth.part_no])
        for booth in store.booth_summaries(audit)
        if booth.flagged
    ]
    return AuditExport(
        audit_id=audit.audit_id, ac_no=audit.ac_no, ac_name=audit.ac_name, generated_at=db.now_iso(),
        snapshot_hashes=store.hashes(audit),
        summary=ExportSummary(
            totals=store.totals(session, audit), constituency_baseline=store.baseline(audit)
        ),
        flagged_booths=flagged,
        methodology=Methodology(
            version=METHODOLOGY_VERSION,
            detectors=[d.name.value for d in DETECTORS],
            thresholds=THRESHOLDS,
        ),
        disclaimer=Bilingual(**templates.DISCLAIMER_FLAGS),
    )
