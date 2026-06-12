"""
Anansi WhatsApp Quick Command Handler — Executes slash commands over WhatsApp.

All commands are connected to the [[Second Brain]] (brain stats, memories,
daily notes) and the AI agent engine.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any, Callable, Coroutine

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_db_session

logger = get_logger(__name__)


# ─── Type Alias ──────────────────────────────────────────────────────────────────

CommandHandler = Callable[
    [str, str, str, AsyncSession],
    Coroutine[Any, Any, dict[str, Any]],
]


# ─── Send WhatsApp helper ────────────────────────────────────────────────────────


async def _send(user_id: str, to: str, message: str) -> None:
    """Send a WhatsApp message."""
    from app.services.whatsapp import WhatsAppService
    db = await anext(get_db_session())
    try:
        svc = WhatsAppService(db=db)
        await svc.send_message(user_id, to, message)
    except Exception as exc:
        logger.error("Failed to send command response", user_id=user_id, error=str(exc))
    finally:
        await db.close()


# ─── /briefing — Morning Briefing ────────────────────────────────────────────────


async def cmd_briefing(
    user_id: str,
    from_number: str,
    args: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Generate and send a morning briefing.

    Aggregates today's events, tasks, recent memory activity,
    and AI suggestions into a concise briefing.
    """
    today = date.today()
    today_str = today.isoformat()

    # Get today's events (from calendar, tasks, etc.)
    try:
        # Count today's messages
        msg_result = await db.execute(
            text("""
                SELECT COUNT(*) FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = :user_id
                AND m.created_at::date = :today
            """),
            {"user_id": user_id, "today": today},
        )
        today_msgs = msg_result.scalar() or 0

        # Recent brain activity (last 7 days)
        brain_result = await db.execute(
            text("""
                SELECT COUNT(*) as nodes,
                       (SELECT COUNT(*) FROM memory_links
                        WHERE user_id = :user_id
                        AND created_at::date >= :week_ago) as links
                FROM memory_nodes
                WHERE user_id = :user_id
                AND created_at::date >= :week_ago
            """),
            {
                "user_id": user_id,
                "today": today,
                "week_ago": today.isoformat() if False else
                    date.fromordinal(today.toordinal() - 7).isoformat(),
            },
        )
        brain_row = brain_result.first()
        new_nodes = brain_row[0] if brain_row else 0
        new_links = brain_row[1] if brain_row else 0

        # Pending reviews
        review_result = await db.execute(
            text("""
                SELECT COUNT(*) FROM memory_nodes
                WHERE user_id = :user_id
                AND next_review_at IS NOT NULL
                AND next_review_at <= :now
            """),
            {"user_id": user_id, "now": datetime.now(timezone.utc)},
        )
        reviews_due = review_result.scalar() or 0

        # Total brain stats
        total_result = await db.execute(
            text("""
                SELECT COUNT(*) as nodes, (SELECT COUNT(*) FROM memory_links WHERE user_id = :user_id2) as links
                FROM memory_nodes WHERE user_id = :user_id
            """),
            {"user_id": user_id, "user_id2": user_id},
        )
        total_row = total_result.first()
        total_nodes = total_row[0] if total_row else 0
        total_links = total_row[1] if total_row else 0

        briefing_parts = [
            "🌅 *Good Morning!*",
            "",
            f"📅 *{today.strftime('%A, %B %d, %Y')}*",
            "",
            "🧠 *Your Second Brain*",
            f"  • {total_nodes} total memories ({new_nodes} new this week)",
            f"  • {total_links} connections ({new_links} new this week)",
            f"  • {reviews_due} reviews due for review",
            "",
            "📊 *Today's Activity*",
            f"  • {today_msgs} messages exchanged today",
            "",
        ]

        if reviews_due > 0:
            briefing_parts.append(f"📝 *Reminder:* You have {reviews_due} memories to review. Try `/brain review`")

        briefing_parts.append("")
        briefing_parts.append("✨ *Tip:* Send `/tasks` to see your task list or `/graph` for your brain snapshot.")

        await _send(user_id, from_number, "\n".join(briefing_parts))

        return {"status": "ok", "command": "briefing"}

    except Exception as exc:
        logger.error("Briefing generation failed", user_id=user_id, error=str(exc))
        await _send(
            user_id,
            from_number,
            "😕 Sorry, I couldn't generate your briefing right now. Please try again later.",
        )
        return {"status": "error", "command": "briefing", "error": str(exc)}


