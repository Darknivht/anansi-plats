"""
Anansi WhatsApp API Endpoints — WhatsApp linking, verification, status,
disconnection, and webhook receiver.

Follows WhatsApp Cloud API conventions for webhook verification and
message handling.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.dependencies import CurrentUser, get_current_user, get_optional_user, rate_limit
from app.core.events import get_db_session, get_redis
from app.core.exceptions import ValidationError
from app.services.whatsapp import WhatsAppService, WhatsAppStatusResponse
from redis.asyncio import Redis

logger = get_logger(__name__)

router = APIRouter()


# ─── Request/Response Schemas ────────────────────────────────────────────────────


class LinkRequest(BaseModel):
    """Request to start WhatsApp linking."""

    phone_number: str = Field(
        ...,
        min_length=8,
        max_length=20,
        pattern=r"^\+[1-9]\d{6,19}$",
        description="International phone number (e.g., +2348012345678)",
    )


class LinkResponse(BaseModel):
    """Response after initiating link."""

    status: str
    message: str
    expires_in: int = 300


class VerifyRequest(BaseModel):
    """Request to verify OTP code."""

    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit verification code",
    )


class VerifyResponse(BaseModel):
    """Response after OTP verification."""

    status: str
    message: str


class UnlinkResponse(BaseModel):
    """Response after disconnecting WhatsApp."""

    status: str
    message: str


class UpdateSettingsRequest(BaseModel):
    """Request to update WhatsApp notification settings."""

    notify_morning_briefing: bool | None = None
    notify_agent_completed: bool | None = None
    notify_alerts: bool | None = None
    notify_suggestions: bool | None = None
    notify_weekly_summary: bool | None = None
    notify_review_reminder: bool | None = None
    notify_brain_insight: bool | None = None


class WebhookResponse(BaseModel):
    """Response from processing a webhook payload."""

    status: str
    processed: int = 0
    errors: list[str] = Field(default_factory=list)


# ─── Helper ──────────────────────────────────────────────────────────────────────


async def _get_whatsapp_service(
    db: AsyncSession = Depends(get_db_session),
) -> WhatsAppService:
    """Dependency that builds a WhatsAppService."""
    return WhatsAppService(db=db)


# ─── POST /api/v1/whatsapp/link — Start Linking ──────────────────────────────────


@router.post(
    "/link",
    response_model=LinkResponse,
    summary="Start WhatsApp linking",
    description="Send OTP to phone number to start WhatsApp linking process",
)
async def link_whatsapp(
    body: LinkRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: WhatsAppService = Depends(_get_whatsapp_service),
) -> LinkResponse:
    """Initiate WhatsApp number linking by sending an OTP.

    The user will receive a 6-digit code on their phone. They must
    call the `/verify` endpoint within 5 minutes.
    """
    result = await service.link_number(current_user.id, body.phone_number)
    return LinkResponse(
        status=result.status,
        message=result.message,
        expires_in=result.expires_in,
    )


# ─── POST /api/v1/whatsapp/verify — Verify OTP ───────────────────────────────────


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify WhatsApp OTP",
    description="Verify the 6-digit code to complete WhatsApp linking",
)
async def verify_whatsapp(
    body: VerifyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: WhatsAppService = Depends(_get_whatsapp_service),
) -> VerifyResponse:
    """Verify the OTP code sent to the user's phone.

    On success, the WhatsApp number is linked and active.
    """
    result = await service.verify_otp(current_user.id, body.code)
    return VerifyResponse(
        status=result.status,
        message=result.message,
    )


# ─── GET /api/v1/whatsapp/status — Connection Status ─────────────────────────────


@router.get(
    "/status",
    response_model=WhatsAppStatusResponse,
    summary="WhatsApp connection status",
    description="Get the current WhatsApp connection status for the authenticated user",
)
async def whatsapp_status(
    current_user: CurrentUser = Depends(get_current_user),
    service: WhatsAppService = Depends(_get_whatsapp_service),
) -> WhatsAppStatusResponse:
    """Return the WhatsApp connection status for the current user."""
    return await service.get_status(current_user.id)


# ─── PATCH /api/v1/whatsapp/settings — Update Settings ──────────────────────────


@router.patch(
    "/settings",
    response_model=WhatsAppStatusResponse,
    summary="Update WhatsApp notification settings",
    description="Update notification preferences for WhatsApp messages",
)
async def update_whatsapp_settings(
    body: UpdateSettingsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: WhatsAppService = Depends(_get_whatsapp_service),
) -> WhatsAppStatusResponse:
    """Update notification preferences for WhatsApp."""
    update_dict = body.model_dump(exclude_none=True)
    return await service.update_settings(current_user.id, update_dict)


# ─── POST /api/v1/whatsapp/unlink — Disconnect ───────────────────────────────────


@router.post(
    "/unlink",
    response_model=UnlinkResponse,
    summary="Disconnect WhatsApp",
    description="Disconnect WhatsApp from your account",
)
async def unlink_whatsapp(
    current_user: CurrentUser = Depends(get_current_user),
    service: WhatsAppService = Depends(_get_whatsapp_service),
) -> UnlinkResponse:
    """Disconnect the linked WhatsApp number."""
    result = await service.unlink(current_user.id)
    return UnlinkResponse(
        status=result["status"],
        message=result["message"],
    )


# ─── POST /api/v1/whatsapp/test — Send Test Message ─────────────────────────────


@router.post(
    "/test",
    summary="Send test WhatsApp message",
    description="Send a test message to the connected WhatsApp number",
)
async def send_test_whatsapp(
    current_user: CurrentUser = Depends(get_current_user),
    service: WhatsAppService = Depends(_get_whatsapp_service),
) -> dict[str, Any]:
    """Send a test message to the user's linked WhatsApp number."""
    status = await service.get_status(current_user.id)
    if not status.connected or not status.phone_number:
        raise ValidationError(message="WhatsApp is not connected. Please link a number first.")

    result = await service.send_message(
        current_user.id,
        status.phone_number,
        "🔔 *Test Message*\n\nYour WhatsApp connection is working perfectly! "
        "You'll receive notifications and can chat with Anansi here.",
    )

    return {
        "sent": result.status == "sent",
        "message": "Test message sent!" if result.status == "sent" else f"Failed: {result.error}",
        "message_id": result.message_id,
    }


