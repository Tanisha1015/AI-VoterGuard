"""POST /api/citizen/lookup (rate limited to 20 requests per minute per client IP).

Nothing from the request (names, EPIC numbers) is logged.
"""

import os
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import db
from app.errors import ApiError
from app.models import CitizenRequest, CitizenResponse, ErrorBody
from app.ratelimit import citizen_rate_limit
from app.services import citizen as citizen_service

router = APIRouter(prefix="/api/citizen")


def claims_deadline() -> Optional[str]:
    """The claims deadline shown in next_step (env CLAIMS_DEADLINE, e.g. 2026-10-31), if set."""
    return os.environ.get("CLAIMS_DEADLINE") or None


@router.post(
    "/lookup",
    response_model=CitizenResponse,
    dependencies=[Depends(citizen_rate_limit)],
    responses={404: {"model": ErrorBody}, 422: {"model": ErrorBody}, 429: {"model": ErrorBody}},
)
def lookup(request: CitizenRequest, session: Session = Depends(db.get_session)) -> CitizenResponse:
    """Find an entry in the latest audit's draft and final rolls and report where it appears."""
    citizen_service.validate(request)  # 422 before any data is touched
    audit_id = db.latest_audit_id(session)
    if audit_id is None:
        raise ApiError(404, "AUDIT_NOT_FOUND", "No audit is available yet.")
    return citizen_service.lookup(request, db.audit_dir(audit_id), claims_deadline())
