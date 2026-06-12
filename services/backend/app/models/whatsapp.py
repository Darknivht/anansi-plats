"""WhatsApp connection model."""

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

from .base import Base, TimestampMixin, UUIDMixin


class WhatsAppConnection(UUIDMixin, TimestampMixin, Base):
    """A user's linked WhatsApp Business account.

    Each user can link exactly one WhatsApp number. This enables
    AI chat, notifications, and quick commands via WhatsApp.
    """

    __tablename__ = "whatsapp_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One WhatsApp connection per user
        index=True,
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    waba_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # WhatsApp Business Account ID
    phone_number_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    business_account_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    verification_code: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'disconnected', 'expired')",
            name="ck_whatsapp_connections_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<WhatsAppConnection user_id={self.user_id} "
            f"phone={self.phone_number} status={self.status}>"
        )


# Forward reference
from .user import User
