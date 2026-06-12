"""
Webhook Service — Register, verify, and dispatch incoming webhooks to agents.

Anansi can receive webhooks from external services (GitHub, Stripe, Slack, etc.)
and trigger agent executions with the webhook payload.

Webhook registration creates a unique endpoint URL that supports:
- HMAC signature verification
- Payload forwarding to matching agents
- Automatic deactivation on repeated failures
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import async_session_factory
from app.models.agent import Agent, AgentRun
from app.websocket.manager import manager, WSServerEvent

logger = get_logger(__name__)


# ─── In-memory webhook registry ──────────────────────────────────────────────
# In production this should be stored in the database. For MVP we use
# an in-memory dict keyed by webhook_id -> config.

_webhook_registry: dict[str, dict[str, Any]] = {}


class WebhookService:
    """Manage webhook registration, verification, and dispatch."""

    # ── Register ────────────────────────────────────────────────────────────────

    async def register_webhook(
        self,
        agent_id: str,
        webhook_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Register a webhook endpoint for an agent.

        Creates a unique webhook endpoint URL that external services can POST to.

        Args:
            agent_id: The agent UUID to trigger.
            webhook_config: Dict with:
                - description: Optional description
                - secret: Optional shared secret for HMAC verification
                - events: Optional list of event types to filter on
                - active: Whether the webhook starts active (default: True)

        Returns:
            Dict with 'webhook_id', 'webhook_url', and 'config'.
        """
        webhook_id = str(uuid.uuid4())
        secret = webhook_config.get("secret", self._generate_secret())
        base_url = settings.app.api_prefix or "http://localhost:8000"
        webhook_url = f"{base_url}/v1/webhooks/incoming/{webhook_id}"

        entry = {
            "webhook_id": webhook_id,
            "agent_id": agent_id,
            "description": webhook_config.get("description", ""),
            "secret": secret,
            "events": webhook_config.get("events", []),
            "active": webhook_config.get("active", True),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "failure_count": 0,
        }

        _webhook_registry[webhook_id] = entry

        logger.info(
            "Webhook registered",
            agent_id=agent_id,
            webhook_id=webhook_id,
        )

        return {
            "webhook_id": webhook_id,
            "webhook_url": webhook_url,
            "secret": secret,
            "description": webhook_config.get("description", ""),
            "events": webhook_config.get("events", []),
            "active": True,
        }

    # ── Handle Incoming ────────────────────────────────────────────────────────

    async def handle_incoming(
        self,
        webhook_id: str,
        headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any]:
        """Handle an incoming webhook request.

        Verifies the signature (if configured), finds the matching agent,
        and triggers execution.

        Args:
            webhook_id: The registered webhook ID.
            headers: Request headers (from the external service).
            body: Raw request body bytes.

        Returns:
            Dict with processing status.

        Raises:
            NotFoundError: If webhook_id is not registered.
            ValidationError: If signature verification fails.
        """
        webhook = _webhook_registry.get(webhook_id)
        if not webhook:
            raise NotFoundError(
                message="Webhook not found. It may have been deleted.",
                resource_type="webhook",
                resource_id=webhook_id,
            )

        if not webhook["active"]:
            logger.warning("Webhook is inactive", webhook_id=webhook_id)
            return {"status": "inactive", "message": "Webhook is disabled"}

        # Verify HMAC signature if configured
        secret = webhook.get("secret")
        if secret:
            signature = headers.get("x-hub-signature-256") or headers.get("x-signature") or headers.get("signature", "")
            if not signature:
                logger.warning("Missing webhook signature header", webhook_id=webhook_id)
                raise ValidationError(message="Missing signature header")
            if not self.verify_signature(body, signature, secret):
                logger.warning("Invalid webhook signature", webhook_id=webhook_id)
                raise ValidationError(message="Invalid webhook signature")

        # Parse the body
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw": body.decode("utf-8", errors="replace")}

        # Check event type filtering if configured
        event_type = headers.get("x-event-type") or headers.get("x-github-event") or headers.get("x-slack-event") or ""
        if webhook["events"] and event_type and event_type not in webhook["events"]:
            logger.info(
                "Event type filtered out",
                webhook_id=webhook_id,
                event_type=event_type,
                allowed_events=webhook["events"],
            )
            return {"status": "ignored", "reason": "event_type_not_subscribed"}

        # Find the agent and create a run
        agent_id = webhook["agent_id"]
        try:
            run_data = await self._trigger_agent(
                agent_id=agent_id,
                webhook_id=webhook_id,
                payload=payload,
                headers=headers,
            )
            status = "triggered"
            run_id = run_data.get("run_id", "")
        except Exception as exc:
            logger.error("Failed to trigger agent from webhook", agent_id=agent_id, error=str(exc))
            webhook["failure_count"] += 1
            if webhook["failure_count"] >= 10:
                webhook["active"] = False
                logger.warning("Webhook auto-deactivated due to failures", webhook_id=webhook_id)
            status = "error"
            run_id = None

        return {
            "status": status,
            "webhook_id": webhook_id,
            "agent_id": agent_id,
            "run_id": run_id,
        }

    # ── Unregister ──────────────────────────────────────────────────────────────

    async def unregister_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Remove a webhook registration.

        Args:
            webhook_id: The webhook to remove.

        Returns:
            Status dict.
        """
        if webhook_id not in _webhook_registry:
            raise NotFoundError(resource_type="webhook", resource_id=webhook_id)

        del _webhook_registry[webhook_id]

        logger.info("Webhook unregistered", webhook_id=webhook_id)

        return {"status": "unregistered"}

    # ── Signature Verification ─────────────────────────────────────────────────

    @staticmethod
    def verify_signature(
        payload: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """Verify an HMAC-signed webhook payload.

        Supports both SHA256 (prefix 'sha256=') and SHA1 (prefix 'sha1=')
        signature formats.

        Args:
            payload: Raw request body bytes.
            signature: The signature header value (e.g. 'sha256=abc123...').
            secret: The shared HMAC secret.

        Returns:
            True if the signature is valid.
        """
        # Parse the algorithm and expected hash from the signature header
        if signature.startswith("sha256="):
            algo = hashlib.sha256
            expected = signature[7:]
        elif signature.startswith("sha1="):
            algo = hashlib.sha1
            expected = signature[5:]
        else:
            # Try SHA256 as default
            algo = hashlib.sha256
            expected = signature

        computed = hmac.new(secret.encode("utf-8"), payload, algo).hexdigest()
        return hmac.compare_digest(computed, expected)

    # ── Agent Trigger ──────────────────────────────────────────────────────────

    async def _trigger_agent(
        self,
        agent_id: str,
        webhook_id: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Trigger an agent execution with the webhook payload.

        Args:
            agent_id: Target agent UUID.
            webhook_id: The webhook ID for logging.
            payload: Parsed JSON payload from the webhook.
            headers: Original request headers.

        Returns:
            Dict with 'run_id' if triggered.
        """
        # Verify the agent exists
        async with async_session_factory() as session:
            result = await session.execute(
                select(Agent).where(Agent.id == uuid.UUID(agent_id))
            )
            agent = result.scalar_one_or_none()

        if not agent:
            raise NotFoundError(resource_type="agent", resource_id=agent_id)

        if agent.status != "active":
            raise ValidationError(message=f"Agent '{agent.name}' is not active")

        # Create a new agent run
        run_id = str(uuid.uuid4())
        run = AgentRun(
            id=uuid.UUID(run_id),
            agent_id=uuid.UUID(agent_id),
            user_id=agent.user_id,
            trigger_type="webhook",
            status="running",
            input_data={
                "webhook_id": webhook_id,
                "payload": payload,
                "headers": {k: v for k, v in headers.items() if k.lower() not in ("authorization", "cookie")},
            },
            started_at=datetime.now(timezone.utc),
        )

        async with async_session_factory() as session:
            session.add(run)
            await session.commit()

        # Send WebSocket notification
        await manager.send_to_user(
            str(agent.user_id),
            WSServerEvent(
                type="agent.running",
                payload={
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "run_id": run_id,
                    "trigger": "webhook",
                    "webhook_id": webhook_id,
                },
            ),
        )

        logger.info(
            "Agent triggered by webhook",
            agent_id=agent_id,
            run_id=run_id,
            webhook_id=webhook_id,
        )

        # Note: Actual agent execution is handled by the Agent Execution Service
        # asynchronously. The webhook service just creates the run record.

        return {"run_id": run_id, "agent_id": agent_id}

    # ── List Webhooks ─────────────────────────────────────────────────────────

    async def list_webhooks(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        """List all registered webhooks.

        Args:
            agent_id: Optional filter by agent.

        Returns:
            List of webhook configs.
        """
        webhooks = []
        for wid, config in _webhook_registry.items():
            if agent_id and config["agent_id"] != agent_id:
                continue
            webhooks.append({
                "webhook_id": wid,
                "agent_id": config["agent_id"],
                "description": config["description"],
                "active": config["active"],
                "failure_count": config["failure_count"],
                "events": config["events"],
                "created_at": config["created_at"],
            })
        return webhooks

    # ── Utility ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _generate_secret(length: int = 32) -> str:
        """Generate a random HMAC secret."""
        return uuid.uuid4().hex + uuid.uuid4().hex[:length - 32]


# ─── Factory for FastAPI DI ────────────────────────────────────────────────────


async def get_webhook_service() -> WebhookService:
    """FastAPI dependency factory."""
    return WebhookService()


__all__ = [
    "WebhookService",
    "get_webhook_service",
]
