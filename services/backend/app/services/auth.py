"""
Anansi Auth Service — Registration, login, OAuth flows, and token management.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

import pyotp
import qrcode
import qrcode.image.svg
from pydantic import BaseModel, EmailStr, field_validator
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.exceptions import (
    AuthError,
    ConflictError,
    NotFoundError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.core.events import get_db_session

logger = get_logger(__name__)


# ─── Schemas ─────────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    password: str
    display_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """Request schema for login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response schema for successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = settings.jwt.access_token_expire_minutes * 60


class UserResponse(BaseModel):
    """Public user profile response."""

    id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    plan: str = "free"
    is_verified: bool = False
    timezone: str = "Africa/Lagos"
    created_at: str | None = None


class Verify2FARequest(BaseModel):
    """Request schema for 2FA verification."""

    code: str
    backup_code: str | None = None


class Enable2FAResponse(BaseModel):
    """Response from enabling 2FA."""

    secret: str
    qr_code_svg: str
    backup_codes: list[str]


class RefreshRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str


# ─── Auth Service ────────────────────────────────────────────────────────────────


class AuthService:
    """Handles user authentication, registration, and token lifecycle."""

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    # ── Registration ──────────────────────────────────────────────────────────────

    async def register(self, request: RegisterRequest) -> TokenResponse:
        """Register a new user account.

        Args:
            request: Registration details.

        Returns:
            TokenResponse with access and refresh tokens.

        Raises:
            ConflictError: If the email is already registered.
        """
        # Check for existing user
        existing = await self.db.execute(
            text("SELECT id FROM users WHERE email = :email AND is_active = true"),
            {"email": request.email},
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                message=f"An account with email '{request.email}' already exists",
                links=["[[Login]]", "[[Reset Password]]"],
            )

        # Create user
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)
        password_hash = hash_password(request.password)
        display_name = request.display_name or request.email.split("@")[0]

        await self.db.execute(
            text("""
                INSERT INTO users (id, email, password_hash, display_name, timezone, is_active, created_at, updated_at)
                VALUES (:id, :email, :password_hash, :display_name, :timezone, true, :now, :now)
            """),
            {
                "id": user_id,
                "email": request.email,
                "password_hash": password_hash,
                "display_name": display_name,
                "timezone": "Africa/Lagos",
                "now": now,
            },
        )
        await self.db.commit()

        logger.info("User registered", user_id=user_id, email=request.email)

        # Generate tokens
        return await self._create_tokens(
            user_id=user_id,
            extra_claims={"email": request.email, "display_name": display_name, "plan": "free"},
        )

    # ── Login ─────────────────────────────────────────────────────────────────────

    async def login(self, request: LoginRequest) -> TokenResponse:
        """Authenticate a user with email and password.

        Args:
            request: Login credentials.

        Returns:
            TokenResponse with access and refresh tokens.

        Raises:
            AuthError: If credentials are invalid or account is inactive.
        """
        result = await self.db.execute(
            text("""
                SELECT id, email, password_hash, display_name, is_active, is_verified, plan
                FROM users WHERE email = :email
            """),
            {"email": request.email},
        )
        user = result.one_or_none()
        if not user:
            raise AuthError(message="Invalid email or password", reason="invalid_credentials")

        user_id, email, password_hash, display_name, is_active, is_verified, plan = user

        if not is_active:
            raise AuthError(message="Account is deactivated", reason="account_inactive")

        if not verify_password(request.password, password_hash):
            raise AuthError(message="Invalid email or password", reason="invalid_credentials")

        logger.info("User logged in", user_id=user_id, email=email)

        return await self._create_tokens(
            user_id=user_id,
            extra_claims={
                "email": email,
                "display_name": display_name,
                "plan": plan,
                "is_active": is_active,
                "is_verified": is_verified,
            },
        )

    # ── Token Refresh ─────────────────────────────────────────────────────────────

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Exchange a valid refresh token for a new token pair.

        Args:
            refresh_token: The current refresh token.

        Returns:
            TokenResponse with new access and refresh tokens.

        Raises:
            AuthError: If the refresh token is invalid or revoked.
        """
        # Check if token is blacklisted
        blacklisted = await self.redis.get(f"token:blacklist:{refresh_token}")
        if blacklisted:
            raise AuthError(message="Refresh token has been revoked", reason="token_revoked")

        try:
            payload = verify_token(refresh_token, expected_type="refresh")
        except ValueError as exc:
            raise AuthError(message=str(exc), reason="invalid_token")

        user_id = payload.get("sub")

        # Fetch fresh user data
        result = await self.db.execute(
            text("""
                SELECT id, email, display_name, plan, is_active, is_verified
                FROM users WHERE id = :user_id
            """),
            {"user_id": user_id},
        )
        user = result.one_or_none()
        if not user:
            raise AuthError(message="User not found", reason="user_not_found")

        user_id, email, display_name, plan, is_active, is_verified = user

        if not is_active:
            raise AuthError(message="Account is deactivated", reason="account_inactive")

        # Revoke old refresh token
        await self.redis.setex(
            f"token:blacklist:{refresh_token}",
            settings.jwt.refresh_token_expire_days * 86400,
            "revoked",
        )

        logger.info("Tokens refreshed", user_id=user_id)

        return await self._create_tokens(
            user_id=user_id,
            extra_claims={
                "email": email,
                "display_name": display_name,
                "plan": plan,
                "is_active": is_active,
                "is_verified": is_verified,
            },
        )

    # ── Logout ────────────────────────────────────────────────────────────────────

    async def logout(self, access_token: str, refresh_token: str | None = None) -> None:
        """Invalidate tokens.

        Blacklists the refresh token (if provided) and stores the access token
        until its natural expiry so it can't be used again.

        Args:
            access_token: The JWT access token to blacklist.
            refresh_token: Optional refresh token to blacklist.
        """
        try:
            payload = verify_token(access_token, expected_type="access")
            exp = payload.get("exp", 0)
            now = datetime.now(timezone.utc).timestamp()
            ttl = max(0, int(exp - now))

            if ttl > 0:
                await self.redis.setex(f"token:blacklist:{access_token}", ttl, "revoked")

            if refresh_token:
                await self.redis.setex(
                    f"token:blacklist:{refresh_token}",
                    settings.jwt.refresh_token_expire_days * 86400,
                    "revoked",
                )

            logger.info("User logged out", user_id=payload.get("sub"))
        except ValueError:
            # Token already expired — nothing to blacklist
            pass

    # ── 2FA ───────────────────────────────────────────────────────────────────────

    async def enable_2fa(self, user_id: str) -> Enable2FAResponse:
        """Generate a TOTP secret and QR code for 2FA setup.

        Args:
            user_id: The user ID.

        Returns:
            Enable2FAResponse with secret, QR SVG, and backup codes.
        """
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=f"Anansi:{user_id[:8]}",
            issuer_name="Anansi",
        )

        # Generate QR code as SVG
        qr = qrcode.make(provisioning_uri, image_factory=qrcode.image.svg.SvgImage)
        qr_svg = qr.to_string().decode("utf-8")

        # Generate backup codes
        backup_codes = [secrets.token_hex(4) for _ in range(8)]

        # Store secret and backup codes
        await self.redis.setex(f"2fa:secret:{user_id}", 300, secret)
        for code in backup_codes:
            await self.redis.setex(f"2fa:backup:{user_id}:{code}", 300, "valid")

        logger.info("2FA enabled", user_id=user_id)

        return Enable2FAResponse(
            secret=secret,
            qr_code_svg=qr_svg,
            backup_codes=backup_codes,
        )

    async def verify_2fa(self, user_id: str, code: str) -> bool:
        """Verify a TOTP code or backup code.

        Args:
            user_id: The user ID.
            code: The 6-digit TOTP code or backup code.

        Returns:
            True if the code is valid.
        """
        # Check TOTP
        secret = await self.redis.get(f"2fa:secret:{user_id}")
        if secret:
            totp = pyotp.TOTP(secret)
            if totp.verify(code, valid_window=1):
                # Code is valid — mark 2FA as enabled in the database
                await self.db.execute(
                    text("UPDATE users SET is_verified = true WHERE id = :user_id"),
                    {"user_id": user_id},
                )
                await self.db.commit()
                await self.redis.delete(f"2fa:secret:{user_id}")
                return True

        # Check backup code
        backup_valid = await self.redis.get(f"2fa:backup:{user_id}:{code}")
        if backup_valid:
            await self.redis.delete(f"2fa:backup:{user_id}:{code}")
            await self.db.execute(
                text("UPDATE users SET is_verified = true WHERE id = :user_id"),
                {"user_id": user_id},
            )
            await self.db.commit()
            return True

        return False

    # ── Google OAuth ──────────────────────────────────────────────────────────────

    async def google_oauth_login(self, code: str) -> TokenResponse:
        """Exchange a Google OAuth authorization code for tokens.

        Args:
            code: Google OAuth authorization code.

        Returns:
            TokenResponse for the authenticated user.

        Raises:
            AuthError: If the OAuth exchange fails.
        """
        import httpx

        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.oauth.google_client_id,
            "client_secret": settings.oauth.google_client_secret,
            "redirect_uri": settings.oauth.google_redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=data)
            if token_response.status_code != 200:
                raise AuthError(message="Google OAuth token exchange failed", reason="oauth_error")

            tokens = token_response.json()
            access_token = tokens.get("access_token")

            # Fetch user info
            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_info_response.status_code != 200:
                raise AuthError(message="Failed to fetch Google user info", reason="oauth_error")

            user_info = user_info_response.json()

        google_id = user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("name", email.split("@")[0] if email else "User")

        if not email:
            raise AuthError(message="Google account has no email", reason="oauth_error")

        # Check if user exists via OAuth
        result = await self.db.execute(
            text("""
                SELECT u.id, u.email, u.display_name, u.plan, u.is_active, u.is_verified
                FROM users u
                JOIN oauth_accounts oa ON oa.user_id = u.id
                WHERE oa.provider = 'google' AND oa.provider_account_id = :google_id
            """),
            {"google_id": google_id},
        )
        user = result.one_or_none()

        if user:
            user_id, user_email, display_name, plan, is_active, is_verified = user
        else:
            # Check if email already registered (link accounts)
            existing = await self.db.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            )
            existing_user = existing.scalar_one_or_none()

            if existing_user:
                # Link the OAuth account
                await self.db.execute(
                    text("""
                        INSERT INTO oauth_accounts (id, user_id, provider, provider_account_id, email)
                        VALUES (:id, :user_id, 'google', :google_id, :email)
                    """),
                    {"id": str(uuid4()), "user_id": existing_user, "google_id": google_id, "email": email},
                )
                await self.db.commit()
                user_id = existing_user
                display_name = name
                plan = "free"
                is_active = True
                is_verified = True
            else:
                # Create new user
                user_id = str(uuid4())
                now = datetime.now(timezone.utc)
                await self.db.execute(
                    text("""
                        INSERT INTO users (id, email, display_name, timezone, is_verified, is_active, created_at, updated_at)
                        VALUES (:id, :email, :name, 'Africa/Lagos', true, true, :now, :now)
                    """),
                    {"id": user_id, "email": email, "name": name, "now": now},
                )
                await self.db.execute(
                    text("""
                        INSERT INTO oauth_accounts (id, user_id, provider, provider_account_id, email)
                        VALUES (:id, :user_id, 'google', :google_id, :email)
                    """),
                    {"id": str(uuid4()), "user_id": user_id, "google_id": google_id, "email": email},
                )
                await self.db.commit()
                display_name = name
                plan = "free"
                is_active = True
                is_verified = True

            logger.info("User registered via Google OAuth", user_id=user_id, email=email)

        return await self._create_tokens(
            user_id=user_id,
            extra_claims={
                "email": email,
                "display_name": display_name,
                "plan": plan,
                "is_active": is_active,
                "is_verified": is_verified,
            },
        )

    # ── GitHub OAuth ──────────────────────────────────────────────────────────────

    async def github_oauth_login(self, code: str) -> TokenResponse:
        """Exchange a GitHub OAuth authorization code for tokens.

        Args:
            code: GitHub OAuth authorization code.

        Returns:
            TokenResponse for the authenticated user.

        Raises:
            AuthError: If the OAuth exchange fails.
        """
        import httpx

        token_url = "https://github.com/login/oauth/access_token"
        headers = {"Accept": "application/json"}
        data = {
            "code": code,
            "client_id": settings.oauth.github_client_id,
            "client_secret": settings.oauth.github_client_secret,
            "redirect_uri": settings.oauth.github_redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=data, headers=headers)
            if token_response.status_code != 200:
                raise AuthError(message="GitHub OAuth token exchange failed", reason="oauth_error")

            tokens = token_response.json()
            access_token = tokens.get("access_token")

            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            if user_response.status_code != 200:
                raise AuthError(message="Failed to fetch GitHub user info", reason="oauth_error")

            user_info = user_response.json()

            # Also fetch primary email
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            emails = email_response.json()
            primary_email = next(
                (e["email"] for e in emails if e.get("primary")),
                user_info.get("email") or "",
            )

        github_id = str(user_info.get("id"))
        email = primary_email
        name = user_info.get("name") or user_info.get("login") or email.split("@")[0]

        if not email:
            raise AuthError(message="GitHub account has no public email", reason="oauth_error")

        # Check existing OAuth link
        result = await self.db.execute(
            text("""
                SELECT u.id, u.email, u.display_name, u.plan, u.is_active, u.is_verified
                FROM users u
                JOIN oauth_accounts oa ON oa.user_id = u.id
                WHERE oa.provider = 'github' AND oa.provider_account_id = :github_id
            """),
            {"github_id": github_id},
        )
        user = result.one_or_none()

        if user:
            user_id, user_email, display_name, plan, is_active, is_verified = user
        else:
            existing = await self.db.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            )
            existing_user = existing.scalar_one_or_none()

            if existing_user:
                await self.db.execute(
                    text("""
                        INSERT INTO oauth_accounts (id, user_id, provider, provider_account_id, email)
                        VALUES (:id, :user_id, 'github', :github_id, :email)
                    """),
                    {"id": str(uuid4()), "user_id": existing_user, "github_id": github_id, "email": email},
                )
                await self.db.commit()
                user_id = existing_user
            else:
                user_id = str(uuid4())
                now = datetime.now(timezone.utc)
                await self.db.execute(
                    text("""
                        INSERT INTO users (id, email, display_name, timezone, is_verified, is_active, created_at, updated_at)
                        VALUES (:id, :email, :name, 'Africa/Lagos', true, true, :now, :now)
                    """),
                    {"id": user_id, "email": email, "name": name, "now": now},
                )
                await self.db.execute(
                    text("""
                        INSERT INTO oauth_accounts (id, user_id, provider, provider_account_id, email)
                        VALUES (:id, :user_id, 'github', :github_id, :email)
                    """),
                    {"id": str(uuid4()), "user_id": user_id, "github_id": github_id, "email": email},
                )
                await self.db.commit()

            logger.info("User registered via GitHub OAuth", user_id=user_id, email=email)
            display_name = name
            plan = "free"
            is_active = True
            is_verified = True

        return await self._create_tokens(
            user_id=user_id,
            extra_claims={
                "email": email,
                "display_name": display_name,
                "plan": plan,
                "is_active": is_active,
                "is_verified": is_verified,
            },
        )

    # ── Get Current User ──────────────────────────────────────────────────────────

    async def get_user(self, user_id: str) -> UserResponse | None:
        """Fetch a user's profile by ID.

        Args:
            user_id: The user UUID.

        Returns:
            UserResponse or None if not found.
        """
        result = await self.db.execute(
            text("""
                SELECT id, email, display_name, avatar_url, plan, is_verified, timezone, created_at
                FROM users WHERE id = :user_id AND is_active = true
            """),
            {"user_id": user_id},
        )
        user = result.one_or_none()
        if not user:
            return None

        return UserResponse(
            id=user[0],
            email=user[1],
            display_name=user[2],
            avatar_url=user[3],
            plan=user[4],
            is_verified=bool(user[5]),
            timezone=user[6],
            created_at=user[7].isoformat() if user[7] else None,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────────

    async def _create_tokens(
        self,
        user_id: str,
        extra_claims: dict[str, Any] | None = None,
    ) -> TokenResponse:
        """Generate access and refresh token pair.

        Also persists the refresh token in Redis for session management.
        """
        access_token = create_access_token(user_id, extra_claims=extra_claims)
        refresh_token = create_refresh_token(user_id, extra_claims=extra_claims)

        # Store refresh token fingerprint in Redis (for session listing / revocation)
        refresh_jti = str(uuid4())
        await self.redis.setex(
            f"session:{user_id}:{refresh_jti}",
            settings.jwt.refresh_token_expire_days * 86400,
            refresh_token[:32],  # Store partial hash as fingerprint
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.jwt.access_token_expire_minutes * 60,
        )


__all__ = [
    "AuthService",
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "UserResponse",
    "RefreshRequest",
    "Verify2FARequest",
    "Enable2FAResponse",
]
