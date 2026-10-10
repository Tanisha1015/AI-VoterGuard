"""Minimal stand-in for the core API's export endpoint, for manual smoke tests only.

Run: python -m uvicorn tests.stub_core:app --port 8000
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from tests.conftest import load_export

app = FastAPI(title="Stub core (export only)")


@app.get("/api/audits/{audit_id}/export")
def export(audit_id: str) -> dict[str, Any]:
    payload = load_export()
    if audit_id != payload["audit_id"]:
        raise HTTPException(status_code=404, detail="unknown audit")
    return payload
