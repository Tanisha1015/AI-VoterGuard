"""SQLite store for recorded reports and report-id allocation."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

REPORT_ID_PATTERN = re.compile(r"^VG-(\d{4})-(\d{4,})$")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    report_id    TEXT PRIMARY KEY,
    report_hash  TEXT NOT NULL,
    tx_hash      TEXT NOT NULL,
    block_number INTEGER NOT NULL,
    recorded_at  TEXT NOT NULL,
    supersedes   TEXT,
    json_path    TEXT NOT NULL,
    pdf_path     TEXT NOT NULL,
    year         INTEGER NOT NULL,
    seq          INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS reports_year_seq ON reports(year, seq);
"""


@dataclass(frozen=True)
class ReportRow:
    """One recorded report. Only written after the chain transaction succeeded."""

    report_id: str
    report_hash: str
    tx_hash: str
    block_number: int
    recorded_at: str
    supersedes: str | None
    json_path: str
    pdf_path: str


def format_report_id(year: int, seq: int) -> str:
    """Report ids look like VG-2026-0001."""
    return f"VG-{year}-{seq:04d}"


def parse_report_id(report_id: str) -> tuple[int, int]:
    """Split a report id into (year, seq). Raises ValueError if malformed."""
    match = REPORT_ID_PATTERN.match(report_id)
    if not match:
        raise ValueError(f"Malformed report id: {report_id!r}")
    return int(match.group(1)), int(match.group(2))


class ReportStore:
    """Thin wrapper around a SQLite file. Safe to use from FastAPI's thread pool."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def next_report_id(self, year: int, min_seq: int = 1) -> str:
        """Next free id for `year` (not reserved; the caller inserts only after success)."""
        with self._connect() as conn:
            row = conn.execute("SELECT MAX(seq) FROM reports WHERE year = ?", (year,)).fetchone()
        seq = max((row[0] or 0) + 1, min_seq)
        return format_report_id(year, seq)

    def insert(self, row: ReportRow) -> None:
        year, seq = parse_report_id(row.report_id)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO reports (report_id, report_hash, tx_hash, block_number, recorded_at, supersedes,"
                " json_path, pdf_path, year, seq) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (*asdict(row).values(), year, seq),
            )

    def get(self, report_id: str) -> ReportRow | None:
        with self._connect() as conn:
            found = conn.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        return _to_row(found) if found else None

    def exists(self, report_id: str) -> bool:
        return self.get(report_id) is not None

    def list_all(self) -> list[ReportRow]:
        """Newest first."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM reports ORDER BY year DESC, seq DESC").fetchall()
        return [_to_row(r) for r in rows]

    def superseded_by(self, report_id: str) -> str | None:
        """Id of the stored report that supersedes `report_id`, if any."""
        with self._connect() as conn:
            found = conn.execute(
                "SELECT report_id FROM reports WHERE supersedes = ? ORDER BY year, seq LIMIT 1", (report_id,)
            ).fetchone()
        return found[0] if found else None


def _to_row(row: sqlite3.Row) -> ReportRow:
    return ReportRow(
        report_id=row["report_id"],
        report_hash=row["report_hash"],
        tx_hash=row["tx_hash"],
        block_number=row["block_number"],
        recorded_at=row["recorded_at"],
        supersedes=row["supersedes"],
        json_path=row["json_path"],
        pdf_path=row["pdf_path"],
    )
