"""Configuration read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent


def _path(value: str, base: Path) -> Path:
    """Resolve a possibly relative path against `base`."""
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Paths are absolute."""

    core_url: str
    chain_rpc_url: str
    submitter_private_key: str
    report_dir: Path
    db_path: Path
    deployments_dir: Path
    assets_dir: Path
    core_timeout_seconds: float

    @property
    def deployment_file(self) -> Path:
        return self.deployments_dir / "local.json"

    @property
    def abi_file(self) -> Path:
        return self.deployments_dir / "ReportRegistry.abi.json"

    @property
    def hindi_font_file(self) -> Path:
        return self.assets_dir / "NotoSansDevanagari-Regular.ttf"


def load_settings() -> Settings:
    """Build settings from the current environment."""
    report_dir = _path(os.getenv("REPORT_DIR", "./data/reports"), SERVICE_ROOT)
    return Settings(
        core_url=os.getenv("CORE_URL", "http://localhost:8000").rstrip("/"),
        chain_rpc_url=os.getenv("CHAIN_RPC_URL", "http://127.0.0.1:8545"),
        submitter_private_key=os.getenv("SUBMITTER_PRIVATE_KEY", "").strip(),
        report_dir=report_dir,
        db_path=_path(os.getenv("TRUST_DB_PATH", str(report_dir.parent / "trust.sqlite3")), SERVICE_ROOT),
        deployments_dir=_path(os.getenv("DEPLOYMENTS_DIR", str(REPO_ROOT / "chain" / "deployments")), SERVICE_ROOT),
        assets_dir=_path(os.getenv("ASSETS_DIR", "./assets"), SERVICE_ROOT),
        core_timeout_seconds=float(os.getenv("CORE_TIMEOUT_SECONDS", "10")),
    )
