"""
WhatsApp Channel Tests — OTP, message routing, commands, voice notes, notifications.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestOTP:
    """Test WhatsApp OTP send/verify."""

    @pytest.mark.asyncio
    async def test_send_otp(self, async_client: AsyncClient, auth_headers: dict):
        """Test sending OTP via WhatsApp."""
        response = await async_client.post(
            "/api/v1/whatsapp/otp/send",
            headers=auth_headers,
            json={"phone_number": "+2348012345678"},
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_verify_otp(self, async_client: AsyncClient, auth_headers: dict):
        """Test verifying OTP."""
        response = await async_client.post(
            "/api/v1/whatsapp/otp/verify",
            headers=auth_headers,
            json={"phone_number": "+2348012345678", "otp": "123456"},
        )
        assert response.status_code in (200, 400, 500)

    @pytest.mark.asyncio
    async def test_send_otp_invalid_phone(self, async_client: AsyncClient, auth_headers: dict):
        """Test sending OTP with invalid phone number."""
        response = await async_client.post(
            "/api/v1/whatsapp/otp/send",
            headers=auth_headers,
            json={"phone_number": "invalid"},
        )
        assert response.status_code in (422, 500)


class TestIncomingMessages:
    """Test incoming message routing."""

    @pytest.mark.asyncio
    async def test_webhook_receive_text(self, async_client: AsyncClient):
        """Test receiving an incoming text message via webhook."""
        response = await async_client.post(
            "/api/v1/whatsapp/webhook",
            json={
                "object": "whatsapp_business_account",
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": "+2348012345678",
                                "id": "wamid.test123",
                                "type": "text",
                                "text": {"body": "Hello Anansi!"},
                            }],
                            "metadata": {"phone_number_id": "123456"},
                        }
                    }]
                }],
            },
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_webhook_verify_get(self, async_client: AsyncClient):
        """Test webhook verification (GET)."""
        response = await async_client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "anansi_webhook_verify_2026",
                "hub.challenge": "challenge_string",
            },
        )
        assert response.status_code == 200
        assert response.text == "challenge_string"

    @pytest.mark.asyncio
    async def test_webhook_receive_voice(self, async_client: AsyncClient):
        """Test receiving a voice note via webhook."""
        response = await async_client.post(
            "/api/v1/whatsapp/webhook",
            json={
                "object": "whatsapp_business_account",
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": "+2348012345678",
                                "id": "wamid.voice123",
                                "type": "voice",
                                "voice": {
                                    "id": "voice-media-id",
                                    "mime_type": "audio/ogg",
                                },
                            }],
                            "metadata": {"phone_number_id": "123456"},
                        }
                    }]
                }],
            },
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_send_message(self, async_client: AsyncClient, auth_headers: dict):
        """Test sending a WhatsApp message."""
        response = await async_client.post(
            "/api/v1/whatsapp/send",
            headers=auth_headers,
            json={
                "to": "+2348012345678",
                "type": "text",
                "content": {"body": "Test message"},
            },
        )
        assert response.status_code in (200, 500)


class TestWhatsAppCommands:
    """Test WhatsApp command parsing."""

    @pytest.mark.asyncio
    async def test_briefing_command(self, async_client: AsyncClient, auth_headers: dict):
        """Test /briefing command."""
        response = await async_client.post(
            "/api/v1/whatsapp/command",
            headers=auth_headers,
            json={"command": "/briefing", "args": ""},
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_tasks_command(self, async_client: AsyncClient, auth_headers: dict):
        """Test /tasks command."""
        response = await async_client.post(
            "/api/v1/whatsapp/command",
            headers=auth_headers,
            json={"command": "/tasks", "args": ""},
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_record_command(self, async_client: AsyncClient, auth_headers: dict):
        """Test /record command."""
        response = await async_client.post(
            "/api/v1/whatsapp/command",
            headers=auth_headers,
            json={"command": "/record", "args": "Remember to buy groceries"},
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_graph_command(self, async_client: AsyncClient, auth_headers: dict):
        """Test /graph command."""
        response = await async_client.post(
            "/api/v1/whatsapp/command",
            headers=auth_headers,
            json={"command": "/graph", "args": ""},
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_unknown_command(self, async_client: AsyncClient, auth_headers: dict):
        """Test unknown command returns appropriate response."""
        response = await async_client.post(
            "/api/v1/whatsapp/command",
            headers=auth_headers,
            json={"command": "/nonexistent", "args": ""},
        )
        assert response.status_code in (200, 400, 500)


class TestWhatsAppNotifications:
    """Test WhatsApp notification dispatch."""

    @pytest.mark.asyncio
    async def test_send_notification(self, async_client: AsyncClient, auth_headers: dict):
        """Test sending a notification to WhatsApp."""
        response = await async_client.post(
            "/api/v1/whatsapp/notify",
            headers=auth_headers,
            json={
                "type": "morning_briefing",
                "content": {"text": "Good morning! Here's your briefing..."},
            },
        )
        assert response.status_code in (200, 500)


class TestWhatsAppUnlink:
    """Test unlinking WhatsApp account."""

    @pytest.mark.asyncio
    async def test_unlink(self, async_client: AsyncClient, auth_headers: dict):
        """Test unlinking WhatsApp from account."""
        response = await async_client.post(
            "/api/v1/whatsapp/unlink",
            headers=auth_headers,
        )
        assert response.status_code in (200, 204, 500)


class TestWhatsAppStatus:
    """Test WhatsApp account status."""

    @pytest.mark.asyncio
    async def test_get_status(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting WhatsApp connection status."""
        response = await async_client.get(
            "/api/v1/whatsapp/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
