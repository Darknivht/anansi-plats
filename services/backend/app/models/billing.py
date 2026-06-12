"""Plan and Subscription billing models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Plan(UUIDMixin, TimestampMixin, Base):
    """Subscription plan definition with feature limits."""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_monthly_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    price_yearly_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Feature limits
    max_agents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_integrations: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_team_members: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_memory_nodes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_graph_depth: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_reviews_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    daily_notes_history_days: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    progressive_summarization_layers: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    auto_linking_level: Mapped[str] = mapped_column(
        String(20), default="basic", nullable=False
    )
    export_formats: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )
    memory_analytics: Mapped[str] = mapped_column(
        String(20), default="weekly", nullable=False
    )

    # Rich feature flags stored as JSON
    features: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=dict, nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("price_monthly_cents >= 0", name="ck_plans_price_monthly"),
        CheckConstraint("price_yearly_cents >= 0", name="ck_plans_price_yearly"),
    )

    def __repr__(self) -> str:
        return f"<Plan slug={self.slug} price=${self.price_monthly_cents/100:.2f}>"


class Subscription(UUIDMixin, TimestampMixin, Base):
    """User subscription linking a user to a plan with billing period."""

    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One subscription per user
        index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True,
    )
    billing_cycle: Mapped[str] = mapped_column(
        String(10), default="monthly", nullable=False
    )
    current_period_start: Mapped[datetime] = mapped_column(nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(nullable=False)
    trial_start: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    trial_end: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Payment provider IDs
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    paystack_subscription_code: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    canceled_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscription")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'past_due', 'cancelled', 'expired', 'trialing')",
            name="ck_subscriptions_status",
        ),
        CheckConstraint(
            "billing_cycle IN ('monthly', 'yearly')",
            name="ck_subscriptions_billing_cycle",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Subscription user_id={self.user_id} "
            f"plan_id={self.plan_id} status={self.status}>"
        )


# Forward references
from .user import User
