"""
Trigger System — Registers, evaluates, and routes agent triggers.

Handles schedule (cron), webhook, and event-based triggers.
Integrates with Celery beat for periodic trigger evaluation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from croniter import croniter
from sqlalchemy import select, and_
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_session_factory, get_redis
from app.core.exceptions import NotFoundError, ValidationError
from app.models.agent import Agent
from app.services.blocks import block_registry
from app.services.execution import execution_engine

logger = get_logger(__name__)


class TriggerService:
    """Manages agent trigger lifecycle — registration, evaluation, and routing."""

    # Redis key prefixes
    _SCHEDULE_KEY = "agent:triggers:schedule"
    _WEBHOOK_KEY = "agent:triggers:webhook"
    _EVENT_KEY = "agent:triggers:event"
    _ACTIVE_TRIGGERS_KEY = "agent:triggers:active"

    # ── Registration ───────────────────────────────────────────────────────────

    async def register_agent_triggers(self, agent_id: str) -> dict[str, Any]:
        """Parse an agent's trigger blocks and register them.

        Scans the agent definition for trigger blocks, then registers
        each one (cron jobs, webhook endpoints, event listeners).

        Args:
            agent_id: UUID of the agent.

        Returns:
            Dict with status and registered trigger count.
        """
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(Agent).where(Agent.id == uuid.UUID(agent_id))
            )
            agent = result.scalar_one_or_none()
            if not agent:
                raise NotFoundError(message=f"Agent not found: {agent_id}")

            definition = agent.definition
            blocks = definition.get("blocks", [])
            trigger_blocks = [b for b in blocks if b.get("type") == "trigger"]

            if not trigger_blocks:
                raise ValidationError(message="Agent has no trigger blocks to register")

            registered = []
            redis = get_redis()

            for block in trigger_blocks:
                subtype = block.get("subtype", "")
                config = block.get("config", {})
                block_id = block.get("id", "")

                if subtype == "schedule":
                    trigger_info = await self._register_schedule(
                        agent_id, block_id, config, redis
                    )
                elif subtype == "webhook":
                    trigger_info = await self._register_webhook(
                        agent_id, block_id, config, redis
                    )
                elif subtype in ("email_received", "message_received", "file_changed",
                                 "form_submitted", "event"):
                    trigger_info = await self._register_event(
                        agent_id, block_id, subtype, config, redis
                    )
                else:
                    logger.warning("Unknown trigger subtype", subtype=subtype)
                    continue

                registered.append(trigger_info)

            # Store active triggers reference
            await redis.sadd(
                f"{self._ACTIVE_TRIGGERS_KEY}:{agent_id}",
                *[t["id"] for t in registered],
            )

            # Set agent status to active
            if agent.status == "draft":
                agent.status = "active"
                await session.commit()

            logger.info(
                "Agent triggers registered",
                agent_id=agent_id,
                count=len(registered),
            )

            return {
                "status": "registered",
                "agent_id": agent_id,
                "triggers": registered,
                "count": len(registered),
            }

    async def _register_schedule(
        self,
        agent_id: str,
        block_id: str,
        config: dict[str, Any],
        redis: Any,
    ) -> dict[str, Any]:
        """Register a schedule trigger."""
        cron = config.get("cron", "")
        timezone_name = config.get("timezone", "UTC")

        if not cron:
            raise ValidationError(message="Schedule trigger requires a cron expression")

        # Validate cron expression
        try:
            croniter(cron)
        except (ValueError, KeyError) as exc:
            raise ValidationError(message=f"Invalid cron expression: {cron}") from exc

        trigger_id = f"schedule:{agent_id}:{block_id}"
        trigger_data = {
            "id": trigger_id,
            "type": "schedule",
            "agent_id": agent_id,
            "block_id": block_id,
            "cron": cron,
            "timezone": timezone_name,
            "created_at": time.time(),
        }

        # Store in Redis for Celery beat to check
        await redis.hset(
            self._SCHEDULE_KEY,
            trigger_id,
            json.dumps(trigger_data),
        )

        return trigger_data

    async def _register_webhook(
        self,
        agent_id: str,
        block_id: str,
        config: dict[str, Any],
        redis: Any,
    ) -> dict[str, Any]:
        """Register a webhook trigger."""
        method = config.get("method", "POST")
        secret = config.get("secret", "")

        # Generate a unique webhook path
        webhook_id = str(uuid.uuid4())
        trigger_id = f"webhook:{agent_id}:{block_id}"

        trigger_data = {
            "id": trigger_id,
            "type": "webhook",
            "agent_id": agent_id,
            "block_id": block_id,
            "webhook_id": webhook_id,
            "method": method,
            "has_secret": bool(secret),
            "webhook_url": f"{settings.app.api_prefix}/webhooks/{webhook_id}",
            "created_at": time.time(),
        }

        # Store by webhook_id for fast lookup on incoming webhook
        await redis.hset(
            self._WEBHOOK_KEY,
            webhook_id,
            json.dumps(trigger_data),
        )

        return trigger_data

    async def _register_event(
        self,
        agent_id: str,
        block_id: str,
        subtype: str,
        config: dict[str, Any],
        redis: Any,
    ) -> dict[str, Any]:
        """Register an event-based trigger."""
        event_type = config.get("event_type", subtype)
        trigger_id = f"event:{agent_id}:{block_id}"

        trigger_data = {
            "id": trigger_id,
            "type": "event",
            "subtype": subtype,
            "agent_id": agent_id,
            "block_id": block_id,
            "event_type": event_type,
            "config": config,
            "created_at": time.time(),
        }

        # Index by event_type for fast event routing
        await redis.hset(
            f"{self._EVENT_KEY}:{event_type}",
            trigger_id,
            json.dumps(trigger_data),
        )

        return trigger_data

    # ── Unregistration ─────────────────────────────────────────────────────────

    async def unregister_agent_triggers(self, agent_id: str) -> dict[str, Any]:
        """Remove all triggers for an agent.

        Args:
            agent_id: UUID of the agent.

        Returns:
            Status dict.
        """
        redis = get_redis()
        removed_count = 0

        # Get active trigger IDs
        active_key = f"{self._ACTIVE_TRIGGERS_KEY}:{agent_id}"
        trigger_ids = await redis.smembers(active_key)

        for trigger_id in trigger_ids:
            trigger_id_str = trigger_id.decode() if isinstance(trigger_id, bytes) else trigger_id

            if trigger_id_str.startswith("schedule:"):
                await redis.hdel(self._SCHEDULE_KEY, trigger_id_str)
            elif trigger_id_str.startswith("webhook:"):
                # Need to look up webhook_id
                data = await redis.hget(self._WEBHOOK_KEY, trigger_id_str)
                if data:
                    parsed = json.loads(data) if isinstance(data, str) else json.loads(data.decode())
                    wh_id = parsed.get("webhook_id")
                    if wh_id:
                        await redis.hdel(self._WEBHOOK_KEY, wh_id)
            elif trigger_id_str.startswith("event:"):
                # Remove from all event type indexes
                if ":" in trigger_id_str:
                    parts = trigger_id_str.split(":")
                    event_type = parts[-1] if len(parts) >= 3 else "unknown"
                    await redis.hdel(f"{self._EVENT_KEY}:{event_type}", trigger_id_str)

            removed_count += 1

        # Remove the active triggers set
        await redis.delete(active_key)

        logger.info(
            "Agent triggers unregistered",
            agent_id=agent_id,
            count=removed_count,
        )

        return {
            "status": "unregistered",
            "agent_id": agent_id,
            "triggers_removed": removed_count,
        }

    # ── Schedule Evaluation ────────────────────────────────────────────────────

    async def evaluate_schedule_triggers(self) -> list[dict[str, Any]]:
        """Check all schedule triggers and queue agent runs for due ones.

        Called by Celery beat on a regular interval (e.g., every minute).

        Returns:
            List of triggered runs.
        """
        redis = get_redis()
        triggered: list[dict[str, Any]] = []

        # Get all schedule triggers
        schedule_data = await redis.hgetall(self._SCHEDULE_KEY)
        now = datetime.now(timezone.utc)

        for trigger_id_bytes, data_bytes in schedule_data.items():
            trigger_id = trigger_id_bytes.decode() if isinstance(trigger_id_bytes, bytes) else trigger_id_bytes
            data_str = data_bytes.decode() if isinstance(data_bytes, bytes) else data_bytes
            trigger = json.loads(data_str)

            cron = trigger.get("cron", "")
            try:
                cron_iter = croniter(cron, now)
                prev_time = cron_iter.get_prev(datetime)
                # If the previous scheduled time is within the last 2 minutes, trigger
                time_diff = (now - prev_time).total_seconds()
                if 0 < time_diff < 120:  # Within last 2 minutes
                    agent_id = trigger.get("agent_id", "")
                    logger.info(
                        "Schedule trigger firing",
                        trigger_id=trigger_id,
                        agent_id=agent_id,
                        scheduled=prev_time.isoformat(),
                    )

                    # Queue the agent execution
                    try:
                        result = await execution_engine.run_agent(
                            agent_id=agent_id,
                            trigger_type="schedule",
                            input_data={
                                "trigger": trigger,
                                "scheduled_at": prev_time.isoformat(),
                            },
                        )
                        triggered.append(result)
                    except Exception as exc:
                        logger.error(
                            "Schedule trigger execution failed",
                            agent_id=agent_id,
                            error=str(exc),
                        )
            except (ValueError, KeyError) as exc:
                logger.warning("Invalid cron in schedule trigger", cron=cron, error=str(exc))
                continue

        return triggered

    # ── Webhook Handling ───────────────────────────────────────────────────────

    async def handle_webhook_trigger(
        self,
        webhook_id: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Handle an incoming webhook request.

        Looks up the webhook registration, verifies authenticity,
        and queues the agent for execution.

        Args:
            webhook_id: The webhook's unique ID.
            payload: The webhook request body.
            headers: Optional HTTP headers for signature verification.

        Returns:
            Trigger result.
        """
        redis = get_redis()

        # Look up webhook registration
        data_bytes = await redis.hget(self._WEBHOOK_KEY, webhook_id)
        if not data_bytes:
            logger.warning("Webhook not found", webhook_id=webhook_id)
            raise NotFoundError(message=f"Webhook not found: {webhook_id}")

        data_str = data_bytes.decode() if isinstance(data_bytes, bytes) else data_bytes
        trigger = json.loads(data_str)

        agent_id = trigger.get("agent_id", "")

        # Verify HMAC signature if configured
        secret = trigger.get("has_secret", False)
        if secret and headers:
            # The full secret would be retrieved from the agent's integration
            # TODO: Implement HMAC verification
            signature = headers.get("x-webhook-signature", "")
            if not self._verify_webhook_signature(payload, signature, agent_id):
                raise ValidationError(message="Invalid webhook signature")

        logger.info(
            "Webhook trigger firing",
            webhook_id=webhook_id,
            agent_id=agent_id,
        )

        try:
            result = await execution_engine.run_agent(
                agent_id=agent_id,
                trigger_type="webhook",
                input_data={
                    "payload": payload,
                    "headers": headers or {},
                    "webhook_id": webhook_id,
                },
            )
            return result
        except Exception as exc:
            logger.error(
                "Webhook agent execution failed",
                agent_id=agent_id,
                error=str(exc),
            )
            raise

    @staticmethod
    def _verify_webhook_signature(
        payload: dict[str, Any],
        signature: str,
        agent_id: str,
    ) -> bool:
        """Verify an HMAC webhook signature.

        Placeholder — full implementation will use agent-specific secrets.
        """
        if not signature:
            return False
        # TODO: Retrieve agent's webhook secret and verify
        return True

    # ── Event Handling ─────────────────────────────────────────────────────────

    async def handle_event_trigger(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Handle an internal platform event and trigger matching agents.

        Args:
            event_type: The event type string (e.g., 'agent.completed').
            data: Event payload data.

        Returns:
            List of triggered executions.
        """
        redis = get_redis()
        triggered: list[dict[str, Any]] = []

        # Find all agents listening for this event type
        event_key = f"{self._EVENT_KEY}:{event_type}"
        event_triggers = await redis.hgetall(event_key)

        for trigger_id_bytes, data_bytes in event_triggers.items():
            data_str = data_bytes.decode() if isinstance(data_bytes, bytes) else data_bytes
            trigger = json.loads(data_str)
            agent_id = trigger.get("agent_id", "")

            # Check event filters
            config = trigger.get("config", {})
            event_filter = config.get("filter", {})
            if event_filter and not self._matches_filter(data, event_filter):
                continue

            logger.info(
                "Event trigger firing",
                event_type=event_type,
                agent_id=agent_id,
            )

            try:
                result = await execution_engine.run_agent(
                    agent_id=agent_id,
                    trigger_type="event",
                    input_data={
                        "event_type": event_type,
                        "event_data": data,
                    },
                )
                triggered.append(result)
            except Exception as exc:
                logger.error(
                    "Event agent execution failed",
                    agent_id=agent_id,
                    event_type=event_type,
                    error=str(exc),
                )

        return triggered

    @staticmethod
    def _matches_filter(data: dict[str, Any], filter_: dict[str, Any]) -> bool:
        """Check if event data matches a filter dict (simple key-value match)."""
        for key, value in filter_.items():
            actual = data.get(key)
            if actual != value:
                return False
        return True

    # ── Active Triggers ────────────────────────────────────────────────────────

    async def list_active_triggers(self, agent_id: str) -> list[dict[str, Any]]:
        """List all active triggers for an agent (for debugging).

        Args:
            agent_id: UUID of the agent.

        Returns:
            List of trigger configurations.
        """
        redis = get_redis()
        triggers: list[dict[str, Any]] = []

        active_key = f"{self._ACTIVE_TRIGGERS_KEY}:{agent_id}"
        trigger_ids = await redis.smembers(active_key)

        for tid_bytes in trigger_ids:
            tid = tid_bytes.decode() if isinstance(tid_bytes, bytes) else tid_bytes

            if tid.startswith("schedule:"):
                data = await redis.hget(self._SCHEDULE_KEY, tid)
            elif tid.startswith("webhook:"):
                data = await redis.hget(self._WEBHOOK_KEY, tid)
            elif tid.startswith("event:"):
                parts = tid.split(":")
                event_type = parts[-1] if len(parts) >= 3 else "unknown"
                data = await redis.hget(f"{self._EVENT_KEY}:{event_type}", tid)
            else:
                continue

            if data:
                data_str = data.decode() if isinstance(data, bytes) else data
                triggers.append(json.loads(data_str))

        return triggers


# ─── Singleton ───────────────────────────────────────────────────────────────────

trigger_service = TriggerService()

__all__ = ["trigger_service", "TriggerService"]