# ─── /tasks — Today's Tasks ──────────────────────────────────────────────────────


async def cmd_tasks(
    user_id: str,
    from_number: str,
    args: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """List today's tasks from memory, agent runs, and conversations."""
    today = date.today()

    try:
        # Get recent agent runs
        agent_result = await db.execute(
            text("""
                SELECT id, status, started_at
                FROM agent_runs
                WHERE user_id = :user_id
                AND started_at::date = :today
                ORDER BY started_at DESC
                LIMIT 10
            """),
            {"user_id": user_id, "today": today},
        )
        agent_runs = agent_result.all()

        # Get memories tagged as tasks
        task_result = await db.execute(
            text("""
                SELECT id, title, content
                FROM memory_nodes
                WHERE user_id = :user_id
                AND (tags @> '{#task}' OR tags @> '{#todo}')
                AND (
                    (metadata->>'status' IS NULL)
                    OR (metadata->>'status' != 'completed')
                )
                ORDER BY created_at DESC
                LIMIT 20
            """),
            {"user_id": user_id},
        )
        tasks = task_result.all()

        parts = ["📋 *Your Tasks*", ""]

        if tasks:
            parts.append("📌 *Open Tasks:*")
            for i, task in enumerate(tasks[:10], 1):
                title = task[1] or "(untitled)"
                parts.append(f"  {i}. {title[:60]}")
            parts.append("")
        else:
            parts.append("📌 No open tasks found.")
            parts.append("  Use `/record [task details]` to add a task.")
            parts.append("")

        if agent_runs:
            parts.append("⚡ *Agent Runs Today:*")
            for run in agent_runs[:5]:
                status_icon = {"completed": "✅", "failed": "❌", "running": "🔄", "cancelled": "⏹️"}
                icon = status_icon.get(run[1], "❓")
                parts.append(f"  {icon} {run[1]} — {run[2].strftime('%H:%M') if run[2] else 'unknown'}")
        else:
            parts.append("⚡ No agent runs today.")
            parts.append("  Agents run automatically based on your schedule.")

        await _send(user_id, from_number, "\n".join(parts))

        return {"status": "ok", "command": "tasks"}

    except Exception as exc:
        logger.error("Tasks command failed", user_id=user_id, error=str(exc))
        await _send(
            user_id,
            from_number,
            "😕 I couldn't fetch your tasks right now. Please try again.",
        )
        return {"status": "error", "command": "tasks", "error": str(exc)}


# ─── /record — Record a Transaction / Event ──────────────────────────────────────


async def cmd_record(
    user_id: str,
    from_number: str,
    args: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Parse and record a transaction, sale, or event into Second Brain memory.

    Examples:
        /record Sold 20 yards of Ankara to Mama Grace for 45,000 naira
        /record Meeting with client at 3pm about Q2 planning
        /record Task: follow up with James about invoice
    """
    if not args:
        await _send(
            user_id,
            from_number,
            "📝 *Record* — Log something to your Second Brain.\n\n"
            "Examples:\n"
            "  `/record Sold 20 yards of Ankara to Mama Grace for ₦45,000`\n"
            "  `/record Meeting with client at 3pm about Q2 planning`\n"
            "  `/record Task: follow up with James about invoice`",
        )
        return {"status": "ok", "command": "record", "info_shown": True}

    try:
        now = datetime.now(timezone.utc)
        node_id = str(uuid.uuid4())

        # Determine node type and tags
        lower_args = args.lower()

        if "sold" in lower_args or "sale" in lower_args or "₦" in args or "naira" in lower_args:
            node_type = "fact"
            tags = ["#transaction", "#sale"]
        elif "task" in lower_args or "todo" in lower_args or lower_args.startswith("task"):
            node_type = "fact"
            tags = ["#task", "#todo"]
            args = args.replace("Task:", "").replace("task:", "").strip()
        elif "meeting" in lower_args or "call with" in lower_args:
            node_type = "fact"
            tags = ["#event", "#meeting"]
        else:
            node_type = "fact"
            tags = ["#note"]

        # Generate a title from content
        title = args[:80] + "..." if len(args) > 80 else args

        # Create the memory node
        await db.execute(
            text("""
                INSERT INTO memory_nodes (id, user_id, type, title, content, tags, metadata, created_at, updated_at)
                VALUES (:id, :user_id, :type, :title, :content, :tags, :metadata, :now, :now)
            """),
            {
                "id": node_id,
                "user_id": user_id,
                "type": node_type,
                "title": title,
                "content": args,
                "tags": tags,
                "metadata": json.dumps({
                    "confidence": 0.9,
                    "source": "whatsapp",
                    "review_status": "current",
                }),
                "now": now,
            },
        )
        await db.commit()

        response_parts = [
            "✅ *Recorded!*",
            f"📝 \"{args[:120]}\"",
            f"🏷️ Tags: {' '.join(tags)}",
            "",
            "🧠 Added to your Second Brain.",
        ]

        # If it's a sale, add extra context
        if "sale" in tags or "transaction" in tags:
            response_parts.append("📊 *Pro tip:* Check your sales summary with `/summary sales`")

        await _send(user_id, from_number, "\n".join(response_parts))

        logger.info("Record command executed", user_id=user_id, node_id=node_id, tags=tags)

        return {"status": "ok", "command": "record", "node_id": node_id}

    except Exception as exc:
        logger.error("Record command failed", user_id=user_id, error=str(exc))
        await _send(
            user_id,
            from_number,
            "😕 Sorry, I couldn't save that record. Please try again.",
        )
        return {"status": "error", "command": "record", "error": str(exc)}


# ─── /summary — Summarize Recent Activity ────────────────────────────────────────


async def cmd_summary(
    user_id: str,
    from_number: str,
    args: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Summarize recent activity on a topic.

    If no topic is given, shows a general recent activity summary.
    """
    try:
        if args:
            # Topic-specific summary: search memory for related nodes
            search_term = f"%{args}%"
            result = await db.execute(
                text("""
                    SELECT id, title, content, tags, created_at
                    FROM memory_nodes
                    WHERE user_id = :user_id
                    AND (title ILIKE :term OR content ILIKE :term OR tags::text ILIKE :term)
                    ORDER BY created_at DESC
                    LIMIT 10
                """),
                {"user_id": user_id, "term": search_term},
            )
            nodes = result.all()

            if nodes:
                parts = [f"📊 *Summary: {args}*", ""]
                for node in nodes[:8]:
                    parts.append(f"• {node[1][:60]}")
                parts.append("")
                parts.append(f"Found {len(nodes)} related memories.")
            else:
                parts = [
                    f"📊 *Summary: {args}*",
                    "",
                    f"No memories found about '{args}'.",
                    "Try recording something with `/record` first!",
                ]
        else:
            # General summary: recent activity across the brain
            result = await db.execute(
                text("""
                    SELECT
                        (SELECT COUNT(*) FROM memory_nodes WHERE user_id = :user_id) as total_nodes,
                        (SELECT COUNT(*) FROM memory_nodes WHERE user_id = :user_id AND created_at::date >= CURRENT_DATE - 7) as week_nodes,
                        (SELECT COUNT(*) FROM memory_links WHERE user_id = :user_id AND created_at::date >= CURRENT_DATE - 7) as week_links,
                        (SELECT COUNT(*) FROM agent_runs WHERE user_id = :user_id AND started_at::date >= CURRENT_DATE - 7) as week_runs
                """),
                {"user_id": user_id},
            )
            row = result.first()
            total_nodes = row[0] if row else 0
            week_nodes = row[1] if row else 0
            week_links = row[2] if row else 0
            week_runs = row[3] if row else 0

            parts = [
                "📊 *Your Second Brain Summary*",
                "",
                f"🧠 *Total:* {total_nodes} memories",
                f"📈 *This week:* +{week_nodes} memories, +{week_links} connections",
                f"⚡ *Agent runs:* {week_runs} this week",
                "",
                "💡 *Tips:*",
                "  • `/summary [topic]` — Deep dive on a topic",
                "  • `/brain` — Full brain stats",
                "  • `/graph` — Visualize your knowledge web",
            ]

        await _send(user_id, from_number, "\n".join(parts))
        return {"status": "ok", "command": "summary"}

    except Exception as exc:
        logger.error("Summary command failed", user_id=user_id, error=str(exc))
        await _send(
            user_id,
            from_number,
            "😕 Sorry, I couldn't generate that summary. Please try again.",
        )
        return {"status": "error", "command": "summary", "error": str(exc)}


# ─── /graph — Knowledge Web Snapshot ─────────────────────────────────────────────


async def cmd_graph(
    user_id: str,
    from_number: str,
    args: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Generate and send a knowledge web snapshot image.

    Creates a visual representation of the user's Second Brain
    graph and sends it as an image attachment via WhatsApp.
    """
    try:
        # Get graph data
        from app.services.graph import GraphService
        graph_svc = GraphService()
        graph_data = await graph_svc.get_full_graph(user_id, db_session=db)

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            await _send(
                user_id,
                from_number,
                "🌐 *Graph Snapshot*\n\n"
                "Your Second Brain is still growing! No memory nodes yet.\n"
                "Start by recording something with `/record` or just chat with me.",
            )
            return {"status": "ok", "command": "graph", "empty": True}

        # Generate a simple text-based stats response (image generation TBD)
        node_types = {}
        for n in nodes:
            ntype = n.get("type", "unknown")
            node_types[ntype] = node_types.get(ntype, 0) + 1

        type_summary = "\n".join(
            f"  • {t.replace('_', ' ').title()}: {c}"
            for t, c in sorted(node_types.items(), key=lambda x: -x[1])
        )

        # Find top-linked nodes
        link_counts: dict[str, int] = {}
        for e in edges:
            link_counts[e.get("source_id", "")] = link_counts.get(e.get("source_id", ""), 0) + 1
            link_counts[e.get("target_id", "")] = link_counts.get(e.get("target_id", ""), 0) + 1

        top_nodes = sorted(link_counts.items(), key=lambda x: -x[1])[:5]
        top_names = []
        for node_id_str, _ in top_nodes:
            for n in nodes:
                if n.get("id") == node_id_str:
                    top_names.append(n.get("title", "(untitled)")[:30])
                    break

        parts = [
            "🌐 *Your Knowledge Web*",
            "",
            f"📊 {len(nodes)} nodes · {len(edges)} connections",
            "",
            "📁 *By Type:*",
            type_summary,
            "",
        ]

        if top_names:
            parts.append("🔗 *Most Connected:*")
            for name in top_names:
                parts.append(f"  • {name}")
            parts.append("")

        # TODO: Generate actual graph image using a rendering service
        # For now, send the stats text
        parts.append("📸 *Graph visualization coming soon!*")
        parts.append("The interactive web view will show your full knowledge graph.")

        await _send(user_id, from_number, "\n".join(parts))

        return {"status": "ok", "command": "graph", "node_count": len(nodes), "edge_count": len(edges)}

    except Exception as exc:
        logger.error("Graph command failed", user_id=user_id, error=str(exc))
        await _send(
            user_id,
            from_number,
            "😕 Sorry, I couldn't generate your graph snapshot. Please try again later.",
        )
        return {"status": "error", "command": "graph", "error": str(exc)}


# ─── /brain — Brain Stats ────────────────────────────────────────────────────────


async def cmd_brain(
    user_id: str,
    from_number: str,
    args: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Show Second Brain stats or start a spaced repetition review.

    Subcommands:
        /brain — Show brain stats
        /brain review — Start spaced repetition review
    """
    if args.strip() == "review":
        return await cmd_brain_review(user_id, from_number, "", db)

    try:
        result = await db.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM memory_nodes WHERE user_id = :user_id) as total_nodes,
                    (SELECT COUNT(*) FROM memory_links WHERE user_id = :user_id) as total_links,
                    (SELECT COUNT(*) FROM memory_nodes WHERE user_id = :user_id
                        AND next_review_at IS NOT NULL AND next_review_at <= :now) as reviews_due,
                    (SELECT COUNT(*) FROM memory_nodes WHERE user_id = :user_id
                        AND tags::text ILIKE '%#%') as tagged_count,
                    (SELECT COUNT(DISTINCT unnest(tags)) FROM memory_nodes WHERE user_id = :user_id) as unique_tags
            """),
            {"user_id": user_id, "now": datetime.now(timezone.utc)},
        )
        row = result.first()
        if not row:
            await _send(
                user_id,
                from_number,
                "🧠 *Second Brain*\n\nYour brain is empty! Start recording memories with `/record`.",
            )
            return {"status": "ok", "command": "brain", "empty": True}

        total_nodes = row[0] or 0
        total_links = row[1] or 0
        reviews_due = row[2] or 0
        tagged_count = row[3] or 0
        unique_tags = row[4] or 0

        avg_links = round(total_links / total_nodes, 1) if total_nodes > 0 else 0

        parts = [
            "🧠 *Second Brain Stats*",
            "",
            f"📝 *Memories:* {total_nodes}",
            f"🔗 *Connections:* {total_links}",
            f"📊 *Avg links/node:* {avg_links}",
            f"🏷️ *Tags:* {unique_tags} unique across {tagged_count} nodes",
            "",
            f"📚 *Reviews due:* {reviews_due}",
            "",
        ]

        if reviews_due > 0:
            parts.append("  → Use `/brain review` to start reviewing")
        parts.append("")
        parts.append("💡 `/brain review` — Start spaced repetition review")
        parts.append("🌐 `/graph` — Visualize your knowledge web")

        await _send(user_id, from_number, "\n".join(parts))

        return {"status": "ok", "command": "brain"}

    except Exception as exc:
        logger.error("Brain stats command failed", user_id=user_id, error=str(exc))
        await _send(
            user_id,
            from_number,
            "😕 I couldn't fetch your brain stats. Please try again.",
        )
        return {"status": "error", "command": "brain", "error": str(exc)}


# ─── /brain review — Spaced Repetition Review ────────────────────────────────────


async def cmd_brain_review(
    user_id: str,
    from_number: str,
    args: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Start an interactive spaced repetition review session.

    Due to WhatsApp's chat-based nature, the review is done one
    card at a time. The user responds with 'easy', 'medium', 'hard',
    or 'forgot' for each card.
    """
    try:
        # Get due reviews
        result = await db.execute(
            text("""
                SELECT id, title, content, next_review_at, review_interval
                FROM memory_nodes
                WHERE user_id = :user_id
                    AND next_review_at IS NOT NULL
                    AND next_review_at <= :now
                ORDER BY next_review_at ASC
                LIMIT 1
            """),
            {"user_id": user_id, "now": datetime.now(timezone.utc)},
        )
        row = result.first()

        if not row:
            # Check if there are any at all
            total = await db.execute(
                text("SELECT COUNT(*) FROM memory_nodes WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            total_count = total.scalar() or 0

            if total_count == 0:
                await _send(
                    user_id,
                    from_number,
                    "🧠 *Spaced Repetition Review*\n\n"
                    "Your Second Brain has no memories yet! Start by "
                    "recording something with `/record` or just chat with me.",
                )
            else:
                await _send(
                    user_id,
                    from_number,
                    "🎉 *All caught up!*\n\n"
                    "You have no memories due for review right now. "
                    "Come back later or check again tomorrow.",
                )

            return {"status": "ok", "command": "brain_review", "empty": True}

        node_id, title, content, next_review_at, review_interval = row

        # Calculate review info
        days_since = (
            (datetime.now(timezone.utc) - next_review_at).days
            if next_review_at and next_review_at < datetime.now(timezone.utc)
            else 0
        )

        if content and len(content) > 500:
            display_content = content[:500] + "..."
        else:
            display_content = content or title

        review_msg = (
            "🧠 *Review Time!*\n\n"
            f"📝 *{title}*\n\n"
            f"_{display_content}_\n\n"
            f"📅 Last reviewed: {days_since} day(s) ago\n\n"
            "How well do you remember this?"
        )

        await _send(user_id, from_number, review_msg)

        # In a full implementation, we'd store the current review state
        # in Redis for multi-turn interaction. For now, send instructions.
        await _send(
            user_id,
            from_number,
            "Reply with:\n"
            "✅ *Easy* — I remember perfectly\n"
            "👍 *Medium* — I mostly remember\n"
            "💪 *Hard* — I struggled\n"
            "❌ *Forgot* — I don't remember\n\n"
            "Tip: You can say 'next' to skip this card.",
        )

        return {
            "status": "ok",
            "command": "brain_review",
            "node_id": str(node_id),
            "title": title,
        }

    except Exception as exc:
        logger.error("Brain review command failed", user_id=user_id, error=str(exc))
        await _send(
            user_id,
            from_number,
            "😕 Sorry, I couldn't start the review. Please try again.",
        )
        return {"status": "error", "command": "brain_review", "error": str(exc)}


# ─── /help — List Commands ───────────────────────────────────────────────────────


async def cmd_help(
    user_id: str,
    from_number: str,
    args: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """List all available WhatsApp commands."""
    help_text = (
        "⚡ *Anansi WhatsApp Commands* ⚡\n\n"
        "🌅 `/briefing` — Your daily morning briefing\n"
        "📋 `/tasks` — Today's tasks and agent runs\n"
        "📝 `/record [details]` — Log a transaction, sale, or event\n"
        "📊 `/summary [topic]` — Summarize recent activity\n"
        "🌐 `/graph` — Knowledge web snapshot\n"
        "🧠 `/brain` — Second Brain stats\n"
        "🧠 `/brain review` — Start spaced repetition review\n"
        "📋 `/help` — This message\n"
        "📊 `/status` — Account and connection status\n\n"
        "💬 *Also try:*\n"
        "• Send a *voice note* — I'll transcribe it\n"
        "• Just *chat with me* — Ask me anything\n"
        "• *Record sales* — `/record Sold 20 yards for ₦45,000`\n\n"
        "Need more help? Reply with your question!"
    )

    await _send(user_id, from_number, help_text)
    return {"status": "ok", "command": "help"}


# ─── /status — Account Status ────────────────────────────────────────────────────


async def cmd_status(
    user_id: str,
    from_number: str,
    args: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Show account and WhatsApp connection status."""
    try:
        # Get user info
        user_result = await db.execute(
            text("""
                SELECT display_name, email, brain_age_days, memory_count, link_count
                FROM users WHERE id = :user_id
            """),
            {"user_id": user_id},
        )
        user_row = user_result.first()

        # Get WhatsApp connection status
        wa_result = await db.execute(
            text("""
                SELECT status, phone_number, verified_at
                FROM whatsapp_connections
                WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        )
        wa_row = wa_result.first()

        # Get brain stats
        brain_result = await db.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM memory_nodes WHERE user_id = :uid) as nodes,
                    (SELECT COUNT(*) FROM memory_links WHERE user_id = :uid) as links
            """),
            {"uid": user_id},
        )
        brain_row = brain_result.first()

        parts = ["📊 *Account Status*", ""]

        if user_row:
            parts.append(f"👤 *User:* {user_row[0] or 'Unnamed'}")
            parts.append(f"📧 *Email:* {user_row[1] or 'N/A'}")
            parts.append(f"🧠 *Brain age:* {user_row[2] or 0} days")
            parts.append("")

        if wa_row:
            wa_status = wa_row[0]
            status_icon = {
                "active": "✅",
                "pending": "⏳",
                "disconnected": "❌",
                "expired": "⏰",
            }.get(wa_status, "❓")

            parts.append(f"{status_icon} *WhatsApp:* {wa_status.title()}")
            parts.append(f"📱 *Phone:* {wa_row[1] or 'N/A'}")
            if wa_row[2]:
                parts.append(f"🔗 *Connected:* {wa_row[2].strftime('%b %d, %Y')}")
        else:
            parts.append("❌ *WhatsApp:* Not connected")
            parts.append("  Use the web app to link your number")

        parts.append("")

        if brain_row:
            parts.append(f"🧠 *Brain:* {brain_row[0] or 0} memories · {brain_row[1] or 0} links")

        await _send(user_id, from_number, "\n".join(parts))

        return {"status": "ok", "command": "status"}

    except Exception as exc:
        logger.error("Status command failed", user_id=user_id, error=str(exc))
        await _send(
            user_id,
            from_number,
            "😕 I couldn't fetch your status. Please try again.",
        )
        return {"status": "error", "command": "status", "error": str(exc)}


# ─── Command Registry ────────────────────────────────────────────────────────────


COMMAND_HANDLERS: dict[str, CommandHandler] = {
    "/briefing": cmd_briefing,
    "/tasks": cmd_tasks,
    "/record": cmd_record,
    "/summary": cmd_summary,
    "/graph": cmd_graph,
    "/brain": cmd_brain,
    "/help": cmd_help,
    "/status": cmd_status,
}


__all__ = [
    "COMMAND_HANDLERS",
    "cmd_briefing",
    "cmd_tasks",
    "cmd_record",
    "cmd_summary",
    "cmd_graph",
    "cmd_brain",
    "cmd_brain_review",
    "cmd_help",
    "cmd_status",
]
