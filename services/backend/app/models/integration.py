"""Integration and Connector models for service connections."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Connector(UUIDMixin, TimestampMixin, Base):
    """A connector type definition — the blueprint for an integration.

    Each connector describes a service (Gmail, Slack, etc.) and its
    authentication requirements. Builtin connectors ship with the platform;
    custom ones can be built via the Connector SDK.
    """

    __tablename__ = "connectors"

    key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auth_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    auth_url_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scopes_available: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "auth_type IN ('oauth2', 'apikey', 'basic')",
            name="ck_connectors_auth_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<Connector key={self.key} name={self.name!r}>"


class Integration(UUIDMixin, TimestampMixin, Base):
    """A user's connection instance of a connector type.

    Stores the actual auth tokens, scopes, and connection state
    for a user's integration with a specific service.
    """

    __tablename__ = "integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connector_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )
    auth_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Encrypted OAuth tokens
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=True
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rate_limit_remaining: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate_limit_reset_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'error', 'disconnected', 'pending')",
            name="ck_integrations_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Integration user_id={self.user_id} "
            f"connector={self.connector_type} status={self.status}>"
        )
