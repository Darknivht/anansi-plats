"""
Anansi Dependencies — FastAPI dependency injection for auth, plans, and rate limiting.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, Header, Request
from pydantic import BaseModel
from structlog import get_logger

from app.core.config import settings
from app.core.exceptions import (
    AuthError,
    PlanLimitError,
    RateLimitError,
)
from app.core.security import (
    TokenBucketRateLimiter,
    get_rate_limiter,
    verify_token,
)
from app.core.events import get_db_session
from app.services.user import UserService

logger = get_logger(__name__)


# ─── Pydantic Models ─────────────────────────────────────────────────────────────


class CurrentUser(BaseModel):
    """Authenticated user info extracted from the JWT."""

    id: str
    email: str
    display_name: str | None = None
    plan: str = "free"
    is_active: bool = True
    is_verified: bool = False


# ─── Extracting user from token ──────────────────────────────────────────────────


async def _get_user_from_token(
    token: str,
    *,
    required: bool = True,
) -> CurrentUser | None:
    """Validate a JWT and return the CurrentUser (or None if optional)."""
    try:
        payload = verify_token(token, expected_type="access")
    except ValueError as exc:
        if required:
            raise AuthError(message=str(exc), reason="invalid_token")
        return None

    user_id = payload.get("sub")
    if not user_id:
        if required:
            raise AuthError(message="Token missing subject claim", reason="invalid_token")
        return None

    return CurrentUser(
        id=user_id,
        email=payload.get("email", ""),
        display_name=payload.get("display_name"),
        plan=payload.get("plan", "free"),
        is_active=payload.get("is_active", True),
        is_verified=payload.get("is_verified", False),
    )


# ─── Dependency: get_current_user ────────────────────────────────────────────────


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """Require a valid authenticated user.

    Extracts the JWT from the ``Authorization: Bearer <token>`` header,
    verifies it, and returns the user info.

    Raises:
        AuthError (401): If the token is missing or invalid.
    """
    if not authorization:
        raise AuthError(
            message="Authorization header is required",
            reason="missing_auth_header",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError(
            message="Authorization header must use Bearer scheme",
            reason="invalid_auth_scheme",
        )

    user = await _get_user_from_token(token, required=True)
    # Attach to request state for downstream use (middleware, logging, etc.)
    request.state.user_id = user.id
    request.state.user_plan = user.plan
    return user


# ─── Dependency: get_optional_user ───────────────────────────────────────────────


async def get_optional_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> CurrentUser | None:
    """Optionally resolve the current user.

    Returns None if no (or invalid) token is provided.
    Useful for public endpoints that show personalised data when available.
    """
    if not authorization:
        return None

    try:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        user = await _get_user_from_token(token, required=False)
        if user:
            request.state.user_id = user.id
            request.state.user_plan = user.plan
        return user
    except Exception:
        return None


# ─── Dependency: require_plan ────────────────────────────────────────────────────


class PlanRequireDependency:
    """Plan-based access control dependency.

    Usage:
        ``require_plan("pro")`` or ``require_plan("business")`` as a dependency.
    """

    def __init__(self, minimum_plan: str, feature: str | None = None) -> None:
        self.minimum_plan = minimum_plan
        self.feature = feature

    _PLAN_ORDER = {"free": 0, "pro": 1, "business": 2}

    async def __call__(self, current_user: CurrentUser = Depends(get_current_user)) -> None:
        user_plan_level = self._PLAN_ORDER.get(current_user.plan, 0)
        required_level = self._PLAN_ORDER.get(self.minimum_plan, 0)

        if user_plan_level < required_level:
            raise PlanLimitError(
                feature=self.feature or f"Plan {self.minimum_plan} feature",
                required_plan=self.minimum_plan,
            )


def require_plan(minimum_plan: str, feature: str | None = None) -> PlanRequireDependency:
    """Require a minimum subscription plan.

    Args:
        minimum_plan: Minimum plan name ('free', 'pro', 'business').
        feature: Optional feature name for the error message.

    Returns:
        FastAPI dependency callable.
    """
    return PlanRequireDependency(minimum_plan=minimum_plan, feature=feature)


# ─── Dependency: rate_limit ──────────────────────────────────────────────────────


class RateLimitDependency:
    """Rate limiting dependency.

    Uses Redis-backed token-bucket. Falls back to config defaults per plan.

    Usage:
        ``RateLimitDependency(key="user", max_requests=100, window=60)``
    """

    def __init__(
        self,
        key: str = "user",
        max_requests: int | None = None,
        window_seconds: int | None = None,
    ) -> None:
        self._key_prefix = key
        self._max_requests = max_requests
        self._window = window_seconds

    async def __call__(
        self,
        request: Request,
        current_user: CurrentUser | None = Depends(get_optional_user),
    ) -> None:
        limiter = get_rate_limiter()

        # Determine the rate limit based on plan
        plan = current_user.plan if current_user else "free"
        max_r, window = self._get_rate_for_plan(plan)

        # Build the Redis key
        if current_user:
            key = f"{self._key_prefix}:{current_user.id}"
        else:
            # Fall back to IP for unauthenticated requests
            forwarded = request.headers.get("X-Forwarded-For", "")
            client_ip = forwarded.split(",")[0].strip() or request.client.host if request.client else "unknown"
            key = f"{self._key_prefix}:ip:{client_ip}"

        allowed, remaining, retry_after = await limiter.check(
            key=key, max_requests=max_r, window_seconds=window
        )

        # Set response headers
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = max_r

        if not allowed:
            raise RateLimitError(
                retry_after_seconds=retry_after,
                limit=max_r,
                window=window,
            )

    def _get_rate_for_plan(self, plan: str) -> tuple[int, int]:
        """Get max_requests and window for a given plan."""
        if self._max_requests is not None and self._window is not None:
            return self._max_requests, self._window

        plan_rates = {
            "free": (settings.rate_limit.free_max_requests, settings.rate_limit.free_window_seconds),
            "pro": (settings.rate_limit.pro_max_requests, settings.rate_limit.pro_window_seconds),
            "business": (settings.rate_limit.business_max_requests, settings.rate_limit.business_window_seconds),
        }
        return plan_rates.get(plan, plan_rates["free"])


def rate_limit(
    key: str = "user",
    max_requests: int | None = None,
    window: int | None = None,
) -> RateLimitDependency:
    """Rate limit a route.

    Args:
        key: Identifier prefix for the rate limit bucket.
        max_requests: Max requests in the window (overrides plan default).
        window: Time window in seconds (overrides plan default).

    Returns:
        FastAPI dependency callable.
    """
    return RateLimitDependency(key=key, max_requests=max_requests, window_seconds=window)


# ─── Dependency: get_user_service ────────────────────────────────────────────────


async def get_user_service() -> UserService:
    """Provide a UserService instance with a database session.

    This is a simple factory; the service manages its own session.
    """
    return UserService()


__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_optional_user",
    "require_plan",
    "rate_limit",
    "get_user_service",
    "RateLimitDependency",
    "PlanRequireDependency",
]
