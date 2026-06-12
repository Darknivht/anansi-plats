"""
Marketplace Service — Browse, search, install agents, reviews, categories, featured.

Integrates with MarketplaceListing, MarketplaceReview, MarketplaceInstall models
and the AgentService for duplicating agents on install.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_session_factory
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.agent import Agent
from app.models.marketplace import (
    MarketplaceListing,
    MarketplaceReview,
    MarketplaceInstall,
)
from app.models.user import User
from app.services.agent import AgentService

logger = get_logger(__name__)

# Valid sort options for marketplace listing
VALID_SORTS = ("popular", "newest", "rating", "price_low", "price_high")


class MarketplaceService:
    """Business logic for the Anansi marketplace (The Bazaar)."""

    def __init__(self) -> None:
        self._agent_service: AgentService | None = None

    @property
    def agent_service(self) -> AgentService:
        if self._agent_service is None:
            self._agent_service = AgentService()
        return self._agent_service

    # ── Browse ─────────────────────────────────────────────────────────────────

    async def list_listings(
        self,
        category: str | None = None,
        tags: list[str] | None = None,
        sort: str = "popular",
        page: int = 1,
        limit: int = 20,
        price_min: int | None = None,
        price_max: int | None = None,
    ) -> dict[str, Any]:
        """Browse marketplace listings with filters and pagination.

        Args:
            category: Filter by category slug.
            tags: Filter by tags (AND logic).
            sort: Sort order — 'popular', 'newest', 'rating', 'price_low', 'price_high'.
            page: Page number (1-indexed).
            limit: Items per page (max 50).
            price_min: Minimum price in cents (0 = free).
            price_max: Maximum price in cents.

        Returns:
            Dict with 'items', 'total', 'page', 'limit', 'pages'.
        """
        if sort not in VALID_SORTS:
            raise ValidationError(
                message=f"Invalid sort option. Must be one of: {', '.join(VALID_SORTS)}"
            )

        factory = get_session_factory()
        async with factory() as session:
            # Base query: only published listings
            query = (
                select(MarketplaceListing)
                .options(
                    joinedload(MarketplaceListing.agent),
                    joinedload(MarketplaceListing.reviews),
                )
                .where(MarketplaceListing.status == "published")
            )

            # ── Filters ──
            if category:
                query = query.where(MarketplaceListing.category == category)

            if tags:
                # PostgreSQL ARRAY overlap operator: && (any overlap)
                # Using ANY for simple tag filtering
                for tag in tags:
                    query = query.where(
                        func.array_position(MarketplaceListing.tags, tag) is not None
                    )

            if price_min is not None:
                query = query.where(MarketplaceListing.price_cents >= price_min)

            if price_max is not None:
                query = query.where(MarketplaceListing.price_cents <= price_max)

            # ── Sort ──
            if sort == "popular":
                query = query.order_by(MarketplaceListing.install_count.desc())
            elif sort == "newest":
                query = query.order_by(MarketplaceListing.created_at.desc())
            elif sort == "rating":
                query = query.order_by(MarketplaceListing.rating_avg.desc())
            elif sort == "price_low":
                query = query.order_by(MarketplaceListing.price_cents.asc())
            elif sort == "price_high":
                query = query.order_by(MarketplaceListing.price_cents.desc())

            # ── Count ──
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            # ── Paginate ──
            limit = min(limit, 50)
            pages = max(1, (total + limit - 1) // limit)
            offset = (page - 1) * limit

            query = query.offset(offset).limit(limit)

            result = await session.execute(query)
            listings = result.unique().scalars().all()

            return {
                "items": [self._serialize_listing(l) for l in listings],
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
            }

    # ── Detail ─────────────────────────────────────────────────────────────────

    async def get_listing(self, listing_id: str) -> dict[str, Any]:
        """Get full marketplace listing detail with screenshots, rating, creator info.

        Args:
            listing_id: UUID of the marketplace listing.

        Returns:
            Full listing detail dict.

        Raises:
            NotFoundError: If listing doesn't exist or isn't published.
        """
        factory = get_session_factory()
        async with factory() as session:
            listing = await self._fetch_listing(session, listing_id)

            # Get creator info
            creator_query = select(User).where(User.id == listing.user_id)
            creator_result = await session.execute(creator_query)
            creator = creator_result.scalar_one_or_none()

            # Get version history from the agent
            agent = listing.agent
            version_history = []
            if agent:
                versions = await self.agent_service.get_versions(str(agent.id))
                version_history = [
                    {
                        "version": v["version"],
                        "created_at": v["created_at"],
                        "change_notes": v.get("change_notes"),
                    }
                    for v in versions[-10:]  # Last 10 versions
                ]

            return {
                **self._serialize_listing(listing),
                "version_history": version_history,
                "creator": {
                    "id": str(creator.id) if creator else None,
                    "display_name": creator.display_name if creator else "Unknown",
                    "avatar_url": creator.avatar_url if creator else None,
                },
                "reviews": [
                    self._serialize_review(r) for r in listing.reviews
                ],
            }

    # ── Install ────────────────────────────────────────────────────────────────

    async def install_agent(self, listing_id: str, user_id: str) -> dict[str, Any]:
        """Install a marketplace agent — creates a copy in the user's library.

        Steps:
        1. Verify the listing exists and is published.
        2. Check user hasn't already installed this listing.
        3. Record the install.
        4. Increment the listing's install_count.
        5. Duplicate the agent under the user's ownership.

        Args:
            listing_id: UUID of the marketplace listing.
            user_id: UUID of the installing user.

        Returns:
            Dict with the new agent info and install record.

        Raises:
            NotFoundError: Listing not found.
            ConflictError: Already installed.
        """
        factory = get_session_factory()
        async with factory() as session:
            listing = await self._fetch_listing(session, listing_id)

            # Check for existing install
            existing_check = await session.execute(
                select(MarketplaceInstall).where(
                    and_(
                        MarketplaceInstall.listing_id == listing.id,
                        MarketplaceInstall.user_id == uuid.UUID(user_id),
                    )
                )
            )
            if existing_check.scalar_one_or_none():
                raise ConflictError(
                    message="You have already installed this agent",
                    details={"listing_id": listing_id},
                )

            # Duplicate the agent for the user
            agent = listing.agent
            if not agent:
                raise NotFoundError(
                    message="The source agent for this listing no longer exists",
                    resource_type="agent",
                )

            # Create a copy of the agent definition
            from copy import deepcopy

            new_agent = Agent(
                user_id=uuid.UUID(user_id),
                name=agent.name,
                description=agent.description,
                definition=deepcopy(agent.definition),
                version=1,
                status="active",
                is_published=False,
                category=agent.category,
                tags=agent.tags[:] if agent.tags else [],
            )
            session.add(new_agent)
            await session.flush()  # Get the ID

            # Record the install
            install = MarketplaceInstall(
                listing_id=listing.id,
                user_id=uuid.UUID(user_id),
                agent_id=new_agent.id,
            )
            session.add(install)

            # Increment install count
            listing.install_count = (listing.install_count or 0) + 1

            await session.commit()

            logger.info(
                "Agent installed from marketplace",
                listing_id=listing_id,
                user_id=user_id,
                new_agent_id=str(new_agent.id),
            )

            return {
                "install_id": str(install.id),
                "agent": {
                    "id": str(new_agent.id),
                    "name": new_agent.name,
                    "description": new_agent.description,
                    "version": new_agent.version,
                },
                "listing_title": listing.title,
                "installed_at": install.created_at.isoformat() if install.created_at else None,
            }

    # ── Search ─────────────────────────────────────────────────────────────────

    async def search_listings(
        self,
        query: str,
        category: str | None = None,
        tags: list[str] | None = None,
        price_free: bool | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Full-text search across marketplace listings.

        Searches title, description, and tags using PostgreSQL full-text search.

        Args:
            query: Search query string.
            category: Optional category filter.
            tags: Optional tags filter.
            price_free: If True, show only free agents. If False, show only paid.
            page: Page number (1-indexed).
            limit: Items per page (max 50).

        Returns:
            Dict with 'items', 'total', 'page', 'limit', 'pages'.
        """
        if not query or not query.strip():
            raise ValidationError(message="Search query is required")

        factory = get_session_factory()
        async with factory() as session:
            search_term = f"%{query.strip()}%"

            base_query = (
                select(MarketplaceListing)
                .options(joinedload(MarketplaceListing.agent))
                .where(
                    and_(
                        MarketplaceListing.status == "published",
                        or_(
                            MarketplaceListing.title.ilike(search_term),
                            MarketplaceListing.description.ilike(search_term),
                            func.array_to_string(MarketplaceListing.tags, " ").ilike(
                                search_term
                            ),
                        ),
                    )
                )
            )

            if category:
                base_query = base_query.where(
                    MarketplaceListing.category == category
                )

            if tags:
                for tag in tags:
                    base_query = base_query.where(
                        func.array_position(MarketplaceListing.tags, tag) is not None
                    )

            if price_free is True:
                base_query = base_query.where(MarketplaceListing.price_cents == 0)
            elif price_free is False:
                base_query = base_query.where(MarketplaceListing.price_cents > 0)

            # Count
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            # Paginate
            limit = min(limit, 50)
            pages = max(1, (total + limit - 1) // limit)
            offset = (page - 1) * limit

            # Sort by relevance (title matches first, then description matches)
            title_match = case(
                (MarketplaceListing.title.ilike(search_term), 0),
                else_=1,
            )
            base_query = base_query.order_by(title_match, MarketplaceListing.install_count.desc())
            base_query = base_query.offset(offset).limit(limit)

            result = await session.execute(base_query)
            listings = result.unique().scalars().all()

            return {
                "items": [self._serialize_listing(l) for l in listings],
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
            }

    # ── Featured ───────────────────────────────────────────────────────────────

    async def get_featured(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get curated/featured marketplace listings.

        Returns listings with is_featured=True, sorted by install count.

        Args:
            limit: Maximum number of featured listings to return.

        Returns:
            List of serialized featured listings.
        """
        factory = get_session_factory()
        async with factory() as session:
            query = (
                select(MarketplaceListing)
                .options(joinedload(MarketplaceListing.agent))
                .where(
                    and_(
                        MarketplaceListing.status == "published",
                        MarketplaceListing.is_featured == True,
                    )
                )
                .order_by(MarketplaceListing.install_count.desc())
                .limit(limit)
            )
            result = await session.execute(query)
            listings = result.unique().scalars().all()

            return [self._serialize_listing(l) for l in listings]

    # ── Categories ─────────────────────────────────────────────────────────────

    async def get_categories(self) -> list[dict[str, Any]]:
        """List all categories with listing counts.

        Returns:
            List of dicts with 'category', 'count', and 'display_name'.
        """
        CATEGORY_DISPLAY_NAMES = {
            "productivity": "Productivity",
            "communications": "Communications",
            "finance": "Finance",
            "social_media": "Social Media",
            "devops": "DevOps",
            "ecommerce": "E-commerce",
            "health": "Health",
            "education": "Education",
            "personal": "Personal",
            "custom": "Custom",
            "uncategorized": "Uncategorized",
        }

        factory = get_session_factory()
        async with factory() as session:
            query = (
                select(
                    MarketplaceListing.category,
                    func.count(MarketplaceListing.id).label("count"),
                )
                .where(
                    and_(
                        MarketplaceListing.status == "published",
                        MarketplaceListing.category.isnot(None),
                    )
                )
                .group_by(MarketplaceListing.category)
                .order_by(func.count(MarketplaceListing.id).desc())
            )
            result = await session.execute(query)
            rows = result.all()

            categories = []
            for row in rows:
                slug = row.category
                categories.append({
                    "slug": slug,
                    "display_name": CATEGORY_DISPLAY_NAMES.get(
                        slug, slug.replace("_", " ").title()
                    ),
                    "count": row.count,
                })

            return categories

    # ── Reviews ────────────────────────────────────────────────────────────────

    async def submit_review(
        self,
        listing_id: str,
        user_id: str,
        rating: int,
        review: str | None = None,
    ) -> dict[str, Any]:
        """Submit or update a review for a marketplace listing.

        One review per user per listing — if a review exists, it is updated.

        Args:
            listing_id: UUID of the marketplace listing.
            user_id: UUID of the reviewer.
            rating: Rating 1-5.
            review: Optional review text.

        Returns:
            Serialized review dict.

        Raises:
            ValidationError: If rating is out of range.
            NotFoundError: If listing doesn't exist.
        """
        if rating < 1 or rating > 5:
            raise ValidationError(message="Rating must be between 1 and 5")

        factory = get_session_factory()
        async with factory() as session:
            listing = await self._fetch_listing(session, listing_id)

            # Check for existing review
            existing_query = select(MarketplaceReview).where(
                and_(
                    MarketplaceReview.listing_id == listing.id,
                    MarketplaceReview.user_id == uuid.UUID(user_id),
                )
            )
            existing_result = await session.execute(existing_query)
            existing_review = existing_result.scalar_one_or_none()

            old_rating = None
            if existing_review:
                old_rating = existing_review.rating
                existing_review.rating = rating
                existing_review.review = review
            else:
                new_review = MarketplaceReview(
                    listing_id=listing.id,
                    user_id=uuid.UUID(user_id),
                    rating=rating,
                    review=review,
                )
                session.add(new_review)

            # Recalculate average rating
            await self._recalculate_rating(session, listing, old_rating, rating)
            await session.commit()

            # Refresh to get updated listing
            await session.refresh(listing)

            # Return the review (existing or new)
            review_query = select(MarketplaceReview).where(
                and_(
                    MarketplaceReview.listing_id == listing.id,
                    MarketplaceReview.user_id == uuid.UUID(user_id),
                )
            )
            review_result = await session.execute(review_query)
            final_review = review_result.scalar_one()

            return {
                "id": str(final_review.id),
                "listing_id": listing_id,
                "user_id": user_id,
                "rating": final_review.rating,
                "review": final_review.review,
                "created_at": final_review.created_at.isoformat() if final_review.created_at else None,
                "listing_rating_avg": listing.rating_avg,
                "listing_rating_count": listing.rating_count,
            }

    # ── Internal Helpers ───────────────────────────────────────────────────────

    @staticmethod
    async def _recalculate_rating(
        session: AsyncSession,
        listing: MarketplaceListing,
        old_rating: int | None,
        new_rating: int,
    ) -> None:
        """Recalculate the average rating for a listing after a review change."""
        # Get all ratings for this listing
        ratings_query = select(MarketplaceReview.rating).where(
            MarketplaceReview.listing_id == listing.id
        )
        ratings_result = await session.execute(ratings_query)
        ratings = [r[0] for r in ratings_result.all()]

        # Handle the case where the review being updated is already counted
        # by re-reading from DB after flush
        await session.flush()
        ratings_query2 = select(MarketplaceReview.rating).where(
            MarketplaceReview.listing_id == listing.id
        )
        ratings_result2 = await session.execute(ratings_query2)
        all_ratings = [r[0] for r in ratings_result2.all()]

        if all_ratings:
            listing.rating_avg = round(sum(all_ratings) / len(all_ratings), 2)
            listing.rating_count = len(all_ratings)
        else:
            listing.rating_avg = 0.0
            listing.rating_count = 0

    @staticmethod
    async def _fetch_listing(
        session: AsyncSession,
        listing_id: str,
    ) -> MarketplaceListing:
        """Fetch a marketplace listing by ID, raising NotFoundError if missing."""
        try:
            uid = uuid.UUID(listing_id)
        except ValueError as exc:
            raise ValidationError(message=f"Invalid listing ID: {listing_id}") from exc

        result = await session.execute(
            select(MarketplaceListing)
            .options(
                joinedload(MarketplaceListing.agent),
                joinedload(MarketplaceListing.reviews),
                joinedload(MarketplaceListing.installs),
            )
            .where(MarketplaceListing.id == uid)
        )
        listing = result.unique().scalar_one_or_none()

        if listing is None:
            raise NotFoundError(
                message=f"Marketplace listing not found: {listing_id}",
                resource_type="marketplace_listing",
                resource_id=listing_id,
            )

        return listing

    @staticmethod
    def _serialize_listing(listing: MarketplaceListing) -> dict[str, Any]:
        """Convert a MarketplaceListing ORM instance to a safe API response dict."""
        agent = listing.agent

        return {
            "id": str(listing.id),
            "agent_id": str(listing.agent_id) if listing.agent_id else None,
            "user_id": str(listing.user_id),
            "title": listing.title,
            "description": listing.description,
            "price_cents": listing.price_cents,
            "price_display": (
                f"${listing.price_cents / 100:.2f}" if listing.price_cents > 0 else "Free"
            ),
            "category": listing.category,
            "tags": listing.tags or [],
            "screenshots": listing.screenshots or [],
            "rating_avg": listing.rating_avg,
            "rating_count": listing.rating_count,
            "install_count": listing.install_count,
            "status": listing.status,
            "is_featured": listing.is_featured,
            "agent_name": agent.name if agent else None,
            "agent_version": agent.version if agent else None,
            "memory_nodes_per_run": listing.memory_nodes_per_run,
            "memory_links_per_run": listing.memory_links_per_run,
            "rejection_reason": listing.rejection_reason,
            "created_at": listing.created_at.isoformat() if listing.created_at else None,
            "updated_at": listing.updated_at.isoformat() if listing.updated_at else None,
        }

    @staticmethod
    def _serialize_review(review: MarketplaceReview) -> dict[str, Any]:
        """Serialize a single review."""
        return {
            "id": str(review.id),
            "listing_id": str(review.listing_id),
            "user_id": str(review.user_id),
            "rating": review.rating,
            "review": review.review,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        }


__all__ = ["MarketplaceService"]
