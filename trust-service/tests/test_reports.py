"""POST/GET /api/reports with a stub chain and mocked core API."""
from __future__ import annotations

from typing import Any, Callable

from fastapi.testclient import TestClient

from app.chain import ChainUnavailable, ContractRejected
from app.hashing import sha256_hex
from tests.conftest import StubChain, core_down, load_export

BODY = {"audit_id": "aud_001", "reviewer_name": "R. Sharma", "supersedes": None}


def files_in(settings: Any) -> list[str]:
    return sorted(p.name for p in settings.report_dir.iterdir()) if settings.report_dir.exists() else []


def test_create_report_returns_contract_shape(client: TestClient, settings: Any) -> None:
    res = client.post("/api/reports", json=BODY)
    assert res.status_code == 201, res.text
    data = res.json()
    assert set(data) == {"report_id", "report_hash", "snapshot_hashes", "tx_hash", "block_number",
                         "recorded_at", "supersedes", "files"}
    assert data["report_id"].startswith("VG-") and data["report_id"].endswith("-0001")
    assert data["snapshot_hashes"] == load_export()["snapshot_hashes"]
    assert data["files"] == {"json": f"/files/{data['report_id']}.json", "pdf": f"/files/{data['report_id']}.pdf"}
    assert data["supersedes"] is None and data["block_number"] == 1

    saved = (settings.report_dir / f"{data['report_id']}.json").read_bytes()
    assert sha256_hex(saved) == data["report_hash"]  # file is exactly the hashed canonical bytes
    assert (settings.report_dir / f"{data['report_id']}.pdf").read_bytes().startswith(b"%PDF")


def test_ids_increment_and_list_get(client: TestClient) -> None:
    first = client.post("/api/reports", json=BODY).json()
    second = client.post("/api/reports", json={**BODY, "supersedes": first["report_id"]}).json()
    assert second["report_id"].endswith("-0002") and second["supersedes"] == first["report_id"]

    items = client.get("/api/reports").json()["items"]
    assert [i["report_id"] for i in items] == [second["report_id"], first["report_id"]]
    assert items[1]["superseded_by"] == second["report_id"] and items[0]["superseded_by"] is None

    detail = client.get(f"/api/reports/{first['report_id']}").json()
    assert detail == {**first, "superseded_by": second["report_id"]}
    assert client.get("/api/reports/VG-2026-9999").status_code == 404


def test_chain_failure_writes_nothing(client: TestClient, settings: Any, stub_chain: StubChain) -> None:
    stub_chain.fail_with = ChainUnavailable("Chain node is not reachable at http://127.0.0.1:8545.")
    res = client.post("/api/reports", json=BODY)
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "CHAIN_UNAVAILABLE"
    assert files_in(settings) == []
    assert client.get("/api/reports").json() == {"items": []}


def test_skips_ids_already_on_chain(client: TestClient, stub_chain: StubChain) -> None:
    taken = client.post("/api/reports", json=BODY).json()["report_id"]
    # Simulate a wiped local store while the chain still has the id.
    client.app.state.services.store = type(client.app.state.services.store)(  # type: ignore[attr-defined]
        client.app.state.services.settings.db_path.with_name("fresh.sqlite3"))  # type: ignore[attr-defined]
    res = client.post("/api/reports", json=BODY)
    assert res.status_code == 201
    assert res.json()["report_id"] != taken


def test_already_superseded_is_409(client: TestClient, stub_chain: StubChain) -> None:
    first = client.post("/api/reports", json=BODY).json()["report_id"]
    stub_chain.fail_with = ContractRejected("Contract rejected the call: AlreadySuperseded", "AlreadySuperseded")
    res = client.post("/api/reports", json={**BODY, "supersedes": first})
    assert res.status_code == 409 and res.json()["error"]["code"] == "ALREADY_SUPERSEDED"


def test_unknown_supersedes_is_404(client: TestClient, settings: Any) -> None:
    res = client.post("/api/reports", json={**BODY, "supersedes": "VG-2026-0042"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "SUPERSEDED_REPORT_NOT_FOUND"
    assert files_in(settings) == []


def test_core_down_is_502(make_client: Callable[..., TestClient], settings: Any) -> None:
    res = make_client(core_down).post("/api/reports", json=BODY)
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "CORE_UNAVAILABLE"
    assert files_in(settings) == []


def test_unknown_audit_is_404(client: TestClient) -> None:
    res = client.post("/api/reports", json={**BODY, "audit_id": "aud_999"})
    assert res.status_code == 404 and res.json()["error"]["code"] == "AUDIT_NOT_FOUND"


def test_blank_reviewer_is_422(client: TestClient) -> None:
    res = client.post("/api/reports", json={**BODY, "reviewer_name": "   "})
    assert res.status_code == 422 and res.json()["error"]["code"] == "VALIDATION_ERROR"
