"""
Integration & Webhook API Endpoints — All /api/v1/integrations routes.

From spec Section 8.2 (Integrations):
- GET  /integrations — List all available connections with status
- GET  /integrations/:id — Integration detail
- POST /integrations/:id/auth — Start OAuth flow
- POST /integrations/:id/disconnect — Remove connection
- GET  /integrations/status — Health of all connections
- GET  /integrations/connectors — List available connector types

Additional:
- POST /integrations/:id/test — Test a connection
- POST /integrations/:id/refresh — Refresh OAuth token
- POST /integrations/connect/:key — Connect via API key

Webhook endpoints:
- POST /integrations/webhooks/register — Register webhook
- POST /integrations/webhooks/:id/unregister — Unregister webhook
- POST /webhooks/incoming/:id — Receive webhook (public, no auth)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path, Query, Request
from pydantic import BaseModel, Field
from structlog import get_logger

from app.core.dependencies import get_current_user, CurrentUser
from app.services.integration import IntegrationService, get_integration_service
from app.services.webhook import WebhookService, get_webhook_service

logger = get_logger(__name__)
router = APIRouter()


# ─── Request / Response Models ──────────────────────────────────────────────


class OAuthInitiateRequest(BaseModel):
    connector_key: str = Field(..., description="Connector key (e.g. 'gmail', 'slack')")
    redirect_uri: str = Field(..., description="OAuth redirect URI for callback")


class OAuthCallbackRequest(BaseModel):
    connector_key: str = Field(..., description="Connector key")
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="State parameter for verification")


class ApiKeyConnectRequest(BaseModel):
    connector_key: str = Field(..., description="Connector key (e.g. 'notion', 'linear')")
    api_key: str = Field(..., description="API key or token for the service")
    config: dict[str, Any] | None = Field(default=None, description="Additional configuration")


class WebhookRegisterRequest(BaseModel):
    agent_id: str = Field(..., description="Agent UUID to trigger")
    config: dict[str, Any] = Field(default_factory=dict, description="Webhook configuration")


# ─── Integration Endpoints ──────────────────────────────────────────────────


@router.get("/integrations", summary="List all available connectors with connection status")
async def list_integrations(
    current_user: CurrentUser = Depends(get_current_user),
    svc: IntegrationService = Depends(get_integration_service),
):
    """List all available connector types with the user's connection status."""
    return await svc.list_available(current_user.id)


@router.get("/integrations/connectors", summary="List available connector types")
async def list_connectors(
    current_user: CurrentUser = Depends(get_current_user),
    svc: IntegrationService = Depends(get_integration_service),
):
    """List all available connector types."""
    available = await svc.list_available(current_user.id)
    # Return just the connector metadata without status
    return [
        {
            "key": c["key"],
            "name": c["name"],
            "description": c["description"],
            "icon_url": c["icon_url"],
            "category": c["category"],
            "auth_type": c["auth_type"],
            "scopes": c.get("scopes", []),
        }
        for c in available
    ]


@router.get("/integrations/status", summary="Health status of all connections")
async def get_integration_status(
    current_user: CurrentUser = Depends(get_current_user),
    svc: IntegrationService = Depends(get_integration_service),
):
    """Return the health of all user connections."""
    return await svc.get_status(current_user.id)


