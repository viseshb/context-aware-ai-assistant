"""Structured error classes and handlers with full logging."""
from __future__ import annotations

import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.utils.logging import get_logger

log = get_logger("errors")


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401, code="AUTH_REQUIRED")


class AuthorizationError(AppError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403, code="FORBIDDEN")


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404, code="NOT_FOUND")


class ValidationError(AppError):
    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, status_code=422, code="VALIDATION_ERROR")


class SecurityError(AppError):
    def __init__(self, message: str = "Security policy violation"):
        super().__init__(message, status_code=403, code="SECURITY_VIOLATION")


class RateLimitError(AppError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429, code="RATE_LIMITED")


class ExternalServiceError(AppError):
    def __init__(self, service: str, message: str = "External service error"):
        super().__init__(f"[{service}] {message}", status_code=502, code="EXTERNAL_SERVICE_ERROR")


class DatabaseError(AppError):
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status_code=500, code="DATABASE_ERROR")


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    # Log based on severity
    if exc.status_code >= 500:
        log.error("app_error", code=exc.code, status=exc.status_code, message=exc.message)
    elif exc.status_code >= 400:
        log.warning("app_error", code=exc.code, status=exc.status_code, message=exc.message)

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — log full traceback."""
    log.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error=str(exc),
        traceback=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Check server logs for details.",
        },
    )
