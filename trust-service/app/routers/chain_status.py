"""GET /api/chain/status (CONTRACT.md 6.5)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/chain/status")
def chain_status(request: Request) -> dict[str, Any]:
    """Always 200; `connected` is false when the node or contract is unavailable."""
    return request.app.state.services.chain.status()  # type: ignore[no-any-return]
