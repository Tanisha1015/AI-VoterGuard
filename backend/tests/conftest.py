"""Shared pytest fixtures for the core API tests.

Every test runs against its own temporary DATA_DIR, so tests never touch backend/data. An audit is
built once per test session (agent service unreachable, so explanations come from templates) and
copied into each test's data directory that asks for the ``client`` fixture.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.ratelimit import citizen_limiter
from app.services import citizen as citizen_service
from app.services import pipeline

UNREACHABLE_AGENT = "http://127.0.0.1:9"  # nothing listens here, so every call fails fast
CLAIMS_DEADLINE = "2026-10-31"


def _reset_state() -> None:
    db.reset_engine()
    citizen_service.clear_cache()
    citizen_limiter.reset()


@pytest.fixture(scope="session")
def seeded_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A data directory that already holds aud_001 built from the synthetic rolls."""
    template = tmp_path_factory.mktemp("seeded")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATA_DIR", str(template))
        mp.setenv("AGENT_URL", UNREACHABLE_AGENT)
        mp.delenv("AUTO_SEED", raising=False)
        _reset_state()
        assert pipeline.run_synthetic_pipeline() == "aud_001"
        db.reset_engine()
    return template


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point DATA_DIR at an empty temp directory and use safe defaults for the environment."""
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("AGENT_URL", UNREACHABLE_AGENT)
    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("CLAIMS_DEADLINE", CLAIMS_DEADLINE)
    monkeypatch.delenv("AUTO_SEED", raising=False)
    _reset_state()
    yield data
    _reset_state()


@pytest.fixture()
def empty_client() -> TestClient:
    """A client whose data directory has no audits."""
    return TestClient(app)


@pytest.fixture()
def client(seeded_template: Path, isolated_env: Path) -> TestClient:
    """A client whose data directory is a private copy of the seeded one (aud_001 exists)."""
    shutil.copytree(seeded_template, isolated_env, dirs_exist_ok=True)
    _reset_state()
    return TestClient(app)


@pytest.fixture()
def demo_voters(seeded_template: Path) -> dict[str, dict[str, object]]:
    """The known synthetic voters: removed, present and added (from demo_voters.json)."""
    import json

    return json.loads((seeded_template / "synthetic" / "demo_voters.json").read_text(encoding="utf-8"))
