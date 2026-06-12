"""
Anansi Discord Connector — Send messages, read channels, manage server info.

Auth: Discord Bot Token (API key-based).
Docs: https://discord.com/developers/docs/intro
"""

from __future__ import annotations

from typing import Any, ClassVar

from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class DiscordConnector(BaseConnector):
    """Connect to Discord — send messages, read channels, manage servers."""

    key: ClassVar[str] = "discord"
    name: ClassVar[str] = "Discord"
    description: ClassVar[str] = "Send messages, read channels, and manage server information."
    icon_url: ClassVar[str] = "/icons/discord.svg"
    category: ClassVar[str] = "communication"
    auth_type: ClassVar[str] = "apikey"
    api_base_url: ClassVar[str] = "https://discord.com/api/v10"

    def _inject_auth_headers(self, headers: dict[str, str]) -> None:
        api_key = self._auth_data.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bot {api_key}"

    async def test_connection(self) -> bool:
        """Verify Discord connection by fetching current user (bot)."""
        try:
            client = await self._get_client()
            resp = await client.get("/users/@me")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Discord connection test failed", error=str(exc))
            return False

    async def validate_api_key(self, api_key: str) -> dict[str, Any]:
        """Validate a Discord bot token."""
        headers = {"Authorization": f"Bot {api_key}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.api_base_url}/users/@me", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return {"valid": True, "details": {"bot_name": f"{data.get('username', '')}#{data.get('discriminator', '0')}"}}
            return {"valid": False, "details": {"error": resp.text}}

    # ── Guilds (Servers) ────────────────────────────────────────────────────

    async def get_current_guilds(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get list of guilds the bot is in.

        Args:
            limit: Max guilds (1-200).

        Returns:
            List of guild objects.
        """
        client = await self._get_client()
        resp = await client.get("/users/@me/guilds", params={"limit": min(limit, 200)})
        resp.raise_for_status()
        return resp.json()

    # ── Channels ────────────────────────────────────────────────────────────

    async def get_channel(self, channel_id: str) -> dict[str, Any]:
        """Get channel info."""
        client = await self._get_client()
        resp = await client.get(f"/channels/{channel_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_channel_messages(
        self,
        channel_id: str,
        limit: int = 50,
        around: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get messages from a channel.

        Args:
            channel_id: Discord channel ID.
            limit: Max messages (1-100).
            around: Get messages around this message ID.

        Returns:
            List of message objects.
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if around:
            params["around"] = around

        client = await self._get_client()
        resp = await client.get(f"/channels/{channel_id}/messages", params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Messages ────────────────────────────────────────────────────────────

    async def send_message(
        self,
        channel_id: str,
        content: str,
        tts: bool = False,
        embeds: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send a message to a channel.

        Args:
            channel_id: Discord channel ID.
            content: Message text (up to 2000 chars).
            tts: Text-to-speech.
            embeds: Rich embed objects.

        Returns:
            Created message object.
        """
        body: dict[str, Any] = {
            "content": content,
            "tts": tts,
        }
        if embeds:
            body["embeds"] = embeds

        client = await self._get_client()
        resp = await client.post(f"/channels/{channel_id}/messages", json=body)
        resp.raise_for_status()
        return resp.json()

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
    ) -> dict[str, Any]:
        """Edit a message."""
        client = await self._get_client()
        resp = await client.patch(
            f"/channels/{channel_id}/messages/{message_id}",
            json={"content": content},
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_message(self, channel_id: str, message_id: str) -> bool:
        """Delete a message."""
        client = await self._get_client()
        resp = await client.delete(f"/channels/{channel_id}/messages/{message_id}")
        return resp.status_code == 204

    async def send_embed(
        self,
        channel_id: str,
        title: str,
        description: str,
        color: int = 0x00AE86,
        fields: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send a rich embed message.

        Args:
            channel_id: Discord channel ID.
            title: Embed title.
            description: Embed description.
            color: Embed color hex (decimal).
            fields: Embed fields (name, value, inline).

        Returns:
            Created message object.
        """
        embed: dict[str, Any] = {
            "title": title,
            "description": description,
            "color": color,
        }
        if fields:
            embed["fields"] = fields

        return await self.send_message(channel_id, content="", embeds=[embed])

    # ── Guild Members ───────────────────────────────────────────────────────

    async def get_guild_members(
        self,
        guild_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get guild members.

        Args:
            guild_id: Guild ID.
            limit: Max members (1-1000).

        Returns:
            List of member objects.
        """
        client = await self._get_client()
        resp = await client.get(f"/guilds/{guild_id}/members", params={"limit": min(limit, 1000)})
        resp.raise_for_status()
        return resp.json()
