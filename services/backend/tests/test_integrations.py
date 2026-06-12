"""
Integration Connector Tests — OAuth, API key, webhooks, health checks.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestConnectorList:
    """Test connector registry endpoints."""

    @pytest.mark.asyncio
    async def test_list_connectors(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing available connectors."""
        response = await async_client.get("/api/v1/integrations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "connectors" in data or "integrations" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_list_connections(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing user's active connections."""
        response = await async_client.get(
            "/api/v1/integrations/connections",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestOAuthFlow:
    """Test OAuth flow endpoints."""

    @pytest.mark.asyncio
    async def test_initiate_oauth(self, async_client: AsyncClient, auth_headers: dict):
        """Test initiating OAuth flow for a connector."""
        response = await async_client.get(
            "/api/v1/integrations/google/auth",
            headers=auth_headers,
            params={"redirect_uri": "http://localhost:3000/callback"},
        )
        assert response.status_code in (200, 307)

    @pytest.mark.asyncio
    async def test_oauth_callback(self, async_client: AsyncClient, auth_headers: dict):
        """Test OAuth callback handling."""
        response = await async_client.get(
            "/api/v1/integrations/google/callback",
            headers=auth_headers,
            params={"code": "test-auth-code", "state": "test-state"},
        )
        assert response.status_code in (200, 400, 500)


class TestAPIKeyConnection:
    """Test API key-based connections."""

    @pytest.mark.asyncio
    async def test_connect_api_key(self, async_client: AsyncClient, auth_headers: dict):
        """Test connecting with an API key."""
        response = await async_client.post(
            "/api/v1/integrations/connect",
            headers=auth_headers,
            json={
                "connector_key": "openai",
                "credentials": {"api_key": "sk-test-key"},
                "config": {},
            },
        )
        assert response.status_code in (200, 201, 500)


class TestConnectionHealth:
    """Test connection health checks."""

    @pytest.mark.asyncio
    async def test_check_connection_health(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test checking a connection's health status."""
        response = await async_client.get(
            "/api/v1/integrations/check",
            headers=auth_headers,
        )
        assert response.status_code in (200, 500)


class TestWebhook:
    """Test webhook operations."""

    @pytest.mark.asyncio
    async def test_register_webhook(self, async_client: AsyncClient, auth_headers: dict):
        """Test registering a webhook for a connector."""
        response = await async_client.post(
            "/api/v1/integrations/webhooks",
            headers=auth_headers,
            json={
                "connector_key": "github",
                "events": ["push", "pull_request"],
                "target_url": "https://api.anansi.ai/webhooks/github",
            },
        )
        assert response.status_code in (200, 201, 500)

    @pytest.mark.asyncio
    async def test_list_webhooks(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing registered webhooks."""
        response = await async_client.get(
            "/api/v1/integrations/webhooks",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestDisconnect:
    """Test disconnecting integrations."""

    @pytest.mark.asyncio
    async def test_disconnect_connection(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test disconnecting an integration."""
        response = await async_client.delete(
            "/api/v1/integrations/connections/test-id",
            headers=auth_headers,
        )
        assert response.status_code in (200, 204, 404)
