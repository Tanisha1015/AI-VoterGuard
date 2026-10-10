"""File hashing for roll snapshots (CONTRACT.md 6.7)."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_BYTES = 1 << 20


def sha256_file(path: str | Path) -> str:
    """Return ``"0x"`` + 64 lowercase hex characters: the SHA-256 of the file's exact bytes."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while chunk := fh.read(_CHUNK_BYTES):
            digest.update(chunk)
    return "0x" + digest.hexdigest()
