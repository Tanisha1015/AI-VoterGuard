"""Unit tests for the pure helpers of e2e_smoke.py (no services needed). Run: python3 -m pytest scripts"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from e2e_smoke import flip_one_character, forbidden_words, sha256_0x, strip_nukta  # noqa: E402


def test_forbidden_english_is_found_case_insensitively() -> None:
    assert forbidden_words("This looks like FRAUD") == ["fraud"]
    assert forbidden_words("ineligible and rigging and illegal and fake") != []


def test_neutral_text_is_clean() -> None:
    assert forbidden_words("Unusual deletion pattern; recommend a field check.") == []
    assert forbidden_words("यह पैटर्न असामान्य है और सत्यापन के योग्य है।") == []


def test_forbidden_hindi_is_found_with_or_without_nukta() -> None:
    assert forbidden_words("यह फर्जी है") != []
    assert forbidden_words("यह फ़र्ज़ी है") != []
    assert strip_nukta("ड़") == strip_nukta("ड\u093c")


def test_flip_changes_exactly_one_byte() -> None:
    data = b'{"reviewer":{"name":"Smoke Test"}}'
    changed = flip_one_character(data, b"Smoke Test")
    assert len(changed) == len(data)
    assert sum(a != b for a, b in zip(data, changed)) == 1


def test_sha256_format() -> None:
    assert sha256_0x(b"") == "0xe3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
