"""POST /api/reports/verify with the stub chain."""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.chain import ChainUnavailable
from tests.conftest import StubChain

BODY = {"audit_id": "aud_001", "reviewer_name": "R. Sharma", "supersedes": None}


def recorded(client: TestClient, settings: Any) -> tuple[str, bytes]:
    report_id = client.post("/api/reports", json=BODY).json()["report_id"]
    return report_id, (settings.report_dir / f"{report_id}.json").read_bytes()


def verify(client: TestClient, data: bytes, report_id: str | None = None, name: str = "report.json") -> Any:
    form = {"report_id": report_id} if report_id else {}
    return client.post("/api/reports/verify", files={"file": (name, data, "application/json")}, data=form)


def test_match(client: TestClient, settings: Any) -> None:
    report_id, data = recorded(client, settings)
    res = verify(client, data)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "MATCH" and body["report_id"] == report_id
    assert body["computed_hash"] == body["onchain_hash"]
    assert body["submitter"].startswith("0x") and body["recorded_at"] and body["superseded_by"] is None


def test_mismatch_after_one_character_flip(client: TestClient, settings: Any) -> None:
    report_id, data = recorded(client, settings)
    tampered = data.replace(b'"removed":182', b'"removed":181', 1)
    assert tampered != data
    body = verify(client, tampered).json()
    assert body["status"] == "MISMATCH" and body["report_id"] == report_id
    assert body["computed_hash"] != body["onchain_hash"]


def test_not_found_for_unknown_id(client: TestClient) -> None:
    body = verify(client, b'{"report_id":"VG-2026-0999"}').json()
    assert body["status"] == "NOT_FOUND" and body["onchain_hash"] is None and body["report_id"] == "VG-2026-0999"


def test_form_report_id_overrides_file(client: TestClient, settings: Any) -> None:
    report_id, data = recorded(client, settings)
    body = verify(client, b"not json at all", report_id=report_id, name="x.pdf").json()
    assert body["status"] == "MISMATCH" and body["report_id"] == report_id


def test_unparsable_without_report_id_is_422(client: TestClient) -> None:
    res = verify(client, b"\x89PNG not json", name="image.png")
    assert res.status_code == 422 and res.json()["error"]["code"] == "REPORT_ID_REQUIRED"


def test_superseded_by_is_reported(client: TestClient, settings: Any) -> None:
    report_id, data = recorded(client, settings)
    newer = client.post("/api/reports", json={**BODY, "supersedes": report_id}).json()["report_id"]
    assert verify(client, data).json()["superseded_by"] == newer


def test_chain_down_is_502(client: TestClient, stub_chain: StubChain) -> None:
    stub_chain.fail_with = ChainUnavailable("Chain node is not reachable.")
    res = verify(client, b'{"report_id":"VG-2026-0001"}')
    assert res.status_code == 502 and res.json()["error"]["code"] == "CHAIN_UNAVAILABLE"
