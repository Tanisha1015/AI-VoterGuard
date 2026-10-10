"""Report document builder and canonical JSON encoding (CONTRACT.md 6.7)."""
from __future__ import annotations

import json
from typing import Any

SCHEMA_VERSION = "1.0"


def build_report(
    export_payload: dict[str, Any],
    report_id: str,
    reviewer_name: str,
    supersedes: str | None,
    generated_at: str,
) -> dict[str, Any]:
    """Assemble the report document with exactly the top-level keys required by the contract."""
    return {
        "schema_version": SCHEMA_VERSION,
        "report_id": report_id,
        "generated_at": generated_at,
        "reviewer": {"name": reviewer_name},
        "audit": export_payload,
        "supersedes": supersedes,
    }


def to_canonical_bytes(document: dict[str, Any]) -> bytes:
    """Canonical form: UTF-8, keys sorted, no whitespace, non-ASCII kept as-is.

    The saved report file is exactly these bytes, and report_hash is their SHA-256.
    """
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text.encode("utf-8")
