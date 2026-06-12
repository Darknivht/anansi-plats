"""Team and TeamMember models for collaboration."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Team(UUIDMixin, TimestampMixin, Base):
    """A team/workspace for multi-user collaboration."""

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="teams_owned")
    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Team id={self.id} name={self.name!r} members={self.member_count}>"


class TeamMember(UUIDMixin, Base):
    """A user's membership in a team with their role."""

    __tablename__ = "team_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), default="member", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default="NOW()",
        nullable=False,
    )

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="team_memberships")

    __table_args__ = (
        UniqueConstraint(
            "team_id", "user_id",
            name="uq_team_members_team_user",
        ),
        CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer')",
            name="ck_team_members_role",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TeamMember team_id={self.team_id} "
            f"user_id={self.user_id} role={self.role}>"
        )


# Forward reference
from .user import User
