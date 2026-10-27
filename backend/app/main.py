"""Main FastAPI application factory and lifespan."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routers import (
    analytics,
    audit,
    auth,
    bureaus,
    complaints,
    institutions,
    notifications,
    relations,
    reports,
    system,
    threads,
    users,
)
from app.core import errors
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.jobs.scheduler import shutdown_scheduler, start_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    setup_logging()
    logger.info("Starting AICTE Complaint Dashboard Backend...")

    # Start background scheduler if enabled
    start_scheduler()

    yield

    # Clean shutdown
    shutdown_scheduler()
    logger.info("AICTE Complaint Dashboard Backend stopped.")


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="AICTE Integrated Institution Complaint Monitoring API",
        version="1.0.0",
        description="Unified grievance and complaint monitoring system across AICTE bureaus",
        lifespan=lifespan,
    )

    # CORS configuration
    origins = [
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Content-Disposition"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    # Exception handlers
    @app.exception_handler(errors.AppError)
    async def handle_app_error(request: Request, exc: errors.AppError):
        return await errors.app_error_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        req_id = getattr(request.state, "request_id", "")
        formatted_errors = {}
        for err in exc.errors():
            loc = ".".join(str(l) for l in err["loc"] if l != "body")
            formatted_errors[loc or "body"] = err["msg"]

        return JSONResponse(
            status_code=422,
            content=errors.error_envelope(
                "VALIDATION_ERROR",
                "Input validation failed",
                details=formatted_errors,
                request_id=req_id,
            ),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException):
        req_id = getattr(request.state, "request_id", "")
        code = "HTTP_ERROR"
        if exc.status_code == 401:
            code = "UNAUTHENTICATED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"
        elif exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 409:
            code = "CONFLICT"

        return JSONResponse(
            status_code=exc.status_code,
            content=errors.error_envelope(
                code,
                str(exc.detail),
                request_id=req_id,
            ),
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return await errors.generic_exception_handler(request, exc)

    # Register Routers under /api/v1
    api_v1_routers = [
        auth.router,
        users.router,
        bureaus.router,
        institutions.router,
        complaints.router,
        relations.router,
        notifications.router,
        analytics.router,
        reports.router,
        audit.router,
        threads.router,
        system.router,
    ]

    for router in api_v1_routers:
        app.include_router(router, prefix="/api/v1")

    # Root health endpoints for convenience
    app.include_router(system.router)

    return app


app = create_app()
