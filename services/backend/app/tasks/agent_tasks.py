"""
Agent Celery Tasks — Background agent execution, schedule checking, and maintenance.

Registered as Celery tasks that can be called asynchronously.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from celery import Celery
from structlog import get_logger

from app.core.config import settings
from app.services.execution import execution_engine
from app.services.trigger import trigger_service

logger = get_logger(__name__)


# ─── Celery App ─────────────────────────────────────────────────────────────────

celery_app = Celery(
    "anansi",
    broker=settings.redis.url.replace("redis://", "redis://") + "/1",
    backend=settings.redis.url.replace("redis://", "redis://") + "/2",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "check-schedule-triggers": {
            "task": "app.tasks.agent_tasks.schedule_check_task",
            "schedule": 60.0,  # Every 60 seconds
        },
        "cleanup-stale-runs": {
            "task": "app.tasks.agent_tasks.cleanup_stale_runs",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)


# ─── Async Runner ───────────────────────────────────────────────────────────────


def _run_async(coro: Any) -> Any:
    """Run an async function in a new event loop.

    Celery workers are synchronous, so we need to bridge to async.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─── Agent Execution ────────────────────────────────────────────────────────────


@celery_app.task(bind=True, name="run_agent_task", max_retries=3, default_retry_delay=30)
def run_agent_task(
    self: Any,
    agent_id: str,
    user_id: str,
    trigger_type: str = "manual",
    input_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute an agent in the background via Celery.

    This is the main Celery task for async agent execution.
    Retries up to 3 times with 30s delay on failure.

    Args:
        agent_id: UUID of the agent to execute.
        user_id: UUID of the user who initiated the run.
        trigger_type: How the agent was triggered.
        input_data: Optional input data for the agent.

    Returns:
        Execution result dict.
    """
    logger.info(
        "Celery agent task starting",
        task_id=self.request.id,
        agent_id=agent_id,
        trigger_type=trigger_type,
    )

    try:
        result = _run_async(
            execution_engine.run_agent(
                agent_id=agent_id,
                trigger_type=trigger_type,
                input_data=input_data or {},
                user_id=user_id,
            )
        )
        logger.info(
            "Celery agent task completed",
            task_id=self.request.id,
            agent_id=agent_id,
            status=result.get("status"),
        )
        return result
    except Exception as exc:
        logger.exception(
            "Celery agent task failed",
            task_id=self.request.id,
            agent_id=agent_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)


# ─── Schedule Check ─────────────────────────────────────────────────────────────


@celery_app.task(name="schedule_check_task")
def schedule_check_task() -> list[dict[str, Any]]:
    """Check all scheduled triggers and fire any that are due.

    Runs every 60 seconds via Celery beat.
    """
    logger.debug("Schedule check task running")
    try:
        triggered = _run_async(trigger_service.evaluate_schedule_triggers())
        if triggered:
            logger.info("Schedule triggers fired", count=len(triggered))
        return triggered
    except Exception as exc:
        logger.error("Schedule check failed", error=str(exc))
        return []


# ─── Stale Run Cleanup ──────────────────────────────────────────────────────────


@celery_app.task(name="cleanup_stale_runs")
def cleanup_stale_runs() -> dict[str, Any]:
    """Timeout agent runs stuck in 'running' state for more than 30 minutes.

    Runs every 5 minutes via Celery beat.
    """
    logger.debug("Stale run cleanup task running")

    try:
        from sqlalchemy import and_, select, update
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.events import get_session_factory
        from app.models.agent import AgentRun

        async def _cleanup() -> dict[str, Any]:
            factory = get_session_factory()
            async with factory() as session:
                # Find runs stuck in 'running' state for >30 minutes
                cutoff = datetime.now(timezone.utc).timestamp() - 1800  # 30 min
                cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)

                result = await session.execute(
                    select(AgentRun).where(
                        and_(
                            AgentRun.status == "running",
                            AgentRun.started_at < cutoff_dt,
                        )
                    )
                )
                stale_runs = result.scalars().all()

                if not stale_runs:
                    return {"cleaned": 0, "message": "No stale runs found"}

                # Update them to 'failed'
                run_ids = [run.id for run in stale_runs]
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id.in_(run_ids))
                    .values(
                        status="failed",
                        error_message="Run timed out after 30 minutes",
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()

                logger.info("Cleaned up stale runs", count=len(stale_runs))
                return {
                    "cleaned": len(stale_runs),
                    "run_ids": [str(rid) for rid in run_ids],
                }

        return _run_async(_cleanup())

    except Exception as exc:
        logger.error("Stale run cleanup failed", error=str(exc))
        return {"cleaned": 0, "error": str(exc)}


# ─── Block Registry Cache ──────────────────────────────────────────────────────


@celery_app.task(name="cache_block_registry")
def cache_block_registry() -> dict[str, Any]:
    """Cache the block registry in Redis for fast API access.

    Can be called on deployment or on demand.
    """
    try:
        from app.services.blocks import block_registry
        from app.core.events import get_redis

        blocks = block_registry.list_all_dicts()

        async def _cache() -> int:
            redis = get_redis()
            await redis.set("block_registry", json.dumps(blocks), ex=86400)  # 24h TTL
            return len(blocks)

        import json
        count = _run_async(_cache())
        logger.info("Block registry cached", count=count)
        return {"cached": count}

    except Exception as exc:
        logger.error("Block registry caching failed", error=str(exc))
        return {"cached": 0, "error": str(exc)}


__all__ = [
    "celery_app",
    "run_agent_task",
    "schedule_check_task",
    "cleanup_stale_runs",
    "cache_block_registry",
]
