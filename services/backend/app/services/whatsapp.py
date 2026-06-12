"""
Anansi WhatsApp Service — Core integration with WhatsApp Cloud API.

Handles number linking via OTP, message sending, template messages,
voice notes, disconnection, and webhook routing.

Uses WhatsApp Cloud API (v22.0) via the graph.facebook.com endpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_db_session
from app.core.exceptions import NotFoundError, ValidationError, ConflictError

logger = get_logger(__name__)


# ─── Schemas ─────────────────────────────────────────────────────────────────────


class WhatsAppLinkResponse(BaseModel):
    """Response after initiating the WhatsApp linking flow."""

    status: str = "pending"
    message: str = "OTP sent to your phone number"
    expires_in: int = 300


class WhatsAppVerifyResponse(BaseModel):
    """Response after OTP verification."""

    status: str = "active"
    message: str = "WhatsApp number linked successfully"


class WhatsAppStatusResponse(BaseModel):
    """Current WhatsApp connection status."""

    connected: bool = False
    phone_number: str | None = None
    status: str = "disconnected"
    verified_at: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class WhatsAppMessageResponse(BaseModel):
    """Response from sending a WhatsApp message."""

    message_id: str | None = None
    status: str = "queued"
    error: str | None = None


class WhatsAppWebhookPayload(BaseModel):
    """Parsed incoming WhatsApp webhook payload."""

    object: str = ""
    entry: list[dict[str, Any]] = Field(default_factory=list)


# ─── Rate Limiter (in-memory, per-number) ────────────────────────────────────────


class _MessageRateLimiter:
    """Simple sliding-window rate limiter for WhatsApp messages.

    Prevents spamming users with too many messages in a short period.
    """

    def __init__(self, max_messages: int = 30, window_seconds: int = 60) -> None:
        self._max = max_messages
        self._window = window_seconds
        self._buckets: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        timestamps = self._buckets.get(key, [])
        # Prune old entries
        timestamps = [t for t in timestamps if now - t < self._window]
        if len(timestamps) >= self._max:
            self._buckets[key] = timestamps
            return False
        timestamps.append(now)
        self._buckets[key] = timestamps
        return True

    def remaining(self, key: str) -> int:
        now = datetime.now(timezone.utc).timestamp()
        timestamps = [t for t in self._buckets.get(key, []) if now - t < self._window]
        return max(0, self._max - len(timestamps))


_message_rate_limiter = _MessageRateLimiter()


# ─── WhatsApp Service ────────────────────────────────────────────────────────────


class WhatsAppService:
    """Core service for WhatsApp Cloud API integration.

    Provides OTP-based number linking, message sending, webhook
    processing, and connection management.
    """

    def __init__(self, db: AsyncSession | None = None) -> None:
        self._db = db
        self._http_client: httpx.AsyncClient | None = None

    # ── HTTP Client ─────────────────────────────────────────────────────────────

    @property
    def client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=settings.whatsapp.base_url,
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._http_client

    @property
    def db(self) -> AsyncSession:
        if self._db is None:
            # Fallback: create a new session (caller should provide one ideally)
            raise RuntimeError("WhatsAppService requires a database session")
        return self._db

    @db.setter
    def db(self, value: AsyncSession) -> None:
        self._db = value

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.whatsapp.api_token}",
            "Content-Type": "application/json",
        }

    def _phone_number_id(self) -> str:
        return settings.whatsapp.phone_number_id

    def _generate_otp(self) -> str:
        """Generate a 6-digit OTP code."""
        return f"{secrets.randbelow(1_000_000):06d}"

    # ── Link Number (Send OTP) ──────────────────────────────────────────────────

    async def link_number(self, user_id: str, phone_number: str) -> WhatsAppLinkResponse:
        """Initiate WhatsApp linking by sending an OTP to the phone number.

        Stores the OTP and phone number in the whatsapp_connections table
        with a 'pending' status.

        Args:
            user_id: The user UUID.
            phone_number: The phone number in international format (e.g., +2348012345678).

        Returns:
            WhatsAppLinkResponse indicating the OTP was sent.

        Raises:
            ConflictError: If the user already has an active connection.
        """
        user_uuid = uuid.UUID(user_id)
        otp = self._generate_otp()
        now = datetime.now(timezone.utc)

        # Check for existing active connection
        existing = await self.db.execute(
            text("""
                SELECT id, status FROM whatsapp_connections
                WHERE user_id = :user_id AND status = 'active'
            """),
            {"user_id": user_id},
        )
        row = existing.first()
        if row:
            raise ConflictError(
                message="WhatsApp number already connected. Disconnect first to link a new number.",
                detail={"connection_id": str(row[0])},
            )

        # Upsert: insert or update pending/expired records
        await self.db.execute(
            text("""
                INSERT INTO whatsapp_connections (user_id, phone_number, status, verification_code, created_at, updated_at)
                VALUES (:user_id, :phone_number, 'pending', :otp, :now, :now)
                ON CONFLICT (user_id) DO UPDATE SET
                    phone_number = EXCLUDED.phone_number,
                    status = 'pending',
                    verification_code = EXCLUDED.verification_code,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "user_id": user_id,
                "phone_number": phone_number,
                "otp": otp,
                "now": now,
            },
        )
        await self.db.commit()

        # TODO: In production, send the OTP via WhatsApp template message or SMS gateway
        # For now, log it (the user will receive it via the configured channel)
        logger.info(
            "WhatsApp linking OTP generated",
            user_id=user_id,
            phone_number=phone_number,
            otp=otp,
        )

        # Attempt to send OTP via WhatsApp template (if number is already on WhatsApp)
        try:
            await self._send_otp_message(phone_number, otp)
        except Exception as exc:
            logger.warning("Failed to send OTP via WhatsApp", error=str(exc))
            # OTP can still be verified through the web UI

        return WhatsAppLinkResponse(
            status="pending",
            message="Verification code sent to your phone",
            expires_in=300,
        )

    async def _send_otp_message(self, phone_number: str, otp: str) -> None:
        """Send the OTP code via a WhatsApp template message."""
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": "anansi_verification",  # Pre-registered template
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": otp},
                            {"type": "text", "text": "5"},
                        ],
                    }
                ],
            },
        }
        async with self.client as client:
            resp = await client.post(
                f"/{settings.whatsapp.api_version}/{self._phone_number_id()}/messages",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code != 200:
                error_data = resp.json()
                logger.error(
                    "WhatsApp OTP send failed",
                    status=resp.status_code,
                    error=error_data,
                )
                raise RuntimeError(f"Failed to send OTP: {error_data}")
            logger.info("OTP sent via WhatsApp template", phone_number=phone_number)

    # ── Verify OTP ──────────────────────────────────────────────────────────────

    async def verify_otp(self, user_id: str, code: str) -> WhatsAppVerifyResponse:
        """Verify the OTP code and activate the WhatsApp connection.

        Args:
            user_id: The user UUID.
            code: The 6-digit verification code.

        Returns:
            WhatsAppVerifyResponse on success.

        Raises:
            ValidationError: If the code is invalid or expired.
        """
        # Fetch the pending connection
        result = await self.db.execute(
            text("""
                SELECT id, phone_number, verification_code, status, created_at
                FROM whatsapp_connections
                WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        )
        row = result.first()
        if not row:
            raise NotFoundError(message="No pending WhatsApp connection found. Please start linking first.")

        conn_id, phone_number, stored_code, status, created_at = row

        if status == "active":
            return WhatsAppVerifyResponse(status="active", message="WhatsApp already connected")

        if status not in ("pending",):
            raise ValidationError(message=f"Cannot verify in '{status}' status. Please re-link.")

        # Check expiry (5 minutes)
        now = datetime.now(timezone.utc)
        if created_at and (now - created_at).total_seconds() > 300:
            await self.db.execute(
                text("UPDATE whatsapp_connections SET status = 'expired' WHERE id = :id"),
                {"id": conn_id},
            )
            await self.db.commit()
            raise ValidationError(message="Verification code expired. Please request a new one.")

        # Verify the code
        if stored_code != code:
            raise ValidationError(message="Invalid verification code. Please try again.")

        # Activate
        now_ts = datetime.now(timezone.utc)
        await self.db.execute(
            text("""
                UPDATE whatsapp_connections
                SET status = 'active', verification_code = NULL, verified_at = :now, updated_at = :now
                WHERE id = :id
            """),
            {"id": conn_id, "now": now_ts},
        )
        await self.db.commit()

        logger.info(
            "WhatsApp number linked successfully",
            user_id=user_id,
            phone_number=phone_number,
        )

        return WhatsAppVerifyResponse(
            status="active",
            message="WhatsApp number linked successfully! Try sending /help to get started.",
        )

    # ── Get Status ──────────────────────────────────────────────────────────────

    async def get_status(self, user_id: str) -> WhatsAppStatusResponse:
        """Return the current WhatsApp connection status for a user.

        Args:
            user_id: The user UUID.

        Returns:
            WhatsAppStatusResponse with connection details.
        """
        result = await self.db.execute(
            text("""
                SELECT phone_number, status, verified_at, settings
                FROM whatsapp_connections
                WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        )
        row = result.first()
        if not row:
            return WhatsAppStatusResponse(
                connected=False,
                status="disconnected",
            )

        phone_number, status, verified_at, settings = row

        return WhatsAppStatusResponse(
            connected=(status == "active"),
            phone_number=phone_number,
            status=status,
            verified_at=verified_at.isoformat() if verified_at else None,
            settings=settings or {},
        )

    # ── Send Message ────────────────────────────────────────────────────────────

    async def send_message(
        self,
        user_id: str,
        to: str,
        message: str,
        *,
        preview_url: bool = False,
    ) -> WhatsAppMessageResponse:
        """Send a text message via WhatsApp Cloud API.

        Args:
            user_id: The user UUID (for rate limiting).
            to: The recipient phone number (international format).
            message: The text message content.
            preview_url: Whether to generate link previews.

        Returns:
            WhatsAppMessageResponse with the message ID.

        Raises:
            RuntimeError: If the API request fails.
        """
        rate_limit_key = f"user:{user_id}:outbound"
        if not _message_rate_limiter.is_allowed(rate_limit_key):
            logger.warning("Rate limit hit for WhatsApp outbound", user_id=user_id, to=to)
            return WhatsAppMessageResponse(
                status="rate_limited",
                error="Too many messages. Please wait before sending more.",
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"preview_url": preview_url, "body": message},
        }

        async with self.client as client:
            resp = await client.post(
                f"/{settings.whatsapp.api_version}/{self._phone_number_id()}/messages",
                headers=self._headers(),
                json=payload,
            )

        if resp.status_code != 200:
            error_data = resp.json()
            logger.error(
                "WhatsApp message send failed",
                user_id=user_id,
                to=to,
                status=resp.status_code,
                error=error_data,
            )
            return WhatsAppMessageResponse(
                status="failed",
                error=str(error_data.get("error", {}).get("message", "Unknown error")),
            )

        resp_data = resp.json()
        message_id = resp_data.get("messages", [{}])[0].get("id")
        logger.info(
            "WhatsApp message sent",
            user_id=user_id,
            to=to,
            message_id=message_id,
        )

        return WhatsAppMessageResponse(
            message_id=message_id,
            status="sent",
        )

    # ── Send Template ───────────────────────────────────────────────────────────

    async def send_template(
        self,
        user_id: str,
        to: str,
        template_name: str,
        params: list[str] | None = None,
    ) -> WhatsAppMessageResponse:
        """Send a WhatsApp template message.

        Templates must be pre-registered in the WhatsApp Business account.

        Args:
            user_id: The user UUID.
            to: The recipient phone number.
            template_name: The template name.
            params: Optional list of body parameter values.

        Returns:
            WhatsAppMessageResponse.
        """
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
            },
        }

        if params:
            payload["template"]["components"] = [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in params],
                }
            ]

        async with self.client as client:
            resp = await client.post(
                f"/{settings.whatsapp.api_version}/{self._phone_number_id()}/messages",
                headers=self._headers(),
                json=payload,
            )

        if resp.status_code != 200:
            error_data = resp.json()
            logger.error(
                "WhatsApp template send failed",
                template=template_name,
                status=resp.status_code,
                error=error_data,
            )
            return WhatsAppMessageResponse(
                status="failed",
                error=str(error_data.get("error", {}).get("message", "Unknown error")),
            )

        resp_data = resp.json()
        message_id = resp_data.get("messages", [{}])[0].get("id")
        return WhatsAppMessageResponse(message_id=message_id, status="sent")

    # ── Send Voice Note ─────────────────────────────────────────────────────────

    async def send_voice_note(
        self,
        user_id: str,
        to: str,
        audio_url: str,
    ) -> WhatsAppMessageResponse:
        """Send an audio/voice note message via WhatsApp.

        The audio file must be hosted at a publicly accessible URL.

        Args:
            user_id: The user UUID.
            to: The recipient phone number.
            audio_url: Public URL to the audio file (OGG/MP3/AAC).

        Returns:
            WhatsAppMessageResponse.
        """
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "audio",
            "audio": {"link": audio_url},
        }

        async with self.client as client:
            resp = await client.post(
                f"/{settings.whatsapp.api_version}/{self._phone_number_id()}/messages",
                headers=self._headers(),
                json=payload,
            )

        if resp.status_code != 200:
            error_data = resp.json()
            logger.error(
                "WhatsApp voice note send failed",
                user_id=user_id,
                status=resp.status_code,
                error=error_data,
            )
            return WhatsAppMessageResponse(
                status="failed",
                error=str(error_data.get("error", {}).get("message", "Unknown error")),
            )

        resp_data = resp.json()
        message_id = resp_data.get("messages", [{}])[0].get("id")
        logger.info("WhatsApp voice note sent", user_id=user_id, message_id=message_id)
        return WhatsAppMessageResponse(message_id=message_id, status="sent")

    # ── Unlink ───────────────────────────────────────────────────────────────────

    async def unlink(self, user_id: str) -> dict[str, Any]:
        """Disconnect WhatsApp for a user.

        Sets the connection status to 'disconnected'.

        Args:
            user_id: The user UUID.

        Returns:
            Dict with status message.

        Raises:
            NotFoundError: If no connection exists.
        """
        result = await self.db.execute(
            text("""
                UPDATE whatsapp_connections
                SET status = 'disconnected', updated_at = :now
                WHERE user_id = :user_id AND status = 'active'
                RETURNING id, phone_number
            """),
            {"user_id": user_id, "now": datetime.now(timezone.utc)},
        )
        row = result.first()
        if not row:
            raise NotFoundError(message="No active WhatsApp connection found to disconnect.")

        await self.db.commit()
        logger.info("WhatsApp disconnected", user_id=user_id, phone_number=row[1])

        return {"status": "disconnected", "message": "WhatsApp disconnected successfully"}

    # ── Update Notification Settings ────────────────────────────────────────────

    async def update_settings(
        self,
        user_id: str,
        settings_update: dict[str, Any],
    ) -> WhatsAppStatusResponse:
        """Update WhatsApp notification preferences.

        Args:
            user_id: The user UUID.
            settings_update: Dict of settings to update.

        Returns:
            Updated WhatsAppStatusResponse.
        """
        # Get current settings
        result = await self.db.execute(
            text("SELECT settings FROM whatsapp_connections WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        row = result.first()
        if not row:
            raise NotFoundError(message="No WhatsApp connection found.")

        current_settings = row[0] or {}
        current_settings.update(settings_update)

        await self.db.execute(
            text("""
                UPDATE whatsapp_connections
                SET settings = :settings, updated_at = :now
                WHERE user_id = :user_id
            """),
            {
                "user_id": user_id,
                "settings": json.dumps(current_settings),
                "now": datetime.now(timezone.utc),
            },
        )
        await self.db.commit()

        return await self.get_status(user_id)

    # ── Webhook Processing ──────────────────────────────────────────────────────

    async def process_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Main webhook handler for WhatsApp Cloud API callbacks.

        Routes incoming messages, status updates, and delivery receipts
        to the appropriate handlers.

        Args:
            payload: The raw webhook payload from WhatsApp.

        Returns:
            Dict with processing summary.
        """
        object_type = payload.get("object", "")
        if object_type != "whatsapp_business_account":
            logger.warning("Unknown webhook object type", object_type=object_type)
            return {"status": "ignored", "reason": "unknown_object"}

        entries = payload.get("entry", [])
        processed_count = 0
        errors = []

        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messaging_product = value.get("messaging_product", "")

                # --- Status Updates ---
                statuses = value.get("statuses", [])
                for status_update in statuses:
                    try:
                        await self._process_status_update(status_update)
                    except Exception as exc:
                        logger.error("Failed to process status update", error=str(exc))
                        errors.append(str(exc))

                # --- Incoming Messages ---
                messages = value.get("messages", [])
                for msg in messages:
                    try:
                        await self._route_incoming_message(msg)
                        processed_count += 1
                    except Exception as exc:
                        logger.error("Failed to process incoming message", error=str(exc))
                        errors.append(str(exc))

        logger.info(
            "WhatsApp webhook processed",
            entries=len(entries),
            messages_processed=processed_count,
            errors=len(errors),
        )

        return {
            "status": "ok",
            "processed": processed_count,
            "errors": errors,
        }

    async def _route_incoming_message(self, msg: dict[str, Any]) -> None:
        """Route an incoming message to the conversation or command handler.

        Handles:
        - Text messages (including commands)
        - Voice notes (audio messages)
        - Interactive button replies
        """
        from_number = msg.get("from", "")
        msg_id = msg.get("id", "")
        msg_type = msg.get("type", "")

        if not from_number:
            logger.warning("Message missing 'from' number", msg_id=msg_id)
            return

        # Resolve user_id from phone number
        user_id = await self._resolve_user_by_phone(from_number)
        if not user_id:
            logger.warning("Unknown sender, ignoring message", from_number=from_number)
            return

        if msg_type == "text":
            text_body = msg.get("text", {}).get("body", "")
            from app.services.whatsapp_conversation import handle_incoming_message
            await handle_incoming_message(user_id, from_number, text_body)

        elif msg_type == "audio":
            audio_media_id = msg.get("audio", {}).get("id", "")
            if audio_media_id:
                # Dispatch voice note processing to Celery
                from app.tasks.whatsapp_tasks import process_voice_note_task
                process_voice_note_task.delay(user_id, from_number, audio_media_id)
                logger.info(
                    "Voice note queued for processing",
                    user_id=user_id,
                    media_id=audio_media_id,
                )

        elif msg_type == "interactive":
            btn_reply = msg.get("interactive", {}).get("button_reply", {})
            if btn_reply:
                reply_id = btn_reply.get("id", "")
                reply_title = btn_reply.get("title", "")
                from app.services.whatsapp_conversation import handle_incoming_message
                await handle_incoming_message(user_id, from_number, reply_title)

        elif msg_type in ("document", "image", "video"):
            logger.info(
                "Received non-audio media message",
                from_number=from_number,
                msg_type=msg_type,
            )
            # Inform user that only text, voice notes, and commands are supported
            from app.services.whatsapp_conversation import handle_incoming_message
            await handle_incoming_message(
                user_id,
                from_number,
                f"[Media type: {msg_type}]",
            )

        else:
            logger.info("Unhandled message type", msg_type=msg_type, from_number=from_number)

    async def _process_status_update(self, status_update: dict[str, Any]) -> None:
        """Process a message status update (sent, delivered, read, failed).

        Used for delivery tracking and webhook callbacks.
        """
        status = status_update.get("status", "")
        message_id = status_update.get("id", "")
        timestamp = status_update.get("timestamp", "")
        recipient_id = status_update.get("recipient_id", "")

        logger.debug(
            "WhatsApp message status update",
            message_id=message_id,
            status=status,
            recipient_id=recipient_id,
        )

        # In production, this would update a message_log table
        # For now, we just log it

    async def _resolve_user_by_phone(self, phone_number: str) -> str | None:
        """Resolve a WhatsApp phone number to a user UUID.

        Args:
            phone_number: The sender's phone number.

        Returns:
            The user UUID string, or None if not found.
        """
        result = await self.db.execute(
            text("""
                SELECT user_id FROM whatsapp_connections
                WHERE phone_number = :phone_number AND status = 'active'
            """),
            {"phone_number": phone_number},
        )
        row = result.first()
        if row:
            return str(row[0])
        return None

    # ── Download Media ──────────────────────────────────────────────────────────

    async def download_media(self, media_id: str) -> bytes | None:
        """Download media from WhatsApp Cloud API by media ID.

        Args:
            media_id: The WhatsApp media object ID.

        Returns:
            Raw bytes of the media file, or None on failure.
        """
        # Step 1: Get the media URL
        async with self.client as client:
            resp = await client.get(
                f"/{settings.whatsapp.api_version}/{media_id}",
                headers=self._headers(),
            )
            if resp.status_code != 200:
                logger.error("Failed to get media info", media_id=media_id, status=resp.status_code)
                return None

            media_info = resp.json()
            media_url = media_info.get("url")
            mime_type = media_info.get("mime_type", "")

            if not media_url:
                logger.warning("Media response missing URL", media_id=media_id)
                return None

            # Step 2: Download the media binary (auth with token in header)
            dl_resp = await client.get(media_url, headers=self._headers())
            if dl_resp.status_code != 200:
                logger.error("Failed to download media", media_id=media_id)
                return None

            logger.info(
                "Media downloaded",
                media_id=media_id,
                mime_type=mime_type,
                size=len(dl_resp.content),
            )
            return dl_resp.content

    # ── Webhook Verification ────────────────────────────────────────────────────

    @staticmethod
    def verify_webhook_token(
        mode: str,
        verify_token: str,
        challenge: str,
    ) -> str | None:
        """Verify the WhatsApp webhook (GET request on setup).

        WhatsApp Cloud API requires a verification challenge during
        webhook configuration. This method validates the token and
        returns the challenge string to echo back.

        Args:
            mode: Should be 'subscribe'.
            verify_token: The token to check.
            challenge: The challenge string to return on success.

        Returns:
            The challenge string if valid, None otherwise.
        """
        expected_token = settings.whatsapp.webhook_verify_token

        if mode == "subscribe" and verify_token == expected_token:
            logger.info("WhatsApp webhook verified successfully")
            return challenge

        logger.warning(
            "WhatsApp webhook verification failed",
            mode=mode,
            token_match=(verify_token == expected_token),
        )
        return None

    # ── Cleanup ─────────────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


__all__ = [
    "WhatsAppService",
    "WhatsAppLinkResponse",
    "WhatsAppVerifyResponse",
    "WhatsAppStatusResponse",
    "WhatsAppMessageResponse",
    "WhatsAppWebhookPayload",
]
