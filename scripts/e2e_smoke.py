#!/usr/bin/env python3
"""End-to-end smoke test for VoterGuard India. No browser needed.

Exercises the running core API, agent service, trust service and local chain through their
public HTTP endpoints (contracts/CONTRACT.md), prints a PASS/FAIL list and exits non-zero if
any check fails.

Usage:
    python3 scripts/e2e_smoke.py [--seed]

Environment (defaults match .env.example):
    CORE_URL=http://localhost:8000  AGENT_URL=http://localhost:8001  TRUST_URL=http://localhost:8002

Start the services first (core with AUTO_SEED=true, agent, trust, local chain), or pass --seed
to create a synthetic audit when the core has none. Synthetic data only.
Note: the review step changes one flag's review status and the report steps record new reports.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import httpx

CORE_URL = os.environ.get("CORE_URL", "http://localhost:8000").rstrip("/")
AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8001").rstrip("/")
TRUST_URL = os.environ.get("TRUST_URL", "http://localhost:8002").rstrip("/")
TIMEOUT_SECONDS = 60.0  # report creation builds a PDF and waits for a chain transaction

BOOTH = 17
REQUIRED_DETECTORS = {"DELETION_RATE", "REASON_DOMINANCE", "GENDER_SKEW"}
REVIEWER = "Smoke Test"

# English words that must never appear in flag text (whole-word, with common suffixes).
FORBIDDEN_ENGLISH = re.compile(
    r"\b(fraud\w*|illegal\w*|rigging|rigged|fake\w*|ineligible|ineligibility)\b", re.IGNORECASE
)
# Hindi stems, matched as substrings after nukta marks are removed (same idea as the agent guard).
FORBIDDEN_HINDI = (
    "धोखाधड़ी", "फर्जी", "फ़र्ज़ी", "जाली", "अवैध", "गैरकानूनी", "धांधली", "हेराफेरी", "अपात्र", "घुसपैठ",
)
EPIC_MASKED = re.compile(r"^VGX\*{4}[0-9A-Za-z]{3}$")
RAW_EPIC = re.compile(r"VGX\d{7}")
HASH_RE = re.compile(r"^0x[0-9a-f]{64}$")


# ------------------------------------------------------------------ pure helpers


def strip_nukta(text: str) -> str:
    """Decompose Devanagari and drop nukta marks so spelling variants compare equal."""
    return unicodedata.normalize("NFD", text).replace("\u093c", "")


def forbidden_words(text: str) -> list[str]:
    """Return the forbidden English or Hindi words found in ``text`` (empty list when clean)."""
    found = [m.group(0).lower() for m in FORBIDDEN_ENGLISH.finditer(text)]
    plain = strip_nukta(text)
    found += [stem for stem in FORBIDDEN_HINDI if strip_nukta(stem) in plain]
    return found


def flag_texts(flag: dict[str, Any]) -> list[str]:
    """Every human-readable string of a flag: explanation and recommended checks, both languages."""
    items = [flag["explanation"], *flag["recommended_checks"]]
    return [text for item in items for text in (item["en"], item["hi"])]


def flip_one_character(data: bytes, needle: bytes) -> bytes:
    """Change the last character of the first ``needle`` in ``data`` (a letter or digit moves by one)."""
    index = data.find(needle)
    if index < 0:
        raise AssertionError(f"could not find {needle!r} in the report file")
    pos = index + len(needle) - 1
    changed = data[pos] + 1 if data[pos] not in (0x7A, 0x5A, 0x39) else data[pos] - 1
    return data[:pos] + bytes([changed]) + data[pos + 1:]


def sha256_0x(data: bytes) -> str:
    """Contract hash format: lowercase 0x + 64 hex characters."""
    return "0x" + hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ runner


@dataclass
class Runner:
    """Runs named checks, records PASS/FAIL, and keeps values shared between checks."""

    results: list[tuple[str, bool, str]] = field(default_factory=list)
    ctx: dict[str, Any] = field(default_factory=dict)

    def check(self, name: str, fn: Callable[[], Optional[str]]) -> bool:
        """Run ``fn``; it raises on failure and may return a short detail string."""
        try:
            detail = fn() or ""
            ok = True
        except AssertionError as exc:
            detail, ok = f"{exc}", False
        except KeyError as exc:
            detail, ok = f"missing {exc} (an earlier check failed, or the response shape differs)", False
        except Exception as exc:  # a smoke script must report, not crash
            detail, ok = f"{type(exc).__name__}: {exc}", False
        self.results.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""), flush=True)
        return ok

    def section(self, title: str) -> None:
        print(f"\n== {title}")

    def summary(self) -> int:
        """Print the totals and return the process exit code."""
        failed = [name for name, ok, _ in self.results if not ok]
        print(f"\n== Summary: {len(self.results) - len(failed)} passed, {len(failed)} failed")
        for name in failed:
            print(f"   FAIL: {name}")
        print("RESULT: " + ("PASS" if not failed else "FAIL"))
        return 1 if failed else 0


def need(ctx: dict[str, Any], key: str) -> Any:
    """Fetch a value saved by an earlier check, or fail clearly."""
    if key not in ctx:
        raise AssertionError(f"skipped: needs '{key}' from an earlier failed check")
    return ctx[key]


def expect(res: httpx.Response, status: int) -> Any:
    """Assert the HTTP status and return the JSON body."""
    assert res.status_code == status, f"{res.request.method} {res.request.url.path} -> {res.status_code} {res.text[:200]}"
    return res.json()


# ------------------------------------------------------------------ check groups


def check_health(run: Runner, http: httpx.Client) -> None:
    run.section("1. Service health")

    def core() -> str:
        body = expect(http.get(f"{CORE_URL}/api/health"), 200)
        assert body.get("audit_ready") is True, (
            f"audit_ready is {body.get('audit_ready')} (start core with AUTO_SEED=true or pass --seed)"
        )
        return "audit_ready true"

    def agent() -> str:
        body = expect(http.get(f"{AGENT_URL}/health"), 200)
        assert body.get("status") == "ok", f"status is {body.get('status')}"
        return f"mode {body.get('mode')}"

    def chain() -> str:
        body = expect(http.get(f"{TRUST_URL}/api/chain/status"), 200)
        assert body.get("connected") is True, f"connected is {body.get('connected')}"
        return f"chain_id {body.get('chain_id')}, block {body.get('latest_block')}"

    run.check("core GET /api/health audit_ready true", core)
    run.check("agent GET /health", agent)
    run.check("trust GET /api/chain/status connected true", chain)


def audit_url(run: Runner) -> str:
    return f"{CORE_URL}/api/audits/{need(run.ctx, 'audit_id')}"


def check_audit(run: Runner, http: httpx.Client) -> None:
    run.section("2. Audit, booths and flags")

    def list_audits() -> str:
        items = expect(http.get(f"{CORE_URL}/api/audits"), 200)["items"]
        assert items, "no audits found"
        run.ctx["audit_id"] = items[0]["audit_id"]
        return f"using {run.ctx['audit_id']}"

    def summary() -> str:
        body = expect(http.get(f"{audit_url(run)}/summary"), 200)
        assert body["audit_id"] == run.ctx["audit_id"], "audit_id differs"
        assert all(HASH_RE.match(h) for h in body["snapshot_hashes"].values()), "snapshot hashes are not 0x+64 hex"
        totals = body["totals"]
        assert totals["flags"] > 0 and totals["flagged_booths"] > 0, "no flags in summary"
        return f"{totals['flags']} flags in {totals['flagged_booths']} booths"

    def booths() -> str:
        items = expect(http.get(f"{audit_url(run)}/booths"), 200)["items"]
        scores = [b["risk_score"] for b in items]
        assert scores == sorted(scores, reverse=True), "booths are not sorted by risk_score descending"
        booth = next((b for b in items if b["part_no"] == BOOTH), None)
        assert booth is not None, f"booth {BOOTH} not in list"
        assert booth["flagged"] is True, f"booth {BOOTH} is not flagged"
        return f"{len(items)} booths"

    def booth_detail() -> str:
        body = expect(http.get(f"{audit_url(run)}/booths/{BOOTH}"), 200)
        run.ctx["booth_flags"] = body["flags"]
        assert body["part_no"] == BOOTH and body["flagged"] is True, f"booth {BOOTH} is not flagged"
        found = {f["detector"] for f in body["flags"]}
        missing = sorted(REQUIRED_DETECTORS - found)
        assert not missing, f"missing detectors {missing}; got {sorted(found)}"
        assert {"F", "M", "O"} <= set(body["gender_removed"]), "gender_removed keys"
        return "detectors " + ", ".join(sorted(found))

    def flags() -> str:
        items = expect(http.get(f"{audit_url(run)}/flags"), 200)["items"]
        assert items, "no flags returned"
        run.ctx["flags"] = items
        found = {f["detector"] for f in items if f["part_no"] == BOOTH}
        assert REQUIRED_DETECTORS <= found, f"flags list for booth {BOOTH} has {sorted(found)}"
        filtered = expect(http.get(f"{audit_url(run)}/flags", params={"part_no": BOOTH}), 200)["items"]
        assert filtered and all(f["part_no"] == BOOTH for f in filtered), "part_no filter"
        return f"{len(items)} flags"

    def neutral_language() -> str:
        flags_ = need(run.ctx, "flags") + need(run.ctx, "booth_flags")
        hits = [(f["flag_id"], w) for f in flags_ for text in flag_texts(f) for w in forbidden_words(text)]
        assert not hits, f"forbidden words in flag text: {hits[:5]}"
        sources = sorted({f["explanation_source"] for f in flags_})
        return f"{len(flags_)} flags checked, explanation_source {sources}"

    run.check("GET /api/audits (first audit_id)", list_audits)
    run.check("GET summary", summary)
    run.check("GET booths", booths)
    run.check(f"GET booth {BOOTH} detail flagged with {', '.join(sorted(REQUIRED_DETECTORS))}", booth_detail)
    run.check("GET flags", flags)
    run.check("no forbidden words in flag text (English and Hindi)", neutral_language)


def lookup(http: httpx.Client, name: str, relative: str, part_no: int = BOOTH) -> dict[str, Any]:
    """POST /api/citizen/lookup by name, relative's name and booth."""
    body = {"name": name, "relative_name": relative, "part_no": part_no, "epic_no": None, "lang": "en"}
    return expect(http.post(f"{CORE_URL}/api/citizen/lookup", json=body), 200)


