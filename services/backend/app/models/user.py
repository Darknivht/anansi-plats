"""User, OAuthAccount, and Session models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    """Core user account model. Holds profile, preferences, and brain stats."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Africa/Lagos")
    language: Mapped[str] = mapped_column(String(10), default="en")
    theme: Mapped[str] = mapped_column(String(10), default="dark")
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    two_factor_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Second Brain stats (denormalized for performance)
    brain_age_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    memory_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    link_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=True
    )

    # Relationships
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    memory_nodes: Mapped[list["MemoryNode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    agents: Mapped[list["Agent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    teams_owned: Mapped[list["Team"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )
    team_memberships: Mapped[list["TeamMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class OAuthAccount(UUIDMixin, TimestampMixin, Base):
    """OAuth provider accounts linked to a user."""

    __tablename__ = "oauth_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="oauth_accounts")

    __table_args__ = (
        # Ensure unique provider accounts
        UniqueConstraint(
            "provider", "provider_account_id",
            name="uq_oauth_accounts_provider_account",
        ),
    )

    def __repr__(self) -> str:
        return f"<OAuthAccount provider={self.provider} account_id={self.provider_account_id}>"


class Session(UUIDMixin, TimestampMixin, Base):
    """User session with refresh token for JWT auth flow."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token: Mapped[str] = mapped_column(String(500), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session user_id={self.user_id} expires={self.expires_at}>"


# Forward references for type hints
from .billing import Subscription
from .brain import MemoryNode
from .agent import Agent
from .team import Team, TeamMember
