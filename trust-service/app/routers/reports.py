"""Report endpoints (CONTRACT.md 6.5) and the /files download route."""
from __future__ import annotations

import json
import re
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from ..deps import Services
from ..errors import ApiError
from ..hashing import sha256_hex
from ..service import chain_or_502, create_report, report_response, snapshot_hashes_from_file

router = APIRouter()
FILE_NAME = re.compile(r"^VG-\d{4}-\d{4,}\.(json|pdf)$")
MEDIA_TYPES = {"json": "application/json", "pdf": "application/pdf"}


def services_of(request: Request) -> Services:
    return request.app.state.services  # type: ignore[no-any-return]


class CreateReportBody(BaseModel):
    audit_id: str = Field(min_length=1, max_length=100)
    reviewer_name: str = Field(min_length=1, max_length=200)
    supersedes: str | None = None

    @field_validator("reviewer_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reviewer_name must not be blank")
        return value

    @field_validator("supersedes")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


@router.post("/api/reports", status_code=201)
def post_report(body: CreateReportBody, request: Request) -> dict[str, Any]:
    return create_report(services_of(request), body.audit_id, body.reviewer_name, body.supersedes)


@router.get("/api/reports")
def list_reports(request: Request) -> dict[str, Any]:
    """superseded_by comes from the local store (it only holds chain-confirmed reports)."""
    store = services_of(request).store
    return {
        "items": [
            {"report_id": r.report_id, "recorded_at": r.recorded_at, "report_hash": r.report_hash,
             "superseded_by": store.superseded_by(r.report_id)}
            for r in store.list_all()
        ]
    }


@router.get("/api/reports/{report_id}")
def get_report(report_id: str, request: Request) -> dict[str, Any]:
    services = services_of(request)
    row = services.store.get(report_id)
    if row is None:
        raise ApiError(404, "REPORT_NOT_FOUND", f"Report {report_id} does not exist.")
    response = report_response(row.report_id, row.report_hash, snapshot_hashes_from_file(row.json_path),
                               row.tx_hash, row.block_number, row.recorded_at, row.supersedes)
    response["superseded_by"] = chain_or_502(services.chain.superseded_by, report_id)
    return response


def _report_id_from_json(data: bytes) -> str | None:
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    value = parsed.get("report_id") if isinstance(parsed, dict) else None
    return value if isinstance(value, str) and value else None


@router.post("/api/reports/verify")
async def verify_report(
    request: Request,
    file: Annotated[UploadFile, File()],
    report_id: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    """Hash the uploaded bytes exactly as received and compare with the on-chain hash."""
    data = await file.read()
    computed = sha256_hex(data)
    rid = (report_id or "").strip() or _report_id_from_json(data)
    if not rid:
        raise ApiError(422, "REPORT_ID_REQUIRED",
                       "Could not read report_id from the file. Upload the report JSON or provide report_id.")
    chain = services_of(request).chain
    onchain = chain_or_502(chain.get_report, rid)
    if onchain is None:
        return {"report_id": rid, "status": "NOT_FOUND", "computed_hash": computed, "onchain_hash": None,
                "recorded_at": None, "submitter": None, "superseded_by": None}
    return {
        "report_id": rid,
        "status": "MATCH" if onchain["report_hash"] == computed else "MISMATCH",
        "computed_hash": computed,
        "onchain_hash": onchain["report_hash"],
        "recorded_at": onchain["recorded_at"],
        "submitter": onchain["submitter"],
        "superseded_by": chain_or_502(chain.superseded_by, rid),
    }


@router.get("/files/{name}")
def get_file(name: str, request: Request) -> FileResponse:
    """Serve saved report files. Only VG-YYYY-NNNN.json/.pdf inside REPORT_DIR; no traversal."""
    match = FILE_NAME.match(name)
    if not match:
        raise ApiError(404, "FILE_NOT_FOUND", "File not found.")
    report_dir = services_of(request).settings.report_dir.resolve()
    path = (report_dir / name).resolve()
    if path.parent != report_dir or not path.is_file():
        raise ApiError(404, "FILE_NOT_FOUND", "File not found.")
    return FileResponse(path, media_type=MEDIA_TYPES[match.group(1)], filename=name)
