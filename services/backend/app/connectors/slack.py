"""
Anansi Slack Connector — Post messages, read channels, user info.

Scopes:
    - channels:history
    - channels:read
    - chat:write
    - users:read
    - reactions:read
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class SlackConnector(BaseConnector):
    """Connect to Slack — post messages, read channels, user info."""

    key: ClassVar[str] = "slack"
    name: ClassVar[str] = "Slack"
    description: ClassVar[str] = "Post messages, read channels, and get user info."
    icon_url: ClassVar[str] = "/icons/slack.svg"
    category: ClassVar[str] = "communication"
    auth_type: ClassVar[str] = "oauth2"
    auth_url: ClassVar[str] = "https://slack.com/oauth/v2/authorize"
    token_url: ClassVar[str] = "https://slack.com/api/oauth.v2.access"
    api_base_url: ClassVar[str] = "https://slack.com/api"
    scopes: ClassVar[list[str]] = [
        "channels:history",
        "channels:read",
        "chat:write",
        "users:read",
        "reactions:read",
        "channels:join",
    ]

    async def test_connection(self) -> bool:
        """Verify Slack connection using auth.test."""
        try:
            client = await self._get_client()
            resp = await client.get("/auth.test")
            resp.raise_for_status()
            data = resp.json()
            return data.get("ok", False)
        except Exception as exc:
            logger.warning("Slack connection test failed", error=str(exc))
            return False

    # ── Team info ───────────────────────────────────────────────────────────

    async def get_team_info(self) -> dict[str, Any]:
        """Get information about the connected Slack workspace."""
        client = await self._get_client()
        resp = await client.get("/team.info")
        resp.raise_for_status()
        return resp.json()

    # ── Channels ────────────────────────────────────────────────────────────

    async def list_channels(
        self,
        cursor: str | None = None,
        limit: int = 100,
        exclude_archived: bool = True,
    ) -> dict[str, Any]:
        """List public channels in the workspace.

        Args:
            cursor: Pagination cursor.
            limit: Max channels per page (1-1000).
            exclude_archived: Exclude archived channels.

        Returns:
            Dict with 'channels' list and 'response_metadata'.
        """
        params: dict[str, Any] = {
            "limit": min(limit, 1000),
            "exclude_archived": exclude_archived,
        }
        if cursor:
            params["cursor"] = cursor

        client = await self._get_client()
        resp = await client.get("/conversations.list", params=params)
        resp.raise_for_status()
        return resp.json()

    async def join_channel(self, channel_id: str) -> bool:
        """Join a public channel.

        Args:
            channel_id: Slack channel ID.

        Returns:
            True if joined successfully.
        """
        client = await self._get_client()
        resp = await client.post("/conversations.join", json={"channel": channel_id})
        resp.raise_for_status()
        data = resp.json()
        return data.get("ok", False)

    async def get_channel_history(
        self,
        channel_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Get message history for a channel.

        Args:
            channel_id: Slack channel ID.
            limit: Max messages (1-999).
            cursor: Pagination cursor.

        Returns:
            Dict with 'messages' list and metadata.
        """
        params: dict[str, Any] = {
            "channel": channel_id,
            "limit": min(limit, 999),
        }
        if cursor:
            params["cursor"] = cursor

        client = await self._get_client()
        resp = await client.get("/conversations.history", params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Messages ────────────────────────────────────────────────────────────

    async def post_message(
        self,
        channel: str,
        text: str,
        thread_ts: str | None = None,
        parse: str = "full",
        link_names: bool = True,
        as_user: bool = True,
    ) -> dict[str, Any]:
        """Post a message to a Slack channel.

        Args:
            channel: Channel ID or name.
            text: Message text (supports Markdown-style formatting).
            thread_ts: Thread timestamp to reply in a thread.
            parse: 'full' or 'none'.
            link_names: Linkify channel names and usernames.
            as_user: Post as the authenticated user.

        Returns:
            API response with 'ts' (message timestamp).
        """
        body: dict[str, Any] = {
            "channel": channel,
            "text": text,
            "parse": parse,
            "link_names": link_names,
            "as_user": str(as_user).lower(),
        }
        if thread_ts:
            body["thread_ts"] = thread_ts

        client = await self._get_client()
        resp = await client.post("/chat.postMessage", json=body)
        resp.raise_for_status()
        return resp.json()

    async def post_ephemeral(
        self,
        channel: str,
        user: str,
        text: str,
    ) -> dict[str, Any]:
        """Post an ephemeral message (only visible to one user).

        Args:
            channel: Channel ID.
            user: User ID to show the message to.
            text: Message text.

        Returns:
            API response.
        """
        body = {
            "channel": channel,
            "user": user,
            "text": text,
        }
        client = await self._get_client()
        resp = await client.post("/chat.postEphemeral", json=body)
        resp.raise_for_status()
        return resp.json()

    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
    ) -> dict[str, Any]:
        """Update a previously posted message.

        Args:
            channel: Channel ID.
            ts: Message timestamp.
            text: New message text.

        Returns:
            API response.
        """
        body = {
            "channel": channel,
            "ts": ts,
            "text": text,
        }
        client = await self._get_client()
        resp = await client.post("/chat.update", json=body)
        resp.raise_for_status()
        return resp.json()

    # ── Users ───────────────────────────────────────────────────────────────

    async def list_users(self, cursor: str | None = None, limit: int = 100) -> dict[str, Any]:
        """List all users in the workspace.

        Args:
            cursor: Pagination cursor.
            limit: Max users per page.

        Returns:
            Dict with 'members' list.
        """
        params: dict[str, Any] = {"limit": min(limit, 200)}
        if cursor:
            params["cursor"] = cursor

        client = await self._get_client()
        resp = await client.get("/users.list", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get info about a specific user.

        Args:
            user_id: Slack user ID.

        Returns:
            User profile data.
        """
        client = await self._get_client()
        resp = await client.get("/users.info", params={"user": user_id})
        resp.raise_for_status()
        return resp.json()
