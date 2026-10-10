"""VoterGuard trust service (:8002): report builder, hashing, PDF and chain integration."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, load_settings
from .deps import Services, build_services
from .errors import ApiError, api_error_handler, validation_error_handler
from .routers import chain_status, reports

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    """App factory. Tests pass their own `services` with stub chain and core clients."""
    app = FastAPI(title="VoterGuard Trust Service", version="0.1.0")
    app.state.services = services or build_services(settings or load_settings())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(reports.router)
    app.include_router(chain_status.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
