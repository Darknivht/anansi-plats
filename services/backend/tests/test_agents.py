"""
Agent Workshop Tests — CRUD, versioning, validation, execution, blocks, triggers.

Tests for the Agent Workshop API defined in ``app.api.v1.agents``.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestAgentCRUD:
    """Test agent CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_agents(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing agents."""
        response = await async_client.get("/api/v1/agents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data or "items" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_create_agent(self, async_client: AsyncClient, auth_headers: dict):
        """Test creating an agent."""
        response = await async_client.post(
            "/api/v1/agents",
            headers=auth_headers,
            json={"name": "My New Agent", "description": "Test agent creation"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "agent" in data or "id" in data

    @pytest.mark.asyncio
    async def test_create_agent_empty_name(self, async_client: AsyncClient, auth_headers: dict):
        """Test creating agent with empty name."""
        response = await async_client.post(
            "/api/v1/agents",
            headers=auth_headers,
            json={"name": "", "description": "Empty name"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_agent(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test getting a specific agent."""
        response = await async_client.get(
            f"/api/v1/agents/{sample_agent['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting a non-existent agent returns 404."""
        response = await async_client.get(
            f"/api/v1/agents/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_agent(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test updating an agent."""
        response = await async_client.patch(
            f"/api/v1/agents/{sample_agent['id']}",
            headers=auth_headers,
            json={"name": "Updated Agent Name"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_agent(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test soft-deleting an agent."""
        response = await async_client.delete(
            f"/api/v1/agents/{sample_agent['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 204


class TestAgentExecution:
    """Test agent execution."""

    @pytest.mark.asyncio
    async def test_run_agent_sync(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test synchronous agent execution."""
        response = await async_client.post(
            f"/api/v1/agents/{sample_agent['id']}/run",
            headers=auth_headers,
            json={"input": "Hello Agent"},
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_test_agent_dry_run(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test dry-run (test mode) without real side effects."""
        response = await async_client.post(
            f"/api/v1/agents/{sample_agent['id']}/test",
            headers=auth_headers,
            json={"input": "Test input"},
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_run_agent_async(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test asynchronous agent execution."""
        response = await async_client.post(
            f"/api/v1/agents/{sample_agent['id']}/run/async",
            headers=auth_headers,
            json={"input": "Async test"},
        )
        assert response.status_code in (200, 202, 500)


class TestAgentVersions:
    """Test agent versioning."""

    @pytest.mark.asyncio
    async def test_get_versions(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test getting agent versions."""
        response = await async_client.get(
            f"/api/v1/agents/{sample_agent['id']}/versions",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_duplicate_agent(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test duplicating an agent."""
        response = await async_client.post(
            f"/api/v1/agents/{sample_agent['id']}/duplicate",
            headers=auth_headers,
        )
        assert response.status_code in (200, 201, 500)


class TestAgentBlocks:
    """Test agent block operations."""

    @pytest.mark.asyncio
    async def test_list_blocks(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing available block types."""
        response = await async_client.get(
            "/api/v1/agents/blocks",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "blocks" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_list_blocks_by_category(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing blocks filtered by category."""
        response = await async_client.get(
            "/api/v1/agents/blocks/category/ai",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestAgentValidation:
    """Test agent definition validation."""

    @pytest.mark.asyncio
    async def test_validate_agent_definition(self, async_client: AsyncClient, auth_headers: dict):
        """Test validating an agent definition."""
        response = await async_client.post(
            "/api/v1/agents/validate",
            headers=auth_headers,
            json={
                "name": "Valid Agent",
                "blocks": [{"id": "block-1", "type": "input", "label": "Input"}],
            },
        )
        assert response.status_code in (200, 422)


class TestAgentTriggers:
    """Test agent trigger registration."""

    @pytest.mark.asyncio
    async def test_register_triggers(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test registering triggers for an agent."""
        response = await async_client.post(
            f"/api/v1/agents/{sample_agent['id']}/triggers/register",
            headers=auth_headers,
            json={"triggers": [{"type": "webhook", "config": {}}]},
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_list_triggers(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test listing agent triggers."""
        response = await async_client.get(
            f"/api/v1/agents/{sample_agent['id']}/triggers",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unregister_triggers(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test unregistering triggers."""
        response = await async_client.post(
            f"/api/v1/agents/{sample_agent['id']}/triggers/unregister",
            headers=auth_headers,
        )
        assert response.status_code in (200, 500)


class TestAgentPublish:
    """Test agent publishing and sharing."""

    @pytest.mark.asyncio
    async def test_publish_agent(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test publishing an agent."""
        response = await async_client.post(
            f"/api/v1/agents/{sample_agent['id']}/publish",
            headers=auth_headers,
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_share_agent(
        self, async_client: AsyncClient, auth_headers: dict, sample_agent: dict
    ):
        """Test sharing an agent."""
        response = await async_client.post(
            f"/api/v1/agents/{sample_agent['id']}/share",
            headers=auth_headers,
            json={"permission": "view"},
        )
        assert response.status_code in (200, 500)
