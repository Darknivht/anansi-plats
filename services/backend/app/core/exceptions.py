"""
Anansi Custom Exceptions — Standardised error responses matching spec Section 8.4.

Error format:
```json
{
  "error": {
    "code": "snake_case_error_code",
    "message": "Human-readable description",
    "details": { ... },
    "links": ["[[Related]]"],
    "request_id": "req_..."
  }
}
```
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from structlog import get_logger

logger = get_logger(__name__)


class AnansiError(Exception):
    """Base exception for all Anansi platform errors."""

    code: str = "internal_error"
    status_code: int = 500
    message: str = "An unexpected error occurred"
    details: dict[str, Any] | None = None
    links: list[str] | None = None
    request_id: str | None = None

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        links: list[str] | None = None,
        request_id: str | None = None,
    ) -> None:
        if message:
            self.message = message
        if code:
            self.code = code
        self.details = details
        self.links = links
        self.request_id = request_id
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        if self.links:
            payload["links"] = self.links
        if self.request_id:
            payload["request_id"] = self.request_id
        return {"error": payload}

    def to_http_exception(self) -> HTTPException:
        return HTTPException(status_code=self.status_code, detail=self.to_dict())


# ─── Specific Exception Classes ──────────────────────────────────────────────────


class NotFoundError(AnansiError):
    """Resource not found — 404."""

    code: str = "not_found"
    status_code: int = 404
    message: str = "The requested resource was not found"

    def __init__(
        self,
        message: str | None = None,
        *,
        resource_type: str = "resource",
        resource_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"resource_type": resource_type}
        if resource_id:
            details["id"] = resource_id
            details["suggestion"] = f"Check the {resource_type} ID or list your {resource_type}s"
        super().__init__(message, details=details, **kwargs)


class AuthError(AnansiError):
    """Authentication / authorisation failure — 401."""

    code: str = "authentication_error"
    status_code: int = 401
    message: str = "Authentication failed"

    def __init__(
        self,
        message: str | None = None,
        *,
        reason: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = {"reason": reason} if reason else None
        super().__init__(message, details=details, **kwargs)


class ForbiddenError(AnansiError):
    """Insufficient permissions — 403."""

    code: str = "forbidden"
    status_code: int = 403
    message: str = "You do not have permission to perform this action"


class RateLimitError(AnansiError):
    """Too many requests — 429."""

    code: str = "rate_limit_exceeded"
    status_code: int = 429
    message: str = "Too many requests. Please try again later."

    def __init__(
        self,
        message: str | None = None,
        *,
        retry_after_seconds: int | None = None,
        limit: int | None = None,
        window: int | None = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {}
        if retry_after_seconds is not None:
            details["retry_after_seconds"] = retry_after_seconds
        if limit is not None:
            details["limit"] = limit
        if window is not None:
            details["window_seconds"] = window
        super().__init__(message, details=details if details else None, **kwargs)


class PlanLimitError(AnansiError):
    """Feature not available on current plan — 403 with upgrade hint."""

    code: str = "plan_limit_exceeded"
    status_code: int = 403
    message: str = "This feature is not available on your current plan"

    def __init__(
        self,
        message: str | None = None,
        *,
        feature: str | None = None,
        required_plan: str | None = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {}
        if feature:
            details["feature"] = feature
        if required_plan:
            details["required_plan"] = required_plan
            details["suggestion"] = f"Upgrade to {required_plan} to access this feature"
        super().__init__(message, details=details if details else None, **kwargs)


class ValidationError(AnansiError):
    """Request validation failure — 422."""

    code: str = "validation_error"
    status_code: int = 422
    message: str = "Request validation failed"

    def __init__(
        self,
        message: str | None = None,
        *,
        fields: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, details={"fields": fields} if fields else None, **kwargs)


class ConflictError(AnansiError):
    """Resource conflict — 409."""

    code: str = "conflict"
    status_code: int = 409
    message: str = "The request could not be completed due to a conflict"


class ServiceUnavailableError(AnansiError):
    """External dependency unavailable — 503."""

    code: str = "service_unavailable"
    status_code: int = 503
    message: str = "A required service is temporarily unavailable"


# ─── Exception Handlers for FastAPI ─────────────────────────────────────────────


async def anansi_exception_handler(request: Request, exc: AnansiError) -> JSONResponse:
    """Handle custom Anansi exceptions and return the structured error format."""
    error_dict = exc.to_dict()
    # Inject request_id if available
    req_id = getattr(request.state, "request_id", None)
    if req_id and "request_id" not in error_dict.get("error", {}):
        error_dict["error"]["request_id"] = req_id

    logger.error(
        "Anansi exception",
        code=exc.code,
        status=exc.status_code,
        path=str(request.url.path),
        request_id=req_id,
    )
    return JSONResponse(status_code=exc.status_code, content=error_dict)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert standard HTTPException to Anansi error format."""
    req_id = getattr(request.state, "request_id", None)

    # If the detail is already our format, pass it through
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = exc.detail
        if req_id and "request_id" not in content.get("error", {}):
            content["error"]["request_id"] = req_id
        return JSONResponse(status_code=exc.status_code, content=content)

    # Build a standard error
    code_map: dict[int, str] = {
        400: "bad_request",
        401: "authentication_error",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_error",
        503: "service_unavailable",
    }
    error_payload: dict[str, Any] = {
        "error": {
            "code": code_map.get(exc.status_code, "error"),
            "message": str(exc.detail) if exc.detail else "An error occurred",
        }
    }
    if req_id:
        error_payload["error"]["request_id"] = req_id

    logger.warning(
        "HTTP exception",
        status=exc.status_code,
        path=str(request.url.path),
        request_id=req_id,
    )
    return JSONResponse(status_code=exc.status_code, content=error_payload)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions (500)."""
    req_id = getattr(request.state, "request_id", None)
    logger.exception(
        "Unhandled exception",
        path=str(request.url.path),
        request_id=req_id,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
                "request_id": req_id or "unknown",
            }
        },
    )


__all__ = [
    "AnansiError",
    "NotFoundError",
    "AuthError",
    "ForbiddenError",
    "RateLimitError",
    "PlanLimitError",
    "ValidationError",
    "ConflictError",
    "ServiceUnavailableError",
    "anansi_exception_handler",
    "http_exception_handler",
    "unhandled_exception_handler",
]
