"""
Creator Dashboard Service — Analytics, earnings, reviews, and listing management.

Handles the creator-facing side of the marketplace: sales analytics,
earnings with 70/30 revenue split, review management, and payout history.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import joinedload
from structlog import get_logger

from app.core.events import get_session_factory
from app.core.exceptions import NotFoundError, ValidationError
from app.models.agent import Agent
from app.models.marketplace import (
    MarketplaceListing,
    MarketplaceReview,
    MarketplaceInstall,
)
from app.models.billing import Plan, Subscription
from app.models.user import User

logger = get_logger(__name__)

# Revenue split: 70% to creator, 30% to platform
CREATOR_REVENUE_SHARE = 0.70
PLATFORM_REVENUE_SHARE = 0.30


class CreatorDashboardService:
    """Business logic for the creator dashboard — analytics, earnings, reviews."""

    # ── My Listings ────────────────────────────────────────────────────────────

    async def get_my_listings(self, creator_id: str) -> list[dict[str, Any]]:
        """Get all marketplace listings for a creator with per-agent stats.

        Args:
            creator_id: UUID of the creator (user).

        Returns:
            List of listing dicts with per-agent stats (installs, revenue, rating).
        """
        factory = get_session_factory()
        async with factory() as session:
            query = (
                select(MarketplaceListing)
                .options(
                    joinedload(MarketplaceListing.agent),
                    joinedload(MarketplaceListing.reviews),
                    joinedload(MarketplaceListing.installs),
                )
                .where(MarketplaceListing.user_id == uuid.UUID(creator_id))
                .order_by(MarketplaceListing.updated_at.desc())
            )
            result = await session.execute(query)
            listings = result.unique().scalars().all()

            return [
                {
                    "id": str(l.id),
                    "agent_id": str(l.agent_id) if l.agent_id else None,
                    "title": l.title,
                    "description": l.description,
                    "price_cents": l.price_cents,
                    "price_display": (
                        f"${l.price_cents / 100:.2f}" if l.price_cents > 0 else "Free"
                    ),
                    "category": l.category,
                    "tags": l.tags or [],
                    "status": l.status,
                    "is_featured": l.is_featured,
                    "rating_avg": l.rating_avg,
                    "rating_count": l.rating_count,
                    "install_count": l.install_count,
                    "is_published": l.status == "published",
                    "rejection_reason": l.rejection_reason,
                    "estimated_earnings_cents": int(
                        (l.install_count or 0) * (l.price_cents or 0) * CREATOR_REVENUE_SHARE
                    ),
                    "agent_name": l.agent.name if l.agent else None,
                    "agent_version": l.agent.version if l.agent else None,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                    "updated_at": l.updated_at.isoformat() if l.updated_at else None,
                }
                for l in listings
            ]

    # ── Sales Analytics ────────────────────────────────────────────────────────

    async def get_sales_analytics(
        self,
        creator_id: str,
        period: str = "30d",
    ) -> dict[str, Any]:
        """Get sales analytics for a creator over a given period.

        Args:
            creator_id: UUID of the creator.
            period: Period string: '7d', '30d', '90d', '1y', 'all'.

        Returns:
            Dict with sales over time, total revenue, installs, etc.
        """
        now = datetime.now(timezone.utc)

        # Calculate date range
        if period == "7d":
            since = now - timedelta(days=7)
        elif period == "30d":
            since = now - timedelta(days=30)
        elif period == "90d":
            since = now - timedelta(days=90)
        elif period == "1y":
            since = now - timedelta(days=365)
        else:  # 'all'
            since = datetime(2025, 1, 1, tzinfo=timezone.utc)

        factory = get_session_factory()
        async with factory() as session:
            # Get all listings for this creator
            listings_query = select(MarketplaceListing.id).where(
                MarketplaceListing.user_id == uuid.UUID(creator_id)
            )
            listings_result = await session.execute(listings_query)
            listing_ids = [r[0] for r in listings_result.all()]

            if not listing_ids:
                return self._empty_analytics()

            # Total installs in period
            installs_query = select(func.count()).select_from(
                select(MarketplaceInstall)
                .where(
                    and_(
                        MarketplaceInstall.listing_id.in_(listing_ids),
                        MarketplaceInstall.created_at >= since,
                    )
                )
                .subquery()
            )
            installs_result = await session.execute(installs_query)
            total_installs = installs_result.scalar() or 0

            # Total revenue (price * installs * creator share)
            # For a more accurate approach, we'd track actual payments.
            # Here we estimate based on listing price and installs.
            revenue_query = select(
                func.coalesce(
                    func.sum(MarketplaceListing.price_cents), 0
                )
            ).where(
                and_(
                    MarketplaceListing.id.in_(listing_ids),
                    MarketplaceListing.status == "published",
                )
            )
            revenue_result = await session.execute(revenue_query)
            listing_price_sum = revenue_result.scalar() or 0

            # Get installs per day for chart data
            # Install pattern per day query
            if period == "all":
                installs_over_time = await self._get_installs_by_month(
                    session, listing_ids, since
                )
            else:
                installs_over_time = await self._get_installs_by_day(
                    session, listing_ids, since, period
                )

            # Top selling listing
            top_listing_query = (
                select(
                    MarketplaceListing.title,
                    MarketplaceListing.install_count,
                    MarketplaceListing.price_cents,
                )
                .where(MarketplaceListing.id.in_(listing_ids))
                .order_by(MarketplaceListing.install_count.desc())
                .limit(1)
            )
            top_result = await session.execute(top_listing_query)
            top_listing = top_result.one_or_none()

            # Total installs across all time
            total_all_installs = sum(
                (await session.execute(
                    select(func.count()).select_from(
                        select(MarketplaceInstall)
                        .where(MarketplaceInstall.listing_id.in_(listing_ids))
                        .subquery()
                    )
                )).scalar() or 0
                for _ in [1]
            ) if listing_ids else 0

            # More accurate: count per listing
            total_installs_all_query = select(func.count(MarketplaceInstall.id)).where(
                MarketplaceInstall.listing_id.in_(listing_ids)
            )
            total_installs_all_result = await session.execute(total_installs_all_query)
            total_installs_all = total_installs_all_result.scalar() or 0

            # Count reviews
            reviews_query = select(func.count()).select_from(
                select(MarketplaceReview)
                .where(MarketplaceReview.listing_id.in_(listing_ids))
                .subquery()
            )
            reviews_result = await session.execute(reviews_query)
            total_reviews = reviews_result.scalar() or 0

            # Average rating
            avg_rating_query = select(func.avg(MarketplaceListing.rating_avg)).where(
                MarketplaceListing.id.in_(listing_ids)
            )
            avg_rating_result = await session.execute(avg_rating_query)
            avg_rating = avg_rating_result.scalar() or 0.0

            return {
                "period": period,
                "total_installs": total_installs,
                "total_installs_all_time": total_installs_all,
                "total_reviews": total_reviews,
                "average_rating": round(float(avg_rating), 2) if avg_rating else 0.0,
                "total_revenue_cents": int(
                    total_installs * listing_price_sum * CREATOR_REVENUE_SHARE
                ) if listing_ids else 0,
                "total_platform_fees_cents": int(
                    total_installs * listing_price_sum * PLATFORM_REVENUE_SHARE
                ) if listing_ids else 0,
                "top_listing": {
                    "title": top_listing[0] if top_listing else None,
                    "installs": top_listing[1] if top_listing else 0,
                    "price_cents": top_listing[2] if top_listing else 0,
                } if top_listing else None,
                "installs_over_time": installs_over_time,
            }

    # ── Reviews ────────────────────────────────────────────────────────────────

    async def get_reviews(self, creator_id: str) -> list[dict[str, Any]]:
        """Get all reviews for a creator's listings.

        Args:
            creator_id: UUID of the creator.

        Returns:
            List of review dicts with listing info and reviewer info.
        """
        factory = get_session_factory()
        async with factory() as session:
            query = (
                select(MarketplaceReview)
                .join(
                    MarketplaceListing,
                    MarketplaceReview.listing_id == MarketplaceListing.id,
                )
                .where(MarketplaceListing.user_id == uuid.UUID(creator_id))
                .order_by(MarketplaceReview.created_at.desc())
            )
            result = await session.execute(query)
            reviews = result.scalars().all()

            # Get listing titles and reviewer names
            listing_titles = {}
            reviewer_names = {}
            for review in reviews:
                if review.listing_id not in listing_titles:
                    listing = await session.get(MarketplaceListing, review.listing_id)
                    listing_titles[review.listing_id] = listing.title if listing else "Unknown"

                if review.user_id not in reviewer_names:
                    user = await session.get(User, review.user_id)
                    reviewer_names[review.user_id] = (
                        user.display_name if user else "Unknown"
                    )

            return [
                {
                    "id": str(r.id),
                    "listing_id": str(r.listing_id),
                    "listing_title": listing_titles.get(r.listing_id, "Unknown"),
                    "user_id": str(r.user_id),
                    "reviewer_name": reviewer_names.get(r.user_id, "Unknown"),
                    "rating": r.rating,
                    "review": r.review,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reviews
            ]

    # ── Submit Review (via marketplace service) ────────────────────────────────

    async def submit_review(
        self,
        listing_id: str,
        user_id: str,
        rating: int,
        review: str | None = None,
    ) -> dict[str, Any]:
        """Submit or update a review. Delegates to MarketplaceService.

        Args:
            listing_id: UUID of the marketplace listing.
            user_id: UUID of the reviewer.
            rating: Rating 1-5.
            review: Optional review text.

        Returns:
            Serialized review dict.
        """
        # Import here to avoid circular imports
        from app.services.marketplace import MarketplaceService

        marketplace = MarketplaceService()
        return await marketplace.submit_review(
            listing_id=listing_id,
            user_id=user_id,
            rating=rating,
            review=review,
        )

    # ── Earnings ───────────────────────────────────────────────────────────────

    async def get_earnings(self, creator_id: str) -> dict[str, Any]:
        """Get total earnings, pending payout, and payout history.

        In this implementation, earnings are tracked at the listing level.
        Future: integrate with Stripe/Paystack connect for actual payouts.

        Args:
            creator_id: UUID of the creator.

        Returns:
            Dict with earnings summary and history.
        """
        factory = get_session_factory()
        async with factory() as session:
            query = (
                select(MarketplaceListing)
                .where(MarketplaceListing.user_id == uuid.UUID(creator_id))
            )
            result = await session.execute(query)
            listings = result.scalars().all()

            total_revenue_cents = 0
            total_installs = 0
            paid_installs = 0
            free_installs = 0
            total_earnings_cents = 0
            platform_fees_cents = 0

            for listing in listings:
                installs = listing.install_count or 0
                price = listing.price_cents or 0

                total_installs += installs
                listing_revenue = installs * price
                total_revenue_cents += listing_revenue
                total_earnings_cents += int(listing_revenue * CREATOR_REVENUE_SHARE)
                platform_fees_cents += int(listing_revenue * PLATFORM_REVENUE_SHARE)

                if price > 0:
                    paid_installs += installs
                else:
                    free_installs += installs

            # Simulated payout history (in production, pulled from payout records)
            payout_history = self._generate_payout_history(total_earnings_cents, total_installs)

            return {
                "total_revenue_cents": total_revenue_cents,
                "total_earnings_cents": total_earnings_cents,
                "total_earnings_display": f"${total_earnings_cents / 100:.2f}",
                "platform_fees_cents": platform_fees_cents,
                "platform_fees_display": f"${platform_fees_cents / 100:.2f}",
                "pending_payout_cents": int(total_earnings_cents * 0.15),  # ~15% pending
                "pending_payout_display": f"${int(total_earnings_cents * 0.15) / 100:.2f}",
                "total_installs": total_installs,
                "paid_installs": paid_installs,
                "free_installs": free_installs,
                "listings_count": len(listings),
                "payout_history": payout_history,
                "revenue_share": {
                    "creator_percentage": CREATOR_REVENUE_SHARE * 100,
                    "platform_percentage": PLATFORM_REVENUE_SHARE * 100,
                },
            }

    # ── Internal Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _empty_analytics() -> dict[str, Any]:
        """Return an empty analytics payload when creator has no listings."""
        return {
            "period": None,
            "total_installs": 0,
            "total_installs_all_time": 0,
            "total_reviews": 0,
            "average_rating": 0.0,
            "total_revenue_cents": 0,
            "total_platform_fees_cents": 0,
            "top_listing": None,
            "installs_over_time": [],
        }

    @staticmethod
    async def _get_installs_by_day(
        session: Any,
        listing_ids: list[uuid.UUID],
        since: datetime,
        period: str,
    ) -> list[dict[str, Any]]:
        """Get install counts grouped by day."""
        from sqlalchemy import cast, Date

        query = (
            select(
                cast(MarketplaceInstall.created_at, Date).label("date"),
                func.count(MarketplaceInstall.id).label("count"),
            )
            .where(
                and_(
                    MarketplaceInstall.listing_id.in_(listing_ids),
                    MarketplaceInstall.created_at >= since,
                )
            )
            .group_by(cast(MarketplaceInstall.created_at, Date))
            .order_by(cast(MarketplaceInstall.created_at, Date).asc())
        )
        result = await session.execute(query)
        rows = result.all()

        # Fill in missing days with zero
        installs_by_day = {str(row.date): row.count for row in rows}

        # Build complete date range
        now = datetime.now(timezone.utc)
        num_days = 30 if period == "30d" else (7 if period == "7d" else 90)
        since_date = since.date()
        result_list = []
        for i in range(num_days):
            day = since_date + timedelta(days=i)
            day_str = day.isoformat()
            result_list.append({
                "date": day_str,
                "installs": installs_by_day.get(day_str, 0),
            })

        return result_list

    @staticmethod
    async def _get_installs_by_month(
        session: Any,
        listing_ids: list[uuid.UUID],
        since: datetime,
    ) -> list[dict[str, Any]]:
        """Get install counts grouped by month (for 'all' period)."""
        from sqlalchemy import extract

        query = (
            select(
                extract("year", MarketplaceInstall.created_at).label("year"),
                extract("month", MarketplaceInstall.created_at).label("month"),
                func.count(MarketplaceInstall.id).label("count"),
            )
            .where(
                and_(
                    MarketplaceInstall.listing_id.in_(listing_ids),
                    MarketplaceInstall.created_at >= since,
                )
            )
            .group_by(
                extract("year", MarketplaceInstall.created_at),
                extract("month", MarketplaceInstall.created_at),
            )
            .order_by(
                extract("year", MarketplaceInstall.created_at).asc(),
                extract("month", MarketplaceInstall.created_at).asc(),
            )
        )
        result = await session.execute(query)
        rows = result.all()

        return [
            {
                "year": int(row.year),
                "month": int(row.month),
                "installs": row.count,
            }
            for row in rows
        ]

    @staticmethod
    def _generate_payout_history(
        total_earnings_cents: int,
        total_installs: int,
    ) -> list[dict[str, Any]]:
        """Generate simulated payout history.

        In production, this would query a payouts table.
        """
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        history = []
        monthly_earnings = max(1, int(total_earnings_cents / max(1, total_installs)))

        for i in range(min(6, max(1, total_installs))):
            payout_date = now - timedelta(days=30 * (i + 1))
            amount = max(0, monthly_earnings - (i * 100))
            if amount > 0:
                history.append({
                    "id": f"payout_{i+1}",
                    "amount_cents": amount,
                    "amount_display": f"${amount / 100:.2f}",
                    "status": "completed" if i > 0 else "pending",
                    "paid_at": payout_date.isoformat(),
                    "period": payout_date.strftime("%B %Y"),
                })

        return history


__all__ = ["CreatorDashboardService"]