def check_citizen(run: Runner, http: httpx.Client) -> None:
    run.section("3. Citizen lookup")

    def removed(name: str) -> Callable[[], str]:
        def run_check() -> str:
            body = lookup(http, name, "Ramesh Kumar")
            assert body["status"] == "REMOVED", f"status {body['status']}"
            assert body["reason"] == "SHIFTED", f"reason {body['reason']}"
            run.ctx.setdefault("citizen_responses", []).append(body)
            return f"confidence {body['match_confidence']}"
        return run_check

    def not_found() -> str:
        body = lookup(http, "Zzyzx Qwertyuiop", "Nobody Atall")
        assert body["status"] == "NOT_FOUND", f"status {body['status']}"
        assert body["record"] is None and body["reason"] is None, "record and reason should be null"
        return ""

    def masked() -> str:
        bodies = need(run.ctx, "citizen_responses")
        for body in bodies:
            epic = body["record"]["epic_masked"]
            assert EPIC_MASKED.match(epic), f"EPIC not masked: {epic}"
            assert not RAW_EPIC.search(str(body)), "response contains an unmasked EPIC"
        return bodies[0]["record"]["epic_masked"]

    run.check("lookup Sunita Devi / Ramesh Kumar / part 17 -> REMOVED, SHIFTED", removed("Sunita Devi"))
    run.check("lookup Sunitha Devi (spelling variant) -> REMOVED, SHIFTED", removed("Sunitha Devi"))
    run.check("lookup unknown name -> NOT_FOUND", not_found)
    run.check("EPIC is masked in the response", masked)


