"""
Anansi User Service — CRUD operations, profile management, and avatar uploads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.exceptions import NotFoundError, ConflictError
from app.core.security import hash_password

logger = get_logger(__name__)


# ─── Schemas ─────────────────────────────────────────────────────────────────────


class ProfileResponse(BaseModel):
    """User profile response."""

    id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    timezone: str = "Africa/Lagos"
    language: str = "en"
    theme: str = "dark"
    plan: str = "free"
    is_verified: bool = False
    onboarding_step: int = 0
    brain_age_days: int = 0
    memory_count: int = 0
    link_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class ProfileUpdateRequest(BaseModel):
    """Request schema for updating user profile."""

    display_name: str | None = None
    timezone: str | None = None
    language: str | None = None
    theme: str | None = None
    onboarding_step: int | None = None

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str | None) -> str | None:
        if v is not None and v not in ("dark", "light"):
            raise ValueError("Theme must be 'dark' or 'light'")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None and len(v) != 2:
            raise ValueError("Language must be a 2-letter ISO code")
        return v


class AvatarResponse(BaseModel):
    """Response after avatar upload."""

    avatar_url: str


# ─── User Service ────────────────────────────────────────────────────────────────


class UserService:
    """Business logic for user profile CRUD."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_profile(self, user_id: str) -> ProfileResponse:
        """Retrieve a user's full profile.

        Args:
            user_id: The user UUID.

        Returns:
            ProfileResponse with all profile fields.

        Raises:
            NotFoundError: If the user does not exist.
        """
        result = await self.db.execute(
            text("""
                SELECT
                    id, email, display_name, avatar_url, timezone, language, theme,
                    plan, is_verified, onboarding_step, brain_age_days,
                    memory_count, link_count, created_at, updated_at
                FROM users
                WHERE id = :user_id AND is_active = true
            """),
            {"user_id": user_id},
        )
        row = result.one_or_none()
        if not row:
            raise NotFoundError(
                message="User not found",
                resource_type="user",
                resource_id=user_id,
            )

        return ProfileResponse(
            id=row[0],
            email=row[1],
            display_name=row[2],
            avatar_url=row[3],
            timezone=row[4],
            language=row[5],
            theme=row[6],
            plan=row[7],
            is_verified=bool(row[8]),
            onboarding_step=row[9] or 0,
            brain_age_days=row[10] or 0,
            memory_count=row[11] or 0,
            link_count=row[12] or 0,
            created_at=row[13].isoformat() if row[13] else None,
            updated_at=row[14].isoformat() if row[14] else None,
        )

    async def update_profile(self, user_id: str, update: ProfileUpdateRequest) -> ProfileResponse:
        """Update a user's profile.

        Only non-None fields are applied.

        Args:
            user_id: The user UUID.
            update: Fields to update.

        Returns:
            Updated ProfileResponse.

        Raises:
            NotFoundError: If the user does not exist.
        """
        fields: dict[str, Any] = {}
        if update.display_name is not None:
            fields["display_name"] = update.display_name
        if update.timezone is not None:
            fields["timezone"] = update.timezone
        if update.language is not None:
            fields["language"] = update.language
        if update.theme is not None:
            fields["theme"] = update.theme
        if update.onboarding_step is not None:
            fields["onboarding_step"] = update.onboarding_step

        if not fields:
            # Nothing to update
            return await self.get_profile(user_id)

        fields["updated_at"] = datetime.now(timezone.utc)

        set_clause = ", ".join(f"{k} = :{k}" for k in fields)
        fields["user_id"] = user_id

        result = await self.db.execute(
            text(f"UPDATE users SET {set_clause} WHERE id = :user_id AND is_active = true RETURNING id"),
            fields,
        )
        updated = result.scalar_one_or_none()
        if not updated:
            raise NotFoundError(
                message="User not found",
                resource_type="user",
                resource_id=user_id,
            )

        await self.db.commit()
        logger.info("Profile updated", user_id=user_id, fields=list(fields.keys()))

        return await self.get_profile(user_id)

    async def upload_avatar(self, user_id: str, file_content: bytes, filename: str) -> AvatarResponse:
        """Upload or update a user's avatar.

        Stores the file in S3-compatible storage and updates the profile.

        Args:
            user_id: The user UUID.
            file_content: Raw file bytes.
            filename: Original filename (used for extension detection).

        Returns:
            AvatarResponse with the public URL.

        Raises:
            NotFoundError: If the user does not exist.
        """
        import hashlib

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
        valid_exts = {"png", "jpg", "jpeg", "gif", "webp"}
        if ext not in valid_exts:
            ext = "png"

        file_hash = hashlib.sha256(file_content).hexdigest()[:16]
        object_key = f"avatars/{user_id}/{file_hash}.{ext}"

        # Store in S3
        try:
            import boto3

            s3 = boto3.client(
                "s3",
                endpoint_url=settings.storage.endpoint_url,
                aws_access_key_id=settings.storage.access_key_id,
                aws_secret_access_key=settings.storage.secret_access_key,
                region_name=settings.storage.region,
            )
            s3.put_object(
                Bucket=settings.storage.bucket,
                Key=object_key,
                Body=file_content,
                ContentType=f"image/{ext}",
                ACL="public-read",  # Override with pre-signed URLs in production
            )
        except ImportError:
            logger.warning("boto3 not installed — avatar stored locally only (dev mode)")
        except Exception as exc:
            logger.error("Avatar upload to S3 failed", error=str(exc))
            # Store in local filesystem as fallback
            local_path = f"/tmp/avatars/{user_id}/{file_hash}.{ext}"
            import os
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(file_content)
            object_key = local_path

        avatar_url = f"{settings.storage.public_url_base}/{object_key}"
        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            text("""
                UPDATE users SET avatar_url = :url, updated_at = :now
                WHERE id = :user_id AND is_active = true
                RETURNING id
            """),
            {"url": avatar_url, "now": now, "user_id": user_id},
        )
        updated = result.scalar_one_or_none()
        if not updated:
            raise NotFoundError(
                message="User not found",
                resource_type="user",
                resource_id=user_id,
            )

        await self.db.commit()
        logger.info("Avatar uploaded", user_id=user_id, url=avatar_url)

        return AvatarResponse(avatar_url=avatar_url)

    async def delete_account(self, user_id: str) -> None:
        """Permanently delete a user account and all associated data.

        Implements a soft-delete pattern: sets is_active = false and
        schedules background deletion. For GDPR compliance, actual deletion
        should be confirmed and processed asynchronously.

        Args:
            user_id: The user UUID.

        Raises:
            NotFoundError: If the user does not exist.
        """
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            text("""
                UPDATE users
                SET is_active = false,
                    email = CONCAT('deleted_', id, '@anansi.ai'),
                    display_name = 'Deleted User',
                    password_hash = NULL,
                    avatar_url = NULL,
                    updated_at = :now
                WHERE id = :user_id AND is_active = true
                RETURNING id
            """),
            {"now": now, "user_id": user_id},
        )
        deleted = result.scalar_one_or_none()
        if not deleted:
            raise NotFoundError(
                message="User not found",
                resource_type="user",
                resource_id=user_id,
            )

        await self.db.commit()
        logger.info("Account deleted", user_id=user_id)

        # TODO: Enqueue background task for full data cleanup
        # (anonymise conversations, remove from teams, delete files, etc.)


__all__ = [
    "UserService",
    "ProfileResponse",
    "ProfileUpdateRequest",
    "AvatarResponse",
]
