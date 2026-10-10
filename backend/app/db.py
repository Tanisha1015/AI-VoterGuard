"""SQLModel tables and the SQLite engine (data/voterguard.db).

The data directory is ``DATA_DIR`` (env, read on every call so tests can point it elsewhere) and
defaults to ``backend/data``. It also holds ``synthetic/`` and ``audits/{audit_id}/``.
"""

import os
import threading
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, create_engine, select

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_FILENAME = "voterguard.db"


class AuditRow(SQLModel, table=True):
    """One audit: snapshot hashes plus JSON blobs for the summary, the booths and the baseline."""

    __tablename__ = "audit"

    audit_id: str = Field(primary_key=True)
    ac_no: int
    ac_name: str
    created_at: str
    draft_hash: str
    final_hash: str
    asdd_hash: str
    summary_json: str  # {"totals": {...}, "reason_mix": {...}}
    booths_json: str  # list of booth dicts (summary fields + gender_removed + age_band_removed_share)
    baseline_json: str  # constituency baseline (deletion_rate, deletion_rate_mad, reason_mix, ...)


class FlagRow(SQLModel, table=True):
    """One flag with its explanation and its human review (review_* columns)."""

    __tablename__ = "flag"

    audit_id: str = Field(primary_key=True, foreign_key="audit.audit_id")
    flag_id: str = Field(primary_key=True)
    seq: int  # keeps the detector order
    part_no: int = Field(index=True)
    detector: str
    severity: str
    metric_name: str
    metric_value: float
    metric_baseline: float
    explanation_en: str
    explanation_hi: str
    checks_json: str  # list of {"en": ..., "hi": ...}
    explanation_source: str  # "agent" or "template"
    review_status: str = "PENDING"
    review_note: Optional[str] = None
    reviewed_at: Optional[str] = None


_ENGINES: dict[str, Engine] = {}
_LOCK = threading.Lock()
CREATE_LOCK = threading.Lock()  # serialises audit-id allocation and persistence


def data_dir() -> Path:
    """Directory that holds the database, the synthetic CSVs and the per-audit CSV copies."""
    return Path(os.environ.get("DATA_DIR") or DEFAULT_DATA_DIR)


def audit_dir(audit_id: str) -> Path:
    """Directory with the three CSVs of one audit (draft_roll.csv, final_roll.csv, asdd.csv)."""
    return data_dir() / "audits" / audit_id


def now_iso() -> str:
    """Current UTC time as an ISO-8601 string with a trailing Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_engine() -> Engine:
    """Return the engine for the current data directory, creating the tables on first use."""
    path = data_dir() / DB_FILENAME
    key = str(path)
    with _LOCK:
        engine = _ENGINES.get(key)
        if engine is None:
            path.parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
            SQLModel.metadata.create_all(engine)
            _ENGINES[key] = engine
    return engine


def reset_engine() -> None:
    """Dispose every cached engine (used by tests after changing DATA_DIR)."""
    with _LOCK:
        for engine in _ENGINES.values():
            engine.dispose()
        _ENGINES.clear()


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""
    with Session(get_engine()) as session:
        yield session


def audit_exists() -> bool:
    """True when at least one audit has been stored."""
    with Session(get_engine()) as session:
        return session.exec(select(AuditRow.audit_id).limit(1)).first() is not None


def latest_audit_id(session: Session) -> Optional[str]:
    """The id of the newest audit, or None when there is none."""
    ids = session.exec(select(AuditRow.audit_id)).all()
    return max(ids) if ids else None


def next_audit_id(session: Session) -> str:
    """Next id in the sequence aud_001, aud_002, ...

    Ids already stored in the database and audit directories already reserved on disk both count,
    so two audits running at once never share an id.
    """
    ids = list(session.exec(select(AuditRow.audit_id)).all())
    root = data_dir() / "audits"
    if root.is_dir():
        ids += [p.name for p in root.iterdir() if p.is_dir()]
    numbers = [int(i.split("_")[1]) for i in ids if i.startswith("aud_") and i.split("_")[1].isdigit()]
    return f"aud_{(max(numbers) if numbers else 0) + 1:03d}"
