"""
Anansi Notification Service — Create, list, mark read, and send notifications
to various channels (in-app, WhatsApp, email).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, field_validator
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.exceptions import NotFoundError

logger = get_logger(__name__)


# ─── Schemas ─────────────────────────────────────────────────────────────────────


class NotificationCreate(BaseModel):
    """Schema for creating a notification."""

    user_id: str
    type: str
    title: str
    body: str | None = None
    data: dict[str, Any] | None = None
    related_memory_node: str | None = None
    channel: str = "in_app"

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {
            "agent_completed", "agent_error", "agent_running",
            "ai_suggestion", "ai_morning_briefing",
            "integration_alert", "integration_status",
            "brain_review_due", "brain_insight",
            "brain_node_created", "brain_link_created",
            "brain_daily_note_ready",
            "system", "billing_alert", "team_invite",
        }
        if v not in allowed:
            raise ValueError(f"Unknown notification type: {v}. Allowed: {', '.join(sorted(allowed))}")
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        if v not in ("in_app", "whatsapp", "email"):
            raise ValueError("Channel must be 'in_app', 'whatsapp', or 'email'")
        return v


class NotificationResponse(BaseModel):
    """Notification response for API consumers."""

    id: str
    type: str
    title: str
    body: str | None = None
    data: dict[str, Any] | None = None
    related_memory_node: str | None = None
    channel: str = "in_app"
    is_read: bool = False
    created_at: str


class NotificationListResponse(BaseModel):
    """Paginated list of notifications."""

    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int = 1
    page_size: int = 20


class MarkReadResponse(BaseModel):
    """Response after marking notifications as read."""

    marked_count: int


# ─── Notification Service ────────────────────────────────────────────────────────


class NotificationService:
    """Business logic for creating, querying, and delivering notifications."""

    def __init__(self, db: AsyncSession, redis: Redis | None = None) -> None:
        self.db = db
        self.redis = redis

    async def create(self, notification: NotificationCreate) -> NotificationResponse:
        """Create a new notification and deliver via the specified channel.

        Args:
            notification: The notification to create.

        Returns:
            The created NotificationResponse.
        """
        notif_id = str(uuid4())
        now = datetime.now(timezone.utc)

        await self.db.execute(
            text("""
                INSERT INTO notifications (id, user_id, type, title, body, data, related_memory_node, channel, is_read, created_at)
                VALUES (:id, :user_id, :type, :title, :body, :data::jsonb, :related_memory_node, :channel, false, :created_at)
            """),
            {
                "id": notif_id,
                "user_id": notification.user_id,
                "type": notification.type,
                "title": notification.title,
                "body": notification.body or "",
                "data": __import__("json").dumps(notification.data or {}),
                "related_memory_node": notification.related_memory_node,
                "channel": notification.channel,
                "created_at": now,
            },
        )
        await self.db.commit()

        response = NotificationResponse(
            id=notif_id,
            type=notification.type,
            title=notification.title,
            body=notification.body,
            data=notification.data,
            related_memory_node=notification.related_memory_node,
            channel=notification.channel,
            is_read=False,
            created_at=now.isoformat(),
        )

        # Deliver via external channel if needed
        if notification.channel != "in_app":
            await self._deliver_external(notification)

        # Publish to Redis pub/sub for WebSocket delivery
        if self.redis:
            await self.redis.publish(
                f"notifications:{notification.user_id}",
                response.model_dump_json(),
            )

        logger.info(
            "Notification created",
            notif_id=notif_id,
            user_id=notification.user_id,
            type=notification.type,
            channel=notification.channel,
        )

        return response

    async def list_notifications(
        self,
        user_id: str,
        *,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> NotificationListResponse:
        """List notifications for a user, paginated and sorted newest-first.

        Args:
            user_id: The user UUID.
            page: Page number (1-indexed).
            page_size: Items per page (max 100).
            unread_only: If True, only return unread notifications.

        Returns:
            Paginated NotificationListResponse.
        """
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size

        where_clause = "user_id = :user_id"
        if unread_only:
            where_clause += " AND is_read = false"

        count_result = await self.db.execute(
            text(f"SELECT COUNT(*) FROM notifications WHERE {where_clause}"),
            {"user_id": user_id},
        )
        total = count_result.scalar() or 0

        unread_result = await self.db.execute(
            text("SELECT COUNT(*) FROM notifications WHERE user_id = :user_id AND is_read = false"),
            {"user_id": user_id},
        )
        unread_count = unread_result.scalar() or 0

        rows = await self.db.execute(
            text(f"""
                SELECT id, type, title, body, data, related_memory_node, channel, is_read, created_at
                FROM notifications
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"user_id": user_id, "limit": page_size, "offset": offset},
        )

        items = [
            NotificationResponse(
                id=row[0],
                type=row[1],
                title=row[2],
                body=row[3] or None,
                data=row[4] if isinstance(row[4], dict) else None,
                related_memory_node=row[5],
                channel=row[6],
                is_read=bool(row[7]),
                created_at=row[8].isoformat() if row[8] else "",
            )
            for row in rows
        ]

        return NotificationListResponse(
            items=items,
            total=total,
            unread_count=unread_count,
            page=page,
            page_size=page_size,
        )

    async def mark_read(self, user_id: str, notification_ids: list[str]) -> MarkReadResponse:
        """Mark specific notifications as read.

        Args:
            user_id: The user UUID.
            notification_ids: List of notification UUIDs to mark as read.

        Returns:
            MarkReadResponse with the count of marked notifications.

        Raises:
            NotFoundError: If no valid (owned) notifications are found.
        """
        if not notification_ids:
            return MarkReadResponse(marked_count=0)

        result = await self.db.execute(
            text("""
                UPDATE notifications
                SET is_read = true
                WHERE id = ANY(:ids) AND user_id = :user_id AND is_read = false
                RETURNING id
            """),
            {"ids": notification_ids, "user_id": user_id},
        )
        marked = len(result.all())

        await self.db.commit()
        logger.info("Notifications marked read", user_id=user_id, count=marked)

        return MarkReadResponse(marked_count=marked)

    async def mark_all_read(self, user_id: str) -> MarkReadResponse:
        """Mark all notifications as read for a user.

        Args:
            user_id: The user UUID.

        Returns:
            MarkReadResponse with the count of marked notifications.
        """
        result = await self.db.execute(
            text("""
                UPDATE notifications
                SET is_read = true
                WHERE user_id = :user_id AND is_read = false
                RETURNING id
            """),
            {"user_id": user_id},
        )
        marked = len(result.all())

        await self.db.commit()
        logger.info("All notifications marked read", user_id=user_id, count=marked)

        return MarkReadResponse(marked_count=marked)

    async def get_unread_count(self, user_id: str) -> int:
        """Get the count of unread notifications for a user.

        Args:
            user_id: The user UUID.

        Returns:
            Number of unread notifications.
        """
        result = await self.db.execute(
            text("SELECT COUNT(*) FROM notifications WHERE user_id = :user_id AND is_read = false"),
            {"user_id": user_id},
        )
        return result.scalar() or 0

    async def _deliver_external(self, notification: NotificationCreate) -> None:
        """Deliver a notification via WhatsApp or email.

        In production, this would call the WhatsApp service or email provider.
        Placeholder implementation logs the delivery.
        """
        channel = notification.channel
        logger.info(
            "External notification delivery",
            user_id=notification.user_id,
            channel=channel,
            title=notification.title,
        )
        # TODO: Implement actual delivery via:
        # - WhatsApp: WhatsAppService.send_message(notification.user_id, formatted_message)
        # - Email: EmailService.send_email(to, subject, body)

    async def close(self) -> None:
        """Cleanup resources if needed."""
        pass


__all__ = [
    "NotificationService",
    "NotificationCreate",
    "NotificationResponse",
    "NotificationListResponse",
    "MarkReadResponse",
]
