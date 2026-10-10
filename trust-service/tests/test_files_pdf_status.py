"""Static file serving, PDF generation, health/CORS and chain status."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.canonical import build_report
from app.config import load_settings
from app.chain import ChainClient
from app.pdf import build_pdf
from tests.conftest import load_export

BODY = {"audit_id": "aud_001", "reviewer_name": "R. Sharma", "supersedes": None}


def test_serves_saved_json_and_pdf(client: TestClient, settings: Any) -> None:
    created = client.post("/api/reports", json=BODY).json()
    res_json = client.get(created["files"]["json"])
    assert res_json.status_code == 200 and res_json.headers["content-type"].startswith("application/json")
    assert res_json.content == (settings.report_dir / f"{created['report_id']}.json").read_bytes()
    res_pdf = client.get(created["files"]["pdf"])
    assert res_pdf.status_code == 200 and res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF")


@pytest.mark.parametrize("name", [
    "VG-2026-0001.txt", "trust.sqlite3", "..%2Ftrust.sqlite3", "..%5C..%5Capp%5Cmain.py",
    "VG-2026-0001.json.tmp", "VG-2026-0404.json",
])
def test_rejects_other_names_and_traversal(client: TestClient, settings: Any, name: str) -> None:
    (settings.report_dir / "VG-2026-0001.txt").write_text("secret", encoding="utf-8")
    assert client.get(f"/files/{name}").status_code == 404


def test_pdf_without_hindi_font_logs_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    doc = build_report(load_export(), "VG-2026-0001", "R. Sharma", None, "2026-10-10T10:05:00Z")
    with caplog.at_level(logging.WARNING):
        pdf = build_pdf(doc, "0x" + "ab" * 32, tmp_path / "missing.ttf")
    assert pdf.startswith(b"%PDF") and len(pdf) > 2000
    assert any("English-only" in r.message for r in caplog.records)


def test_pdf_with_broken_font_file_still_renders(tmp_path: Path) -> None:
    bad_font = tmp_path / "NotoSansDevanagari-Regular.ttf"
    bad_font.write_bytes(b"not a font")
    doc = build_report(load_export(), "VG-2026-0001", "R. Sharma", None, "2026-10-10T10:05:00Z")
    assert build_pdf(doc, "0x" + "cd" * 32, bad_font).startswith(b"%PDF")


def test_health_and_cors(client: TestClient) -> None:
    res = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert res.json() == {"status": "ok"}
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_chain_status_route(client: TestClient) -> None:
    assert set(client.get("/api/chain/status").json()) == {"connected", "chain_id", "contract_address", "latest_block"}


def test_real_chain_client_reports_disconnected(tmp_path: Path) -> None:
    from dataclasses import replace

    settings = replace(load_settings(), chain_rpc_url="http://127.0.0.1:9", deployments_dir=tmp_path)
    status = ChainClient(settings).status()
    assert status == {"connected": False, "chain_id": None, "contract_address": None, "latest_block": None}
