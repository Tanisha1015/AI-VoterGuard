"""Shared service objects, created once per app and overridable in tests."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

import httpx

from .chain import ChainClient
from .config import Settings
from .store import ReportStore


@dataclass
class Services:
    """Everything a request handler needs. Tests replace `chain` and `core_http` with stubs."""

    settings: Settings
    store: ReportStore
    chain: ChainClient
    core_http: httpx.Client
    create_lock: Lock = field(default_factory=Lock)


def build_services(settings: Settings) -> Services:
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    return Services(
        settings=settings,
        store=ReportStore(settings.db_path),
        chain=ChainClient(settings),
        core_http=httpx.Client(base_url=settings.core_url, timeout=settings.core_timeout_seconds),
    )
