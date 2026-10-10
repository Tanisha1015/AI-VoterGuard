"""Audit endpoints of the core API (CONTRACT.md 6.3)."""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import ValidationError
from sqlmodel import Session, select
from starlette.datastructures import UploadFile

from app import db
from app.errors import ApiError
from app.models import (
    AuditCreated, AuditExport, AuditList, AuditListItem, AuditSummary, BoothDetail, BoothList,
    CreateAuditRequest, DetectorName, ErrorBody, Flag, FlagList, ReviewRequest, Severity,
)
from app.services import export as export_service
from app.services import pipeline, store

router = APIRouter(prefix="/api/audits")
NOT_FOUND = {404: {"model": ErrorBody}}
UPLOAD_FIELDS = ("draft", "final", "asdd")


# ------------------------------------------------------------------ create and list


async def _save_uploads(request: Request, folder: Path) -> dict[str, Path]:
    """Save the multipart files draft, final and asdd into ``folder``."""
    form = await request.form()
    paths: dict[str, Path] = {}
    for field in UPLOAD_FIELDS:
        upload = form.get(field)
        if not isinstance(upload, UploadFile):
            raise ApiError(422, "VALIDATION_ERROR", f"Upload the three CSV files: missing file '{field}'.")
        paths[field] = folder / f"{field}.csv"
        paths[field].write_bytes(await upload.read())
    return paths


async def _create_from_upload(request: Request) -> str:
    with tempfile.TemporaryDirectory(prefix="vg_upload_") as tmp:
        paths = await _save_uploads(request, Path(tmp))
        try:
            return await asyncio.to_thread(
                pipeline.run_pipeline, paths["draft"], paths["final"], paths["asdd"]
            )
        except ValueError as exc:  # the CSV loader reports schema problems as ValueError
            raise ApiError(422, "INVALID_CSV", str(exc)) from exc


async def _create_synthetic() -> str:
    return await asyncio.to_thread(pipeline.run_synthetic_pipeline)


@router.post(
    "", status_code=201, response_model=AuditCreated, responses={422: {"model": ErrorBody}}
)
async def create_audit(request: Request) -> AuditCreated:
    """Create an audit from the synthetic data (JSON body) or from three uploaded CSV files (multipart)."""
    if "multipart/form-data" in request.headers.get("content-type", ""):
        audit_id = await _create_from_upload(request)
    else:
        try:
            raw = await request.body()
            body = CreateAuditRequest.model_validate_json(raw) if raw else CreateAuditRequest()
        except ValidationError as exc:
            raise ApiError(422, "VALIDATION_ERROR", "Body must be {\"use_synthetic\": true} or multipart files.") from exc
        if not body.use_synthetic:
            raise ApiError(422, "VALIDATION_ERROR", "Set use_synthetic to true or upload draft, final and asdd files.")
        audit_id = await _create_synthetic()
    return AuditCreated(audit_id=audit_id, status="READY")


@router.get("", response_model=AuditList)
def list_audits(session: Session = Depends(db.get_session)) -> AuditList:
    """All audits, oldest first."""
    rows = session.exec(select(db.AuditRow).order_by(db.AuditRow.audit_id)).all()
    return AuditList(items=[
        AuditListItem(audit_id=r.audit_id, ac_name=r.ac_name, created_at=r.created_at) for r in rows
    ])


# ------------------------------------------------------------------ read


@router.get("/{audit_id}/summary", response_model=AuditSummary, responses=NOT_FOUND)
def get_summary(audit_id: str, session: Session = Depends(db.get_session)) -> AuditSummary:
    return store.summary(session, store.get_audit(session, audit_id))


@router.get("/{audit_id}/booths", response_model=BoothList, responses=NOT_FOUND)
def list_booths(audit_id: str, session: Session = Depends(db.get_session)) -> BoothList:
    """Booths sorted by risk_score, highest first."""
    return BoothList(items=store.booth_summaries(store.get_audit(session, audit_id)))


@router.get("/{audit_id}/booths/{part_no}", response_model=BoothDetail, responses=NOT_FOUND)
def get_booth(audit_id: str, part_no: int, session: Session = Depends(db.get_session)) -> BoothDetail:
    return store.booth_detail(session, store.get_audit(session, audit_id), part_no)


@router.get("/{audit_id}/flags", response_model=FlagList, responses=NOT_FOUND)
def list_flags(
    audit_id: str,
    part_no: Optional[int] = Query(default=None),
    severity: Optional[Severity] = Query(default=None),
    detector: Optional[DetectorName] = Query(default=None),
    session: Session = Depends(db.get_session),
) -> FlagList:
    """Flags, optionally filtered by part_no, severity and detector."""
    store.get_audit(session, audit_id)
    return FlagList(items=store.list_flags(session, audit_id, part_no, severity, detector))


@router.put("/{audit_id}/flags/{flag_id}/review", response_model=Flag, responses=NOT_FOUND)
def review_flag(
    audit_id: str, flag_id: str, body: ReviewRequest, session: Session = Depends(db.get_session)
) -> Flag:
    """Record a human review (ACCEPTED, REJECTED or back to PENDING) and return the updated flag."""
    store.get_audit(session, audit_id)
    row = session.get(db.FlagRow, (audit_id, flag_id))
    if row is None:
        raise ApiError(404, "FLAG_NOT_FOUND", f"Flag {flag_id} was not found in audit {audit_id}.")
    row.review_status = body.status
    row.review_note = body.note
    row.reviewed_at = None if body.status == "PENDING" else db.now_iso()
    session.add(row)
    session.commit()
    session.refresh(row)
    return store.flag_from_row(row)


@router.get("/{audit_id}/export", response_model=AuditExport, responses=NOT_FOUND)
def export_audit(audit_id: str, session: Session = Depends(db.get_session)) -> AuditExport:
    """Everything the trust service needs to build a report."""
    return export_service.build_export(session, store.get_audit(session, audit_id))
