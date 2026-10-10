"""Standard error body from CONTRACT.md 6.1: {"error": {"code": "...", "message": "..."}}."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """An error that is returned to the client with the standard error body."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Build a JSON response with the standard error body."""
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def _api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Describe which fields are wrong, never the submitted values (they may be personal data)."""
    parts = [f"{'.'.join(str(p) for p in e['loc'] if p != 'body')}: {e['msg']}" for e in exc.errors()]
    return error_response(422, "VALIDATION_ERROR", "; ".join(parts) or "Invalid request")


def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
    return error_response(exc.status_code, code, str(exc.detail))


def _unexpected_handler(_: Request, __: Exception) -> JSONResponse:
    return error_response(500, "INTERNAL_ERROR", "Unexpected server error")


def install_error_handlers(app: FastAPI) -> None:
    """Register handlers so every error response uses the standard body."""
    app.add_exception_handler(ApiError, _api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unexpected_handler)
