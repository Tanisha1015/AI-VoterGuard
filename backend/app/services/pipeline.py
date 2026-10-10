"""Audit pipeline: hash -> compare -> aggregate -> detect -> explain -> persist.

Every number, flag and score comes from deterministic code (``app.engine`` and ``app.detectors``).
The agent service may only phrase the explanation text; when it cannot, ``templates`` is used.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Optional

import httpx
import pandas as pd
from sqlmodel import Session

from app import db
from app.detectors.base import Flag
from app.detectors.registry import run_all
from app.engine import config as cfg
from app.engine.aggregate import aggregate_booths, constituency_baseline
from app.engine.compare import compare, load_rolls
from app.engine.hashing import sha256_file
from app.services import agent_client, templates
from app.synth.generate import AC_NAME as SYNTHETIC_AC_NAME
from app.synth.generate import generate
from app.synth.names import AC_NO as SYNTHETIC_AC_NO

CSV_NAMES = {"draft": "draft_roll.csv", "final": "final_roll.csv", "asdd": "asdd.csv"}
SYNTHETIC_SEED = 42
ROUND_DIGITS = 4
SUMMARY_KEYS = (
    "part_no", "draft_count", "final_count", "removed", "added", "deletion_rate", "reason_mix",
    "female_removed_share", "risk_score", "flagged", "flag_count",
)

Explained = tuple[dict[str, str], list[dict[str, str]], str]  # (explanation, checks, source)


# ------------------------------------------------------------------ booth and flag records


def _booth_records(booth_df: pd.DataFrame, flags: list[Flag]) -> list[dict[str, Any]]:
    """One plain-Python dict per booth: the contract BoothSummary fields plus the detail fields."""
    per_booth: dict[int, int] = {}
    for flag in flags:
        per_booth[flag.part_no] = per_booth.get(flag.part_no, 0) + 1
    records: list[dict[str, Any]] = []
    for row in booth_df.to_dict("records"):
        part_no = int(row["part_no"])
        records.append({
            "part_no": part_no,
            "draft_count": int(row["draft_count"]),
            "final_count": int(row["final_count"]),
            "removed": int(row["removed"]),
            "added": int(row["added"]),
            "deletion_rate": round(float(row["deletion_rate"]), ROUND_DIGITS),
            "reason_mix": {r: round(float(row["reason_mix"][r]), ROUND_DIGITS) for r in cfg.REASONS},
            "female_removed_share": round(float(row["female_removed_share"]), ROUND_DIGITS),
            "risk_score": int(row["risk_score"]),
            "flagged": bool(row["flagged"]),
            "flag_count": per_booth.get(part_no, 0),
            "gender_removed": {g: int(row["gender_removed"][g]) for g in cfg.GENDERS},
            "age_band_removed_share": {
                b: round(float(row["age_band_removed_share"][b]), ROUND_DIGITS)
                for b in cfg.AGE_BAND_LABELS
            },
        })
    return records


def booth_summary(record: dict[str, Any]) -> dict[str, Any]:
    """The BoothSummary subset of a stored booth record (this is what the agent receives)."""
    return {k: record[k] for k in SUMMARY_KEYS}


def _flag_dict(flag: Flag) -> dict[str, Any]:
    """The flag fields the agent request needs: detector, severity and metric."""
    return {
        "detector": flag.detector.value,
        "severity": flag.severity.value,
        "metric": {
            "name": flag.metric_name,
            "value": round(flag.metric_value, ROUND_DIGITS),
            "baseline": round(flag.baseline, ROUND_DIGITS),
        },
    }


# ------------------------------------------------------------------ explanations


def _template_explanation(flag: Flag, booth: dict[str, Any]) -> Explained:
    explanation, checks = templates.explain_flag(
        flag.detector.value, flag.metric_name, round(flag.metric_value, ROUND_DIGITS),
        round(flag.baseline, ROUND_DIGITS), flag.part_no, booth,
    )
    return explanation, checks, "template"


async def _explain_one(
    audit_id: str, flag: Flag, booth: dict[str, Any], baseline: dict[str, Any],
    client: httpx.AsyncClient, semaphore: asyncio.Semaphore,
) -> Explained:
    """Ask the agent; on ANY failure use the template and mark the source as "template"."""
    try:
        reply = await agent_client.explain(
            audit_id, booth_summary(booth), _flag_dict(flag), baseline, client, semaphore
        )
    except Exception:  # noqa: BLE001 - every failure mode falls back to the neutral template
        return _template_explanation(flag, booth)
    return (
        reply.explanation.model_dump(),
        [check.model_dump() for check in reply.recommended_checks],
        "agent",
    )


async def _explain_all(
    audit_id: str, flags: list[Flag], booths: dict[int, dict[str, Any]], baseline: dict[str, Any]
) -> list[Explained]:
    """Explain every flag, with at most 3 agent calls in flight at once."""
    semaphore = agent_client.new_semaphore()
    async with httpx.AsyncClient() as client:
        tasks = [_explain_one(audit_id, f, booths[f.part_no], baseline, client, semaphore) for f in flags]
        return list(await asyncio.gather(*tasks))


# ------------------------------------------------------------------ persistence


def _reserve_audit_id() -> str:
    """Allocate the next audit id and reserve it by creating its directory."""
    with db.CREATE_LOCK:
        with Session(db.get_engine()) as session:
            audit_id = db.next_audit_id(session)
        db.audit_dir(audit_id).mkdir(parents=True, exist_ok=False)
    return audit_id


def _copy_csvs(audit_id: str, paths: dict[str, Path]) -> None:
    """Copy the three CSVs to data/audits/{audit_id}/ for the citizen lookup."""
    target = db.audit_dir(audit_id)
    for key, source in paths.items():
        shutil.copyfile(source, target / CSV_NAMES[key])


def _ac_identity(draft: pd.DataFrame, ac_name: Optional[str]) -> tuple[int, str]:
    """(ac_no, ac_name): the AC number comes from the draft roll; the synthetic one has a known name."""
    ac_no = int(draft["ac_no"].iloc[0]) if len(draft) else 0
    if ac_name:
        return ac_no, ac_name
    return ac_no, SYNTHETIC_AC_NAME if ac_no == SYNTHETIC_AC_NO else f"Constituency {ac_no}"


def _store(
    audit_id: str, ac_no: int, ac_name: str, hashes: dict[str, str], totals: dict[str, int],
    baseline: dict[str, Any], booths: list[dict[str, Any]], flags: list[Flag],
    explained: list[Explained],
) -> None:
    """Insert the Audit row and the Flag rows in one transaction."""
    audit = db.AuditRow(
        audit_id=audit_id, ac_no=ac_no, ac_name=ac_name, created_at=db.now_iso(),
        draft_hash=hashes["draft"], final_hash=hashes["final"], asdd_hash=hashes["asdd"],
        summary_json=json.dumps({"totals": totals, "reason_mix": baseline["reason_mix"]}),
        booths_json=json.dumps(booths),
        baseline_json=json.dumps(baseline),
    )
    rows = []
    for seq, (flag, (explanation, checks, source)) in enumerate(zip(flags, explained)):
        rows.append(db.FlagRow(
            audit_id=audit_id, flag_id=flag.flag_id, seq=seq, part_no=flag.part_no,
            detector=flag.detector.value, severity=flag.severity.value, metric_name=flag.metric_name,
            metric_value=round(flag.metric_value, ROUND_DIGITS),
            metric_baseline=round(flag.baseline, ROUND_DIGITS),
            explanation_en=explanation["en"], explanation_hi=explanation["hi"],
            checks_json=json.dumps(checks, ensure_ascii=False), explanation_source=source,
        ))
    with Session(db.get_engine()) as session:
        session.add(audit)
        session.add_all(rows)
        session.commit()


# ------------------------------------------------------------------ public entry points


def run_pipeline(
    draft_path: str | Path, final_path: str | Path, asdd_path: str | Path,
    ac_name: Optional[str] = None,
) -> str:
    """Run the full audit pipeline on three CSV files and return the new audit id (aud_001, ...).

    Raises ValueError (from the CSV loader) when a file does not follow the CSV schema. It is a
    blocking function (it runs its own event loop for the agent calls), so call it with
    ``asyncio.to_thread`` or from a sync endpoint, never directly inside a running event loop.
    """
    paths = {"draft": Path(draft_path), "final": Path(final_path), "asdd": Path(asdd_path)}
    hashes = {key: sha256_file(path) for key, path in paths.items()}
    draft, final, asdd = load_rolls(paths["draft"], paths["final"], paths["asdd"])
    result = compare(draft, final, asdd)
    booth_df = aggregate_booths(result, draft, final)
    baseline = constituency_baseline(booth_df)
    flags, scored = run_all(booth_df, draft, final, result, baseline)
    booths = _booth_records(scored, flags)
    totals = {
        "draft_count": len(draft), "final_count": len(final), "removed": len(result.removed),
        "added": len(result.added), "modified": len(result.modified), "booths": len(booths),
        "flagged_booths": sum(1 for b in booths if b["flagged"]), "flags": len(flags),
    }
    ac_no, name = _ac_identity(draft, ac_name)

    audit_id = _reserve_audit_id()
    try:
        by_part = {b["part_no"]: b for b in booths}
        explained = asyncio.run(_explain_all(audit_id, flags, by_part, baseline))
        _copy_csvs(audit_id, paths)
        _store(audit_id, ac_no, name, hashes, totals, baseline, booths, flags, explained)
    except BaseException:
        shutil.rmtree(db.audit_dir(audit_id), ignore_errors=True)
        raise
    return audit_id


def ensure_synthetic() -> Path:
    """Return data/synthetic, generating the synthetic rolls first when they are missing."""
    out = db.data_dir() / "synthetic"
    if not all((out / name).exists() for name in CSV_NAMES.values()):
        generate(out, SYNTHETIC_SEED)
    return out


def run_synthetic_pipeline() -> str:
    """Run the pipeline on the synthetic Demo Nagar rolls (generated on first use)."""
    out = ensure_synthetic()
    return run_pipeline(out / CSV_NAMES["draft"], out / CSV_NAMES["final"], out / CSV_NAMES["asdd"])

