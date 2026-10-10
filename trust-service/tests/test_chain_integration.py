"""End-to-end against the Hardhat node (run with: pytest -m chain).

Needs: `npm run node` and `npm run deploy:local` in chain/, and SUBMITTER_PRIVATE_KEY set to
Hardhat account #1's key. The core API is mocked with tests/fixtures/export.json.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.chain import ChainClient
from app.config import load_settings
from app.deps import Services
from app.main import create_app
from app.store import ReportStore
from tests.conftest import core_ok

pytestmark = pytest.mark.chain


@pytest.fixture
def live_client(tmp_path: Any) -> TestClient:
    settings = replace(load_settings(), report_dir=tmp_path / "reports", db_path=tmp_path / "trust.sqlite3")
    chain = ChainClient(settings)
    status = chain.status()
    if not status["connected"]:
        pytest.skip(f"Hardhat node/contract not available at {settings.chain_rpc_url}; start it and deploy first.")
    if not settings.submitter_private_key:
        pytest.fail("SUBMITTER_PRIVATE_KEY is not set (use Hardhat account #1's key).")
    settings.report_dir.mkdir(parents=True)
    store = ReportStore(settings.db_path)
    # Start past ids already used on this node by earlier runs (local store is fresh per test).
    services = Services(settings, store, chain,
                        httpx.Client(base_url="http://core.test", transport=httpx.MockTransport(core_ok())))
    return TestClient(create_app(services=services))


def verify(client: TestClient, data: bytes) -> dict[str, Any]:
    res = client.post("/api/reports/verify", files={"file": ("report.json", data, "application/json")})
    assert res.status_code == 200, res.text
    return res.json()  # type: ignore[no-any-return]


def test_record_verify_tamper_supersede(live_client: TestClient) -> None:
    body = {"audit_id": "aud_001", "reviewer_name": "R. Sharma", "supersedes": None}
    first_res = live_client.post("/api/reports", json=body)
    assert first_res.status_code == 201, first_res.text
    first = first_res.json()
    assert first["tx_hash"].startswith("0x") and first["block_number"] > 0

    saved = live_client.get(first["files"]["json"]).content
    match = verify(live_client, saved)
    assert match["status"] == "MATCH" and match["onchain_hash"] == first["report_hash"]
    assert match["submitter"] == "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"

    tampered = saved.replace(b'"removed":182', b'"removed":183', 1)
    assert tampered != saved and len(tampered) == len(saved)
    assert verify(live_client, tampered)["status"] == "MISMATCH"

    second_res = live_client.post("/api/reports", json={**body, "supersedes": first["report_id"]})
    assert second_res.status_code == 201, second_res.text
    second = second_res.json()
    assert second["supersedes"] == first["report_id"]

    detail = live_client.get(f"/api/reports/{first['report_id']}").json()
    assert detail["superseded_by"] == second["report_id"]
    assert verify(live_client, saved)["superseded_by"] == second["report_id"]
    assert live_client.get("/api/chain/status").json()["connected"] is True
