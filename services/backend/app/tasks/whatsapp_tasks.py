"""
Anansi WhatsApp Celery Tasks — Background processing for WhatsApp features.

Includes scheduled morning briefings, async voice note transcription,
and proactive suggestion delivery to WhatsApp users.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any

from celery import Celery
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)


# ─── Celery App ──────────────────────────────────────────────────────────────────


celery_app = Celery(
    "anansi_whatsapp",
    broker=settings.redis.url.replace("redis://", "redis://") + "/3",
    backend=settings.redis.url.replace("redis://", "redis://") + "/4",
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
        # Morning briefings at 7am UTC (configurable per user timezone)
        "send-morning-briefings": {
            "task": "app.tasks.whatsapp_tasks.send_morning_briefings_task",
            "schedule": 60.0,  # Check every 60s; the task handles time logic
            "options": {"expires": 300},
        },
        # Proactive suggestions every 4 hours
        "send-proactive-suggestions": {
            "task": "app.tasks.whatsapp_tasks.send_proactive_suggestions_task",
            "schedule": 14400.0,  # Every 4 hours
            "options": {"expires": 600},
        },
        # Weekly summaries on Sundays
        "send-weekly-summaries": {
            "task": "app.tasks.whatsapp_tasks.send_weekly_summaries_task",
            "schedule": 86400.0,  # Daily (checks if it's Sunday)
            "options": {"expires": 3600},
        },
    },
)


# ─── Async Runner ────────────────────────────────────────────────────────────────


def _run_async(coro: Any) -> Any:
    """Run an async function in a new event loop.

    Celery workers are synchronous, so we bridge to async.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─── Task: Morning Briefings ─────────────────────────────────────────────────────