def check_review(run: Runner, http: httpx.Client) -> None:
    run.section("4. Human review")

    def pending() -> int:
        return int(expect(http.get(f"{audit_url(run)}/export"), 200)["summary"]["totals"]["pending_reviews"])

    def review() -> str:
        flags_ = expect(http.get(f"{audit_url(run)}/flags"), 200)["items"]
        target = next((f for f in flags_ if f["review"]["status"] == "PENDING"), None)
        if target is None:  # a rerun where everything was already reviewed: reset one flag first
            target = flags_[0]
            reset = {"status": "PENDING", "note": None}
            expect(http.put(f"{audit_url(run)}/flags/{target['flag_id']}/review", json=reset), 200)
        before = pending()
        accept = {"status": "ACCEPTED", "note": "Field check scheduled (smoke test)"}
        body = expect(http.put(f"{audit_url(run)}/flags/{target['flag_id']}/review", json=accept), 200)
        assert body["review"]["status"] == "ACCEPTED", f"status {body['review']['status']}"
        assert body["review"]["reviewed_at"], "reviewed_at not set"
        run.ctx["pending"] = (before, pending())
        return f"flag {target['flag_id']}"

    def decreased() -> str:
        before, after = need(run.ctx, "pending")
        assert after < before, f"pending_reviews {before} -> {after}"
        return f"pending_reviews {before} -> {after}"

    run.check("PUT review on one flag -> ACCEPTED", review)
    run.check("GET export pending_reviews decreased", decreased)


def create_report(http: httpx.Client, audit_id: str, supersedes: Optional[str] = None) -> dict[str, Any]:
    """POST trust /api/reports (expects 201)."""
    body = {"audit_id": audit_id, "reviewer_name": REVIEWER, "supersedes": supersedes}
    return expect(http.post(f"{TRUST_URL}/api/reports", json=body), 201)


