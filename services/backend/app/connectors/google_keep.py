"""
Anansi Google Keep Connector — Read and import notes into Second Brain.

Scopes:
    - https://www.googleapis.com/auth/keep.readonly
    - https://www.googleapis.com/auth/keep

Note: Google Keep API is limited. This connector uses the available
Google Keep API endpoints and supports importing notes into the
Anansi Second Brain as memory nodes.
"""

from __future__ import annotations

from typing import Any, ClassVar

from structlog import get_logger

from app.connectors import register_connector
from app.connectors.google_base import GoogleBaseConnector

logger = get_logger(__name__)


@register_connector
class GoogleKeepConnector(GoogleBaseConnector):
    """Connect to Google Keep — read notes, import into Second Brain."""

    key: ClassVar[str] = "google_keep"
    name: ClassVar[str] = "Google Keep"
    description: ClassVar[str] = "Read and import notes from Google Keep into your Second Brain."
    icon_url: ClassVar[str] = "/icons/google-keep.svg"
    category: ClassVar[str] = "productivity"
    scopes: ClassVar[list[str]] = [
        "https://www.googleapis.com/auth/keep.readonly",
        "https://www.googleapis.com/auth/keep",
    ]

    async def test_connection(self) -> bool:
        """Verify Keep connection by listing notes."""
        try:
            await self.list_notes(max_results=1)
            return True
        except Exception as exc:
            logger.warning("Keep connection test failed", error=str(exc))
            return False

    async def list_notes(
        self,
        max_results: int = 50,
        page_token: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all Keep notes.

        Args:
            max_results: Max notes to return (1-500).
            page_token: Pagination token.

        Returns:
            List of note summaries.
        """
        params: dict[str, Any] = {
            "pageSize": min(max_results, 500),
        }
        if page_token:
            params["pageToken"] = page_token

        client = await self._get_client()
        resp = await client.get("/keep/v1/notes", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("notes", [])

    async def get_note(self, note_id: str) -> dict[str, Any]:
        """Get a single note with full content.

        Args:
            note_id: Keep note ID.

        Returns:
            Full note data including text content, list items, etc.
        """
        client = await self._get_client()
        resp = await client.get(f"/keep/v1/notes/{note_id}")
        resp.raise_for_status()
        return resp.json()

    async def import_to_brain(self, note_id: str) -> dict[str, Any]:
        """Import a Keep note into the Second Brain as a memory node.

        Args:
            note_id: Keep note ID.

        Returns:
            Dict with the imported note content ready for Brain service ingestion.
        """
        note = await self.get_note(note_id)

        # Extract text content from the note
        title = note.get("title", "")
        body = ""

        # Keep notes can have text content or list content
        text_content = note.get("textContent", {})
        list_content = note.get("listContent", {})

        if text_content and "text" in text_content:
            body = text_content["text"]
        elif list_content:
            items = list_content.get("listItems", [])
            lines = []
            for item in items:
                text = item.get("text", "")
                if text:
                    lines.append(f"- {text}")
            body = "\n".join(lines)

        # Build tags from Keep labels
        labels = note.get("labels", [])
        tags = [label.get("name", "").lower().replace(" ", "_") for label in labels if label.get("name")]

        return {
            "title": title or "Untitled Keep Note",
            "content": body,
            "source": "google_keep",
            "source_id": note_id,
            "source_url": note.get("webViewLink", ""),
            "tags": tags + ["#imported/keep"],
            "created_at": note.get("createTime"),
            "updated_at": note.get("updateTime"),
            "is_archived": note.get("isArchived", False),
            "is_pinned": note.get("isPinned", False),
            "color": note.get("color", ""),
        }

    async def list_and_import_all(self, max_results: int = 200) -> list[dict[str, Any]]:
        """List all notes and prepare them for bulk import.

        Args:
            max_results: Max notes to process.

        Returns:
            List of import-ready note dicts.
        """
        notes = await self.list_notes(max_results=max_results)
        results = []
        for note in notes:
            try:
                imported = await self.import_to_brain(note["name"].split("/")[-1])
                results.append(imported)
            except Exception as exc:
                logger.warning("Failed to import Keep note", note_id=note.get("name"), error=str(exc))
                continue
        return results
