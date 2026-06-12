"""Second Brain memory models.

Core entities for the knowledge web:
- MemoryNode: Atomic notes with vector embeddings for semantic search
- MemoryLink: Bidirectional links between memory nodes
- DailyNote: Temporal anchor notes
- MemoryReview: Spaced repetition review log
"""

from __future__ import annotations

import uuid
from datetime import datetime, date as date_type
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from .base import Base, TimestampMixin, UUIDMixin


class MemoryNode(UUIDMixin, TimestampMixin, Base):
    """An atomic memory fact (Atomic Note) in the user's Second Brain.

    Each node is a self-contained piece of knowledge that can be linked
    to other nodes bidirectionally. Supports progressive summarization
    layers, vector embeddings for semantic search, and spaced repetition
    scheduling.
    """

    __tablename__ = "memory_nodes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="fact",
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Progressive summarization layers
    # Structure: {l1_summary, l2_highlights[], l3_full, l4_compressed}
    layers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Vector embedding for semantic similarity search (OpenAI ada-002)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536), nullable=True
    )

    # Hierarchical tags: ['#work/client', '#finance/tax']
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )

    # Flexible metadata for AI-inferred attributes
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    # Spaced repetition fields
    review_interval: Mapped[int] = mapped_column(
        Integer, default=86400, nullable=False
    )  # Interval in seconds
    next_review_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Provenance
    source: Mapped[str] = mapped_column(
        String(20), default="explicit", nullable=False
    )
    confidence: Mapped[float] = mapped_column(
        Float, default=0.7, nullable=False
    )
    review_status: Mapped[str] = mapped_column(
        String(20), default="current", nullable=False
    )

    # Graph state (denormalized for performance)
    is_orphan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    links_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # PARA organization
    para_category: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="memory_nodes")
    outgoing_links: Mapped[list["MemoryLink"]] = relationship(
        foreign_keys="MemoryLink.source_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    incoming_links: Mapped[list["MemoryLink"]] = relationship(
        foreign_keys="MemoryLink.target_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reviews: Mapped[list["MemoryReview"]] = relationship(
        back_populates="node", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def all_links(self) -> list["MemoryLink"]:
        """Get all links (both directions) for this node."""
        return self.outgoing_links + self.incoming_links

    def __repr__(self) -> str:
        return f"<MemoryNode id={self.id} title={self.title[:50]!r}>"


class MemoryLink(UUIDMixin, TimestampMixin, Base):
    """A bidirectional link between two memory nodes.

    Links are always bidirectional. When querying links for a node, both
    source_id and target_id should be searched to get the full picture.
    """

    __tablename__ = "memory_links"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memory_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memory_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    link_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Why this link exists
    strength: Mapped[float] = mapped_column(
        Float, default=0.5, nullable=False
    )  # 0.0-1.0, increases with use
    confidence: Mapped[float] = mapped_column(
        Float, default=0.7, nullable=False
    )  # 0.0-1.0
    is_auto_generated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship()
    source_node: Mapped["MemoryNode"] = relationship(
        foreign_keys=[source_id], back_populates="outgoing_links", lazy="selectin"
    )
    target_node: Mapped["MemoryNode"] = relationship(
        foreign_keys=[target_id], back_populates="incoming_links", lazy="selectin"
    )

    __table_args__ = (
        # Prevent duplicate links
        UniqueConstraint(
            "source_id", "target_id", "link_type",
            name="uq_memory_links_source_target_type",
        ),
    )

    def get_linked_node_id(self, from_node_id: uuid.UUID) -> uuid.UUID:
        """Get the ID of the node on the other end of this link."""
        if self.source_id == from_node_id:
            return self.target_id
        return self.source_id

    def __repr__(self) -> str:
        return (
            f"<MemoryLink {self.link_type} "
            f"{self.source_id} -> {self.target_id}>"
        )


class DailyNote(UUIDMixin, TimestampMixin, Base):
    """Temporal anchor note that links all memory activity for a day."""

    __tablename__ = "daily_notes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    note_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    highlights: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )
    decisions: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )  # [{description, related_node_id, approved}]
    connections_made: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )  # [{from_node, to_node, link_type}]
    metrics: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )  # {emails_processed, tasks_completed, ...}
    ai_reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "user_id", "note_date",
            name="uq_daily_notes_user_date",
        ),
    )

    def __repr__(self) -> str:
        return f"<DailyNote user_id={self.user_id} date={self.note_date}>"


class MemoryReview(UUIDMixin, Base):
    """Log entry for a spaced repetition review of a memory node.

    Tracks rating, response time, and interval adjustments for
    the spaced repetition algorithm.
    """

    __tablename__ = "memory_reviews"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memory_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating: Mapped[str] = mapped_column(String(10), nullable=False)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    interval_before: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Seconds
    interval_after: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Seconds
    created_at: Mapped[datetime] = mapped_column(
        server_default="NOW()", nullable=False
    )

    # Relationships
    node: Mapped["MemoryNode"] = relationship(back_populates="reviews")

    __table_args__ = (
        CheckConstraint(
            "rating IN ('easy', 'medium', 'hard', 'forgot')",
            name="ck_memory_reviews_rating",
        ),
    )

    def __repr__(self) -> str:
        return f"<MemoryReview rating={self.rating} node_id={self.node_id}>"


# Forward references
from .user import User
