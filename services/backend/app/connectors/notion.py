"""
Anansi Notion Connector — Read, create, update pages and databases.

Scopes:
    - Notion API internal integration token
    - Read, insert, update, and search capabilities

Auth: Uses Notion Internal Integration Secret (API key stored as token).
"""

from __future__ import annotations

from typing import Any, ClassVar

from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class NotionConnector(BaseConnector):
    """Connect to Notion — read/create/update pages and databases."""

    key: ClassVar[str] = "notion"
    name: ClassVar[str] = "Notion"
    description: ClassVar[str] = "Read, create, and update pages and databases."
    icon_url: ClassVar[str] = "/icons/notion.svg"
    category: ClassVar[str] = "productivity"
    auth_type: ClassVar[str] = "apikey"
    api_base_url: ClassVar[str] = "https://api.notion.com/v1"

    # Notion uses API key (Internal Integration Token) in Authorization header
    def _inject_auth_headers(self, headers: dict[str, str]) -> None:
        api_key = self._auth_data.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        headers["Notion-Version"] = "2022-06-28"

    async def test_connection(self) -> bool:
        """Verify Notion connection by fetching user/bot info."""
        try:
            client = await self._get_client()
            resp = await client.get("/users/me")
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("id"))
        except Exception as exc:
            logger.warning("Notion connection test failed", error=str(exc))
            return False

    async def validate_api_key(self, api_key: str) -> dict[str, Any]:
        """Validate a Notion integration token."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.api_base_url}/users/me", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return {"valid": True, "details": {"bot_name": data.get("name", "")}}
            return {"valid": False, "details": {"error": resp.text}}

    # ── Pages ───────────────────────────────────────────────────────────────

    async def get_page(self, page_id: str) -> dict[str, Any]:
        """Get a Notion page's properties.

        Args:
            page_id: Notion page UUID (with or without hyphens).

        Returns:
            Page object with properties.
        """
        client = await self._get_client()
        resp = await client.get(f"/pages/{page_id}")
        resp.raise_for_status()
        return resp.json()

    async def create_page(
        self,
        parent_page_id: str,
        title: str,
        properties: dict[str, Any] | None = None,
        children: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new Notion page.

        Args:
            parent_page_id: Parent page or database ID.
            title: Page title.
            properties: Additional property values.
            children: Block content for the page.

        Returns:
            Created page object.
        """
        body: dict[str, Any] = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}],
                },
                **(properties or {}),
            },
        }
        if children:
            body["children"] = children

        client = await self._get_client()
        resp = await client.post("/pages", json=body)
        resp.raise_for_status()
        return resp.json()

    async def update_page(
        self,
        page_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a Notion page's properties.

        Args:
            page_id: Page UUID.
            properties: Property values to update.

        Returns:
            Updated page object.
        """
        client = await self._get_client()
        resp = await client.patch(f"/pages/{page_id}", json={"properties": properties})
        resp.raise_for_status()
        return resp.json()

    async def get_page_content(self, page_id: str) -> list[dict[str, Any]]:
        """Get all blocks (content) of a page.

        Args:
            page_id: Page UUID.

        Returns:
            List of block objects.
        """
        client = await self._get_client()
        resp = await client.get(f"/blocks/{page_id}/children")
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])

    # ── Databases ───────────────────────────────────────────────────────────

    async def query_database(
        self,
        database_id: str,
        filter_: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """Query a Notion database.

        Args:
            database_id: Database UUID.
            filter_: Filter conditions.
            sorts: Sort directives.
            page_size: Results per page (1-100).

        Returns:
            Query results with 'results' list.
        """
        body: dict[str, Any] = {"page_size": min(page_size, 100)}
        if filter_:
            body["filter"] = filter_
        if sorts:
            body["sorts"] = sorts

        client = await self._get_client()
        resp = await client.post(f"/databases/{database_id}/query", json=body)
        resp.raise_for_status()
        return resp.json()

    async def get_database(self, database_id: str) -> dict[str, Any]:
        """Get database metadata and schema.

        Args:
            database_id: Database UUID.

        Returns:
            Database object with properties schema.
        """
        client = await self._get_client()
        resp = await client.get(f"/databases/{database_id}")
        resp.raise_for_status()
        return resp.json()

    # ── Search ──────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        sort: dict[str, Any] | None = None,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Search all Notion pages and databases.

        Args:
            query: Search query string.
            sort: Sort options.
            page_size: Results per page.

        Returns:
            Search results.
        """
        body: dict[str, Any] = {
            "query": query,
            "page_size": min(page_size, 100),
        }
        if sort:
            body["sort"] = sort

        client = await self._get_client()
        resp = await client.post("/search", json=body)
        resp.raise_for_status()
        return resp.json()

    # ── Blocks ──────────────────────────────────────────────────────────────

    async def append_block_children(
        self,
        block_id: str,
        children: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Append block children to a parent block or page.

        Args:
            block_id: Parent block or page UUID.
            children: List of block objects to append.

        Returns:
            API response with created blocks.
        """
        client = await self._get_client()
        resp = await client.patch(
            f"/blocks/{block_id}/children",
            json={"children": children},
        )
        resp.raise_for_status()
        return resp.json()
