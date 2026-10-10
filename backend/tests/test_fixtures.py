"""Sanity checks that contracts/fixtures/*.json are valid and follow CONTRACT.md."""
import json
import re
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
HASH = re.compile(r"^0x[0-9a-f]{64}$")
EXPECTED = {
    "audit_summary", "booths", "booth_17", "flags", "export", "citizen_removed",
    "citizen_present", "citizen_not_found", "citizen_ambiguous", "explain_response",
    "report_created", "report_list", "verify_match", "verify_mismatch", "chain_status",
}
DETECTORS = {"DELETION_RATE", "REASON_DOMINANCE", "GENDER_SKEW", "AGE_SKEW",
             "HOUSE_CLUSTER", "DUPLICATE_ENTRY", "DATA_QUALITY"}
SEVERITIES = {"LOW", "MEDIUM", "HIGH"}
REASONS = {"ABSENT", "SHIFTED", "DEAD", "DUPLICATE"}
BOOTH_KEYS = {"part_no", "draft_count", "final_count", "removed", "added", "deletion_rate",
              "reason_mix", "female_removed_share", "risk_score", "flagged", "flag_count"}
FLAG_KEYS = {"flag_id", "part_no", "detector", "severity", "metric", "explanation",
             "recommended_checks", "explanation_source", "review"}
BLOCKED_EN = ("fraud", "illegal", "rigging", "ineligible", "foreigner", "infiltrator", "fake")
BLOCKED_HI = ("धोखाधड़ी", "फर्जी", "फ़र्ज़ी", "अवैध", "जाली", "घुसपैठ", "विदेशी")


def load(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def walk(obj: Any) -> Any:
    """Yield every (key, value) pair in a nested JSON structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from walk(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


def strings(obj: Any) -> Any:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def check_flag(flag: dict[str, Any]) -> None:
    assert set(flag) == FLAG_KEYS
    assert flag["detector"] in DETECTORS
    assert flag["severity"] in SEVERITIES
    assert flag["explanation_source"] in {"agent", "template"}
    assert set(flag["explanation"]) == {"en", "hi"}
    assert set(flag["metric"]) == {"name", "value", "baseline"}
    assert set(flag["review"]) == {"status", "note", "reviewed_at"}
    assert flag["review"]["status"] in {"PENDING", "ACCEPTED", "REJECTED"}
    for check in flag["recommended_checks"]:
        assert set(check) == {"en", "hi"}


def test_all_fixtures_present_and_valid_json() -> None:
    found = {p.stem for p in FIXTURES.glob("*.json")}
    assert found == EXPECTED
    for name in EXPECTED:
        load(name)


def test_all_hashes_are_well_formed() -> None:
    hash_keys = {"draft", "final", "asdd", "report_hash", "tx_hash", "computed_hash", "onchain_hash"}
    for name in EXPECTED:
        for key, value in walk(load(name)):
            if key in hash_keys and isinstance(value, str):
                assert HASH.match(value), f"{name}.{key}"


def test_booths_sorted_and_shaped() -> None:
    items = load("booths")["items"]
    assert len(items) == 8
    assert items[0]["part_no"] == 17 and items[0]["risk_score"] == 87
    scores = [b["risk_score"] for b in items]
    assert scores == sorted(scores, reverse=True)
    for booth in items:
        assert set(booth) == BOOTH_KEYS
        assert set(booth["reason_mix"]) == REASONS


def test_booth_17_detail() -> None:
    booth = load("booth_17")
    assert BOOTH_KEYS <= set(booth)
    assert booth["gender_removed"] == {"F": 129, "M": 53, "O": 0}
    assert set(booth["age_band_removed_share"]) == {"18-25", "26-35", "36-45", "46-60", "61-80", "80+"}
    assert len(booth["flags"]) == booth["flag_count"]
    for flag in booth["flags"]:
        check_flag(flag)


def test_flags_cover_four_detectors() -> None:
    items = load("flags")["items"]
    assert len(items) == 4
    assert len({f["detector"] for f in items}) == 4
    for flag in items:
        check_flag(flag)


def test_export_shape() -> None:
    export = load("export")
    assert {"audit_id", "ac_no", "ac_name", "generated_at", "snapshot_hashes", "summary",
            "flagged_booths", "methodology", "disclaimer"} == set(export)
    assert set(export["methodology"]) == {"version", "detectors", "thresholds"}
    for entry in export["flagged_booths"]:
        assert set(entry) == {"booth", "flags"}


def test_citizen_fixtures() -> None:
    statuses = {n: load(n)["status"] for n in
                ["citizen_removed", "citizen_present", "citizen_not_found", "citizen_ambiguous"]}
    assert statuses == {"citizen_removed": "REMOVED", "citizen_present": "PRESENT",
                        "citizen_not_found": "NOT_FOUND", "citizen_ambiguous": "AMBIGUOUS"}
    removed = load("citizen_removed")
    assert removed["reason"] in REASONS
    assert removed["record"]["epic_masked"].startswith("VGX")
    for name in ("citizen_not_found", "citizen_ambiguous"):
        data = load(name)
        assert data["record"] is None and data["reason"] is None and data["next_step"] is None
    assert "message" in load("citizen_ambiguous")


def test_trust_fixtures() -> None:
    assert load("verify_match")["status"] == "MATCH"
    assert load("verify_mismatch")["status"] == "MISMATCH"
    match, mismatch = load("verify_match"), load("verify_mismatch")
    assert match["computed_hash"] == match["onchain_hash"]
    assert mismatch["computed_hash"] != mismatch["onchain_hash"]
    assert set(load("chain_status")) == {"connected", "chain_id", "contract_address", "latest_block"}
    assert len(load("report_list")["items"]) == 2


def test_language_safety() -> None:
    for name in EXPECTED:
        for text in strings(load(name)):
            low = text.lower()
            assert not any(w in low for w in BLOCKED_EN), f"{name}: {text}"
            assert not any(w in text for w in BLOCKED_HI), f"{name}: {text}"
