"""
Anansi Auth Endpoints — Register, login, refresh, logout, OAuth, and 2FA.

All endpoints are async, use Pydantic v2 models, and return structured errors
matching spec Section 8.4.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
    rate_limit,
)
from app.core.events import get_db_session, get_redis
from app.core.exceptions import AuthError
from app.services.auth import (
    AuthService,
    Enable2FAResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    Verify2FARequest,
)
from redis.asyncio import Redis

logger = get_logger(__name__)

router = APIRouter()


# ─── Helper ──────────────────────────────────────────────────────────────────────


async def _get_auth_service(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> AuthService:
    """Dependency that builds an AuthService with a DB session and Redis client."""
    return AuthService(db=db, redis=redis)


# ─── Register ────────────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=201,
    summary="Register a new account",
    description="Create a new user account with email and password. Returns JWT tokens.",
)
async def register(
    request: RegisterRequest,
    auth: AuthService = Depends(_get_auth_service),
    _: None = Depends(rate_limit(key="auth", max_requests=10, window=60)),
) -> TokenResponse:
    """Register a new user account.

    Args:
        request: Registration payload (email, password, optional display_name).

    Returns:
        TokenResponse with access and refresh tokens.

    Raises:
        409 Conflict: If the email is already registered.
        422 Unprocessable: If validation fails.
    """
    logger.info("Registration attempt", email=request.email)
    return await auth.register(request)


# ─── Login ───────────────────────────────────────────────────────────────────────


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=200,
    summary="Login with email and password",
    description="Authenticate with email/password and receive JWT tokens.",
)
async def login(
    request: LoginRequest,
    auth: AuthService = Depends(_get_auth_service),
    _: None = Depends(rate_limit(key="auth", max_requests=20, window=60)),
) -> TokenResponse:
    """Login with email and password.

    Args:
        request: Login credentials.

    Returns:
        TokenResponse with access and refresh tokens.

    Raises:
        401 Unauthorized: If credentials are invalid.
    """
    logger.info("Login attempt", email=request.email)
    return await auth.login(request)


# ─── Refresh ─────────────────────────────────────────────────────────────────────


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=200,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access/refresh token pair.",
)
async def refresh(
    request: RefreshRequest,
    auth: AuthService = Depends(_get_auth_service),
    _: None = Depends(rate_limit(key="auth", max_requests=10, window=60)),
) -> TokenResponse:
    """Refresh expired access token.

    Args:
        request: Refresh token payload.

    Returns:
        New TokenResponse with fresh tokens.

    Raises:
        401 Unauthorized: If refresh token is invalid or revoked.
    """
    logger.info("Token refresh attempt")
    return await auth.refresh_tokens(request.refresh_token)


# ─── Logout ──────────────────────────────────────────────────────────────────────


@router.post(
    "/logout",
    status_code=200,
    summary="Logout and invalidate tokens",
    description="Invalidate the current session. Blacklists access and refresh tokens.",
)
async def logout(
    request: Request,
    auth: AuthService = Depends(_get_auth_service),
    authorization: str | None = Header(default=None),
    refresh_token: str | None = Header(default=None, alias="X-Refresh-Token"),
) -> None:
    """Logout by invalidating the current tokens.

    Headers:
        Authorization: Bearer <access_token>
        X-Refresh-Token: Optional refresh token to blacklist.

    Returns:
        204 No Content on success.
    """
    access_token = None
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            access_token = token

    await auth.logout(access_token, refresh_token)
    logger.info("User logged out")


# ─── Me ──────────────────────────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=200,
    summary="Get current user",
    description="Return the profile of the currently authenticated user.",
)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    auth: AuthService = Depends(_get_auth_service),
) -> UserResponse:
    """Get the current authenticated user's profile.

    Returns:
        UserResponse with public profile fields.

    Raises:
        401 Unauthorized: If the token is missing or invalid.
    """
    user = await auth.get_user(current_user.id)
    if not user:
        raise AuthError(message="User not found", reason="user_not_found")
    return user


# ─── 2FA Enable ──────────────────────────────────────────────────────────────────


@router.post(
    "/2fa/enable",
    response_model=Enable2FAResponse,
    status_code=200,
    summary="Enable two-factor authentication",
    description="Generate a TOTP secret and QR code for 2FA setup with an authenticator app.",
)
async def enable_2fa(
    current_user: CurrentUser = Depends(get_current_user),
    auth: AuthService = Depends(_get_auth_service),
) -> Enable2FAResponse:
    """Enable 2FA for the current user.

    Returns:
        Enable2FAResponse with secret, QR code SVG, and backup codes.
    """
    return await auth.enable_2fa(current_user.id)


# ─── 2FA Verify ──────────────────────────────────────────────────────────────────


@router.post(
    "/2fa/verify",
    status_code=200,
    summary="Verify 2FA setup",
    description="Verify a TOTP code or backup code to confirm 2FA setup.",
)
async def verify_2fa(
    request: Verify2FARequest,
    current_user: CurrentUser = Depends(get_current_user),
    auth: AuthService = Depends(_get_auth_service),
) -> dict[str, Any]:
    """Verify a 2FA code to confirm setup.

    Args:
        request: 2FA verification payload (code or backup_code).

    Returns:
        dict with success status.
    """
    valid = await auth.verify_2fa(current_user.id, request.code)
    if not valid:
        raise AuthError(message="Invalid 2FA code", reason="invalid_2fa_code")

    return {"status": "verified", "message": "Two-factor authentication is now enabled"}


# ─── Google OAuth ────────────────────────────────────────────────────────────────


@router.get(
    "/google/login",
    status_code=307,
    summary="Google OAuth login redirect",
    description="Redirect to Google's OAuth consent screen.",
)
async def google_login() -> dict[str, Any]:
    """Initiate Google OAuth flow.

    Returns redirect URL for the frontend to navigate the user to Google.
    """
    from app.core.config import settings as s

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={s.oauth.google_client_id}"
        f"&redirect_uri={s.oauth.google_redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
    )
    return {"redirect_url": auth_url}


@router.get(
    "/google/callback",
    response_model=TokenResponse,
    status_code=200,
    summary="Google OAuth callback",
    description="Exchange Google's authorization code for JWT tokens.",
)
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    auth: AuthService = Depends(_get_auth_service),
    _: None = Depends(rate_limit(key="oauth", max_requests=10, window=60)),
) -> TokenResponse:
    """Handle the Google OAuth callback.

    Args:
        code: Authorization code returned by Google.

    Returns:
        TokenResponse with access and refresh tokens.
    """
    logger.info("Google OAuth callback received")
    return await auth.google_oauth_login(code)


# ─── GitHub OAuth ────────────────────────────────────────────────────────────────


@router.get(
    "/github/login",
    status_code=307,
    summary="GitHub OAuth login redirect",
    description="Redirect to GitHub's OAuth consent screen.",
)
async def github_login() -> dict[str, Any]:
    """Initiate GitHub OAuth flow."""
    from app.core.config import settings as s

    auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={s.oauth.github_client_id}"
        f"&redirect_uri={s.oauth.github_redirect_uri}"
        f"&scope=read:user%20user:email"
    )
    return {"redirect_url": auth_url}


@router.get(
    "/github/callback",
    response_model=TokenResponse,
    status_code=200,
    summary="GitHub OAuth callback",
    description="Exchange GitHub's authorization code for JWT tokens.",
)
async def github_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    auth: AuthService = Depends(_get_auth_service),
    _: None = Depends(rate_limit(key="oauth", max_requests=10, window=60)),
) -> TokenResponse:
    """Handle the GitHub OAuth callback.

    Args:
        code: Authorization code returned by GitHub.

    Returns:
        TokenResponse with access and refresh tokens.
    """
    logger.info("GitHub OAuth callback received")
    return await auth.github_oauth_login(code)


__all__ = ["router"]
