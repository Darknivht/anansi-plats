"""Agent, AgentVersion, and AgentRun models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Agent(UUIDMixin, TimestampMixin, Base):
    """An agent definition — the core automation unit in Anansi.

    Each agent is a visual workflow with blocks, triggers, and edges.
    Agents can be published individually or to the marketplace.
    """

    __tablename__ = "agents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Full agent JSON (blocks, edges, triggers, configuration)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False, index=True
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    marketplace_price_cents: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    # Performance stats (denormalized for quick queries)
    total_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Memory impact tracking
    memory_nodes_created: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    memory_links_created: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="agents")
    versions: Mapped[list["AgentVersion"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AgentVersion.version.desc()",
    )
    runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AgentRun.started_at.desc()",
    )
    marketplace_listing: Mapped[Optional["MarketplaceListing"]] = relationship(
        back_populates="agent", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'archived')",
            name="ck_agents_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name!r} status={self.status}>"


class AgentVersion(UUIDMixin, Base):
    """Immutable snapshot of an agent's definition at a point in time."""

    __tablename__ = "agent_versions"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    change_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default="NOW()", nullable=False
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"<AgentVersion agent_id={self.agent_id} v{self.version}>"


class AgentRun(UUIDMixin, Base):
    """Record of a single agent execution."""

    __tablename__ = "agent_runs"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    trigger_detail: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False
    )
    input_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    steps: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Memory impact
    memory_nodes_created: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    memory_links_created: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        server_default="NOW()", nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default="NOW()", nullable=False
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="runs")

    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('manual', 'schedule', 'webhook', 'event')",
            name="ck_agent_runs_trigger_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled')",
            name="ck_agent_runs_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AgentRun agent_id={self.agent_id} "
            f"status={self.status} started={self.started_at}>"
        )


# Forward references
from .user import User
from .marketplace import MarketplaceListing
