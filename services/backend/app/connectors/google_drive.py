"""
Anansi Google Drive Connector — Read, search files; organize folders.

Scopes:
    - https://www.googleapis.com/auth/drive.readonly
    - https://www.googleapis.com/auth/drive.file
"""

from __future__ import annotations

from typing import Any, ClassVar

from structlog import get_logger

from app.connectors import register_connector
from app.connectors.google_base import GoogleBaseConnector

logger = get_logger(__name__)


@register_connector
class GoogleDriveConnector(GoogleBaseConnector):
    """Connect to Google Drive — read, search files, organize folders."""

    key: ClassVar[str] = "google_drive"
    name: ClassVar[str] = "Google Drive"
    description: ClassVar[str] = "Read, search, and organize files and folders."
    icon_url: ClassVar[str] = "/icons/google-drive.svg"
    category: ClassVar[str] = "storage"
    scopes: ClassVar[list[str]] = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
    ]

    async def test_connection(self) -> bool:
        """Verify Drive connection by fetching user's Drive info."""
        try:
            client = await self._get_client()
            resp = await client.get("/drive/v3/about", params={"fields": "user"})
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Drive connection test failed", error=str(exc))
            return False

    # ── Files ───────────────────────────────────────────────────────────────

    async def list_files(
        self,
        query: str = "",
        page_size: int = 20,
        order_by: str = "modifiedTime desc",
        fields: str = "files(id,name,mimeType,size,modifiedTime,iconLink,webViewLink,parents)",
    ) -> list[dict[str, Any]]:
        """List files matching a query.

        Args:
            query: Drive search query (e.g. "name contains 'report'").
            page_size: Results per page (1-1000).
            order_by: Sort order (e.g. 'modifiedTime desc', 'name').
            fields: Fields to return.

        Returns:
            List of file metadata objects.
        """
        params: dict[str, Any] = {
            "pageSize": min(page_size, 1000),
            "orderBy": order_by,
            "fields": f"nextPageToken,{fields}",
        }
        if query:
            params["q"] = query

        client = await self._get_client()
        resp = await client.get("/drive/v3/files", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("files", [])

    async def get_file(self, file_id: str) -> dict[str, Any]:
        """Get metadata for a specific file.

        Args:
            file_id: Drive file ID.

        Returns:
            File metadata.
        """
        client = await self._get_client()
        resp = await client.get(
            f"/drive/v3/files/{file_id}",
            params={"fields": "id,name,mimeType,size,modifiedTime,createdTime,webViewLink,owners,description"},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_file_content(self, file_id: str, mime_type: str = "text/plain") -> str:
        """Export or download file content as text.

        Args:
            file_id: Drive file ID.
            mime_type: Desired export MIME type (e.g. 'text/plain', 'text/markdown').

        Returns:
            File content as a string.
        """
        client = await self._get_client()
        # Use export for Google-native formats, download for others
        resp = await client.get(
            f"/drive/v3/files/{file_id}/export",
            params={"mimeType": mime_type},
        )
        resp.raise_for_status()
        return resp.text

    async def search_files(self, query: str, max_results: int = 20) -> list[dict[str, Any]]:
        """Search files across Drive.

        Args:
            query: Full-text search query.
            max_results: Maximum results.

        Returns:
            List of matching files.
        """
        escaped_query = query.replace("'", "\\'")
        search_query = f"fullText contains '{escaped_query}'"
        return await self.list_files(query=search_query, page_size=max_results)

    # ── Folders ─────────────────────────────────────────────────────────────

    async def list_folder_contents(self, folder_id: str = "root", page_size: int = 50) -> list[dict[str, Any]]:
        """List files and folders inside a folder.

        Args:
            folder_id: Folder ID ("root" for root folder).
            page_size: Max results.

        Returns:
            List of files/folders in the folder.
        """
        return await self.list_files(
            query=f"'{folder_id}' in parents and trashed=false",
            page_size=page_size,
        )

    async def create_folder(self, name: str, parent_id: str | None = None) -> dict[str, Any]:
        """Create a new folder.

        Args:
            name: Folder name.
            parent_id: Parent folder ID (None for root).

        Returns:
            Created folder metadata.
        """
        body: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            body["parents"] = [parent_id]

        client = await self._get_client()
        resp = await client.post("/drive/v3/files", json=body)
        resp.raise_for_status()
        return resp.json()