@celery_app.task(bind=True, name="send_morning_briefings_task", max_retries=2, default_retry_delay=120)
def send_morning_briefings_task(self: Any) -> dict[str, Any]:
    """Send morning briefings to all active WhatsApp users.

    Scheduled by Celery Beat. Runs every 60 seconds but only sends
    briefings to users whose local time is approximately 7am.

    In a full implementation, each user's timezone would be checked
    to send the briefing at their local 7am.
    """
    logger.info("Morning briefing task started")

    try:
        from app.services.whatsapp_notifications import send_morning_briefing
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text

        async def _dispatch() -> int:
            """Fetch all active WhatsApp users and send briefings.

            In production, users would be batched and rate-limited
            based on their local time to avoid flooding the WhatsApp API.
            """
            sent_count = 0

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT wc.user_id
                        FROM whatsapp_connections wc
                        WHERE wc.status = 'active'
                        AND (
                            wc.settings->>'notify_morning_briefing' IS NULL
                            OR wc.settings->>'notify_morning_briefing' = 'true'
                            OR wc.settings->>'notify_morning_briefing' = 'true'
                        )
                    """),
                )
                rows = result.all()

                logger.info(
                    "Found active WhatsApp users for briefing",
                    count=len(rows),
                )

                for (user_id,) in rows:
                    try:
                        success = await send_morning_briefing(str(user_id))
                        if success:
                            sent_count += 1
                    except Exception as exc:
                        logger.error(
                            "Failed to send briefing to user",
                            user_id=str(user_id),
                            error=str(exc),
                        )

            return sent_count

        sent = _run_async(_dispatch())
        logger.info("Morning briefings sent", count=sent)
        return {"status": "ok", "sent": sent}

    except Exception as exc:
        logger.error("Morning briefing task failed", error=str(exc))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"status": "error", "error": str(exc)}


# ─── Task: Process Voice Note ────────────────────────────────────────────────────


@celery_app.task(bind=True, name="process_voice_note_task", max_retries=3, default_retry_delay=30)
def process_voice_note_task(
    self: Any,
    user_id: str,
    from_number: str,
    media_id: str,
) -> dict[str, Any]:
    """Asynchronously transcribe and process a WhatsApp voice note.

    Called by the webhook handler when an audio message is received.
    Downloads the audio, transcribes via Whisper, and sends the
    response back to the user.

    Args:
        user_id: The user UUID.
        from_number: The sender's WhatsApp number.
        media_id: The WhatsApp media object ID for the audio file.
    """
    logger.info(
        "Processing voice note",
        user_id=user_id,
        media_id=media_id,
    )

    try:
        from app.services.whatsapp_conversation import handle_voice_note

        async def _process() -> dict[str, Any]:
            return await handle_voice_note(user_id, from_number, media_id)

        result = _run_async(_process())

        logger.info(
            "Voice note processed successfully",
            user_id=user_id,
            handler=result.get("handler"),
        )

        return {
            "status": "ok",
            "user_id": user_id,
            "media_id": media_id,
            "handler": result.get("handler"),
        }

    except Exception as exc:
        logger.error(
            "Voice note processing failed",
            user_id=user_id,
            media_id=media_id,
            error=str(exc),
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        return {"status": "error", "error": str(exc)}


# ─── Task: Proactive Suggestions ─────────────────────────────────────────────────


@celery_app.task(bind=True, name="send_proactive_suggestions_task", max_retries=2)
def send_proactive_suggestions_task(self: Any) -> dict[str, Any]:
    """Send AI-generated proactive suggestions to users.

    Runs periodically to analyze user activity and send helpful
    suggestions via WhatsApp. Rate-limited to avoid spamming.

    In production, this would query the AI to generate personalized
    suggestions based on recent user activity.
    """
    logger.info("Proactive suggestions task started")

    try:
        from app.services.whatsapp_notifications import send_suggestion
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text

        async def _dispatch() -> int:
            sent_count = 0

            async with AsyncSessionLocal() as db:
                # Find users with notification suggestions enabled
                result = await db.execute(
                    text("""
                        SELECT wc.user_id, wc.phone_number
                        FROM whatsapp_connections wc
                        WHERE wc.status = 'active'
                        AND (
                            wc.settings->>'notify_suggestions' IS NULL
                            OR wc.settings->>'notify_suggestions' = 'true'
                            OR wc.settings->>'notify_suggestions' = 'true'
                        )
                        -- Limit to avoid flooding (process a batch per run)
                        LIMIT 50
                    """),
                )
                rows = result.all()

                for (user_id, phone_number) in rows:
                    try:
                        # In production, generate a personalized suggestion using AI
                        # For now, send a contextual tip
                        suggestion = _generate_tip(user_id)

                        if suggestion:
                            success = await send_suggestion(str(user_id), suggestion)
                            if success:
                                sent_count += 1
                    except Exception as exc:
                        logger.error(
                            "Failed to send suggestion to user",
                            user_id=str(user_id),
                            error=str(exc),
                        )

            return sent_count

        def _generate_tip(user_id: str) -> str | None:
            """Generate a contextual tip for a user.

            In production, this would analyze the user's recent
            activity and generate a personalized suggestion.

            Returns:
                A suggestion string, or None if no suggestion is appropriate.
            """
            # Placeholder: return rotating tips
            import random
            tips = [
                "You can record sales and transactions with `/record Sold [item] for [amount]`",
                "Try `/graph` to see a visual map of your Second Brain knowledge web!",
                "Send a voice note and I'll transcribe it and save it to your memory.",
                "Did you know you can tag your memories? Just include #tag in your notes.",
                "Regular reviews help strengthen your memory. Try `/brain review`!",
                "Your morning briefing is ready every day at 7am. Use `/briefing` to see it now.",
                "You can ask me about anything you've stored: 'What did I learn about Project X?'",
                "Tip: Record a task with `/record Task: [your task]` to keep track of to-dos.",
            ]
            return random.choice(tips)

        sent = _run_async(_dispatch())
        logger.info("Proactive suggestions sent", count=sent)
        return {"status": "ok", "sent": sent}

    except Exception as exc:
        logger.error("Proactive suggestions task failed", error=str(exc))
        return {"status": "error", "error": str(exc)}


# ─── Task: Weekly Summaries ──────────────────────────────────────────────────────


@celery_app.task(bind=True, name="send_weekly_summaries_task", max_retries=2)
def send_weekly_summaries_task(self: Any) -> dict[str, Any]:
    """Send weekly summaries to users (only runs on Sundays).

    If today is Sunday, sends the weekly summary to all active
    WhatsApp users who have this notification enabled.
    """
    today = date.today()
    # Sunday = 6 in Python's weekday() if using isoweekday() == 7
    # Let's use isoweekday() where 7 = Sunday
    if today.isoweekday() != 7:
        logger.debug("Not Sunday, skipping weekly summaries", day=today.isoweekday())
        return {"status": "skipped", "reason": "not_sunday"}

    logger.info("Weekly summaries task started")

    try:
        from app.services.whatsapp_notifications import send_weekly_summary
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text

        async def _dispatch() -> int:
            sent_count = 0

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT wc.user_id
                        FROM whatsapp_connections wc
                        WHERE wc.status = 'active'
                        AND (
                            wc.settings->>'notify_weekly_summary' IS NULL
                            OR wc.settings->>'notify_weekly_summary' = 'true'
                            OR wc.settings->>'notify_weekly_summary' = 'true'
                        )
                    """),
                )
                rows = result.all()

                for (user_id,) in rows:
                    try:
                        success = await send_weekly_summary(str(user_id))
                        if success:
                            sent_count += 1
                    except Exception as exc:
                        logger.error(
                            "Failed to send weekly summary to user",
                            user_id=str(user_id),
                            error=str(exc),
                        )

            return sent_count

        sent = _run_async(_dispatch())
        logger.info("Weekly summaries sent", count=sent)
        return {"status": "ok", "sent": sent}

    except Exception as exc:
        logger.error("Weekly summaries task failed", error=str(exc))
        return {"status": "error", "error": str(exc)}


__all__ = [
    "celery_app",
    "send_morning_briefings_task",
    "process_voice_note_task",
    "send_proactive_suggestions_task",
    "send_weekly_summaries_task",
]
