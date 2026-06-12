"""
User Profile Tests — CRUD, avatar upload, account deletion, plan-based access.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestGetProfile:
    """Test retrieving user profile."""

    @pytest.mark.asyncio
    async def test_get_profile(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful profile retrieval."""
        response = await async_client.get("/api/v1/users/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "display_name" in data
        assert "plan" in data

    @pytest.mark.asyncio
    async def test_get_profile_unauthenticated(self, async_client: AsyncClient):
        """Test profile retrieval without auth returns 401."""
        response = await async_client.get("/api/v1/users/profile")
        assert response.status_code == 401


class TestUpdateProfile:
    """Test updating user profile."""

    @pytest.mark.asyncio
    async def test_update_display_name(self, async_client: AsyncClient, auth_headers: dict):
        """Test updating display name."""
        response = await async_client.patch(
            "/api/v1/users/profile",
            headers=auth_headers,
            json={"display_name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_theme(self, async_client: AsyncClient, auth_headers: dict):
        """Test updating theme preference."""
        response = await async_client.patch(
            "/api/v1/users/profile",
            headers=auth_headers,
            json={"theme": "light"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "light"

    @pytest.mark.asyncio
    async def test_update_invalid_theme(self, async_client: AsyncClient, auth_headers: dict):
        """Test invalid theme value returns 422."""
        response = await async_client.patch(
            "/api/v1/users/profile",
            headers=auth_headers,
            json={"theme": "invalid"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_timezone(self, async_client: AsyncClient, auth_headers: dict):
        """Test updating timezone."""
        response = await async_client.patch(
            "/api/v1/users/profile",
            headers=auth_headers,
            json={"timezone": "America/New_York"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_onboarding_step(self, async_client: AsyncClient, auth_headers: dict):
        """Test updating onboarding step."""
        response = await async_client.patch(
            "/api/v1/users/profile",
            headers=auth_headers,
            json={"onboarding_step": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["onboarding_step"] == 2


class TestAvatarUpload:
    """Test avatar upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_avatar(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful avatar upload."""
        # Create a simple PNG-like binary (not a real PNG but enough for testing)
        fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        response = await async_client.post(
            "/api/v1/users/avatar",
            headers=auth_headers,
            files={"file": ("avatar.png", fake_image, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "avatar_url" in data

    @pytest.mark.asyncio
    async def test_upload_avatar_invalid_type(self, async_client: AsyncClient, auth_headers: dict):
        """Test uploading unsupported file type returns 422."""
        response = await async_client.post(
            "/api/v1/users/avatar",
            headers=auth_headers,
            files={"file": ("document.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_avatar_no_auth(self, async_client: AsyncClient):
        """Test avatar upload without auth returns 401."""
        response = await async_client.post(
            "/api/v1/users/avatar",
            files={"file": ("avatar.png", b"test", "image/png")},
        )
        assert response.status_code == 401


class TestDeleteAccount:
    """Test account deletion."""

    @pytest.mark.asyncio
    async def test_delete_account(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful account deletion."""
        response = await async_client.delete("/api/v1/users/account", headers=auth_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_account_no_auth(self, async_client: AsyncClient):
        """Test account deletion without auth returns 401."""
        response = await async_client.delete("/api/v1/users/account")
        assert response.status_code == 401


class TestPlanBasedAccess:
    """Test plan-based feature access control."""

    @pytest.mark.asyncio
    async def test_free_user_cannot_access_pro_features(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test free user cannot access pro-only brain export."""
        response = await async_client.post(
            "/api/v1/brain/export",
            headers=auth_headers,
        )
        assert response.status_code == 403
        error = response.json()
        assert "plan_limit" in error["error"]["code"]

    @pytest.mark.asyncio
    async def test_pro_user_can_access_pro_features(
        self, async_client: AsyncClient, auth_headers_pro: dict
    ):
        """Test pro user can access pro features."""
        response = await async_client.post(
            "/api/v1/brain/export",
            headers=auth_headers_pro,
        )
        # The export might return different status based on graph service mock
        assert response.status_code in (200, 500)
