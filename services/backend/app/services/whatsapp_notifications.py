"""
Anansi WhatsApp Notification Dispatcher — Proactive messaging over WhatsApp.

Sends daily briefings, agent results, alerts, suggestions, insights,
and reminders to users via WhatsApp, respecting their notification
preferences.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_db_session

logger = get_logger(__name__)


# ─── Settings Key Constants ──────────────────────────────────────────────────────

SETTING_MORNING_BRIEFING = "notify_morning_briefing"
SETTING_AGENT_COMPLETED = "notify_agent_completed"
SETTING_ALERTS = "notify_alerts"
SETTING_SUGGESTIONS = "notify_suggestions"
SETTING_WEEKLY_SUMMARY = "notify_weekly_summary"
SETTING_REVIEW_REMINDER = "notify_review_reminder"
SETTING_BRAIN_INSIGHT = "notify_brain_insight"


# ─── Dispatch Helpers ────────────────────────────────────────────────────────────


async def _get_active_whatsapp_users(
    db: AsyncSession,
    *,
    setting_key: str | None = None,
) -> list[dict[str, Any]]:
    """Get all users with active WhatsApp connections, optionally filtered by a setting.

    Args:
        db: Database session.
        setting_key: If provided, only return users who have this setting enabled.

    Returns:
        List of dicts with 'user_id', 'phone_number', and 'settings'.
    """
    query = """
        SELECT wc.user_id, wc.phone_number, wc.settings
        FROM whatsapp_connections wc
        WHERE wc.status = 'active'
    """
    params: dict[str, Any] = {}

    if setting_key:
        query += " AND (wc.settings->>:setting_key IS NULL OR wc.settings->>:setting_key = 'true' OR wc.settings->>:setting_key = true)"
        params["setting_key"] = setting_key

    result = await db.execute(text(query), params)
    rows = result.all()

    users = []
    for row in rows:
        users.append({
            "user_id": str(row[0]),
            "phone_number": row[1],
            "settings": row[2] if isinstance(row[2], dict) else {},
        })

    return users


async def _send_whatsapp_message(user_id: str, to_number: str, message: str) -> bool:
    """Send a message via WhatsApp service.

    Args:
        user_id: The user UUID.
        to_number: The recipient phone number.
        message: The message text.

    Returns:
        True if sent successfully, False otherwise.
    """
    from app.services.whatsapp import WhatsAppService

    db = await anext(get_db_session())
    try:
        svc = WhatsAppService(db=db)
        result = await svc.send_message(user_id, to_number, message)
        return result.status == "sent"
    except Exception as exc:
        logger.error(
            "Failed to send WhatsApp notification",
            user_id=user_id,
            error=str(exc),
        )
        return False
    finally:
        await db.close()


# ─── Notification Senders ────────────────────────────────────────────────────────


async def send_morning_briefing(user_id: str) -> bool:
    """Send a morning briefing to a specific user via WhatsApp.

    Scheduled for 7am daily. Provides AI summary of the day ahead,
    brain stats, and reminders.

    Args:
        user_id: The target user UUID.

    Returns:
        True if sent successfully.
    """
    db = await anext(get_db_session())
    try:
        # Get user's phone and check preference
        result = await db.execute(
            text("""
                SELECT phone_number, settings FROM whatsapp_connections
                WHERE user_id = :user_id AND status = 'active'
            """),
            {"user_id": user_id},
        )
        row = result.first()
        if not row:
            return False

        phone_number = row[0]
        settings_dict = row[1] if isinstance(row[1], dict) else {}

        # Check opt-in
        pref = settings_dict.get(SETTING_MORNING_BRIEFING, True)
        if not pref:
            logger.debug("User opted out of morning briefing", user_id=user_id)
            return False

        today = date.today()

        # Gather briefing data
        brain_result = await db.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM memory_nodes WHERE user_id = :uid) as nodes,
                    (SELECT COUNT(*) FROM memory_nodes WHERE user_id = :uid
                        AND next_review_at IS NOT NULL AND next_review_at <= :now) as reviews
            """),
            {"uid": user_id, "now": datetime.now(timezone.utc)},
        )
        brain_row = brain_result.first()
        total_nodes = brain_row[0] if brain_row else 0
        reviews_due = brain_row[1] if brain_row else 0

        # Weather placeholder
        # TODO: Integrate with weather API based on user's timezone/city

        # Generate briefing
        day_name = today.strftime("%A")

        briefing = (
            f"🌅 *Good Morning!*\n"
            f"📅 {day_name}, {today.strftime('%B %d, %Y')}\n\n"
        )

        if total_nodes > 0:
            briefing += f"🧠 *Your Second Brain:* {total_nodes} memories stored\n"
        if reviews_due > 0:
            briefing += f"📚 *{reviews_due} memories* due for review today\n\n"
        else:
            briefing += "\n"

        briefing += (
            "✨ *Quick actions:*\n"
            "  • `/briefing` — Full briefing\n"
            "  • `/tasks` — Today's tasks\n"
            "  • `/brain` — Brain stats\n"
            "  • Just chat with me!\n\n"
            "Have a great day! 🕷️"
        )

        success = await _send_whatsapp_message(user_id, phone_number, briefing)
        if success:
            logger.info("Morning briefing sent", user_id=user_id)
        return success

    except Exception as exc:
        logger.error("Failed to send morning briefing", user_id=user_id, error=str(exc))
        return False
    finally:
        await db.close()


