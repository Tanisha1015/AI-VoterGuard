"""API tests for the core service: contract shapes, citizen lookup, reviews and the template fallback."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app

from app.detectors.config import THRESHOLDS

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
ROLL_HEADER = "epic_no,ac_no,part_no,serial_no,name,relative_name,relation_type,house_no,age,gender"


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def keys(obj: dict[str, Any]) -> set[str]:
    return set(obj)


def assert_flag_shape(flag: dict[str, Any]) -> None:
    sample = fixture("flags")["items"][0]
    assert keys(flag) == keys(sample)
    assert keys(flag["metric"]) == keys(sample["metric"])
    assert keys(flag["explanation"]) == keys(sample["explanation"]) == {"en", "hi"}
    assert keys(flag["review"]) == keys(sample["review"])
    assert flag["recommended_checks"]
    for check in flag["recommended_checks"]:
        assert keys(check) == {"en", "hi"}


def assert_error_body(res: httpx.Response, status: int) -> None:
    assert res.status_code == status
    body = res.json()
    assert keys(body) == {"error"}
    assert keys(body["error"]) == {"code", "message"}


# ------------------------------------------------------------------ small uploaded audits


def roll_csv(rows: list[tuple[str, int, str, str, int, str]]) -> str:
    """Build a roll CSV from (epic, part_no, name, relative_name, age, gender) tuples."""
    lines = [ROLL_HEADER]
    for serial, (epic, part, name, relative, age, gender) in enumerate(rows, start=1):
        lines.append(f"{epic},123,{part},{serial},{name},{relative},FATHER,{serial},{age},{gender}")
    return "\n".join(lines) + "\n"


def upload(client: TestClient, draft: str, final: str, asdd: str) -> httpx.Response:
    files = {
        "draft": ("draft_roll.csv", draft.encode(), "text/csv"),
        "final": ("final_roll.csv", final.encode(), "text/csv"),
        "asdd": ("asdd.csv", asdd.encode(), "text/csv"),
    }
    return client.post("/api/audits", files=files)


def ambiguous_audit(client: TestClient) -> None:
    """An audit where two different entries in booth 1 share the same name and relative name."""
    people = [("VGX1000001", 1, "Rekha Devi", "Mohan Lal", 30, "F"),
              ("VGX1000002", 1, "Rekha Devi", "Mohan Lal", 52, "F"),
              ("VGX1000003", 1, "Anil Kumar", "Suresh Kumar", 41, "M"),
              ("VGX1000004", 2, "Geeta Sharma", "Dinesh Sharma", 36, "F")]
    csv = roll_csv(people)
    assert upload(client, csv, csv, "epic_no,part_no,reason,remark\n").status_code == 201


# ------------------------------------------------------------------ health and shapes


def test_health_without_audit(empty_client: TestClient) -> None:
    assert empty_client.get("/api/health").json() == {"status": "ok", "audit_ready": False}


def test_health_with_audit(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok", "audit_ready": True}


def test_audit_list_and_summary_shapes(client: TestClient) -> None:
    items = client.get("/api/audits").json()["items"]
    assert [i["audit_id"] for i in items] == ["aud_001"]
    assert keys(items[0]) == {"audit_id", "ac_name", "created_at"}
    assert items[0]["ac_name"] == "Demo Nagar (Synthetic)"

    summary = client.get("/api/audits/aud_001/summary").json()
    sample = fixture("audit_summary")
    assert keys(summary) == keys(sample)
    assert keys(summary["snapshot_hashes"]) == keys(sample["snapshot_hashes"])
    assert keys(summary["totals"]) == keys(sample["totals"])
    assert keys(summary["constituency_baseline"]) == keys(sample["constituency_baseline"])
    assert keys(summary["reason_mix"]) == keys(sample["reason_mix"])
    assert summary["ac_no"] == 999
    assert summary["totals"]["flags"] == summary["totals"]["pending_reviews"] > 0


def test_booths_shape_and_order(client: TestClient) -> None:
    items = client.get("/api/audits/aud_001/booths").json()["items"]
    sample = fixture("booths")["items"][0]
    assert len(items) == 60
    scores = [b["risk_score"] for b in items]
    assert scores == sorted(scores, reverse=True)
    for booth in items:
        assert keys(booth) == keys(sample)
        assert keys(booth["reason_mix"]) == keys(sample["reason_mix"])


def test_booth_detail_shape(client: TestClient) -> None:
    sample = fixture("booth_17")
    booth = client.get("/api/audits/aud_001/booths/17").json()
    assert keys(booth) == keys(sample)
    assert keys(booth["gender_removed"]) == keys(sample["gender_removed"])
    assert keys(booth["age_band_removed_share"]) == keys(sample["age_band_removed_share"])
    assert booth["flag_count"] == len(booth["flags"]) > 0
    for flag in booth["flags"]:
        assert_flag_shape(flag)


def test_flags_shape_and_filters(client: TestClient) -> None:
    flags = client.get("/api/audits/aud_001/flags").json()["items"]
    assert flags
    for flag in flags:
        assert_flag_shape(flag)
    first = flags[0]
    for param, value in (("part_no", first["part_no"]), ("severity", first["severity"]),
                         ("detector", first["detector"])):
        items = client.get(f"/api/audits/aud_001/flags?{param}={value}").json()["items"]
        assert items and all(f[param] == value for f in items)
    assert client.get("/api/audits/aud_001/flags?part_no=9999").json() == {"items": []}
    assert client.get("/api/audits/aud_001/flags?severity=BOGUS").status_code == 422


def test_unknown_ids_return_standard_404(client: TestClient) -> None:
    for path in ("summary", "booths", "booths/17", "flags", "export"):
        assert_error_body(client.get(f"/api/audits/aud_999/{path}"), 404)
    assert_error_body(client.get("/api/audits/aud_001/booths/9999"), 404)
    body = {"status": "ACCEPTED"}
    assert_error_body(client.put("/api/audits/aud_001/flags/f_0_0/review", json=body), 404)
    assert_error_body(client.put("/api/audits/aud_999/flags/f_1_1/review", json=body), 404)


# ------------------------------------------------------------------ review persistence


def test_review_is_persisted_and_counted(client: TestClient) -> None:
    flag = client.get("/api/audits/aud_001/flags").json()["items"][0]
    before = client.get("/api/audits/aud_001/summary").json()["totals"]["pending_reviews"]
    assert flag["review"] == {"status": "PENDING", "note": None, "reviewed_at": None}

    url = f"/api/audits/aud_001/flags/{flag['flag_id']}/review"
    res = client.put(url, json={"status": "ACCEPTED", "note": "Field check scheduled"})
    assert res.status_code == 200
    updated = res.json()
    assert_flag_shape(updated)
    assert updated["review"]["status"] == "ACCEPTED"
    assert updated["review"]["note"] == "Field check scheduled"
    assert updated["review"]["reviewed_at"].endswith("Z")

    again = client.get(f"/api/audits/aud_001/flags?part_no={flag['part_no']}").json()["items"]
    stored = next(f for f in again if f["flag_id"] == flag["flag_id"])
    assert stored["review"] == updated["review"]
    assert client.get("/api/audits/aud_001/summary").json()["totals"]["pending_reviews"] == before - 1

    reverted = client.put(url, json={"status": "PENDING"}).json()
    assert reverted["review"] == {"status": "PENDING", "note": None, "reviewed_at": None}


def test_review_rejects_bad_status(client: TestClient) -> None:
    flag_id = client.get("/api/audits/aud_001/flags").json()["items"][0]["flag_id"]
    res = client.put(f"/api/audits/aud_001/flags/{flag_id}/review", json={"status": "FRAUD"})
    assert_error_body(res, 422)


# ------------------------------------------------------------------ export


def test_export_shape_and_content(client: TestClient) -> None:
    sample = fixture("export")
    export = client.get("/api/audits/aud_001/export").json()
    assert keys(export) == keys(sample)
    assert keys(export["summary"]) == keys(sample["summary"])
    assert keys(export["snapshot_hashes"]) == keys(sample["snapshot_hashes"])
    assert keys(export["methodology"]) == keys(sample["methodology"])
    assert keys(export["disclaimer"]) == {"en", "hi"}
    assert export["methodology"]["version"] == "0.1"
    assert export["methodology"]["thresholds"] == THRESHOLDS
    assert export["methodology"]["detectors"] == sample["methodology"]["detectors"]
    assert export["disclaimer"]["en"] == sample["disclaimer"]["en"]
    assert export["flagged_booths"]
    all_flags = client.get("/api/audits/aud_001/flags").json()["items"]
    exported = [f for entry in export["flagged_booths"] for f in entry["flags"]]
    assert sorted(f["flag_id"] for f in exported) == sorted(f["flag_id"] for f in all_flags)
    for entry in export["flagged_booths"]:
        assert keys(entry) == {"booth", "flags"}
        assert keys(entry["booth"]) == keys(sample["flagged_booths"][0]["booth"])
        assert entry["booth"]["flagged"] is True



def test_export_contains_reviews(client: TestClient) -> None:
    flag = client.get("/api/audits/aud_001/flags").json()["items"][0]
    client.put(f"/api/audits/aud_001/flags/{flag['flag_id']}/review",
               json={"status": "REJECTED", "note": "Explained by records"})
    export = client.get("/api/audits/aud_001/export").json()
    exported = {f["flag_id"]: f for e in export["flagged_booths"] for f in e["flags"]}
    assert exported[flag["flag_id"]]["review"]["status"] == "REJECTED"


def test_snapshot_hashes_are_sha256_of_stored_files(client: TestClient, isolated_env: Path) -> None:
    hashes = client.get("/api/audits/aud_001/summary").json()["snapshot_hashes"]
    folder = isolated_env / "audits" / "aud_001"
    for key, name in (("draft", "draft_roll.csv"), ("final", "final_roll.csv"), ("asdd", "asdd.csv")):
        assert hashes[key] == "0x" + hashlib.sha256((folder / name).read_bytes()).hexdigest()


# ------------------------------------------------------------------ creating audits


def test_create_audit_synthetic_and_ids_increment(client: TestClient, isolated_env: Path) -> None:
    res = client.post("/api/audits", json={"use_synthetic": True})
    assert res.status_code == 201
    assert res.json() == {"audit_id": "aud_002", "status": "READY"}
    assert [i["audit_id"] for i in client.get("/api/audits").json()["items"]] == ["aud_001", "aud_002"]
    for name in ("draft_roll.csv", "final_roll.csv", "asdd.csv"):
        assert (isolated_env / "audits" / "aud_002" / name).is_file()


def test_create_audit_from_upload(empty_client: TestClient) -> None:
    ambiguous_audit(empty_client)
    items = empty_client.get("/api/audits").json()["items"]
    assert [i["audit_id"] for i in items] == ["aud_001"]
    assert items[0]["ac_name"] == "Constituency 123"


def test_create_audit_validation_errors(empty_client: TestClient) -> None:
    assert_error_body(empty_client.post("/api/audits", json={"use_synthetic": False}), 422)
    assert_error_body(empty_client.post("/api/audits", files={"draft": ("d.csv", b"x", "text/csv")}), 422)
    bad = "epic_no,part_no\nVGX1,1\n"
    assert_error_body(upload(empty_client, bad, bad, bad), 422)
    assert empty_client.get("/api/audits").json() == {"items": []}



# ------------------------------------------------------------------ citizen lookup


def lookup(client: TestClient, **body: Any) -> httpx.Response:
    return client.post("/api/citizen/lookup", json=body)


def test_citizen_removed_exact_match(client: TestClient, demo_voters: dict[str, Any]) -> None:
    voter = demo_voters["removed"]
    res = lookup(client, name=voter["name"], relative_name=voter["relative_name"],
                 part_no=voter["part_no"], epic_no=None, lang="en")
    assert res.status_code == 200
    body = res.json()
    sample = fixture("citizen_removed")
    assert keys(body) == keys(sample)
    assert keys(body["record"]) == keys(sample["record"])
    assert keys(body["next_step"]) == keys(sample["next_step"])
    assert body["status"] == "REMOVED"
    assert body["reason"] == voter["reason"]
    assert body["match_confidence"] >= 0.9
    assert body["next_step"]["deadline"] == "2026-10-31"
    assert body["next_step"]["disclaimer"]["en"] == sample["next_step"]["disclaimer"]["en"]
    record = body["record"]
    assert record["epic_masked"] == voter["epic_no"][:3] + "****" + voter["epic_no"][-3:]
    assert record["name_display"] == "Sunita D."
    assert record["age_band"] == "26-35"
    assert voter["epic_no"] not in res.text and voter["house_no"] not in res.text


def test_citizen_present_and_added(client: TestClient, demo_voters: dict[str, Any]) -> None:
    sample = fixture("citizen_present")
    present = demo_voters["present"]
    body = lookup(client, name=present["name"], relative_name=present["relative_name"],
                  part_no=present["part_no"]).json()
    assert keys(body) == keys(sample)
    assert body["status"] == "PRESENT"
    assert body["reason"] is None and body["next_step"] is None
    assert body["record"]["name_display"] == "Meena K."

    added = demo_voters["added"]
    body = lookup(client, name=added["name"], relative_name=added["relative_name"],
                  part_no=added["part_no"]).json()
    assert body["status"] == "ADDED"
    assert body["reason"] is None and body["next_step"] is None


def test_citizen_lookup_by_epic(client: TestClient, demo_voters: dict[str, Any]) -> None:
    body = lookup(client, epic_no=demo_voters["removed"]["epic_no"].lower()).json()
    assert body["status"] == "REMOVED" and body["match_confidence"] == 1.0
    assert body["reason"] == "SHIFTED"
    assert lookup(client, epic_no="VGX0000000").json()["status"] == "NOT_FOUND"


def test_citizen_misspelled_names_still_match(client: TestClient, demo_voters: dict[str, Any]) -> None:
    voter = demo_voters["removed"]
    # "Shri" honorific, doubled/shifted vowels and different letter case and punctuation.
    res = lookup(client, name="SHRI Suneeta  Devi.", relative_name="ramesh, kumaar",
                 part_no=voter["part_no"])
    body = res.json()
    assert body["status"] == "REMOVED"
    assert body["record"]["epic_masked"].startswith("VGX****")
    assert 0.9 <= body["match_confidence"] <= 1.0


def test_citizen_not_found(client: TestClient, demo_voters: dict[str, Any]) -> None:
    sample = fixture("citizen_not_found")
    body = lookup(client, name="Zzyzx Qwerty", relative_name="Plugh Xyzzy",
                  part_no=demo_voters["removed"]["part_no"]).json()
    assert body == sample
    wrong_booth = lookup(client, name="Sunita Devi", relative_name="Ramesh Kumar", part_no=60).json()
    assert wrong_booth["status"] in ("NOT_FOUND", "REMOVED")  # another booth may hold a namesake
    assert lookup(client, name="Sunita Devi", relative_name="Ramesh Kumar", part_no=9999).json() == sample


def test_citizen_ambiguous_lists_no_candidates(empty_client: TestClient) -> None:
    ambiguous_audit(empty_client)
    res = lookup(empty_client, name="Rekha Devi", relative_name="Mohan Lal", part_no=1)
    body = res.json()
    sample = fixture("citizen_ambiguous")
    assert keys(body) == keys(sample)
    assert body["status"] == "AMBIGUOUS"
    assert body["record"] is None and body["reason"] is None and body["next_step"] is None
    assert keys(body["message"]) == {"en", "hi"}
    assert "VGX" not in res.text and "Rekha" not in res.text


def test_citizen_unique_match_beats_a_close_runner_up(empty_client: TestClient) -> None:
    people = [("VGX2000001", 1, "Rekha Devi", "Mohan Lal", 30, "F"),
              ("VGX2000002", 1, "Rekha Verma", "Sohan Gupta", 52, "F")]
    csv = roll_csv(people)
    assert upload(empty_client, csv, csv, "epic_no,part_no,reason,remark\n").status_code == 201
    body = lookup(empty_client, name="Rekha Devi", relative_name="Mohan Lal", part_no=1).json()
    assert body["status"] == "PRESENT"
    assert body["record"]["epic_masked"] == "VGX****001"


def test_citizen_missing_fields_are_422(client: TestClient) -> None:
    for body in ({}, {"name": "Sunita Devi"}, {"name": "Sunita Devi", "relative_name": "Ramesh Kumar"},
                 {"relative_name": "Ramesh Kumar", "part_no": 17}, {"epic_no": "  "}):
        assert_error_body(lookup(client, **body), 422)
    assert_error_body(client.post("/api/citizen/lookup", json={"part_no": "abc"}), 422)


def test_citizen_without_audit_is_404(empty_client: TestClient) -> None:
    assert_error_body(lookup(empty_client, epic_no="VGX1234567"), 404)


def test_citizen_rate_limit(client: TestClient) -> None:
    for _ in range(20):
        assert lookup(client, epic_no="VGX0000000").status_code == 200
    assert_error_body(lookup(client, epic_no="VGX0000000"), 429)



# ------------------------------------------------------------------ agent service and template fallback

AGENT = "http://agent.test"
AGENT_REPLY = {
    "explanation": {"en": "Agent text: this pattern is unusual and worth verifying.",
                    "hi": "एजेंट: यह पैटर्न असामान्य है और सत्यापन के योग्य है।"},
    "recommended_checks": [{"en": "Recommend a field check.", "hi": "क्षेत्रीय जाँच की सिफारिश की जाती है।"}],
    "neutrality": {"passed": True, "method": "blocklist+number_check+agent", "violations": []},
    "source": "agent",
}
BLOCKED_EN = ("fraud", "illegal", "rigging", "ineligible", "foreigner", "infiltrator", "fake")
BLOCKED_HI = ("धोखाधड़ी", "फर्जी", "फ़र्ज़ी", "अवैध", "जाली", "घुसपैठ", "विदेशी")


def run_with_agent(monkeypatch: pytest.MonkeyPatch, route_setup: Any) -> list[dict[str, Any]]:
    """Run the synthetic pipeline against a mocked agent and return the stored flags (as dicts)."""
    monkeypatch.setenv("AGENT_URL", AGENT)
    with respx.mock(assert_all_called=False) as router:
        route_setup(router)
        client = TestClient(app)
        assert client.post("/api/audits", json={"use_synthetic": True}).status_code == 201
        flags = client.get("/api/audits/aud_001/flags").json()["items"]
    assert flags
    return flags


def assert_template_text(flags: list[dict[str, Any]]) -> None:
    """Template text is bilingual, has 2-3 checks, mentions numbers, and never implies wrongdoing."""
    for flag in flags:
        assert flag["explanation"]["en"].strip() and flag["explanation"]["hi"].strip()
        assert 2 <= len(flag["recommended_checks"]) <= 3
        assert any(c.isdigit() for c in flag["explanation"]["en"])
        assert any("\u0900" <= ch <= "\u097f" for ch in flag["explanation"]["hi"])
        text = json.dumps(flag, ensure_ascii=False).lower()
        assert not any(word in text for word in BLOCKED_EN)
        assert not any(word in text for word in BLOCKED_HI)
        assert "unusual" in flag["explanation"]["en"] or "worth" in flag["explanation"]["en"]


def test_agent_success_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def reply(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=AGENT_REPLY)

    flags = run_with_agent(monkeypatch, lambda r: r.post(f"{AGENT}/explain").mock(side_effect=reply))
    assert len(calls) == len(flags)
    assert all(f["explanation_source"] == "agent" for f in flags)
    assert flags[0]["explanation"] == AGENT_REPLY["explanation"]
    request = calls[0]  # request shape from CONTRACT.md 6.4
    assert keys(request) == {"audit_id", "booth", "flag", "baseline"}
    assert request["audit_id"] == "aud_001"
    assert keys(request["booth"]) == keys(fixture("booths")["items"][0])
    assert keys(request["flag"]) == {"detector", "severity", "metric"}
    assert keys(request["flag"]["metric"]) == {"name", "value", "baseline"}
    assert keys(request["baseline"]) == {"deletion_rate", "deletion_rate_mad"}


def test_agent_at_most_three_calls_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"now": 0, "peak": 0}

    async def slow_reply(request: httpx.Request) -> httpx.Response:
        state["now"] += 1
        state["peak"] = max(state["peak"], state["now"])
        await asyncio.sleep(0.05)
        state["now"] -= 1
        return httpx.Response(200, json=AGENT_REPLY)

    flags = run_with_agent(monkeypatch, lambda r: r.post(f"{AGENT}/explain").mock(side_effect=slow_reply))
    assert len(flags) > 3
    assert state["peak"] == 3



@pytest.mark.parametrize("failure", ["422", "503", "connection", "timeout", "bad_json", "blocked_text"])
def test_agent_failure_falls_back_to_templates(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    blocked = {**AGENT_REPLY, "explanation": {"en": "This looks like fraud.", "hi": "यह अवैध है।"}}
    outcomes: dict[str, Any] = {
        "422": httpx.Response(422, json={"error": {"code": "NEUTRALITY_FAILED", "message": "x"}}),
        "503": httpx.Response(503, json={"error": {"code": "AGENT_UNAVAILABLE", "message": "x"}}),
        "connection": httpx.ConnectError("refused"),
        "timeout": httpx.ReadTimeout("slow"),
        "bad_json": httpx.Response(200, text="not json"),
        "blocked_text": httpx.Response(200, json=blocked),
    }
    outcome = outcomes[failure]

    def respond(request: httpx.Request) -> httpx.Response:
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    flags = run_with_agent(monkeypatch, lambda r: r.post(f"{AGENT}/explain").mock(side_effect=respond))
    assert all(f["explanation_source"] == "template" for f in flags)
    assert_template_text(flags)


def test_agent_service_down_uses_templates(client: TestClient) -> None:
    """The seeded audit was built while no agent was reachable (connection refused)."""
    flags = client.get("/api/audits/aud_001/flags").json()["items"]
    assert flags and all(f["explanation_source"] == "template" for f in flags)
    assert_template_text(flags)


def test_one_agent_failure_only_affects_that_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"calls": 0}

    def respond(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 2:
            return httpx.Response(503, json={"error": {"code": "AGENT_UNAVAILABLE", "message": "x"}})
        return httpx.Response(200, json=AGENT_REPLY)

    flags = run_with_agent(monkeypatch, lambda r: r.post(f"{AGENT}/explain").mock(side_effect=respond))
    sources = [f["explanation_source"] for f in flags]
    assert sources.count("template") == 1 and sources.count("agent") == len(flags) - 1


def test_agent_timeout_setting_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import agent_client

    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "3.5")
    assert agent_client.agent_timeout() == 3.5
    monkeypatch.delenv("AGENT_TIMEOUT_SECONDS")
    assert agent_client.agent_timeout() == 8.0
    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "oops")
    assert agent_client.agent_timeout() == 8.0


def test_deletion_rate_template_wording() -> None:
    from app.services import templates

    booth = {"reason_mix": {"ABSENT": 0.1, "SHIFTED": 0.82, "DEAD": 0.05, "DUPLICATE": 0.03}}
    explanation, checks = templates.explain_flag("DELETION_RATE", "deletion_rate", 0.224, 0.048, 17, booth)
    assert explanation["en"] == (
        "Booth 17 shows a deletion rate of 22.4%, about 4.7 times the constituency median of 4.8%. "
        "This is an unusual pattern worth verifying."
    )
    assert "22.4%" in explanation["hi"] and "4.8%" in explanation["hi"]
    assert checks[0]["en"] == "Re-verify a sample of 20 removed households."


@pytest.mark.parametrize("detector,metric", [
    ("DELETION_RATE", "deletion_rate"), ("REASON_DOMINANCE", "reason_share"),
    ("GENDER_SKEW", "f_removed_share"), ("GENDER_SKEW", "m_removed_share"),
    ("AGE_SKEW", "dead_under_40"), ("AGE_SKEW", "young_removed_share"),
    ("HOUSE_CLUSTER", "max_house_additions"), ("HOUSE_CLUSTER", "max_house_voters"),
    ("DUPLICATE_ENTRY", "duplicate_pairs"), ("DATA_QUALITY", "dq_count"), ("UNKNOWN", "x"),
])
def test_every_detector_has_neutral_bilingual_templates(detector: str, metric: str) -> None:
    from app.services import templates

    booth = {"reason_mix": {"ABSENT": 0.1, "SHIFTED": 0.8, "DEAD": 0.05, "DUPLICATE": 0.05}}
    explanation, checks = templates.explain_flag(detector, metric, 0.5, 0.0, 7, booth)
    assert 2 <= len(checks) <= 3
    text = json.dumps([explanation, checks], ensure_ascii=False).lower()
    assert not any(word in text for word in BLOCKED_EN + BLOCKED_HI)
    assert "booth 7" in explanation["en"].lower() and "7" in explanation["hi"]


# ------------------------------------------------------------------ startup seeding and misc


def test_auto_seed_creates_audit_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTO_SEED", "true")
    with TestClient(app) as seeded:
        assert seeded.get("/api/health").json() == {"status": "ok", "audit_ready": True}
        assert [i["audit_id"] for i in seeded.get("/api/audits").json()["items"]] == ["aud_001"]
    with TestClient(app) as restarted:  # an audit already exists, so nothing new is created
        assert [i["audit_id"] for i in restarted.get("/api/audits").json()["items"]] == ["aud_001"]


def test_no_auto_seed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTO_SEED", "false")
    with TestClient(app) as unseeded:
        assert unseeded.get("/api/health").json()["audit_ready"] is False


def test_cors_and_unknown_route_error_body(client: TestClient) -> None:
    res = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert_error_body(client.get("/api/nope"), 404)

