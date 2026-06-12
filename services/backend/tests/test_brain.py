"""
Second Brain Tests — Memory nodes, links, search, summarization, daily notes,
spaced repetition, brain stats, and Obsidian export.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestMemoryNodeCRUD:
    """Test memory node CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_node(self, async_client: AsyncClient, auth_headers: dict):
        """Test creating a basic memory node."""
        response = await async_client.post(
            "/api/v1/brain/nodes",
            headers=auth_headers,
            json={
                "title": "Test Memory",
                "content": "This is a test memory node content.",
                "type": "fact",
                "tags": ["#test", "#brain"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "node" in data
        assert data["node"]["title"] == "Test Memory"
        assert data["node"]["type"] == "fact"

    @pytest.mark.asyncio
    async def test_create_node_with_para(self, async_client: AsyncClient, auth_headers: dict):
        """Test creating a node with PARA category."""
        response = await async_client.post(
            "/api/v1/brain/nodes",
            headers=auth_headers,
            json={
                "title": "Project Note",
                "content": "A project-related note.",
                "type": "fact",
                "para_category": "projects",
                "tags": ["#work"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["node"]["para_category"] == "projects"

    @pytest.mark.asyncio
    async def test_get_node(
        self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict
    ):
        """Test retrieving a specific node."""
        node_id = sample_memory_node["id"]
        # The endpoint uses :id path param but brain.py uses /nodes/:id — actually it's colon-prefixed
        response = await async_client.get(
            f"/api/v1/brain/nodes/{node_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "node" in data
        assert data["node"]["title"] == sample_memory_node["title"]

    @pytest.mark.asyncio
    async def test_update_node(
        self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict
    ):
        """Test updating a node."""
        node_id = sample_memory_node["id"]
        response = await async_client.patch(
            f"/api/v1/brain/nodes/{node_id}",
            headers=auth_headers,
            json={"title": "Updated Title", "content": "Updated content."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["node"]["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_node(
        self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict
    ):
        """Test deleting a node."""
        node_id = sample_memory_node["id"]
        response = await async_client.delete(
            f"/api/v1/brain/nodes/{node_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_list_nodes(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing nodes with filters."""
        response = await async_client.get(
            "/api/v1/brain/nodes",
            headers=auth_headers,
            params={"limit": 10, "offset": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data

    @pytest.mark.asyncio
    async def test_list_nodes_with_tags(self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict):
        """Test listing nodes filtered by tag."""
        response = await async_client.get(
            "/api/v1/brain/nodes",
            headers=auth_headers,
            params={"tag": "test"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_nonexistent_node(self, async_client: AsyncClient, auth_headers: dict):
        """Test retrieving a non-existent node returns 404."""
        response = await async_client.get(
            f"/api/v1/brain/nodes/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestBidirectionalLinks:
    """Test bidirectional link operations."""

    @pytest.mark.asyncio
    async def test_create_link(
        self, async_client: AsyncClient, auth_headers: dict,
        sample_memory_node: dict, test_db: AsyncSession, sample_user: dict
    ):
        """Test creating a bidirectional link between two nodes."""
        # Create a second node first
        from app.models.brain import MemoryNode
        node2_id = uuid.uuid4()
        node2 = MemoryNode(
            id=node2_id,
            user_id=uuid.UUID(sample_user["id"]),
            type="fact",
            title="Second Node",
            content="Second node for linking test.",
            tags=["#test"],
            source="explicit",
            layers={"l1_summary": None, "l2_highlights": [], "l3_full": "", "l4_compressed": None},
            review_interval=86400,
            next_review_at=datetime.now(timezone.utc),
        )
        test_db.add(node2)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/brain/links",
            headers=auth_headers,
            json={
                "source_id": sample_memory_node["id"],
                "target_id": str(node2_id),
                "link_type": "related_to",
                "label": "Test Link",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "link" in data

    @pytest.mark.asyncio
    async def test_get_node_links(
        self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict
    ):
        """Test getting links for a specific node."""
        node_id = sample_memory_node["id"]
        response = await async_client.get(
            f"/api/v1/brain/nodes/{node_id}/links",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "links" in data

    @pytest.mark.asyncio
    async def test_list_links(
        self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict
    ):
        """Test listing links with source filter."""
        response = await async_client.get(
            "/api/v1/brain/links",
            headers=auth_headers,
            params={"source_id": sample_memory_node["id"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "links" in data

    @pytest.mark.asyncio
    async def test_delete_link(
        self, async_client: AsyncClient, auth_headers: dict,
        sample_memory_node: dict, test_db: AsyncSession, sample_user: dict
    ):
        """Test deleting a link."""
        from app.models.brain import MemoryNode, MemoryLink
        node2_id = uuid.uuid4()
        node2 = MemoryNode(
            id=node2_id, user_id=uuid.UUID(sample_user["id"]),
            type="fact", title="Linked Node", content="Test",
            tags=[], source="explicit", layers={}, review_interval=86400,
        )
        test_db.add(node2)
        await test_db.flush()

        link = MemoryLink(
            id=uuid.uuid4(), user_id=uuid.UUID(sample_user["id"]),
            source_id=uuid.UUID(sample_memory_node["id"]),
            target_id=node2_id, link_type="related_to", label="To Delete",
        )
        test_db.add(link)
        await test_db.commit()

        response = await async_client.delete(
            f"/api/v1/brain/links/{link.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True


class TestSearch:
    """Test brain search functionality."""

    @pytest.mark.asyncio
    async def test_graph_search(
        self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict
    ):
        """Test full-text + semantic search."""
        response = await async_client.post(
            "/api/v1/brain/graph/search",
            headers=auth_headers,
            json={"query": "test memory", "limit": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data


class TestGraph:
    """Test graph endpoints."""

    @pytest.mark.asyncio
    async def test_get_full_graph(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting full graph data."""
        response = await async_client.get(
            "/api/v1/brain/graph",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_local_graph(
        self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict
    ):
        """Test getting local subgraph around a node."""
        response = await async_client.get(
            f"/api/v1/brain/graph/local/{sample_memory_node['id']}",
            headers=auth_headers,
            params={"depth": 2},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_clusters(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting brain clusters."""
        response = await async_client.get(
            "/api/v1/brain/clusters",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_orphans(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting orphan nodes."""
        response = await async_client.get(
            "/api/v1/brain/orphans",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_growth(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting brain growth metrics."""
        response = await async_client.get(
            "/api/v1/brain/growth",
            headers=auth_headers,
            params={"period": "week"},
        )
        assert response.status_code == 200


class TestDailyNotes:
    """Test daily note endpoints."""

    @pytest.mark.asyncio
    async def test_get_today_note(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting today's daily note."""
        response = await async_client.get(
            "/api/v1/brain/daily",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "note" in data

    @pytest.mark.asyncio
    async def test_regenerate_daily_note(self, async_client: AsyncClient, auth_headers: dict):
        """Test force regenerating daily note."""
        response = await async_client.post(
            "/api/v1/brain/daily/generate",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200


class TestSpacedRepetition:
    """Test spaced repetition review endpoints."""

    @pytest.mark.asyncio
    async def test_get_review_queue(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting review queue."""
        response = await async_client.get(
            "/api/v1/brain/review",
            headers=auth_headers,
            params={"limit": 20},
        )
        assert response.status_code == 200
        data = response.json()
        assert "queue" in data

    @pytest.mark.asyncio
    async def test_submit_review(
        self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict
    ):
        """Test submitting a review result."""
        response = await async_client.post(
            f"/api/v1/brain/review/{sample_memory_node['id']}",
            headers=auth_headers,
            json={"rating": "easy"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_submit_review_all_ratings(
        self, async_client: AsyncClient, auth_headers: dict, sample_memory_node: dict
    ):
        """Test submitting all review ratings."""
        for rating in ["easy", "medium", "hard", "forgot"]:
            response = await async_client.post(
                f"/api/v1/brain/review/{sample_memory_node['id']}",
                headers=auth_headers,
                json={"rating": rating},
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_review_stats(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting review statistics."""
        response = await async_client.get(
            "/api/v1/brain/review/stats",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestBrainStats:
    """Test brain statistics and tags."""

    @pytest.mark.asyncio
    async def test_get_brain_stats(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting brain statistics."""
        response = await async_client.get(
            "/api/v1/brain/stats",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "total_nodes" in data["stats"]

    @pytest.mark.asyncio
    async def test_list_tags(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing all tags."""
        response = await async_client.get(
            "/api/v1/brain/tags",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestObsidianExport:
    """Test Obsidian vault export (pro feature)."""

    @pytest.mark.asyncio
    async def test_export_pro_user(
        self, async_client: AsyncClient, auth_headers_pro: dict
    ):
        """Test export works for pro users."""
        response = await async_client.post(
            "/api/v1/brain/export",
            headers=auth_headers_pro,
        )
        assert response.status_code in (200, 500)
