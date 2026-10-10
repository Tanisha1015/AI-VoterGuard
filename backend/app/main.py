"""VoterGuard core API (skeleton). Business logic is added in later tasks."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VoterGuard Core API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    """Liveness probe. `audit_ready` becomes true once an audit has been loaded."""
    return {"status": "ok", "audit_ready": False}
