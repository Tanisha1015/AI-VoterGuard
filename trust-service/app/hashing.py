"""SHA-256 helpers. Hashes are lowercase 0x + 64 hex (CONTRACT.md 6.1)."""
from __future__ import annotations

import hashlib
import re

HASH_PATTERN = re.compile(r"^0x[0-9a-f]{64}$")


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 of `data` as "0x" + 64 lowercase hex characters."""
    return "0x" + hashlib.sha256(data).hexdigest()


def is_hash(value: str) -> bool:
    """True if `value` is a well-formed contract hash string."""
    return bool(HASH_PATTERN.match(value))


def to_bytes32(hex_str: str) -> bytes:
    """Convert a 0x-prefixed 64-hex string to 32 raw bytes for a Solidity bytes32 argument."""
    normalized = hex_str.lower()
    if not is_hash(normalized):
        raise ValueError(f"Expected 0x followed by 64 hex characters, got {hex_str!r}")
    return bytes.fromhex(normalized[2:])


def from_bytes32(value: bytes) -> str:
    """Convert 32 raw bytes back to the 0x-prefixed lowercase hex form."""
    if len(value) != 32:
        raise ValueError(f"Expected 32 bytes, got {len(value)}")
    return "0x" + value.hex()
