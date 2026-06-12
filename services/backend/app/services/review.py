"""
Anansi Spaced Repetition Service — SM-2-based memory review scheduling.

Implements a variant of the SM-2 algorithm (from SuperMemo) for scheduling
memory reviews. The interval doubles on correct recall, halves on failure,
and the user rates each review as easy/medium/hard/forgot.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog import get_logger

from app.core.events import get_db_session
from app.core.exceptions import NotFoundError
from app.models.brain import MemoryNode, MemoryReview

logger = get_logger(__name__)

# Rating multipliers for SM-2 variant
RATING_MULTIPLIERS = {
    "easy": 2.0,    # Correct, easy → interval × 2
    "medium": 1.5,  # Correct, medium → interval × 1.5
    "hard": 1.2,    # Correct but hard → interval × 1.2
    "forgot": 0.5,  # Failed → interval ÷ 2
}

# Rating weights for stats calculation
RATING_WEIGHTS = {
    "easy": 4,
    "medium": 3,
    "hard": 2,
    "forgot": 1,
}

# Maximum interval cap (6 months)
MAX_INTERVAL_SECONDS = 6 * 30 * 86400  # ~6 months

# Default interval for new nodes (1 day)
DEFAULT_INTERVAL = 86400

# Minimum interval (1 hour)
MIN_INTERVAL = 3600


class ReviewService:
    """Service for [[Spaced Repetition]] review scheduling.

    Uses an SM-2 variant algorithm to optimise memory retention.
    """

    async def get_queue(
        self,
        user_id: str,
        limit: int = 20,
        db_session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Get nodes due for review with their review history.

        Returns nodes where ``next_review_at <= NOW()``, prioritising
        those with the earliest next review and those reviewed less
        recently.

        Args:
            user_id: The user's UUID.
            limit: Max number of results.
            db_session: Optional existing DB session.

        Returns:
            List of node dicts with review context.
        """
        user_uuid = uuid.UUID(user_id)
        now = datetime.now(timezone.utc)

        async def _query(db: AsyncSession) -> list[dict[str, Any]]:
            stmt = (
                select(MemoryNode)
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                        MemoryNode.next_review_at <= now,
                    )
                )
                .order_by(MemoryNode.next_review_at.asc())
                .limit(limit)
            )
            rows = await db.execute(stmt)
            nodes = rows.scalars().all()

            results = []
            for node in nodes:
                # Get latest review for this node
                review_stmt = (
                    select(MemoryReview)
                    .where(MemoryReview.node_id == node.id)
                    .order_by(MemoryReview.created_at.desc())
                    .limit(5)
                )
                review_rows = await db.execute(review_stmt)
                recent_reviews = review_rows.scalars().all()

                # Calculate days since last review
                days_since_review = None
                if node.last_reviewed_at:
                    days_since_review = (now - node.last_reviewed_at).days

                results.append({
                    "id": str(node.id),
                    "title": node.title,
                    "content": node.content,
                    "layers": node.layers or {},
                    "tags": node.tags or [],
                    "type": node.type,
                    "review_interval": node.review_interval,
                    "next_review_at": node.next_review_at.isoformat() if node.next_review_at else None,
                    "last_reviewed_at": node.last_reviewed_at.isoformat() if node.last_reviewed_at else None,
                    "days_since_review": days_since_review,
                    "recent_reviews": [
                        {
                            "rating": r.rating,
                            "interval_before": r.interval_before,
                            "interval_after": r.interval_after,
                            "created_at": r.created_at.isoformat() if r.created_at else None,
                        }
                        for r in recent_reviews
                    ],
                    "links_count": node.links_count,
                })

            return results

        if db_session:
            return await _query(db_session)

        async for db in get_db_session():
            return await _query(db)

    async def submit_review(
        self,
        user_id: str,
        node_id: str,
        rating: str,
        response_time_ms: int | None = None,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Record a [[Spaced Repetition]] review result.

        Implements SM-2 variant algorithm:
        - **easy** → interval × 2 (strong recall)
        - **medium** → interval × 1.5 (moderate recall)
        - **hard** → interval × 1.2 (weak recall)
        - **forgot** → interval ÷ 2 (failed recall)

        Updates the node's ``review_interval``, ``next_review_at``,
        and ``last_reviewed_at``, and logs the review to the
        ``memory_reviews`` table.

        Args:
            user_id: The user's UUID.
            node_id: The node's UUID.
            rating: Review rating (easy, medium, hard, forgot).
            response_time_ms: Optional response time in milliseconds.
            db_session: Optional existing DB session.

        Returns:
            Updated node review info.

        Raises:
            NotFoundError: If the node doesn't exist.
            ValueError: If the rating is invalid.
        """
        if rating not in RATING_MULTIPLIERS:
            raise ValueError(
                f"Invalid rating '{rating}'. Must be one of: {', '.join(RATING_MULTIPLIERS.keys())}"
            )

        uid = uuid.UUID(node_id)
        user_uuid = uuid.UUID(user_id)
        now = datetime.now(timezone.utc)

        async def _submit(db: AsyncSession) -> dict[str, Any]:
            node = await db.get(MemoryNode, uid)
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            # Calculate new interval using SM-2 variant
            interval_before = node.review_interval
            multiplier = RATING_MULTIPLIERS[rating]

            new_interval = int(interval_before * multiplier)

            # Apply min/max constraints
            new_interval = max(new_interval, MIN_INTERVAL)
            new_interval = min(new_interval, MAX_INTERVAL_SECONDS)

            # If forgot, also schedule a sooner follow-up
            next_review_offset = new_interval
            if rating == "forgot":
                # Schedule a quick re-review at half the new interval
                next_review_offset = max(new_interval // 2, MIN_INTERVAL)

            # Create review log entry
            review = MemoryReview(
                id=uuid.uuid4(),
                user_id=user_uuid,
                node_id=uid,
                rating=rating,
                response_time_ms=response_time_ms,
                interval_before=interval_before,
                interval_after=new_interval,
            )
            db.add(review)

            # Update node
            node.review_interval = new_interval
            node.next_review_at = now + timedelta(seconds=next_review_offset)
            node.last_reviewed_at = now
            node.review_status = "current"

            await db.commit()

            return {
                "node_id": str(node.id),
                "title": node.title,
                "rating": rating,
                "interval_before": interval_before,
                "interval_after": new_interval,
                "next_review_at": node.next_review_at.isoformat() if node.next_review_at else None,
                "last_reviewed_at": node.last_reviewed_at.isoformat() if node.last_reviewed_at else None,
            }

        if db_session:
            return await _submit(db_session)

        async for db in get_db_session():
            return await _submit(db)

    async def get_review_stats(
        self,
        user_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Get review statistics for the user.

        Returns:
            - reviews_today: Number completed today
            - reviews_this_week: Number completed this week
            - streak: Consecutive days with at least one review
            - average_rating: Average rating across all reviews
            - upcoming_queue_size: Nodes due for review
            - total_reviews: Lifetime review count
        """
        user_uuid = uuid.UUID(user_id)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())

        async def _stats(db: AsyncSession) -> dict[str, Any]:
            # Reviews today
            today_count = await db.execute(
                select(func.count(MemoryReview.id)).where(
                    and_(
                        MemoryReview.user_id == user_uuid,
                        MemoryReview.created_at >= today_start,
                    )
                )
            )
            reviews_today = today_count.scalar() or 0

            # Reviews this week
            week_count = await db.execute(
                select(func.count(MemoryReview.id)).where(
                    and_(
                        MemoryReview.user_id == user_uuid,
                        MemoryReview.created_at >= week_start,
                    )
                )
            )
            reviews_this_week = week_count.scalar() or 0

            # Total reviews
            total_count = await db.execute(
                select(func.count(MemoryReview.id)).where(
                    MemoryReview.user_id == user_uuid,
                )
            )
            total_reviews = total_count.scalar() or 0

            # Average rating
            avg_result = await db.execute(
                select(func.count(MemoryReview.id)).where(
                    and_(
                        MemoryReview.user_id == user_uuid,
                    )
                )
            )
            # Manual average since we store string ratings
            all_reviews_result = await db.execute(
                select(MemoryReview.rating).where(
                    MemoryReview.user_id == user_uuid,
                )
            )
            all_ratings = all_reviews_result.scalars().all()
            average_rating = 0.0
            if all_ratings:
                weighted_sum = sum(RATING_WEIGHTS.get(r, 0) for r in all_ratings)
                average_rating = round(weighted_sum / len(all_ratings), 2)

            # Upcoming queue size
            upcoming = await db.execute(
                select(func.count(MemoryNode.id)).where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                        MemoryNode.next_review_at <= now,
                    )
                )
            )
            upcoming_queue = upcoming.scalar() or 0

            # Streak calculation
            streak = await self._calculate_streak(db, user_uuid)

            # Rating distribution
            dist_result = await db.execute(
                select(MemoryReview.rating, func.count(MemoryReview.id))
                .where(MemoryReview.user_id == user_uuid)
                .group_by(MemoryReview.rating)
            )
            rating_distribution = {row[0]: row[1] for row in dist_result}

            return {
                "reviews_today": reviews_today,
                "reviews_this_week": reviews_this_week,
                "total_reviews": total_reviews,
                "streak": streak,
                "average_rating": average_rating,
                "upcoming_queue_size": upcoming_queue,
                "rating_distribution": rating_distribution,
            }

        if db_session:
            return await _stats(db_session)

        async for db in get_db_session():
            return await _stats(db)

    async def schedule_reviews(
        self,
        user_id: str,
        db_session: AsyncSession | None = None,
    ) -> int:
        """Ensure the review queue is populated for today.

        For nodes that have never been reviewed and have no next_review_at,
        set them to review now. This runs daily to ensure the queue
        is populated.

        Args:
            user_id: The user's UUID.
            db_session: Optional existing DB session.

        Returns:
            Number of nodes scheduled.
        """
        user_uuid = uuid.UUID(user_id)
        now = datetime.now(timezone.utc)

        async def _schedule(db: AsyncSession) -> int:
            stmt = (
                select(MemoryNode)
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                        MemoryNode.next_review_at.is_(None),
                    )
                )
                .limit(100)
            )
            rows = await db.execute(stmt)
            nodes = rows.scalars().all()

            count = 0
            for node in nodes:
                node.next_review_at = now
                node.review_interval = DEFAULT_INTERVAL
                count += 1

            if count > 0:
                await db.commit()
                logger.info(
                    "Reviews scheduled",
                    user_id=user_id,
                    count=count,
                )

            return count

        if db_session:
            return await _schedule(db_session)

        async for db in get_db_session():
            return await _schedule(db)

    # ── Internal Helpers ─────────────────────────────────────────────────────

    async def _calculate_streak(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        """Calculate the current review streak (consecutive days)."""
        stmt = (
            select(
                func.date_trunc("day", MemoryReview.created_at).label("review_day"),
                func.count(MemoryReview.id).label("count"),
            )
            .where(MemoryReview.user_id == user_id)
            .group_by("review_day")
            .order_by(func.date_trunc("day", MemoryReview.created_at).desc())
            .limit(365)
        )
        rows = await db.execute(stmt)
        days = [row[0] for row in rows if row[1] > 0]

        if not days:
            return 0

        streak = 0
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        for i, day in enumerate(days):
            expected = today - timedelta(days=i)
            if day.date() == expected.date():
                streak += 1
            else:
                # Allow today to be missing if reviews happened yesterday
                if i == 0 and days:
                    continue
                break

        return streak


__all__ = ["ReviewService"]
