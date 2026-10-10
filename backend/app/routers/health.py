"""GET /api/health."""

from fastapi import APIRouter

from app import db
from app.models import Health

router = APIRouter(prefix="/api")


@router.get("/health", response_model=Health)
def health() -> Health:
    """Liveness probe. ``audit_ready`` is true once at least one audit exists."""
    return Health(status="ok", audit_ready=db.audit_exists())