async def send_agent_completed(
    user_id: str,
    agent_name: str,
    result: dict[str, Any],
) -> bool:
    """Notify a user that an agent has finished execution.

    Args:
        user_id: The user UUID.
        agent_name: The name of the agent that completed.
        result: The agent's output data.

    Returns:
        True if sent successfully.
    """
    db = await anext(get_db_session())
    try:
        row = await _get_user_phone_with_setting(
            db, user_id, SETTING_AGENT_COMPLETED, default=True
        )
        if not row:
            return False

        phone_number = row[0]
        memories_created = result.get("memory_nodes_created", 0)
        links_created = result.get("memory_links_created", 0)
        status = result.get("status", "completed")

        status_icon = "✅" if status == "completed" else "❌"
        message = (
            f"{status_icon} *Agent Completed: {agent_name}*\n\n"
            f"Status: {status}\n"
        )

        if memories_created:
            message += f"🧠 New memories: {memories_created}\n"
        if links_created:
            message += f"🔗 New connections: {links_created}\n"

        if result.get("output_summary"):
            message += f"\n📝 {result['output_summary']}"

        return await _send_whatsapp_message(user_id, phone_number, message)

    except Exception as exc:
        logger.error("Failed to send agent completed notification", user_id=user_id, error=str(exc))
        return False
    finally:
        await db.close()


async def send_alert(user_id: str, message: str) -> bool:
    """Send an alert about something needing attention.

    Args:
        user_id: The user UUID.
        message: The alert message content.

    Returns:
        True if sent successfully.
    """
    db = await anext(get_db_session())
    try:
        row = await _get_user_phone_with_setting(
            db, user_id, SETTING_ALERTS, default=True
        )
        if not row:
            return False

        phone_number = row[0]
        alert_text = f"⚠️ *Alert*\n\n{message}"

        return await _send_whatsapp_message(user_id, phone_number, alert_text)

    except Exception as exc:
        logger.error("Failed to send alert", user_id=user_id, error=str(exc))
        return False
    finally:
        await db.close()


async def send_suggestion(user_id: str, suggestion: str) -> bool:
    """Send an AI proactive suggestion to a user.

    Args:
        user_id: The user UUID.
        suggestion: The suggestion text.

    Returns:
        True if sent successfully.
    """
    db = await anext(get_db_session())
    try:
        row = await _get_user_phone_with_setting(
            db, user_id, SETTING_SUGGESTIONS, default=True
        )
        if not row:
            return False

        phone_number = row[0]
        sug_text = f"💡 *Suggestion*\n\n{suggestion}"

        return await _send_whatsapp_message(user_id, phone_number, sug_text)

    except Exception as exc:
        logger.error("Failed to send suggestion", user_id=user_id, error=str(exc))
        return False
    finally:
        await db.close()


