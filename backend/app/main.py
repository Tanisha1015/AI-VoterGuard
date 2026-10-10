"""VoterGuard core API on port 8000 (CONTRACT.md 6.3).

Run from backend/:  uvicorn app.main:app --port 8000
Environment: AUTO_SEED, AGENT_URL, AGENT_TIMEOUT_SECONDS, CLAIMS_DEADLINE, DATA_DIR (see .env.example).
"""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.errors import install_error_handlers
from app.routers import audits, citizen, health
from app.services import pipeline


def auto_seed_enabled() -> bool:
    """True when env AUTO_SEED is "true" (any letter case)."""
    return os.environ.get("AUTO_SEED", "").strip().lower() == "true"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """On startup, create aud_001 from the synthetic data when AUTO_SEED=true and no audit exists."""
    if auto_seed_enabled() and not await asyncio.to_thread(db.audit_exists):
        await asyncio.to_thread(pipeline.run_synthetic_pipeline)
    yield


app = FastAPI(title="VoterGuard Core API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_error_handlers(app)
app.include_router(health.router)
app.include_router(audits.router)
app.include_router(citizen.router)
