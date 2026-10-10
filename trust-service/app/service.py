"""Report creation logic, independent of HTTP."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

import httpx

from .canonical import build_report, to_canonical_bytes
from .chain import ChainError, ContractRejected
from .deps import Services
from .errors import ApiError
from .hashing import is_hash, sha256_hex
from .pdf import build_pdf
from .store import ReportRow, parse_report_id

log = logging.getLogger(__name__)
T = TypeVar("T")
MAX_ID_ATTEMPTS = 5


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_export(services: Services, audit_id: str) -> dict[str, Any]:
    """GET {CORE_URL}/api/audits/{id}/export. Core down -> 502; unknown audit -> 404."""
    try:
        res = services.core_http.get(f"/api/audits/{audit_id}/export")
    except httpx.HTTPError as exc:
        raise ApiError(502, "CORE_UNAVAILABLE", f"The core API could not be reached: {exc}") from exc
    if res.status_code == 404:
        raise ApiError(404, "AUDIT_NOT_FOUND", f"Audit {audit_id} was not found by the core API.")
    if res.status_code != 200:
        raise ApiError(502, "CORE_ERROR", f"The core API returned HTTP {res.status_code} for the export.")
    try:
        payload = res.json()
    except ValueError as exc:
        raise ApiError(502, "CORE_ERROR", "The core API returned an export that is not valid JSON.") from exc
    hashes = payload.get("snapshot_hashes") if isinstance(payload, dict) else None
    if not isinstance(hashes, dict) or not all(is_hash(str(hashes.get(k, ""))) for k in ("draft", "final", "asdd")):
        raise ApiError(502, "CORE_ERROR", "The export is missing well-formed snapshot_hashes.")
    return payload


def _write_atomic(path: Path, data: bytes) -> None:
    """Write via a temp file + rename so readers never see a partial file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


MAX_ID_SCAN = 10_000


def _next_free_on_chain(services: Services, year: int, start_seq: int) -> str:
    """First id >= start_seq that is free both locally and on chain (read-only scan)."""
    seq = start_seq
    for _ in range(MAX_ID_SCAN):
        candidate = services.store.next_report_id(year, min_seq=seq)
        if services.chain.get_report(candidate) is None:
            return candidate
        seq = parse_report_id(candidate)[1] + 1
    raise ApiError(502, "REPORT_ID_CONFLICT", "Could not find a free report id on the chain.")


def _chain_api_error(exc: ChainError) -> ApiError:
    if isinstance(exc, ContractRejected) and exc.error_name in ("AlreadySuperseded", "UnknownSupersededReport"):
        return ApiError(409, exc.code, str(exc))
    return ApiError(502, exc.code, f"Recording on the chain failed; nothing was saved. {exc}")


def create_report(services: Services, audit_id: str, reviewer_name: str, supersedes: str | None) -> dict[str, Any]:
    """Build, record on chain, and only after success persist files and the store row."""
    store, settings = services.store, services.settings
    export = fetch_export(services, audit_id)
    hashes = export["snapshot_hashes"]
    if supersedes and not store.exists(supersedes):
        raise ApiError(404, "SUPERSEDED_REPORT_NOT_FOUND", f"Report {supersedes} does not exist.")

    with services.create_lock:
        year = datetime.now(timezone.utc).year
        report_id = store.next_report_id(year)
        for _attempt in range(MAX_ID_ATTEMPTS):
            document = build_report(export, report_id, reviewer_name, supersedes, utc_now())
            canonical = to_canonical_bytes(document)
            report_hash = sha256_hex(canonical)
            pdf_bytes = build_pdf(document, report_hash, settings.hindi_font_file)
            try:
                result = services.chain.record_report(
                    report_id, report_hash, hashes["draft"], hashes["final"], hashes["asdd"], supersedes
                )
                break
            except ContractRejected as exc:
                if exc.error_name != "ReportExists":
                    raise _chain_api_error(exc) from exc
                # The local store is behind the chain (e.g. data/ was wiped): jump past taken ids.
                log.warning("Report id %s already on chain; looking for the next free id.", report_id)
                report_id = _next_free_on_chain(services, year, parse_report_id(report_id)[1] + 1)
            except ChainError as exc:
                raise _chain_api_error(exc) from exc
        else:
            raise ApiError(502, "REPORT_ID_CONFLICT", "Could not find a free report id on the chain.")

        json_path = settings.report_dir / f"{report_id}.json"
        pdf_path = settings.report_dir / f"{report_id}.pdf"
        _write_atomic(json_path, canonical)
        _write_atomic(pdf_path, pdf_bytes)
        store.insert(ReportRow(report_id, report_hash, result.tx_hash, result.block_number, result.recorded_at,
                               supersedes, str(json_path), str(pdf_path)))

    return report_response(report_id, report_hash, hashes, result.tx_hash, result.block_number,
                           result.recorded_at, supersedes)


def report_response(report_id: str, report_hash: str, snapshot_hashes: dict[str, str], tx_hash: str,
                    block_number: int, recorded_at: str, supersedes: str | None) -> dict[str, Any]:
    """Exactly the CONTRACT.md 6.5 POST /api/reports shape."""
    return {
        "report_id": report_id,
        "report_hash": report_hash,
        "snapshot_hashes": {k: snapshot_hashes[k] for k in ("draft", "final", "asdd")},
        "tx_hash": tx_hash,
        "block_number": block_number,
        "recorded_at": recorded_at,
        "supersedes": supersedes,
        "files": {"json": f"/files/{report_id}.json", "pdf": f"/files/{report_id}.pdf"},
    }


def snapshot_hashes_from_file(json_path: str) -> dict[str, str]:
    """Read snapshot hashes back from a saved report file."""
    data = json.loads(Path(json_path).read_bytes().decode("utf-8"))
    return dict(data["audit"]["snapshot_hashes"])


def chain_or_502(fn: Callable[..., T], *args: Any) -> T:
    """Call a chain read, turning chain errors into 502 responses."""
    try:
        return fn(*args)
    except ChainError as exc:
        raise ApiError(502, exc.code, str(exc)) from exc