# ─── GET /api/v1/whatsapp/webhook — Webhook Verification ─────────────────────────


@router.get(
    "/webhook",
    summary="WhatsApp webhook verification",
    description="Handle WhatsApp Cloud API webhook verification (GET request)",
    include_in_schema=False,
)
async def webhook_verify(
    request: Request,
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
) -> str:
    """WhatsApp Cloud API webhook verification endpoint.

    When setting up the webhook in the WhatsApp Business Account,
    Meta sends a GET request to verify the endpoint. We must echo
    back the challenge if the verify_token matches.
    """
    challenge = WhatsAppService.verify_webhook_token(
        mode=hub_mode,
        verify_token=hub_verify_token,
        challenge=hub_challenge,
    )

    if challenge is not None:
        logger.info("WhatsApp webhook verified successfully")
        return challenge

    logger.warning(
        "WhatsApp webhook verification failed",
        mode=hub_mode,
    )
    raise ValidationError(message="Verification failed. Invalid token or mode.")


# ─── POST /api/v1/whatsapp/webhook — Receive Webhook ────────────────────────────


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="Receive WhatsApp webhook",
    description="Receive incoming messages, status updates, and delivery receipts from WhatsApp Cloud API",
)
async def webhook_receive(
    payload: dict[str, Any],
    service: WhatsAppService = Depends(_get_whatsapp_service),
) -> WebhookResponse:
    """Process incoming webhook payload from WhatsApp Cloud API.

    Handles:
    - Text messages (including commands like /briefing)
    - Voice notes (queued for async transcription)
    - Interactive button replies
    - Message status updates (sent, delivered, read, failed)
    """
    result = await service.process_webhook(payload)
    return WebhookResponse(
        status=result.get("status", "ok"),
        processed=result.get("processed", 0),
        errors=result.get("errors", []),
    )


__all__ = [
    "router",
    "LinkRequest",
    "LinkResponse",
    "VerifyRequest",
    "VerifyResponse",
    "UnlinkResponse",
    "UpdateSettingsRequest",
    "WebhookResponse",
]