def verify(http: httpx.Client, data: bytes, report_id: str) -> dict[str, Any]:
    """POST trust /api/reports/verify with the exact bytes given."""
    files = {"file": (f"{report_id}.json", data, "application/json")}
    return expect(http.post(f"{TRUST_URL}/api/reports/verify", files=files, data={"report_id": report_id}), 200)


def check_reports(run: Runner, http: httpx.Client) -> None:
    run.section("5. Trust service and chain")

    def create() -> str:
        report = create_report(http, need(run.ctx, "audit_id"))
        run.ctx["report"] = report
        assert HASH_RE.match(report["report_hash"]), "report_hash format"
        assert HASH_RE.match(report["tx_hash"]), "tx_hash format"
        return report["report_id"]

    def download() -> str:
        report = need(run.ctx, "report")
        res = http.get(f"{TRUST_URL}{report['files']['json']}")
        assert res.status_code == 200, f"download -> {res.status_code}"
        run.ctx["file_bytes"] = res.content
        return f"{len(res.content)} bytes"

    def match() -> str:
        report, data = need(run.ctx, "report"), need(run.ctx, "file_bytes")
        body = verify(http, data, report["report_id"])
        assert body["status"] == "MATCH", f"status {body['status']}"
        run.ctx["verify_ok"] = body
        return ""

    def mismatch() -> str:
        report, data = need(run.ctx, "report"), need(run.ctx, "file_bytes")
        tampered = flip_one_character(data, REVIEWER.encode())
        assert tampered != data and len(tampered) == len(data), "test bug: file was not changed by one character"
        body = verify(http, tampered, report["report_id"])
        assert body["status"] == "MISMATCH", f"status {body['status']}"
        return ""

    def onchain_hash() -> str:
        report, data = need(run.ctx, "report"), need(run.ctx, "file_bytes")
        body = need(run.ctx, "verify_ok")
        expected = sha256_0x(data)
        assert body["onchain_hash"] == expected, f"on-chain {body['onchain_hash']} != sha256(file) {expected}"
        assert report["report_hash"] == expected, "POST report_hash differs from sha256(file)"
        return expected[:18] + "..."

    def supersede() -> str:
        old = need(run.ctx, "report")
        new = create_report(http, need(run.ctx, "audit_id"), supersedes=old["report_id"])
        assert new["supersedes"] == old["report_id"], f"supersedes {new['supersedes']}"
        detail = expect(http.get(f"{TRUST_URL}/api/reports/{old['report_id']}"), 200)
        assert detail["superseded_by"] == new["report_id"], f"superseded_by {detail['superseded_by']}"
        listed = expect(http.get(f"{TRUST_URL}/api/reports"), 200)["items"]
        row = next((r for r in listed if r["report_id"] == old["report_id"]), None)
        assert row is not None and row["superseded_by"] == new["report_id"], "list does not show old as superseded"
        checked = verify(http, need(run.ctx, "file_bytes"), old["report_id"])
        assert checked["superseded_by"] == new["report_id"], f"verify superseded_by {checked['superseded_by']}"
        return f"{old['report_id']} superseded by {new['report_id']}"

    run.check("POST trust /api/reports -> 201", create)
    run.check("download report JSON file", download)
    run.check("verify unchanged file -> MATCH", match)
    run.check("verify file with one character changed -> MISMATCH", mismatch)
    run.check("on-chain hash equals sha256 of the file", onchain_hash)
    run.check("corrected report with supersedes marks the old one superseded", supersede)


def seed_if_empty(http: httpx.Client) -> None:
    """With --seed: create the synthetic audit when the core has none."""
    items = expect(http.get(f"{CORE_URL}/api/audits"), 200)["items"]
    if not items:
        created = expect(http.post(f"{CORE_URL}/api/audits", json={"use_synthetic": True}), 201)
        print(f"Seeded synthetic audit {created['audit_id']}")


def main(argv: list[str]) -> int:
    print(f"VoterGuard end-to-end smoke test\n  core {CORE_URL}\n  agent {AGENT_URL}\n  trust {TRUST_URL}")
    run = Runner()
    with httpx.Client(timeout=TIMEOUT_SECONDS) as http:
        if "--seed" in argv:
            try:
                seed_if_empty(http)
            except (httpx.HTTPError, AssertionError) as exc:
                print(f"Could not seed an audit: {exc}")
        check_health(run, http)
        check_audit(run, http)
        check_citizen(run, http)
        check_review(run, http)
        check_reports(run, http)
    return run.summary()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

