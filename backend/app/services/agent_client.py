"""Client for the agent service: POST {AGENT_URL}/explain (CONTRACT.md 6.4).

The agent only phrases text; every number in a request comes from the deterministic detectors. Any
failure (timeout, connection error, 422 NEUTRALITY_FAILED, 503 AGENT_UNAVAILABLE, malformed or
non-neutral reply) raises ``AgentError`` and the caller uses ``services.templates`` instead.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.models import Bilingual

DEFAULT_AGENT_URL = "http://localhost:8001"
DEFAULT_TIMEOUT_SECONDS = 8.0
MAX_CONCURRENT_CALLS = 3

# Defence in depth: the agent has its own neutrality guard, but text that still contains one of
# these words is never shown. It is rejected here and the neutral template is used instead.
_BLOCKED_WORDS = (
    "fraud", "illegal", "rigging", "rigged", "ineligible", "foreigner", "infiltrator", "fake",
    "धोखाधड़ी", "फर्जी", "फ़र्ज़ी", "अवैध", "जाली", "घुसपैठ", "विदेशी",
)


class AgentError(Exception):
    """The agent could not provide an acceptable explanation for a flag."""


class AgentReply(BaseModel):
    """The parts of a 200 response from /explain that the core API stores."""

    explanation: Bilingual
    recommended_checks: list[Bilingual]
    source: str


def agent_url() -> str:
    """Base URL of the agent service (env AGENT_URL)."""
    return (os.environ.get("AGENT_URL") or DEFAULT_AGENT_URL).rstrip("/")


def agent_timeout() -> float:
    """Per-call timeout in seconds (env AGENT_TIMEOUT_SECONDS, default 8)."""
    try:
        value = float(os.environ.get("AGENT_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_TIMEOUT_SECONDS


def new_semaphore() -> asyncio.Semaphore:
    """A semaphore allowing at most 3 agent calls at the same time."""
    return asyncio.Semaphore(MAX_CONCURRENT_CALLS)


def build_request(
    audit_id: str, booth: dict[str, Any], flag: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    """Build the request body exactly as CONTRACT.md 6.4 shows it."""
    return {
        "audit_id": audit_id,
        "booth": booth,
        "flag": {
            "detector": flag["detector"],
            "severity": flag["severity"],
            "metric": flag["metric"],
        },
        "baseline": {
            "deletion_rate": baseline["deletion_rate"],
            "deletion_rate_mad": baseline["deletion_rate_mad"],
        },
    }


def _check_reply(reply: AgentReply) -> None:
    """Reject empty or non-neutral text."""
    texts = [reply.explanation.en, reply.explanation.hi]
    for check in reply.recommended_checks:
        texts += [check.en, check.hi]
    if not reply.explanation.en.strip() or not reply.explanation.hi.strip():
        raise AgentError("empty explanation")
    lowered = " ".join(texts).lower()
    if any(word in lowered for word in _BLOCKED_WORDS):
        raise AgentError("reply failed the neutrality check")


async def explain(
    audit_id: str,
    booth: dict[str, Any],
    flag: dict[str, Any],
    baseline: dict[str, Any],
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> AgentReply:
    """Ask the agent to phrase one flag. Raises ``AgentError`` on any failure."""
    body = build_request(audit_id, booth, flag, baseline)
    try:
        async with semaphore:
            response = await client.post(f"{agent_url()}/explain", json=body, timeout=agent_timeout())
        if response.status_code != 200:
            raise AgentError(f"agent returned HTTP {response.status_code}")
        reply = AgentReply.model_validate(response.json())
    except AgentError:
        raise
    except (httpx.HTTPError, ValueError, ValidationError) as exc:
        # ValueError covers a non-JSON body; ValidationError is a ValueError subclass in pydantic v2.
        raise AgentError(f"{type(exc).__name__}") from exc
    _check_reply(reply)
    return reply
