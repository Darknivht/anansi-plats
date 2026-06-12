"""
Anansi Outlook / Office 365 Connector — Send/receive email, calendar via Microsoft Graph.

Auth: OAuth 2.0 via Microsoft Identity Platform (Azure AD).
Scopes: Mail.Read, Mail.Send, Calendars.Read, User.Read, offline_access
Docs: https://learn.microsoft.com/en-us/graph/api/overview
"""

from __future__ import annotations

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, ClassVar

from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class OutlookConnector(BaseConnector):
    """Connect to Outlook / Office 365 — email and calendar via Microsoft Graph."""

    key: ClassVar[str] = "outlook"
    name: ClassVar[str] = "Outlook / Office 365"
    description: ClassVar[str] = "Send and receive email, manage calendar via Microsoft Graph."
    icon_url: ClassVar[str] = "/icons/outlook.svg"
    category: ClassVar[str] = "communication"
    auth_type: ClassVar[str] = "oauth2"
    auth_url: ClassVar[str] = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    token_url: ClassVar[str] = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    api_base_url: ClassVar[str] = "https://graph.microsoft.com/v1.0"
    scopes: ClassVar[list[str]] = [
        "Mail.Read",
        "Mail.Send",
        "Calendars.Read",
        "User.Read",
        "offline_access",
    ]

    async def test_connection(self) -> bool:
        """Verify Outlook connection by fetching current user."""
        try:
            client = await self._get_client()
            resp = await client.get("/me")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Outlook connection test failed", error=str(exc))
            return False

    # ── User ────────────────────────────────────────────────────────────────

    async def get_me(self) -> dict[str, Any]:
        """Get the authenticated user's profile."""
        client = await self._get_client()
        resp = await client.get("/me")
        resp.raise_for_status()
        return resp.json()

    # ── Email ───────────────────────────────────────────────────────────────

    async def list_messages(
        self,
        folder_id: str = "inbox",
        top: int = 20,
        filter_: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """List email messages in a folder.

        Args:
            folder_id: Folder ID ('inbox', 'sentitems', 'drafts', 'archive', or folder ID).
            top: Max results (1-1000).
            filter_: OData filter string.
            search: Search query string.

        Returns:
            List of message objects.
        """
        params: dict[str, Any] = {"$top": min(top, 1000)}
        if filter_:
            params["$filter"] = filter_
        if search:
            params["$search"] = f'"{search}"'

        client = await self._get_client()
        resp = await client.get(f"/me/mailFolders/{folder_id}/messages", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("value", [])

    async def get_message(self, message_id: str) -> dict[str, Any]:
        """Get a single email message.

        Args:
            message_id: Outlook message ID.

        Returns:
            Full message data.
        """
        client = await self._get_client()
        resp = await client.get(f"/me/messages/{message_id}")
        resp.raise_for_status()
        return resp.json()

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
        is_html: bool = False,
    ) -> dict[str, Any]:
        """Send an email via Outlook.

        Args:
            to: Recipient email address(es), semicolon-separated.
            subject: Email subject.
            body: Plain text or HTML body.
            cc: CC recipients.
            is_html: If True, body is HTML.

        Returns:
            API response.
        """
        recipients = [{"emailAddress": {"address": addr.strip()}} for addr in to.split(";")]

        message: dict[str, Any] = {
            "subject": subject,
            "toRecipients": recipients,
            "body": {
                "contentType": "HTML" if is_html else "Text",
                "content": body,
            },
        }

        if cc:
            message["ccRecipients"] = [
                {"emailAddress": {"address": addr.strip()}}
                for addr in cc.split(";")
            ]

        client = await self._get_client()
        resp = await client.post("/me/sendMail", json={"message": message})
        resp.raise_for_status()
        return {"status": "sent", "message": message}

    async def list_folders(self) -> list[dict[str, Any]]:
        """List all mail folders."""
        client = await self._get_client()
        resp = await client.get("/me/mailFolders")
        resp.raise_for_status()
        data = resp.json()
        return data.get("value", [])

    # ── Calendar ────────────────────────────────────────────────────────────

    async def list_events(
        self,
        top: int = 20,
        start_datetime: str | None = None,
        end_datetime: str | None = None,
    ) -> list[dict[str, Any]]:
        """List calendar events.

        Args:
            top: Max results (1-1000).
            start_datetime: ISO 8601 start time.
            end_datetime: ISO 8601 end time.

        Returns:
            List of event objects.
        """
        params: dict[str, Any] = {"$top": min(top, 1000)}
        if start_datetime and end_datetime:
            params["$filter"] = (
                f"start/dateTime ge '{start_datetime}' and end/dateTime le '{end_datetime}'"
            )

        client = await self._get_client()
        resp = await client.get("/me/events", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("value", [])

    async def create_event(
        self,
        subject: str,
        start: dict[str, str],
        end: dict[str, str],
        body: str | None = None,
        attendees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a calendar event.

        Args:
            subject: Event title.
            start: {'dateTime': '2024-01-01T09:00:00', 'timeZone': 'UTC'}.
            end: {'dateTime': '2024-01-01T10:00:00', 'timeZone': 'UTC'}.
            body: Optional description.
            attendees: List of email addresses.

        Returns:
            Created event data.
        """
        event: dict[str, Any] = {
            "subject": subject,
            "start": start,
            "end": end,
        }
        if body:
            event["body"] = {"contentType": "text", "content": body}
        if attendees:
            event["attendees"] = [
                {"emailAddress": {"address": email}} for email in attendees
            ]

        client = await self._get_client()
        resp = await client.post("/me/events", json=event)
        resp.raise_for_status()
        return resp.json()

    async def get_today_agenda(self) -> list[dict[str, Any]]:
        """Get all events for today."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(hours=23, minutes=59, seconds=59)

        return await self.list_events(
            top=50,
            start_datetime=day_start.isoformat(),
            end_datetime=day_end.isoformat(),
        )
