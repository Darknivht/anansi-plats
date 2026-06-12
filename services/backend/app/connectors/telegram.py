"""
Anansi Telegram Connector — Send/receive messages, manage bots.

Auth: Telegram Bot Token (API key-based).
Docs: https://core.telegram.org/bots/api
"""

from __future__ import annotations

from typing import Any, ClassVar

from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class TelegramConnector(BaseConnector):
    """Connect to Telegram Bot API — send/receive messages, manage bot."""

    key: ClassVar[str] = "telegram"
    name: ClassVar[str] = "Telegram"
    description: ClassVar[str] = "Send and receive messages via a Telegram bot."
    icon_url: ClassVar[str] = "/icons/telegram.svg"
    category: ClassVar[str] = "communication"
    auth_type: ClassVar[str] = "apikey"

    # Dynamic base URL: https://api.telegram.org/bot<TOKEN>/<method>
    api_base_url: ClassVar[str] = "https://api.telegram.org"

    async def _bot_url(self, method: str) -> str:
        token = self._auth_data.get("api_key", "")
        return f"{self.api_base_url}/bot{token}/{method}"

    def _inject_auth_headers(self, headers: dict[str, str]) -> None:
        # Telegram uses token in the URL, not headers
        pass

    async def _get_client(self) -> httpx.AsyncClient:
        """Override: use a client without base_url since bot token is in path."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def test_connection(self) -> bool:
        """Verify Telegram connection by calling getMe."""
        try:
            client = await self._get_client()
            url = await self._bot_url("getMe")
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data.get("ok", False)
        except Exception as exc:
            logger.warning("Telegram connection test failed", error=str(exc))
            return False

    async def validate_api_key(self, api_key: str) -> dict[str, Any]:
        """Validate a Telegram bot token."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.api_base_url}/bot{api_key}/getMe")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    bot_info = data.get("result", {})
                    return {
                        "valid": True,
                        "details": {
                            "bot_name": bot_info.get("first_name", ""),
                            "username": bot_info.get("username", ""),
                        },
                    }
            return {"valid": False, "details": {"error": resp.text}}

    # ── Messages ────────────────────────────────────────────────────────────

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = False,
        reply_to_message_id: int | None = None,
    ) -> dict[str, Any]:
        """Send a text message.

        Args:
            chat_id: Chat ID (or @username for public chats).
            text: Message text.
            parse_mode: 'Markdown', 'HTML', or ''.
            disable_web_page_preview: Disable link previews.
            reply_to_message_id: Reply to a specific message.

        Returns:
            API response with sent message.
        """
        body: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_to_message_id is not None:
            body["reply_to_message_id"] = reply_to_message_id

        client = await self._get_client()
        url = await self._bot_url("sendMessage")
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        return resp.json()

    async def edit_message(
        self,
        chat_id: str,
        message_id: int,
        text: str,
        parse_mode: str = "Markdown",
    ) -> dict[str, Any]:
        """Edit a message.

        Args:
            chat_id: Chat ID.
            message_id: Message ID to edit.
            text: New text.
            parse_mode: Parse mode.

        Returns:
            API response.
        """
        body = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        client = await self._get_client()
        url = await self._bot_url("editMessageText")
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        return resp.json()

    async def delete_message(self, chat_id: str, message_id: int) -> bool:
        """Delete a message."""
        client = await self._get_client()
        url = await self._bot_url("deleteMessage")
        resp = await client.post(url, json={"chat_id": chat_id, "message_id": message_id})
        return resp.status_code == 200

    async def send_sticker(self, chat_id: str, sticker: str) -> dict[str, Any]:
        """Send a sticker by file_id or URL."""
        body = {"chat_id": chat_id, "sticker": sticker}
        client = await self._get_client()
        url = await self._bot_url("sendSticker")
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        return resp.json()

    # ── Bot Info ────────────────────────────────────────────────────────────

    async def get_me(self) -> dict[str, Any]:
        """Get bot information."""
        client = await self._get_client()
        url = await self._bot_url("getMe")
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", {})

    async def get_updates(
        self,
        offset: int | None = None,
        limit: int = 100,
        timeout: int = 0,
    ) -> list[dict[str, Any]]:
        """Get incoming updates (messages, callbacks, etc.).

        Args:
            offset: Update ID offset for polling.
            limit: Max updates (1-100).
            timeout: Long polling timeout (seconds).

        Returns:
            List of update objects.
        """
        params: dict[str, Any] = {"limit": min(limit, 100), "timeout": timeout}
        if offset is not None:
            params["offset"] = offset

        client = await self._get_client()
        url = await self._bot_url("getUpdates")
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", [])

    # ── Chat ────────────────────────────────────────────────────────────────

    async def get_chat(self, chat_id: str) -> dict[str, Any]:
        """Get chat info."""
        client = await self._get_client()
        url = await self._bot_url("getChat")
        resp = await client.get(url, params={"chat_id": chat_id})
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", {})

    async def get_chat_member(self, chat_id: str, user_id: int) -> dict[str, Any]:
        """Get information about a chat member."""
        client = await self._get_client()
        url = await self._bot_url("getChatMember")
        resp = await client.get(url, params={"chat_id": chat_id, "user_id": user_id})
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", {})
