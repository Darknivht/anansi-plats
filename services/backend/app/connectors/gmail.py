"""
Anansi Gmail Connector — Send, read, search emails; manage drafts and labels.

Scopes:
    - https://www.googleapis.com/auth/gmail.readonly
    - https://www.googleapis.com/auth/gmail.send
    - https://www.googleapis.com/auth/gmail.modify
    - https://www.googleapis.com/auth/gmail.labels
"""

from __future__ import annotations

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, ClassVar

from structlog import get_logger

from app.connectors import register_connector
from app.connectors.google_base import GoogleBaseConnector

logger = get_logger(__name__)


@register_connector
class GmailConnector(GoogleBaseConnector):
    """Connect to Gmail API — read, search, send emails, manage drafts/labels."""

    key: ClassVar[str] = "gmail"
    name: ClassVar[str] = "Gmail"
    description: ClassVar[str] = "Send, read, and search emails. Manage drafts and labels."
    icon_url: ClassVar[str] = "/icons/gmail.svg"
    category: ClassVar[str] = "communication"
    scopes: ClassVar[list[str]] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels",
    ]

    async def test_connection(self) -> bool:
        """Verify Gmail connection by fetching the user's profile."""
        try:
            client = await self._get_client()
            resp = await client.get("/gmail/v1/users/me/profile")
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("emailAddress"))
        except Exception as exc:
            logger.warning("Gmail connection test failed", error=str(exc))
            return False

    # ── Email operations ────────────────────────────────────────────────────

    async def list_messages(
        self,
        query: str = "",
        max_results: int = 20,
        label_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List email messages matching a search query.

        Args:
            query: Gmail search syntax (same as web search).
            max_results: Maximum messages to return (1-500).
            label_ids: Only return messages with these labels.

        Returns:
            List of message summaries (id, threadId, snippet).
        """
        params: dict[str, Any] = {
            "maxResults": min(max_results, 500),
        }
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = ",".join(label_ids)

        client = await self._get_client()
        resp = await client.get("/gmail/v1/users/me/messages", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("messages", [])

    async def get_message(self, message_id: str, format: str = "full") -> dict[str, Any]:
        """Get a single email message with full content.

        Args:
            message_id: Gmail message ID.
            format: 'full', 'metadata', 'minimal', or 'raw'.

        Returns:
            Full message data including headers, body parts, and attachments.
        """
        client = await self._get_client()
        resp = await client.get(
            f"/gmail/v1/users/me/messages/{message_id}",
            params={"format": format},
        )
        resp.raise_for_status()
        return resp.json()

    async def search_emails(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search emails with full content using Gmail query syntax.

        Args:
            query: Gmail search query (e.g. 'from:alice@example.com after:2024/1/1').
            max_results: Maximum results to return.

        Returns:
            List of email messages with full content.
        """
        messages = await self.list_messages(query=query, max_results=max_results)
        results = []
        for msg in messages:
            full = await self.get_message(msg["id"])
            results.append(self._parse_message(full))
        return results

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
        bcc: str | None = None,
        is_html: bool = False,
    ) -> dict[str, Any]:
        """Send an email via Gmail.

        Args:
            to: Recipient email address(es), comma-separated.
            subject: Email subject line.
            body: Email body text (plain text or HTML).
            cc: CC recipients, comma-separated.
            bcc: BCC recipients, comma-separated.
            is_html: If True, body is treated as HTML.

        Returns:
            Sent message data including the Gmail message ID.
        """
        mime_message = MIMEMultipart("alternative")
        mime_message["To"] = to
        mime_message["Subject"] = subject
        if cc:
            mime_message["Cc"] = cc
        subtype = "html" if is_html else "plain"
        mime_message.attach(MIMEText(body, subtype))

        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

        client = await self._get_client()
        resp = await client.post(
            "/gmail/v1/users/me/messages/send",
            json={"raw": raw},
        )
        resp.raise_for_status()
        return resp.json()

    async def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
    ) -> dict[str, Any]:
        """Create an email draft.

        Args:
            to: Recipient email address(es).
            subject: Email subject.
            body: Email body text.
            cc: CC recipients.

        Returns:
            Draft data including the draft ID.
        """
        mime_message = MIMEMultipart("alternative")
        mime_message["To"] = to
        mime_message["Subject"] = subject
        if cc:
            mime_message["Cc"] = cc
        mime_message.attach(MIMEText(body, "plain"))
        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

        client = await self._get_client()
        resp = await client.post(
            "/gmail/v1/users/me/drafts",
            json={"message": {"raw": raw}},
        )
        resp.raise_for_status()
        return resp.json()

    async def list_drafts(self, max_results: int = 20) -> list[dict[str, Any]]:
        """List all drafts.

        Args:
            max_results: Maximum drafts to return.

        Returns:
            List of draft summaries.
        """
        client = await self._get_client()
        resp = await client.get(
            "/gmail/v1/users/me/drafts",
            params={"maxResults": min(max_results, 500)},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("drafts", [])

    async def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft.

        Args:
            draft_id: Gmail draft ID.

        Returns:
            True if deleted successfully.
        """
        client = await self._get_client()
        resp = await client.delete(f"/gmail/v1/users/me/drafts/{draft_id}")
        return resp.status_code == 204

    # ── Labels ──────────────────────────────────────────────────────────────

    async def list_labels(self) -> list[dict[str, Any]]:
        """List all Gmail labels for the user.

        Returns:
            List of labels with id, name, type, and color info.
        """
        client = await self._get_client()
        resp = await client.get("/gmail/v1/users/me/labels")
        resp.raise_for_status()
        data = resp.json()
        return data.get("labels", [])

    async def create_label(self, name: str, label_list_visibility: str = "labelShow") -> dict[str, Any]:
        """Create a new Gmail label.

        Args:
            name: Display name for the label.
            label_list_visibility: 'labelShow' or 'labelHide'.

        Returns:
            Created label data.
        """
        client = await self._get_client()
        resp = await client.post(
            "/gmail/v1/users/me/labels",
            json={"name": name, "labelListVisibility": label_list_visibility, "messageListVisibility": "show"},
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_label(self, label_id: str) -> bool:
        """Delete a label.

        Args:
            label_id: Gmail label ID.

        Returns:
            True if deleted.
        """
        client = await self._get_client()
        resp = await client.delete(f"/gmail/v1/users/me/labels/{label_id}")
        return resp.status_code == 204

    async def modify_message_labels(
        self,
        message_id: str,
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add/remove labels on a message.

        Args:
            message_id: Gmail message ID.
            add_label_ids: Label IDs to add.
            remove_label_ids: Label IDs to remove.

        Returns:
            Updated message data.
        """
        body: dict[str, Any] = {}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids

        client = await self._get_client()
        resp = await client.post(
            f"/gmail/v1/users/me/messages/{message_id}/modify",
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_message(msg: dict[str, Any]) -> dict[str, Any]:
        """Extract useful fields from a raw Gmail message."""
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        return {
            "id": msg["id"],
            "thread_id": msg.get("threadId"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "cc": headers.get("Cc", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "label_ids": msg.get("labelIds", []),
            "internal_date": msg.get("internalDate"),
            "has_attachments": any(
                part.get("filename")
                for part in msg.get("payload", {}).get("parts", [msg.get("payload", {})])
                if part.get("filename")
            ),
        }
