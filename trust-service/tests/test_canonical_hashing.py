"""Canonical JSON determinism and hash stability (CONTRACT.md 6.7)."""
from __future__ import annotations

import json
import random
from typing import Any

import pytest

from app.canonical import SCHEMA_VERSION, build_report, to_canonical_bytes
from app.hashing import from_bytes32, is_hash, sha256_hex, to_bytes32
from tests.conftest import load_export


def shuffled(obj: Any, rng: random.Random) -> Any:
    """Deep copy with every dict's key order shuffled."""
    if isinstance(obj, dict):
        items = list(obj.items())
        rng.shuffle(items)
        return {k: shuffled(v, rng) for k, v in items}
    if isinstance(obj, list):
        return [shuffled(v, rng) for v in obj]
    return obj


def sample_report() -> dict[str, Any]:
    return build_report(load_export(), "VG-2026-0001", "R. Sharma", None, "2026-10-10T10:05:00Z")


def test_build_report_has_exact_top_level_keys() -> None:
    doc = sample_report()
    assert set(doc) == {"schema_version", "report_id", "generated_at", "reviewer", "audit", "supersedes"}
    assert doc["schema_version"] == SCHEMA_VERSION == "1.0"
    assert doc["reviewer"] == {"name": "R. Sharma"}
    assert doc["audit"] == load_export()


@pytest.mark.parametrize("seed", range(5))
def test_shuffled_keys_give_identical_bytes(seed: int) -> None:
    doc = sample_report()
    assert to_canonical_bytes(shuffled(doc, random.Random(seed))) == to_canonical_bytes(doc)


def test_canonical_form_is_compact_sorted_utf8() -> None:
    raw = to_canonical_bytes({"b": 1, "a": {"y": "भाग", "x": [1, 2]}})
    assert raw == '{"a":{"x":[1,2],"y":"भाग"},"b":1}'.encode("utf-8")
    assert b"\\u" not in raw  # ensure_ascii=False keeps Devanagari as UTF-8
    assert json.loads(raw.decode("utf-8")) == {"b": 1, "a": {"y": "भाग", "x": [1, 2]}}


def test_sha256_known_vector_and_format() -> None:
    assert sha256_hex(b"abc") == "0xba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert is_hash(sha256_hex(b""))


def test_report_hash_is_stable_and_sensitive() -> None:
    canonical = to_canonical_bytes(sample_report())
    first = sha256_hex(canonical)
    assert first == sha256_hex(to_canonical_bytes(sample_report()))
    assert first != sha256_hex(canonical + b" ")  # any edit, even a space, changes the hash


def test_bytes32_round_trip_and_validation() -> None:
    h = sha256_hex(b"voterguard")
    assert len(to_bytes32(h)) == 32
    assert from_bytes32(to_bytes32(h)) == h
    assert to_bytes32(h.upper().replace("0X", "0x")) == to_bytes32(h)
    for bad in ("", "0x1234", "ab" * 32, "0x" + "zz" * 32):
        with pytest.raises(ValueError):
            to_bytes32(bad)
