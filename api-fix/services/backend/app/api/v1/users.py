"""
Anansi User Endpoints — Profile retrieval, update, avatar upload, and account deletion.

All endpoints require authentication and use async I/O throughout.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.dependencies import CurrentUser, get_current_user, rate_limit
from app.core.events import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.services.user import (
    AvatarResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    UserService,
)

logger = get_logger(__name__)

router = APIRouter()


# ─── Helper ──────────────────────────────────────────────────────────────────────


async def _get_user_service(db: AsyncSession = Depends(get_db_session)) -> UserService:
    """Dependency that builds a UserService."""
    return UserService(db=db)


# ─── Get Profile ─────────────────────────────────────────────────────────────────


@router.get(
    "/profile",
    response_model=ProfileResponse,
    status_code=200,
    summary="Get user profile",
    description="Retrieve the authenticated user's full profile including preferences and brain stats.",
)
async def get_profile(
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
) -> ProfileResponse:
    """Get the current user's profile.

    Returns:
        ProfileResponse with all profile fields.

    Raises:
        401 Unauthorized: If the token is missing or invalid.
        404 Not Found: If the user does not exist.
    """
    logger.info("Profile fetched", user_id=current_user.id)
    return await service.get_profile(current_user.id)


# ─── Update Profile ──────────────────────────────────────────────────────────────


@router.patch(
    "/profile",
    response_model=ProfileResponse,
    status_code=200,
    summary="Update user profile",
    description="Update profile fields. Only provided fields are changed.",
)
async def update_profile(
    update: ProfileUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
    _: None = Depends(rate_limit(key="profile", max_requests=30, window=60)),
) -> ProfileResponse:
    """Update the current user's profile.

    Args:
        update: Fields to update (all optional).

    Returns:
        Updated ProfileResponse.

    Raises:
        404 Not Found: If the user does not exist.
        422 Unprocessable: If validation fails (invalid theme, language, etc.).
    """
    logger.info("Profile update", user_id=current_user.id, update=update.model_dump(exclude_none=True))
    return await service.update_profile(current_user.id, update)


# ─── Upload Avatar ───────────────────────────────────────────────────────────────


@router.post(
    "/avatar",
    response_model=AvatarResponse,
    status_code=200,
    summary="Upload profile avatar",
    description="Upload a new avatar image. Accepted formats: PNG, JPG, JPEG, GIF, WebP. Max 50MB.",
)
async def upload_avatar(
    file: UploadFile = File(..., description="Avatar image file"),
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
    _: None = Depends(rate_limit(key="avatar", max_requests=10, window=60)),
) -> AvatarResponse:
    """Upload a new avatar image.

    Args:
        file: The image file to upload.

    Returns:
        AvatarResponse with the public URL of the uploaded avatar.

    Raises:
        422 Unprocessable: If file is too large or invalid type.
    """
    from app.core.config import settings as s

    # Validate file size
    content = await file.read()
    max_bytes = s.storage.max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationError(
            message=f"File too large. Maximum size is {s.storage.max_file_size_mb}MB",
            fields=[{"field": "file", "error": f"max_size_{s.storage.max_file_size_mb}MB"}],
        )

    # Validate content type
    allowed_types = {"image/png", "image/jpeg", "image/gif", "image/webp"}
    if file.content_type and file.content_type not in allowed_types:
        raise ValidationError(
            message=f"Unsupported file type: {file.content_type}",
            fields=[{"field": "file", "error": "unsupported_type", "allowed": list(allowed_types)}],
        )

    result = await service.upload_avatar(current_user.id, content, file.filename or "avatar.png")
    logger.info("Avatar uploaded", user_id=current_user.id, url=result.avatar_url)
    return result


# ─── Delete Account ──────────────────────────────────────────────────────────────


@router.delete(
    "/account",
    status_code=200,
    summary="Delete user account",
    description="Permanently delete the authenticated user's account and all associated data.",
)
async def delete_account(
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
    _: None = Depends(rate_limit(key="account_delete", max_requests=3, window=3600)),
) -> None:
    """Delete the current user's account.

    This is a permanent action that schedules full data cleanup.

    Returns:
        204 No Content on successful deletion.
    """
    logger.info("Account deletion requested", user_id=current_user.id)
    await service.delete_account(current_user.id)


__all__ = ["router"]
