"""
Anansi — FastAPI Application Factory.

Creates and configures the FastAPI application with middleware, exception handlers,
router includes, OpenAPI documentation, health checks, and the lifespan context
manager for infrastructure connections.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from structlog import get_logger

from app import __version__, __app_name__, __description__
from app.api import api_router
from app.core.config import settings
from app.core.events import lifespan
from app.core.exceptions import (
    AnansiError,
    RateLimitError,
    anansi_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)
from app.websocket.handler import router as ws_router

logger = get_logger(__name__)


# ─── Request ID Middleware ───────────────────────────────────────────────────────


async def request_id_middleware(request: Request, call_next: Any) -> JSONResponse:
    """Attach a unique request ID to every request.

    Uses the ``X-Request-ID`` header if provided by the client, otherwise
    generates a new UUID.  The ID is available in ``request.state.request_id``
    and set on the response header.
    """
    req_id = request.headers.get(settings.app.request_id_header, str(uuid.uuid4()))
    request.state.request_id = req_id

    start_time = time.monotonic()

    response = await call_next(request)

    elapsed_ms = (time.monotonic() - start_time) * 1000
    response.headers[settings.app.request_id_header] = req_id
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"

    logger.info(
        "Request processed",
        method=request.method,
        path=str(request.url.path),
        status=response.status_code,
        elapsed_ms=f"{elapsed_ms:.1f}",
        request_id=req_id,
    )

    return response


# ─── Rate Limit Headers Middleware ────────────────────────────────────────────────


async def rate_limit_headers_middleware(request: Request, call_next: Any) -> JSONResponse:
    """Inject ``X-RateLimit-*`` headers from the rate limiter state."""
    response = await call_next(request)

    remaining = getattr(request.state, "rate_limit_remaining", None)
    limit = getattr(request.state, "rate_limit_limit", None)

    if remaining is not None:
        response.headers["X-RateLimit-Remaining"] = str(remaining)
    if limit is not None:
        response.headers["X-RateLimit-Limit"] = str(limit)

    return response


# ─── App Factory ─────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI instance ready for ``uvicorn``.
    """
    app = FastAPI(
        title=__app_name__,
        description=__description__,
        version=__version__,
        docs_url=settings.app.docs_url if settings.app.environment != "production" else None,
        redoc_url=settings.app.redoc_url if settings.app.environment != "production" else None,
        openapi_url=settings.app.openapi_url if settings.app.environment != "production" else None,
        lifespan=lifespan,
        terms_of_service="https://anansi.ai/terms",
        contact={
            "name": "Anansi Support",
            "url": "https://anansi.ai/support",
            "email": "support@anansi.ai",
        },
        license_info={
            "name": "Proprietary",
            "url": "https://anansi.ai/license",
        },
    )

    # ── OpenAPI Tags ─────────────────────────────────────────────────────────────
    app.openapi_tags = [
        {"name": "Authentication", "description": "Login, register, OAuth, 2FA, token management"},
        {"name": "Users", "description": "Profile management, avatars, account settings"},
        {"name": "Notifications", "description": "In-app and channel notifications"},
        {"name": "Health", "description": "Service health and readiness checks"},
    ]

    # ── Middleware ────────────────────────────────────────────────────────────────

    # CORS — whitelist anansi.ai domains
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )

    # Request ID (runs first so ID is available to all downstream middleware)
    app.middleware("http")(request_id_middleware)

    # Rate limit headers
    app.middleware("http")(rate_limit_headers_middleware)

    # ── Exception Handlers ───────────────────────────────────────────────────────
    app.add_exception_handler(AnansiError, anansi_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    # Override FastAPI's default 422 handler — not strictly needed since our
    # http_exception_handler covers it, but we register for clarity.

    # ── Routers ──────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.app.api_prefix)

    # WebSocket router (separate — not under /api prefix)
    app.include_router(ws_router, prefix="/ws")

    # ── Health Check ─────────────────────────────────────────────────────────────
    _register_health_endpoint(app)

    logger.info(
        "Anansi application created",
        version=__version__,
        environment=settings.app.environment,
        docs_enabled=settings.app.docs_url is not None,
    )

    return app


# ─── Health Check ────────────────────────────────────────────────────────────────


def _register_health_endpoint(app: FastAPI) -> None:
    """Register the /health endpoint with dependency checks."""

    @app.get(
        "/health",
        tags=["Health"],
        summary="Health check",
        description="Returns the health status of the application and its dependencies.",
        operation_id="health_check",
    )
    async def health_check(request: Request) -> dict[str, Any]:
        """Return the current health status of the service.

        Checks connectivity to PostgreSQL, Redis, and Neo4j.
        Returns HTTP 200 if healthy, 503 if critical dependencies are down.
        """
        from app.core.events import get_redis, get_neo4j, get_session_factory

        health: dict[str, Any] = {
            "status": "healthy",
            "version": __version__,
            "app": __app_name__,
            "environment": settings.app.environment,
            "request_id": getattr(request.state, "request_id", None),
            "checks": {},
        }

        all_ok = True

        # Database check
        try:
            factory = get_session_factory()
            async with factory() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
            health["checks"]["database"] = {"status": "ok"}
        except Exception as exc:
            health["checks"]["database"] = {"status": "error", "detail": str(exc)}
            all_ok = False

        # Redis check
        try:
            redis = get_redis()
            await redis.ping()
            health["checks"]["redis"] = {"status": "ok"}
        except Exception as exc:
            health["checks"]["redis"] = {"status": "error", "detail": str(exc)}
            all_ok = False

        # Neo4j check
        try:
            neo4j = get_neo4j()
            async with neo4j.session(database=settings.neo4j.database) as session:
                result = await session.run("RETURN 1 AS ok")
                record = await result.single()
                if record and record.get("ok") == 1:
                    health["checks"]["neo4j"] = {"status": "ok"}
                else:
                    health["checks"]["neo4j"] = {"status": "error", "detail": "Unexpected response"}
                    all_ok = False
        except Exception as exc:
            health["checks"]["neo4j"] = {"status": "error", "detail": str(exc)}
            all_ok = False

        if not all_ok:
            health["status"] = "degraded"

        status_code = 200 if health["status"] != "degraded" else 503
        from fastapi.responses import JSONResponse
        return JSONResponse(content=health, status_code=status_code)

    logger.debug("Health endpoint registered at /health")


# ─── Instantiate for uvicorn ────────────────────────────────────────────────────

app = create_app()

__all__ = ["app", "create_app"]
