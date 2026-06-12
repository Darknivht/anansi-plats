"""
Marketplace API Endpoints — Browse, install, review, and manage marketplace agents.

From spec section 8.2:
- GET    /api/v1/marketplace — Browse agents (paginated, filterable)
- GET    /api/v1/marketplace/:id — Agent detail
- POST   /api/v1/marketplace/:id/install — Install agent
- POST   /api/v1/marketplace/:id/review — Submit review
- GET    /api/v1/marketplace/categories — List categories
- GET    /api/v1/marketplace/featured — Featured agents
- GET    /api/v1/marketplace/my-listings — Creator's listings
- GET    /api/v1/marketplace/analytics — Creator sales analytics
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from structlog import get_logger

from app.core.dependencies import CurrentUser, get_current_user, get_optional_user, rate_limit
from app.core.exceptions import ValidationError
from app.services.marketplace import MarketplaceService
from app.services.creator import CreatorDashboardService

logger = get_logger(__name__)

router = APIRouter()
marketplace_service = MarketplaceService()
creator_service = CreatorDashboardService()


# ─── Browse ────────────────────────────────────────────────────────────────────


@router.get("")
async def browse_marketplace(
    category: str | None = Query(None, description="Filter by category slug"),
    tags: str | None = Query(None, description="Comma-separated tags to filter by"),
    sort: str = Query("popular", description="Sort: popular, newest, rating, price_low, price_high"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    price_min: int | None = Query(None, description="Minimum price in cents (0 = free)"),
    price_max: int | None = Query(None, description="Maximum price in cents"),
    current_user: CurrentUser | None = Depends(get_optional_user),
) -> dict[str, Any]:
    """Browse marketplace with filters and pagination."""
    tag_list = tags.split(",") if tags else None

    return await marketplace_service.list_listings(
        category=category,
        tags=tag_list,
        sort=sort,
        page=page,
        limit=limit,
        price_min=price_min,
        price_max=price_max,
    )


# ─── Listing Detail ────────────────────────────────────────────────────────────


@router.get("/{listing_id}")
async def get_listing(
    listing_id: str = Path(..., description="Marketplace listing UUID"),
    current_user: CurrentUser | None = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get full marketplace listing detail."""
    return await marketplace_service.get_listing(listing_id=listing_id)


# ─── Install ───────────────────────────────────────────────────────────────────


@router.post("/{listing_id}/install")
async def install_agent(
    listing_id: str = Path(..., description="Marketplace listing UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Install a marketplace agent into the current user's library."""
    return await marketplace_service.install_agent(
        listing_id=listing_id,
        user_id=current_user.id,
    )


# ─── Submit Review ─────────────────────────────────────────────────────────────


@router.post("/{listing_id}/review")
async def submit_review(
    body: dict[str, Any],
    listing_id: str = Path(..., description="Marketplace listing UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Submit or update a review for a marketplace listing."""
    rating = body.get("rating")
    review_text = body.get("review")

    if rating is None:
        raise ValidationError(message="Rating is required")

    return await marketplace_service.submit_review(
        listing_id=listing_id,
        user_id=current_user.id,
        rating=int(rating),
        review=review_text,
    )


# ─── Categories ────────────────────────────────────────────────────────────────


@router.get("/categories")
async def list_categories(
    current_user: CurrentUser | None = Depends(get_optional_user),
) -> list[dict[str, Any]]:
    """List all marketplace categories with listing counts."""
    return await marketplace_service.get_categories()


# ─── Featured ──────────────────────────────────────────────────────────────────


@router.get("/featured")
async def get_featured(
    limit: int = Query(10, ge=1, le=50, description="Number of featured listings"),
    current_user: CurrentUser | None = Depends(get_optional_user),
) -> list[dict[str, Any]]:
    """Get featured/curated marketplace listings."""
    return await marketplace_service.get_featured(limit=limit)


# ─── Search ────────────────────────────────────────────────────────────────────


@router.get("/search")
async def search_marketplace(
    q: str = Query(..., min_length=1, description="Search query"),
    category: str | None = Query(None, description="Filter by category"),
    tags: str | None = Query(None, description="Comma-separated tags"),
    price_free: bool | None = Query(None, description="Filter free agents only"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    current_user: CurrentUser | None = Depends(get_optional_user),
) -> dict[str, Any]:
    """Full-text search across marketplace listings."""
    tag_list = tags.split(",") if tags else None

    return await marketplace_service.search_listings(
        query=q,
        category=category,
        tags=tag_list,
        price_free=price_free,
        page=page,
        limit=limit,
    )


# ─── Creator Dashboard: My Listings ───────────────────────────────────────────


@router.get("/my-listings")
async def get_my_listings(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get the current user's published marketplace listings.

    Requires the user to be a marketplace creator (has published agents).
    """
    return await creator_service.get_my_listings(creator_id=current_user.id)


# ─── Creator Dashboard: Sales Analytics ─────────────────────────────────────


@router.get("/analytics")
async def get_sales_analytics(
    period: str = Query("30d", description="Period: 7d, 30d, 90d, 1y, all"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get sales analytics for the current user's marketplace listings."""
    return await creator_service.get_sales_analytics(
        creator_id=current_user.id,
        period=period,
    )


# ─── Creator Dashboard: Earnings ─────────────────────────────────────────────


@router.get("/earnings")
async def get_earnings(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get earnings summary, pending payout, and payout history."""
    return await creator_service.get_earnings(creator_id=current_user.id)


# ─── Creator Dashboard: Reviews ──────────────────────────────────────────────


@router.get("/reviews")
async def get_creator_reviews(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get all reviews for the current user's marketplace listings."""
    return await creator_service.get_reviews(creator_id=current_user.id)
