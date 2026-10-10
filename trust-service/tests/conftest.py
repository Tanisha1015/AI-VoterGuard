"""Shared fixtures: isolated settings, a stub chain, and a mocked core API."""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.chain import ChainUnavailable, ContractRejected, RecordResult
from app.config import load_settings
from app.deps import Services
from app.main import create_app
from app.store import ReportStore

FIXTURES = Path(__file__).parent / "fixtures"


def load_export() -> dict[str, Any]:
    return json.loads((FIXTURES / "export.json").read_text(encoding="utf-8"))


class StubChain:
    """In-memory stub for ChainClient with the same public methods."""

    def __init__(self) -> None:
        self.reports: dict[str, dict[str, Any]] = {}
        self.superseded: dict[str, str] = {}
        self.fail_with: Exception | None = None
        self.block = 0

    def record_report(self, report_id: str, report_hash: str, draft_hash: str, final_hash: str,
                      asdd_hash: str, supersedes: str | None) -> RecordResult:
        if self.fail_with:
            raise self.fail_with
        if report_id in self.reports:
            raise ContractRejected("Contract rejected the call: ReportExists", "ReportExists", (report_id,))
        self.block += 1
        recorded_at = "2026-10-10T10:05:00Z"
        self.reports[report_id] = {
            "report_hash": report_hash, "draft_hash": draft_hash, "final_hash": final_hash,
            "asdd_hash": asdd_hash, "recorded_at": recorded_at,
            "submitter": "0x70997970c51812dc3a010c7d01b50e0d17dc79c8", "supersedes": supersedes,
        }
        if supersedes:
            self.superseded[supersedes] = report_id
        return RecordResult(tx_hash="0x" + f"{self.block:064x}", block_number=self.block, recorded_at=recorded_at)

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        if isinstance(self.fail_with, ChainUnavailable):
            raise self.fail_with
        return self.reports.get(report_id)

    def superseded_by(self, report_id: str) -> str | None:
        return self.superseded.get(report_id)

    def status(self) -> dict[str, Any]:
        return {"connected": True, "chain_id": 31337, "contract_address": "0x" + "ab" * 20, "latest_block": self.block}


CoreHandler = Callable[[httpx.Request], httpx.Response]


def core_ok(export: dict[str, Any] | None = None) -> CoreHandler:
    payload = export or load_export()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/api/audits/{payload['audit_id']}/export":
            return httpx.Response(200, json=copy.deepcopy(payload))
        return httpx.Response(404, json={"error": {"code": "NOT_FOUND", "message": "unknown audit"}})

    return handler


def core_down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)


@pytest.fixture
def settings(tmp_path: Path) -> Any:
    base = load_settings()
    return replace(base, report_dir=tmp_path / "reports", db_path=tmp_path / "trust.sqlite3",
                   assets_dir=tmp_path / "assets")


@pytest.fixture
def stub_chain() -> StubChain:
    return StubChain()


@pytest.fixture
def make_client(settings: Any, stub_chain: StubChain) -> Iterator[Callable[[CoreHandler], TestClient]]:
    """Factory: build a TestClient whose core API is served by `handler`."""
    clients: list[TestClient] = []

    def build(handler: CoreHandler = core_ok()) -> TestClient:
        settings.report_dir.mkdir(parents=True, exist_ok=True)
        services = Services(
            settings=settings,
            store=ReportStore(settings.db_path),
            chain=stub_chain,  # type: ignore[arg-type]
            core_http=httpx.Client(base_url="http://core.test", transport=httpx.MockTransport(handler)),
        )
        client = TestClient(create_app(services=services))
        clients.append(client)
        return client

    yield build
    for c in clients:
        c.close()


@pytest.fixture
def client(make_client: Callable[[CoreHandler], TestClient]) -> TestClient:
    return make_client(core_ok())
