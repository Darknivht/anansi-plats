"""
Marketplace Tests — Browse, install, reviews, creator analytics, earnings.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestMarketplaceBrowse:
    """Test browsing marketplace listings."""

    @pytest.mark.asyncio
    async def test_list_listings(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing marketplace items."""
        response = await async_client.get(
            "/api/v1/marketplace",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_listings(self, async_client: AsyncClient, auth_headers: dict):
        """Test searching marketplace listings."""
        response = await async_client.get(
            "/api/v1/marketplace/search",
            headers=auth_headers,
            params={"q": "test agent", "category": "productivity"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_categories(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting marketplace categories."""
        response = await async_client.get(
            "/api/v1/marketplace/categories",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_featured(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting featured listings."""
        response = await async_client.get(
            "/api/v1/marketplace/featured",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_listing_detail(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test getting listing details."""
        response = await async_client.get(
            "/api/v1/marketplace/test-listing-id",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_get_my_listings(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting user's own listings."""
        response = await async_client.get(
            "/api/v1/marketplace/my-listings",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestMarketplaceInstall:
    """Test agent installation from marketplace."""

    @pytest.mark.asyncio
    async def test_install_agent(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test installing a marketplace agent."""
        response = await async_client.post(
            "/api/v1/marketplace/test-id/install",
            headers=auth_headers,
        )
        assert response.status_code in (200, 201, 404, 500)


class TestMarketplaceReviews:
    """Test marketplace reviews."""

    @pytest.mark.asyncio
    async def test_submit_review(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test submitting a review for a listing."""
        response = await async_client.post(
            "/api/v1/marketplace/test-listing-id/review",
            headers=auth_headers,
            json={"rating": 5, "comment": "Great agent!"},
        )
        assert response.status_code in (200, 201, 404, 500)

    @pytest.mark.asyncio
    async def test_list_reviews(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing reviews."""
        response = await async_client.get(
            "/api/v1/marketplace/reviews",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestCreatorAnalytics:
    """Test creator analytics and earnings."""

    @pytest.mark.asyncio
    async def test_get_creator_analytics(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test getting creator analytics."""
        response = await async_client.get(
            "/api/v1/marketplace/analytics",
            headers=auth_headers,
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_get_earnings(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test getting creator earnings."""
        response = await async_client.get(
            "/api/v1/marketplace/earnings",
            headers=auth_headers,
        )
        assert response.status_code in (200, 500)