@router.get("/integrations/connectors/{key}", summary="Get connector type detail")
async def get_connector_detail(
    key: str = Path(..., description="Connector key"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: IntegrationService = Depends(get_integration_service),
):
    """Get detailed info about a specific connector type."""
    return await svc.get_connector_detail(key)


@router.get("/integrations/{integration_id}", summary="Get integration detail")
async def get_integration_detail(
    integration_id: str = Path(..., description="Integration UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: IntegrationService = Depends(get_integration_service),
):
    """Get detailed info about a specific user integration."""
    return await svc.get_integration_detail(integration_id, current_user.id)


@router.post("/integrations/auth", summary="Start OAuth flow for a connector")
async def initiate_oauth(
    req: OAuthInitiateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: IntegrationService = Depends(get_integration_service),
):
    """Initiate OAuth flow. Returns the authorization URL to redirect the user to."""
    return await svc.initiate_oauth(
        connector_key=req.connector_key,
        user_id=current_user.id,
        redirect_uri=req.redirect_uri,
    )


@router.post("/integrations/auth/callback", summary="Complete OAuth flow")
async def oauth_callback(
    req: OAuthCallbackRequest,
    svc: IntegrationService = Depends(get_integration_service),
):
    """Complete the OAuth flow by exchanging the authorization code for tokens.

    This endpoint is called by the OAuth provider's redirect, or can be called
    from the frontend after the redirect is captured.
    """
    return await svc.handle_oauth_callback(
        connector_key=req.connector_key,
        code=req.code,
        state=req.state,
    )


@router.post("/integrations/connect", summary="Connect via API key")
async def connect_api_key(
    req: ApiKeyConnectRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: IntegrationService = Depends(get_integration_service),
):
    """Connect a service using an API key (for services without OAuth)."""
    return await svc.connect_api_key(
        connector_key=req.connector_key,
        user_id=current_user.id,
        api_key=req.api_key,
        config=req.config,
    )


@router.post("/integrations/{integration_id}/disconnect", summary="Remove a connection")
async def disconnect_integration(
    integration_id: str = Path(..., description="Integration UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: IntegrationService = Depends(get_integration_service),
):
    """Disconnect and remove an integration, revoking tokens if possible."""
    return await svc.disconnect(integration_id, current_user.id)


@router.post("/integrations/{integration_id}/test", summary="Test a connection")
async def test_connection(
    integration_id: str = Path(..., description="Integration UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: IntegrationService = Depends(get_integration_service),
):
    """Test a connection by calling the service's endpoint."""
    return await svc.test_connection(integration_id, current_user.id)


@router.post("/integrations/{integration_id}/refresh", summary="Refresh OAuth token")
async def refresh_token(
    integration_id: str = Path(..., description="Integration UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: IntegrationService = Depends(get_integration_service),
):
    """Force refresh an OAuth token if it's expired or about to expire."""
    return await svc.refresh_token(integration_id, current_user.id)


# ─── Webhook Endpoints ─────────────────────────────────────────────────────


@router.post("/integrations/webhooks/register", summary="Register a webhook for an agent")
async def register_webhook(
    req: WebhookRegisterRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: WebhookService = Depends(get_webhook_service),
):
    """Register a webhook endpoint for an agent. Returns the webhook URL and secret."""
    return await svc.register_webhook(
        agent_id=req.agent_id,
        webhook_config=req.config,
    )


@router.post("/integrations/webhooks/{webhook_id}/unregister", summary="Unregister a webhook")
async def unregister_webhook(
    webhook_id: str = Path(..., description="Webhook UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: WebhookService = Depends(get_webhook_service),
):
    """Remove a webhook registration."""
    return await svc.unregister_webhook(webhook_id)


@router.get("/integrations/webhooks", summary="List registered webhooks")
async def list_webhooks(
    agent_id: str | None = Query(default=None, description="Filter by agent"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: WebhookService = Depends(get_webhook_service),
):
    """List all registered webhooks, optionally filtered by agent."""
    return await svc.list_webhooks(agent_id=agent_id)


# ─── Public Incoming Webhook Endpoint ──────────────────────────────────────


@router.post(
    "/webhooks/incoming/{webhook_id}",
    summary="Receive an incoming webhook (public)",
    include_in_schema=False,  # Hide from OpenAPI docs — this is a machine-to-machine endpoint
)
async def receive_webhook(
    webhook_id: str = Path(...),
    request: Request,
    svc: WebhookService = Depends(get_webhook_service),
):
    """Public endpoint for external services to send webhooks to.

    No authentication required. Signature verification is done via HMAC
    if a secret was configured during registration.
    """
    body = await request.body()
    headers = dict(request.headers)
    return await svc.handle_incoming(webhook_id, headers, body)
