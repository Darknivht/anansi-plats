"""
Anansi Notification Endpoints — List, create, mark as read, and manage notifications.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.dependencies import CurrentUser, get_current_user, rate_limit
from app.core.events import get_db_session, get_redis
from app.core.exceptions import NotFoundError
from app.services.notification import (
    MarkReadResponse,
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationService,
)
from redis.asyncio import Redis

logger = get_logger(__name__)

router = APIRouter()


# ─── Helper ──────────────────────────────────────────────────────────────────────


async def _get_notification_service(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> NotificationService:
    """Dependency that builds a NotificationService."""
    return NotificationService(db=db, redis=redis)


# ─── List Notifications ──────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=200,
    summary="List notifications",
    description="Retrieve paginated notifications for the authenticated user, sorted newest-first.",
)
async def list_notifications(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(default=False, description="Filter to only unread notifications"),
    current_user: CurrentUser = Depends(get_current_user),
    service: NotificationService = Depends(_get_notification_service),
    _: None = Depends(rate_limit(key="notifications", max_requests=60, window=60)),
) -> NotificationListResponse:
    """List notifications for the current user.

    Args:
        page: Page number (default 1).
        page_size: Items per page (default 20, max 100).
        unread_only: If true, only return unread notifications.

    Returns:
        Paginated NotificationListResponse.

    Raises:
        401 Unauthorized: If the token is missing or invalid.
    """
    logger.info(
        "Notifications listed",
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )
    return await service.list_notifications(
        current_user.id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )


# ─── Mark Notifications as Read ──────────────────────────────────────────────────


@router.patch(
    "/read",
    response_model=MarkReadResponse,
    status_code=200,
    summary="Mark notifications as read",
    description="Mark specific notification IDs as read.",
)
async def mark_read(
    notification_ids: list[str],
    current_user: CurrentUser = Depends(get_current_user),
    service: NotificationService = Depends(_get_notification_service),
) -> MarkReadResponse:
    """Mark specific notifications as read.

    Args:
        notification_ids: List of notification UUIDs to mark as read.

    Returns:
        MarkReadResponse with count of notifications marked as read.
    """
    logger.info(
        "Marking notifications read",
        user_id=current_user.id,
        count=len(notification_ids),
    )
    return await service.mark_read(current_user.id, notification_ids)


# ─── Mark All Notifications as Read ──────────────────────────────────────────────


@router.patch(
    "/read-all",
    response_model=MarkReadResponse,
    status_code=200,
    summary="Mark all notifications as read",
    description="Mark every unread notification for the current user as read.",
)
async def mark_all_read(
    current_user: CurrentUser = Depends(get_current_user),
    service: NotificationService = Depends(_get_notification_service),
) -> MarkReadResponse:
    """Mark all of the current user's notifications as read.

    Returns:
        MarkReadResponse with count of notifications marked as read.
    """
    logger.info("Marking all notifications read", user_id=current_user.id)
    return await service.mark_all_read(current_user.id)


# ─── Unread Count ────────────────────────────────────────────────────────────────


@router.get(
    "/unread-count",
    response_model=dict[str, int],
    status_code=200,
    summary="Get unread notification count",
    description="Returns the count of unread notifications for the current user.",
)
async def unread_count(
    current_user: CurrentUser = Depends(get_current_user),
    service: NotificationService = Depends(_get_notification_service),
) -> dict[str, int]:
    """Get the number of unread notifications.

    Returns:
        dict with 'count' key.
    """
    count = await service.get_unread_count(current_user.id)
    return {"count": count}


# ─── Create Notification (admin/system use) ──────────────────────────────────────


@router.post(
    "",
    response_model=NotificationResponse,
    status_code=201,
    summary="Create a notification (internal)",
    description="Create a new notification. Intended for system/internal use, not user-facing.",
    include_in_schema=False,
)
async def create_notification(
    notification: NotificationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: NotificationService = Depends(_get_notification_service),
) -> NotificationResponse:
    """Create a notification. Internal endpoint, not exposed in public docs.

    Args:
        notification: The notification to create.

    Returns:
        The created NotificationResponse.
    """
    logger.info(
        "Notification created via API",
        user_id=notification.user_id,
        type=notification.type,
    )
    return await service.create(notification)


__all__ = ["router"]
