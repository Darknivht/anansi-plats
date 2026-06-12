"""
Agent Execution Engine — The heart of the agent system.

Executes blocks in topological order, handles errors gracefully,
streams real-time status via WebSocket, and tracks memory impact.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import and_, select, update
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_session_factory, get_neo4j
from app.core.exceptions import NotFoundError, ValidationError
from app.models.agent import Agent, AgentRun
from app.services.blocks import block_registry
from app.websocket.manager import manager, WSServerEvent

logger = get_logger(__name__)


# ─── Execution Context ───────────────────────────────────────────────────────────


class ExecutionContext:
    """Holds state for a single agent execution run.

    Passed through the block execution chain so each block can read
    upstream outputs and write its own.
    """

    def __init__(
        self,
        agent_id: str,
        user_id: str,
        run_id: str,
        trigger_type: str,
        input_data: dict[str, Any],
        is_test: bool = False,
    ) -> None:
        self.agent_id = agent_id
        self.user_id = user_id
        self.run_id = run_id
        self.trigger_type = trigger_type
        self.input_data = input_data
        self.is_test = is_test

        # Block execution results: block_id → output dict
        self.block_outputs: dict[str, dict[str, Any]] = {}

        # Block execution metadata: block_id → {started_at, completed_at, duration_ms, status, error}
        self.block_meta: dict[str, dict[str, Any]] = {}

        # Steps log for the run
        self.steps: list[dict[str, Any]] = []

        # Memory tracking
        self.memory_nodes_created = 0
        self.memory_links_created = 0

        # Token tracking
        self.tokens_used = 0
        self.cost_cents = 0
        self.model_used: str | None = None

        # Whether the overall run has failed
        self.has_errors = False

        # Cancellation flag
        self.cancelled = False

    def add_step(self, step: dict[str, Any]) -> None:
        """Record a step in the execution log."""
        self.steps.append(step)

    async def notify(self, event: WSServerEvent) -> None:
        """Send a WebSocket notification for this execution."""
        if not self.is_test:
            await manager.send_to_user(self.user_id, event)

    def cancel(self) -> None:
        """Mark this execution as cancelled."""
        self.cancelled = True


# ─── Block Executors ─────────────────────────────────────────────────────────────


class BlockExecutor:
    """Routes block execution to the appropriate handler based on block type."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register("trigger", self._execute_trigger)
        self.register("ai", self._execute_ai)
        self.register("action", self._execute_action)
        self.register("logic", self._execute_logic)
        self.register("connector", self._execute_connector)

    def register(self, block_type: str, handler: Callable) -> None:
        """Register a handler for a block type."""
        self._handlers[block_type] = handler

    async def execute(
        self,
        block: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute a block and return its output.

        Args:
            block: The block definition (type, subtype, config).
            context: The current execution context.

        Returns:
            Block output dict.

        Raises:
            ValueError: If block type is unknown or execution fails.
        """
        block_type = block.get("type", "")
        handler = self._handlers.get(block_type)
        if not handler:
            raise ValueError(f"Unknown block type: {block_type}")

        return await handler(block, context)

    # ── Trigger blocks ─────────────────────────────────────────────────────────

    async def _execute_trigger(
        self,
        block: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute a trigger block — simply passes through the input data."""
        subtype = block.get("subtype", "")
        config = block.get("config", {})

        if subtype == "schedule":
            return {"triggered_at": datetime.now(timezone.utc).isoformat(), "cron": config.get("cron", "")}
        elif subtype == "webhook":
            return {"payload": context.input_data.get("payload", context.input_data)}
        elif subtype == "email_received":
            return context.input_data.get("email", context.input_data)
        elif subtype == "message_received":
            return context.input_data.get("message", context.input_data)
        elif subtype in ("file_changed", "form_submitted", "event"):
            return context.input_data

        return context.input_data

    # ── AI blocks ──────────────────────────────────────────────────────────────

    async def _execute_ai(
        self,
        block: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute an AI block by calling the AI service.

        Supports mock execution in test mode.
        """
        subtype = block.get("subtype", "")
        config = block.get("config", {})
        model = config.get("model", settings.ai.default_provider)
        input_text = json.dumps(context.input_data) if isinstance(context.input_data, dict) else str(context.input_data)

        context.model_used = model

        if context.is_test:
            # Mock AI response in test mode
            return await self._mock_ai_execution(subtype, config, input_text)

        # Real AI execution - call the AI service
        try:
            result = await self._call_ai_service(subtype, config, context)
            # Track token usage
            tokens = result.get("tokens_used", 0)
            context.tokens_used += tokens
            cost = self._estimate_cost(tokens, model)
            context.cost_cents += cost
            return result
        except Exception as exc:
            logger.error("AI block execution failed", subtype=subtype, error=str(exc))
            raise

    async def _mock_ai_execution(
        self,
        subtype: str,
        config: dict[str, Any],
        input_text: str,
    ) -> dict[str, Any]:
        """Generate mock AI block output for testing."""
        await asyncio.sleep(0.3)  # Simulate latency

        if subtype == "conversation":
            return {
                "response": f"[TEST] AI response based on: {config.get('system_prompt', '')[:50]}...",
                "model": config.get("model", "claude-sonnet-4"),
                "tokens_used": 50,
            }
        elif subtype == "extract":
            return {
                "extracted": {"result": "[TEST] Extracted data"},
                "tokens_used": 30,
            }
        elif subtype == "classify":
            categories = config.get("categories", [])
            return {
                "classification": categories[0]["name"] if categories else "unknown",
                "confidence": 0.92,
                "tokens_used": 20,
            }
        elif subtype == "summarize":
            return {
                "summary": "[TEST] This is a mock summary of the input text.",
                "tokens_used": 40,
            }
        elif subtype == "generate":
            return {
                "generated": f"[TEST] Generated {config.get('format', 'text')} content.",
                "format": config.get("format", "text"),
                "tokens_used": 100,
            }
        elif subtype == "transform":
            return {
                "transformed": f"[TEST] Transformed: {input_text[:100]}",
                "tokens_used": 35,
            }
        return {"result": "[TEST] AI block executed", "tokens_used": 10}

    async def _call_ai_service(
        self,
        subtype: str,
        config: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Call the AI service for real model inference.

        Placeholder — will integrate with the AI service layer.
        """
        # TODO: Integrate with AI service
        # from app.services.ai import ai_service
        # For now, return a placeholder
        await asyncio.sleep(0.1)
        return {
            "response": f"[AI] Response from {config.get('model', 'default')}",
            "model": config.get("model", "default"),
            "tokens_used": 100,
        }

    @staticmethod
    def _estimate_cost(tokens: int, model: str) -> int:
        """Estimate cost in cents based on model and token count."""
        rates = {
            "claude-sonnet-4": (3, 15),  # input, output per 1K tokens (cents)
            "claude-haiku-3": (0.25, 1.25),
            "gpt-4o": (2.5, 10),
            "gpt-4o-mini": (0.15, 0.6),
            "llama3": (0.05, 0.05),
        }
        rate = rates.get(model, (0.5, 1.5))
        # Rough estimate: half input, half output
        return round((tokens // 2 * rate[0] + tokens // 2 * rate[1]) / 1000)

    # ── Action blocks ──────────────────────────────────────────────────────────

    async def _execute_action(
        self,
        block: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute an action block — routes to integration service or simulates."""
        subtype = block.get("subtype", "")
        config = block.get("config", {})

        if context.is_test:
            return self._mock_action(subtype, config)

        # Real action execution
        return await self._execute_real_action(subtype, config, context)

    def _mock_action(self, subtype: str, config: dict[str, Any]) -> dict[str, Any]:
        """Mock action execution for test mode."""
        if subtype == "send_email":
            return {
                "status": "draft_created" if config.get("draft_only") else "sent",
                "to": config.get("to", ""),
                "subject": config.get("subject", ""),
                "message": "[TEST MODE] Email not actually sent",
            }
        elif subtype == "send_whatsapp":
            return {
                "status": "simulated",
                "to": config.get("to", ""),
                "message": "[TEST MODE] WhatsApp not actually sent",
            }
        elif subtype == "http_request":
            return {
                "status": "simulated",
                "url": config.get("url", ""),
                "method": config.get("method", "GET"),
                "response": {"status_code": 200, "body": {"test": True}},
                "message": "[TEST MODE] HTTP request not actually made",
            }
        return {
            "status": "simulated",
            "message": f"[TEST MODE] {subtype} action simulated",
        }

    async def _execute_real_action(
        self,
        subtype: str,
        config: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute a real action via the integration service.

        Placeholder — will integrate with the Integration Service.
        """
        # TODO: Route to integration service
        # from app.services.integration import integration_service
        return {
            "status": "executed",
            "action": subtype,
            "config": config,
        }

    # ── Logic blocks ────────────────────────────────────────────────────────────

    async def _execute_logic(
        self,
        block: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute a logic block (condition, filter, router, delay, loop, wait)."""
        subtype = block.get("subtype", "")
        config = block.get("config", {})

        if subtype == "condition":
            return self._execute_condition(config, context)
        elif subtype == "filter":
            return self._execute_filter(config, context)
        elif subtype == "router":
            return self._execute_router(config, context)
        elif subtype == "delay":
            return await self._execute_delay(config)
        elif subtype == "loop":
            return await self._execute_loop(config, context)
        elif subtype == "wait":
            return await self._execute_wait(config, context)

        raise ValueError(f"Unknown logic subtype: {subtype}")

    @staticmethod
    def _execute_condition(
        config: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Evaluate a condition expression and route to true/false branch."""
        expression = config.get("expression", "")
        data = context.input_data

        try:
            # Safe eval of simple expressions using data variable
            local_vars = {"data": data}
            result = bool(eval(expression, {"__builtins__": {}}, local_vars))
        except Exception as exc:
            logger.warning("Condition evaluation failed", expression=expression, error=str(exc))
            result = False

        return {
            "condition_result": result,
            "branch": "true" if result else "false",
            "label": config.get("label_true" if result else "label_false", ""),
        }

    @staticmethod
    def _execute_filter(
        config: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Filter an array based on a condition."""
        condition = config.get("condition", "True")
        array_field = config.get("input_array_field", "")
        data = context.input_data

        # Get the array to filter
        if array_field:
            items = _get_nested(data, array_field, [])
        else:
            items = data if isinstance(data, list) else [data]

        filtered = []
        for item in items:
            try:
                local_vars = {"item": item, "data": data}
                if eval(condition, {"__builtins__": {}}, local_vars):
                    filtered.append(item)
            except Exception:
                continue

        return {
            "original_count": len(items) if isinstance(items, list) else 1,
            "filtered_count": len(filtered),
            "items": filtered,
        }

    @staticmethod
    def _execute_router(
        config: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Route execution based on multiple cases (switch/case)."""
        cases = config.get("cases", [])
        data = context.input_data

        matched_case = None
        for case in cases:
            expression = case.get("expression", "")
            try:
                local_vars = {"data": data}
                if eval(expression, {"__builtins__": {}}, local_vars):
                    matched_case = case
                    break
            except Exception:
                continue

        if matched_case:
            return {
                "matched": True,
                "case_label": matched_case.get("label", ""),
                "case_index": cases.index(matched_case),
            }
        return {
            "matched": False,
            "case_label": config.get("default_case", "Other"),
            "case_index": -1,
        }

    @staticmethod
    async def _execute_delay(config: dict[str, Any]) -> dict[str, Any]:
        """Pause execution for a duration."""
        duration = config.get("duration", 5)
        unit = config.get("unit", "seconds")
        multipliers = {"seconds": 1, "minutes": 60, "hours": 3600}
        seconds = duration * multipliers.get(unit, 1)

        await asyncio.sleep(min(seconds, 300))  # Cap at 5 min
        return {"delayed_seconds": seconds}

    @staticmethod
    async def _execute_loop(
        config: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Set up loop context for iterating over data."""
        max_iterations = config.get("iterations", 10)
        array_field = config.get("input_array_field", "")
        data = context.input_data

        if array_field:
            items = _get_nested(data, array_field, [])
        else:
            items = data if isinstance(data, list) else [data]

        items = items[:max_iterations] if max_iterations > 0 else items

        return {
            "items": items,
            "total_items": len(items),
            "batch_size": config.get("batch_size", 1),
        }

    @staticmethod
    async def _execute_wait(config: dict[str, Any]) -> dict[str, Any]:
        """Wait for a condition (placeholder — simplified to a timeout)."""
        timeout_minutes = config.get("timeout_minutes", 60)
        check_interval = config.get("check_interval_seconds", 10)

        # In a real implementation, this would check the condition periodically.
        # For now, just return immediately.
        return {
            "waited_seconds": 0,
            "condition_met": True,
            "timeout_minutes": timeout_minutes,
            "check_interval_seconds": check_interval,
        }

    # ── Connector blocks ───────────────────────────────────────────────────────

    async def _execute_connector(
        self,
        block: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute a connector block — calls the integration service.
        
        Placeholder — will be integrated with the Integration Service.
        """
        subtype = block.get("subtype", "")
        config = block.get("config", {})

        if context.is_test:
            return {
                "status": "simulated",
                "connector": subtype,
                "message": f"[TEST MODE] {subtype} connector simulated",
            }

        # TODO: Route to integration connector
        return {
            "status": "executed",
            "connector": subtype,
            "output": config,
        }


# ─── Execution Engine ────────────────────────────────────────────────────────────


class ExecutionEngine:
    """The agent execution engine — runs agents through their block graph."""

    def __init__(self) -> None:
        self.block_executor = BlockExecutor()

    # ── Main entry point ───────────────────────────────────────────────────────

    async def run_agent(
        self,
        agent_id: str,
        trigger_type: str = "manual",
        input_data: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute an agent by running all blocks in topological order.

        This is the main entry point for agent execution.

        Args:
            agent_id: UUID of the agent to execute.
            trigger_type: How the agent was triggered ('manual', 'schedule', 'webhook', 'event').
            input_data: Input data to pass to the agent.
            user_id: User ID initiating the execution.

        Returns:
            Dict with execution results: run_id, status, steps, output_data, etc.
        """
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(Agent).where(Agent.id == uuid.UUID(agent_id))
            )
            agent = result.scalar_one_or_none()
            if not agent:
                raise NotFoundError(
                    message=f"Agent not found: {agent_id}",
                    resource_type="agent",
                    resource_id=agent_id,
                )

            uid = user_id or str(agent.user_id)
            run = AgentRun(
                agent_id=agent.id,
                user_id=uuid.UUID(uid),
                trigger_type=trigger_type,
                status="running",
                input_data=input_data or {},
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)

        run_id = str(run.id)
        context = ExecutionContext(
            agent_id=agent_id,
            user_id=uid,
            run_id=run_id,
            trigger_type=trigger_type,
            input_data=input_data or {},
            is_test=False,
        )

        try:
            result = await self._execute_blocks(agent.definition, context, agent.name)

            # Update run record
            async with factory() as session:
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == uuid.UUID(run_id))
                    .values(
                        status=result["status"],
                        output_data=result.get("output_data"),
                        error_message=result.get("error_message"),
                        steps=context.steps,
                        memory_nodes_created=context.memory_nodes_created,
                        memory_links_created=context.memory_links_created,
                        model_used=context.model_used,
                        tokens_used=context.tokens_used,
                        completed_at=datetime.now(timezone.utc),
                        duration_ms=result.get("duration_ms", 0),
                        cost_cents=context.cost_cents,
                    )
                )
                await session.commit()

        except Exception as exc:
            logger.exception("Agent execution failed", agent_id=agent_id, run_id=run_id)

            # Update run as failed
            async with factory() as session:
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == uuid.UUID(run_id))
                    .values(
                        status="failed",
                        error_message=str(exc),
                        steps=context.steps,
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()

            result = {
                "status": "failed",
                "error_message": str(exc),
                "steps": context.steps,
            }

        # Update agent stats
        await self._update_agent_stats(agent_id, result["status"])

        return {
            "run_id": run_id,
            "agent_id": agent_id,
            **result,
        }

    async def _execute_blocks(
        self,
        definition: dict[str, Any],
        context: ExecutionContext,
        agent_name: str,
    ) -> dict[str, Any]:
        """Execute blocks in topological order."""
        blocks: list[dict[str, Any]] = definition.get("blocks", [])
        edges: list[dict[str, Any]] = definition.get("edges", [])

        if not blocks:
            return {
                "status": "completed",
                "output_data": {},
                "error_message": None,
                "duration_ms": 0,
            }

        # Notify start
        await context.notify(
            manager.event_agent_running(
                agent_id=context.agent_id,
                agent_name=agent_name,
                run_id=context.run_id,
            )
        )

        start_time = time.monotonic()

        # Build adjacency list for topological sort
        block_map = {b["id"]: b for b in blocks}
        adj: dict[str, list[str]] = {b["id"]: [] for b in blocks}
        in_degree: dict[str, int] = {b["id"]: 0 for b in blocks}

        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source in adj and target in adj:
                adj[source].append(target)
                in_degree[target] = in_degree.get(target, 0) + 1

        # Topological sort (Kahn's algorithm)
        queue = [bid for bid, deg in in_degree.items() if deg == 0]
        execution_order: list[str] = []

        while queue:
            # Sort by block type priority: triggers first, then AI, then logic, then action/connector
            queue.sort(key=lambda bid: _block_type_priority(block_map.get(bid, {}).get("type", "")))
            node = queue.pop(0)
            execution_order.append(node)

            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(execution_order) != len(blocks):
            raise ValidationError(message="Agent has circular dependencies")

        # Execute blocks in order
        output_data: dict[str, Any] = {}
        for block_id in execution_order:
            if context.cancelled:
                break

            block = block_map[block_id]
            block_start = time.monotonic()

            # Set context input to the accumulated data + previous block outputs
            context.input_data = output_data

            # Notify step start
            step_event = {
                "block_id": block_id,
                "block_type": block.get("type", ""),
                "block_subtype": block.get("subtype", ""),
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
            context.add_step({**step_event, "output": None, "error": None})

            try:
                block_output = await self.block_executor.execute(block, context)
                block_duration = (time.monotonic() - block_start) * 1000

                output_data[block_id] = block_output
                context.block_outputs[block_id] = block_output

                # Update step
                step_event["status"] = "completed"
                step_event["duration_ms"] = int(block_duration)
                step_event["output"] = block_output

                # Notify step
                await context.notify(
                    manager.event_agent_step(
                        agent_id=context.agent_id,
                        step=step_event,
                    )
                )

            except Exception as exc:
                block_duration = (time.monotonic() - block_start) * 1000
                error_msg = str(exc)

                step_event["status"] = "error"
                step_event["duration_ms"] = int(block_duration)
                step_event["error"] = error_msg

                # Notify error — but don't fail the whole agent
                context.has_errors = True
                logger.warning("Block execution error", block_id=block_id, error=error_msg)

                await context.notify(
                    WSServerEvent(
                        type="agent.error",
                        payload={
                            "agent_id": context.agent_id,
                            "run_id": context.run_id,
                            "block_id": block_id,
                            "error": error_msg,
                        },
                    )
                )

        total_duration = (time.monotonic() - start_time) * 1000
        status = "cancelled" if context.cancelled else ("completed" if not context.has_errors else "completed_with_errors")

        # Notify completion
        await context.notify(
            manager.event_agent_completed(
                agent_id=context.agent_id,
                agent_name=agent_name,
                result={
                    "status": status,
                    "output_data": output_data,
                    "duration_ms": int(total_duration),
                },
                run_id=context.run_id,
            )
        )

        return {
            "status": status,
            "output_data": output_data,
            "error_message": "Some blocks had errors" if context.has_errors else None,
            "duration_ms": int(total_duration),
            "steps": context.steps,
        }

    # ── Sync execution ─────────────────────────────────────────────────────────

    async def execute_agent_sync(
        self,
        agent_id: str,
        input_data: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute an agent synchronously (for testing/direct calls).

        Returns the full execution result directly.
        """
        return await self.run_agent(
            agent_id=agent_id,
            trigger_type="manual",
            input_data=input_data,
            user_id=user_id,
        )

    # ── Async execution ────────────────────────────────────────────────────────

    async def execute_agent_async(
        self,
        agent_id: str,
        input_data: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Queue agent execution for the Celery background worker.

        Returns immediately with a task ID.
        """
        from app.tasks.agent_tasks import run_agent_task

        task = run_agent_task.delay(
            agent_id=agent_id,
            user_id=user_id or "",
            trigger_type="manual",
            input_data=input_data or {},
        )

        return {
            "task_id": task.id,
            "agent_id": agent_id,
            "status": "queued",
            "message": "Agent execution queued for background processing",
        }

    # ── Cancel ─────────────────────────────────────────────────────────────────

    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        """Cancel a running agent execution.

        Args:
            run_id: UUID of the AgentRun to cancel.

        Returns:
            Updated run status.
        """
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == uuid.UUID(run_id))
            )
            run = result.scalar_one_or_none()
            if not run:
                raise NotFoundError(message=f"Run not found: {run_id}")

            if run.status != "running":
                raise ValidationError(message=f"Cannot cancel run with status '{run.status}'")

            run.status = "cancelled"
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()

            return {
                "run_id": run_id,
                "status": "cancelled",
            }

    # ── Run log ────────────────────────────────────────────────────────────────

    async def get_run_log(self, run_id: str) -> dict[str, Any]:
        """Get the full execution log for a run.

        Args:
            run_id: UUID of the AgentRun.

        Returns:
            Full run details with step-by-step log.
        """
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == uuid.UUID(run_id))
            )
            run = result.scalar_one_or_none()
            if not run:
                raise NotFoundError(message=f"Run not found: {run_id}")

            return {
                "id": str(run.id),
                "agent_id": str(run.agent_id),
                "user_id": str(run.user_id),
                "trigger_type": run.trigger_type,
                "status": run.status,
                "input_data": run.input_data,
                "output_data": run.output_data,
                "error_message": run.error_message,
                "error_details": run.error_details,
                "steps": run.steps,
                "memory_nodes_created": run.memory_nodes_created,
                "memory_links_created": run.memory_links_created,
                "model_used": run.model_used,
                "tokens_used": run.tokens_used,
                "duration_ms": run.duration_ms,
                "cost_cents": run.cost_cents,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            }

    # ── Test mode ──────────────────────────────────────────────────────────────

    async def test_agent(
        self,
        agent_id: str,
        input_data: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute an agent in test mode — no real side effects.

        Test mode:
        - Does NOT create real memory nodes
        - Does NOT send real messages
        - Does NOT make real HTTP requests
        - Mocks AI responses (no token cost)

        Args:
            agent_id: UUID of the agent to test.
            input_data: Sample input data for testing.
            user_id: User ID.

        Returns:
            Test execution results.
        """
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(Agent).where(Agent.id == uuid.UUID(agent_id))
            )
            agent = result.scalar_one_or_none()
            if not agent:
                raise NotFoundError(message=f"Agent not found: {agent_id}")

            uid = user_id or str(agent.user_id)
            run = AgentRun(
                agent_id=agent.id,
                user_id=uuid.UUID(uid),
                trigger_type="manual",
                status="running",
                input_data=input_data or {},
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)

        run_id = str(run.id)
        context = ExecutionContext(
            agent_id=agent_id,
            user_id=uid,
            run_id=run_id,
            trigger_type="manual",
            input_data=input_data or {},
            is_test=True,
        )

        try:
            result = await self._execute_blocks(agent.definition, context, f"{agent.name} (TEST)")

            # Update run (test runs save results too for debugging)
            async with factory() as session:
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == uuid.UUID(run_id))
                    .values(
                        status=result["status"],
                        output_data=result.get("output_data"),
                        steps=context.steps,
                        completed_at=datetime.now(timezone.utc),
                        duration_ms=result.get("duration_ms", 0),
                    )
                )
                await session.commit()

        except Exception as exc:
            async with factory() as session:
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == uuid.UUID(run_id))
                    .values(
                        status="failed",
                        error_message=str(exc),
                        steps=context.steps,
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()

            result = {
                "status": "failed",
                "error_message": str(exc),
                "steps": context.steps,
            }

        return {
            "run_id": run_id,
            "agent_id": agent_id,
            "test_mode": True,
            "no_real_side_effects": True,
            **result,
        }

    # ── Memory impact estimation ───────────────────────────────────────────────

    @staticmethod
    def calculate_memory_impact(definition: dict[str, Any]) -> dict[str, Any]:
        """Estimate how many memory nodes and links an agent run will create.

        Based on the number and type of blocks in the definition.
        AI blocks tend to create the most memory entries.

        Args:
            definition: The agent definition dict.

        Returns:
            Dict with estimated memory_nodes and memory_links.
        """
        blocks = definition.get("blocks", [])
        edges = definition.get("edges", [])

        nodes_estimate = 0
        links_estimate = len(edges)  # Each edge could create a link

        for block in blocks:
            btype = block.get("type", "")
            if btype == "ai":
                nodes_estimate += 3  # AI blocks create more memory
            elif btype == "trigger":
                nodes_estimate += 1
            elif btype == "action":
                nodes_estimate += 2  # Actions create result records
            elif btype == "logic":
                nodes_estimate += 1
            elif btype == "connector":
                nodes_estimate += 1

        return {
            "estimated_memory_nodes": nodes_estimate,
            "estimated_memory_links": links_estimate,
            "blocks_count": len(blocks),
            "edges_count": len(edges),
        }

    # ── Agent stats update ─────────────────────────────────────────────────────

    @staticmethod
    async def _update_agent_stats(agent_id: str, run_status: str) -> None:
        """Update an agent's performance stats after a run."""
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(Agent).where(Agent.id == uuid.UUID(agent_id))
            )
            agent = result.scalar_one_or_none()
            if not agent:
                return

            agent.total_runs += 1
            if run_status == "completed":
                agent.successful_runs += 1
            agent.success_rate = (
                agent.successful_runs / agent.total_runs
                if agent.total_runs > 0
                else 0.0
            )
            await session.commit()


# ─── Utility Helpers ─────────────────────────────────────────────────────────────


def _get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """Get a nested value from a dict using a dot-separated path.

    Example: _get_nested({"a": {"b": "c"}}, "a.b") → "c"
    """
    if not path:
        return data
    keys = path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def _block_type_priority(block_type: str) -> int:
    """Sort key for block execution order.

    Priority order: trigger (0) → ai (1) → logic (2) → action/connector (3)
    """
    priorities = {
        "trigger": 0,
        "ai": 1,
        "logic": 2,
        "action": 3,
        "connector": 3,
    }
    return priorities.get(block_type, 99)


# ─── Singleton ───────────────────────────────────────────────────────────────────

execution_engine = ExecutionEngine()

__all__ = [
    "execution_engine",
    "ExecutionEngine",
    "ExecutionContext",
    "BlockExecutor",
]
