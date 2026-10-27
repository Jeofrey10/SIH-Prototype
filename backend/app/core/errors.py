"""Structured error responses."""
from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    """Application error with structured envelope."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | None = None,
    ):
        self.code = code
        self.error_message = message
        self.details = details or {}
        super().__init__(status_code=status_code, detail=message)


def error_envelope(code: str, message: str, details: dict | None = None, request_id: str | None = None) -> dict:
    """Create standard error envelope."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id or "",
        }
    }


# Pre-defined error factories
def unauthorized(message: str = "Authentication required") -> AppError:
    return AppError(401, "UNAUTHENTICATED", message)


def unauthenticated(message: str = "Authentication required") -> AppError:
    return AppError(401, "UNAUTHENTICATED", message)


def bad_request(message: str = "Bad request", details: dict | None = None) -> AppError:
    return AppError(400, "BAD_REQUEST", message, details)


def invalid_credentials() -> AppError:
    return AppError(401, "INVALID_CREDENTIALS", "Invalid email or password")


def account_locked() -> AppError:
    return AppError(423, "ACCOUNT_LOCKED", "Account is temporarily locked due to too many failed login attempts")


def forbidden(message: str = "Permission denied") -> AppError:
    return AppError(403, "FORBIDDEN", message)


def not_found(entity: str = "Resource") -> AppError:
    return AppError(404, "NOT_FOUND", f"{entity} not found")


def validation_error(details: dict) -> AppError:
    return AppError(422, "VALIDATION_ERROR", "Validation failed", details)


def invalid_status_transition(from_status: str, to_status: str) -> AppError:
    return AppError(
        409,
        "INVALID_STATUS_TRANSITION",
        f"Cannot transition from {from_status} to {to_status}",
        {"from_status": from_status, "to_status": to_status},
    )


def version_conflict() -> AppError:
    return AppError(409, "VERSION_CONFLICT", "Resource has been modified by another user. Please reload.")


def conflict(message: str) -> AppError:
    return AppError(409, "CONFLICT", message)


def internal_error() -> AppError:
    return AppError(500, "INTERNAL_ERROR", "An internal error occurred")


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle AppError exceptions."""
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(exc.code, exc.error_message, exc.details, request_id),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions without leaking stack traces."""
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=500,
        content=error_envelope("INTERNAL_ERROR", "An internal error occurred", request_id=request_id),
    )
