"""Marketplace models for the agent ecosystem."""

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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class MarketplaceListing(UUIDMixin, TimestampMixin, Base):
    """A published agent listing on the Anansi marketplace."""

    __tablename__ = "marketplace_listings"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0 = free
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )
    screenshots: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )

    # Rating & stats
    rating_avg: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    install_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False, index=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Memory impact estimate
    memory_nodes_per_run: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    memory_links_per_run: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="marketplace_listing")
    reviews: Mapped[list["MarketplaceReview"]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    installs: Mapped[list["MarketplaceInstall"]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "price_cents >= 0", name="ck_marketplace_listings_price"
        ),
        CheckConstraint(
            "rating_avg >= 0 AND rating_avg <= 5",
            name="ck_marketplace_listings_rating",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'unpublished', 'rejected')",
            name="ck_marketplace_listings_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketplaceListing title={self.title!r} "
            f"price=${self.price_cents/100:.2f} status={self.status}>"
        )


class MarketplaceReview(UUIDMixin, Base):
    """A user's review and rating for a marketplace listing."""

    __tablename__ = "marketplace_reviews"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default="NOW()", nullable=False
    )

    # Relationships
    listing: Mapped["MarketplaceListing"] = relationship(back_populates="reviews")

    __table_args__ = (
        UniqueConstraint(
            "listing_id", "user_id",
            name="uq_marketplace_reviews_listing_user",
        ),
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_marketplace_reviews_rating",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketplaceReview listing_id={self.listing_id} "
            f"rating={self.rating}>"
        )


class MarketplaceInstall(UUIDMixin, Base):
    """Record of a user installing a marketplace agent."""

    __tablename__ = "marketplace_installs"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default="NOW()", nullable=False
    )

    # Relationships
    listing: Mapped["MarketplaceListing"] = relationship(back_populates="installs")


# Forward reference
from .agent import Agent