async def send_weekly_summary(user_id: str) -> bool:
    """Send a weekly summary to a user on Sunday evening.

    Covers the past week's activity, brain growth, and insights.

    Args:
        user_id: The user UUID.

    Returns:
        True if sent successfully.
    """
    db = await anext(get_db_session())
    try:
        row = await _get_user_phone_with_setting(
            db, user_id, SETTING_WEEKLY_SUMMARY, default=True
        )
        if not row:
            return False

        phone_number = row[0]
        today = date.today()
        week_ago = date.fromordinal(today.toordinal() - 7)

        # Gather weekly stats
        stats_result = await db.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM memory_nodes WHERE user_id = :uid
                        AND created_at::date >= :week_start) as new_nodes,
                    (SELECT COUNT(*) FROM memory_links WHERE user_id = :uid
                        AND created_at::date >= :week_start) as new_links,
                    (SELECT COUNT(*) FROM agent_runs WHERE user_id = :uid
                        AND started_at::date >= :week_start) as agent_runs,
                    (SELECT COUNT(*) FROM memory_reviews WHERE user_id = :uid
                        AND created_at::date >= :week_start) as reviews_done,
                    (SELECT COUNT(*) FROM memory_nodes WHERE user_id = :uid) as total_nodes
            """),
            {"uid": user_id, "week_start": week_ago.isoformat()},
        )
        row = stats_result.first()
        new_nodes = row[0] if row else 0
        new_links = row[1] if row else 0
        agent_runs = row[2] if row else 0
        reviews_done = row[3] if row else 0
        total_nodes = row[4] if row else 0

        # Get top tags from the week
        tags_result = await db.execute(
            text("""
                SELECT unnest(tags) as tag, COUNT(*) as cnt
                FROM memory_nodes
                WHERE user_id = :uid AND created_at::date >= :week_start
                GROUP BY tag
                ORDER BY cnt DESC
                LIMIT 5
            """),
            {"uid": user_id, "week_start": week_ago.isoformat()},
        )
        top_tags = [(r[0], r[1]) for r in tags_result.all()]

        # Build message
        summary = (
            f"📊 *Weekly Summary*\n"
            f"📅 {week_ago.strftime('%b %d')} — {today.strftime('%b %d, %Y')}\n\n"
            f"🧠 *Second Brain Growth:*\n"
            f"  • +{new_nodes} new memories\n"
            f"  • +{new_links} new connections\n"
            f"  • {total_nodes} total memories\n\n"
        )

        if top_tags:
            summary += "🏷️ *Top Tags This Week:*\n"
            for tag, count in top_tags:
                summary += f"  • {tag}: {count}\n"
            summary += "\n"

        summary += (
            f"⚡ *Activity:*\n"
            f"  • {agent_runs} agent executions\n"
            f"  • {reviews_done} memory reviews completed\n\n"
        )

        if total_nodes > 0:
            summary += "💡 *Tip:* Review your weekly growth with `/graph` to see your knowledge web!"

        return await _send_whatsapp_message(user_id, phone_number, summary)

    except Exception as exc:
        logger.error("Failed to send weekly summary", user_id=user_id, error=str(exc))
        return False
    finally:
        await db.close()


async def send_review_reminder(user_id: str, count: int) -> bool:
    """Send a reminder about pending spaced repetition reviews.

    Args:
        user_id: The user UUID.
        count: Number of items waiting for review.

    Returns:
        True if sent successfully.
    """
    db = await anext(get_db_session())
    try:
        row = await _get_user_phone_with_setting(
            db, user_id, SETTING_REVIEW_REMINDER, default=True
        )
        if not row:
            return False

        phone_number = row[0]

        reminder = (
            f"📚 *Review Reminder*\n\n"
            f"You have *{count} memories* waiting for review.\n\n"
            f"Regular reviews help strengthen your Second Brain and "
            f"ensure you retain important information.\n\n"
            f"Type `/brain review` to start reviewing now! 🧠"
        )

        return await _send_whatsapp_message(user_id, phone_number, reminder)

    except Exception as exc:
        logger.error("Failed to send review reminder", user_id=user_id, error=str(exc))
        return False
    finally:
        await db.close()


async def send_brain_insight(user_id: str, insight: str) -> bool:
    """Send an AI-generated insight about the user's Second Brain.

    Examples: "I noticed a connection between [[Project Alpha]] and [[Client X]]..."
    "You've been most productive on Tuesday mornings this month."

    Args:
        user_id: The user UUID.
        insight: The insight text (may contain [[wikilinks]]).

    Returns:
        True if sent successfully.
    """
    db = await anext(get_db_session())
    try:
        row = await _get_user_phone_with_setting(
            db, user_id, SETTING_BRAIN_INSIGHT, default=True
        )
        if not row:
            return False

        phone_number = row[0]
        insight_text = f"🧠 *Brain Insight*\n\n{insight}"

        return await _send_whatsapp_message(user_id, phone_number, insight_text)

    except Exception as exc:
        logger.error("Failed to send brain insight", user_id=user_id, error=str(exc))
        return False
    finally:
        await db.close()


# ─── Internal Helpers ────────────────────────────────────────────────────────────


async def _get_user_phone_with_setting(
    db: AsyncSession,
    user_id: str,
    setting_key: str,
    *,
    default: bool = True,
) -> tuple[str, dict] | None:
    """Get phone number for a user if they have the given setting enabled.

    Args:
        db: Database session.
        user_id: The user UUID.
        setting_key: The settings key to check.
        default: Default value if the setting is not set.

    Returns:
        Tuple of (phone_number, settings_dict) or None if not found/opted out.
    """
    result = await db.execute(
        text("""
            SELECT phone_number, settings FROM whatsapp_connections
            WHERE user_id = :user_id AND status = 'active'
        """),
        {"user_id": user_id},
    )
    row = result.first()
    if not row:
        return None

    phone_number = row[0]
    settings_dict = row[1] if isinstance(row[1], dict) else {}

    pref = settings_dict.get(setting_key, default)
    if not pref:
        return None

    return (phone_number, settings_dict)


__all__ = [
    "send_morning_briefing",
    "send_agent_completed",
    "send_alert",
    "send_suggestion",
    "send_weekly_summary",
    "send_review_reminder",
    "send_brain_insight",
    "SETTING_MORNING_BRIEFING",
    "SETTING_AGENT_COMPLETED",
    "SETTING_ALERTS",
    "SETTING_SUGGESTIONS",
    "SETTING_WEEKLY_SUMMARY",
    "SETTING_REVIEW_REMINDER",
    "SETTING_BRAIN_INSIGHT",
]
