"""
Anansi WhatsApp Business Connector — Send/receive messages, manage templates.

Auth: WhatsApp Business API Token (API key-based).
Uses the WhatsApp Cloud API (graph.facebook.com).

Note: This is used by agents to send WhatsApp messages on behalf of
the linked business account.
"""

from __future__ import annotations

from typing import Any, ClassVar

from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class WhatsAppConnector(BaseConnector):
    """Connect to WhatsApp Business API — send/receive messages."""

    key: ClassVar[str] = "whatsapp"
    name: ClassVar[str] = "WhatsApp Business"
    description: ClassVar[str] = "Send and receive WhatsApp messages, manage templates."
    icon_url: ClassVar[str] = "/icons/whatsapp.svg"
    category: ClassVar[str] = "communication"
    auth_type: ClassVar[str] = "apikey"
    api_base_url: ClassVar[str] = "https://graph.facebook.com/v22.0"

    def _inject_auth_headers(self, headers: dict[str, str]) -> None:
        api_key = self._auth_data.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

    async def test_connection(self) -> bool:
        """Verify WhatsApp connection by fetching business profile."""
        try:
            phone_id = self._auth_data.get("phone_number_id", "")
            if not phone_id:
                return False
            client = await self._get_client()
            resp = await client.get(f"/{phone_id}")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("WhatsApp connection test failed", error=str(exc))
            return False

    # ── Messages ────────────────────────────────────────────────────────────

    async def send_text(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> dict[str, Any]:
        """Send a text message.

        Args:
            to: Recipient phone number (E.164 format).
            text: Message text.
            preview_url: Show URL preview.

        Returns:
            API response with message ID.
        """
        phone_id = self._auth_data.get("phone_number_id", "")
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": preview_url, "body": text},
        }
        client = await self._get_client()
        resp = await client.post(f"/{phone_id}/messages", json=body)
        resp.raise_for_status()
        return resp.json()

    async def send_template(
        self,
        to: str,
        template_name: str,
        language: str = "en",
        components: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send a message template.

        Args:
            to: Recipient phone number.
            template_name: Name of the approved template.
            language: Language code.
            components: Template components (header, body, buttons).

        Returns:
            API response.
        """
        phone_id = self._auth_data.get("phone_number_id", "")
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
            },
        }
        if components:
            body["template"]["components"] = components

        client = await self._get_client()
        resp = await client.post(f"/{phone_id}/messages", json=body)
        resp.raise_for_status()
        return resp.json()

    async def send_image(
        self,
        to: str,
        image_url: str,
        caption: str | None = None,
    ) -> dict[str, Any]:
        """Send an image message.

        Args:
            to: Recipient phone number.
            image_url: Public URL of the image.
            caption: Optional caption.

        Returns:
            API response.
        """
        phone_id = self._auth_data.get("phone_number_id", "")
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": {"link": image_url},
        }
        if caption:
            body["image"]["caption"] = caption

        client = await self._get_client()
        resp = await client.post(f"/{phone_id}/messages", json=body)
        resp.raise_for_status()
        return resp.json()

    async def send_document(
        self,
        to: str,
        document_url: str,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Send a document message.

        Args:
            to: Recipient phone number.
            document_url: Public URL of the document.
            filename: Display filename.

        Returns:
            API response.
        """
        phone_id = self._auth_data.get("phone_number_id", "")
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": {"link": document_url},
        }
        if filename:
            body["document"]["filename"] = filename

        client = await self._get_client()
        resp = await client.post(f"/{phone_id}/messages", json=body)
        resp.raise_for_status()
        return resp.json()

    # ── Media ───────────────────────────────────────────────────────────────

    async def upload_media(self, file_url: str, mime_type: str) -> dict[str, Any]:
        """Upload media to WhatsApp servers.

        Args:
            file_url: Public URL of the file.
            mime_type: MIME type.

        Returns:
            Upload response with media ID.
        """
        phone_id = self._auth_data.get("phone_number_id", "")
        body = {
            "messaging_product": "whatsapp",
            "file": file_url,
            "type": mime_type,
        }
        client = await self._get_client()
        resp = await client.post(f"/{phone_id}/media", json=body)
        resp.raise_for_status()
        return resp.json()

    # ── Business Profile ────────────────────────────────────────────────────

    async def get_business_profile(self) -> dict[str, Any]:
        """Get the WhatsApp Business profile."""
        phone_id = self._auth_data.get("phone_number_id", "")
        client = await self._get_client()
        resp = await client.get(
            f"/{phone_id}/whatsapp_business_profile",
            params={"fields": "about,address,description,email,profile_picture_url,websites"},
        )
        resp.raise_for_status()
        return resp.json()
