"""Notification model for in-app and push notifications."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin


class Notification(UUIDMixin, Base):
    """A notification delivered to a user through one or more channels.

    Supports various notification types from agent completions to
    brain insights and billing alerts.
    """

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Link to specific memory node (when type is brain_*)
    related_memory_node: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memory_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    related_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    channel: Mapped[str] = mapped_column(
        String(20), default="in_app", nullable=False
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default="NOW()", nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship()
    memory_node: Mapped[Optional["MemoryNode"]] = relationship()

    __table_args__ = (
        CheckConstraint(
            "channel IN ('in_app', 'whatsapp', 'email', 'push')",
            name="ck_notifications_channel",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Notification type={self.type} "
            f"title={self.title!r} is_read={self.is_read}>"
        )


# Forward references
from .user import User
from .brain import MemoryNode
