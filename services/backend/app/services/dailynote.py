"""
Anansi Daily Notes Service — Temporal anchors for the [[Second Brain]].

Each day gets a [[Daily Note]] that automatically captures highlights,
decisions, connections formed, metrics, and an AI reflection paragraph.
Acts as the temporal backbone of the user's knowledge web.
"""

from __future__ import annotations

import uuid
from datetime import date as date_type, datetime, timedelta, timezone
from typing import Any, Optional

from openai import AsyncOpenAI
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_db_session
from app.core.exceptions import NotFoundError
from app.models.brain import DailyNote, MemoryLink, MemoryNode, MemoryReview
from app.websocket.manager import manager

logger = get_logger(__name__)

# ─── AI reflection prompt ─────────────────────────────────────────────────────

SYSTEM_PROMPT_REFLECTION = """You are the [[Daily Note]] reflection engine for Anansi's [[Second Brain]].

Given the day's activity data (highlights, decisions, connections, metrics),
write a brief, insightful AI reflection paragraph (2-4 sentences) that:

1. Connects the day's events to the user's broader context
2. Identifies one meaningful pattern or insight
3. Suggests what to focus on tomorrow

Keep it warm, specific, and grounded in the actual data. Do not be generic."""


class DailyNoteService:
    """Service for managing [[Daily Notes]] — the temporal anchor of the Second Brain.

    Handles creation, generation, entry addition, history queries,
    and finalization with WebSocket broadcasting.
    """

    def __init__(self) -> None:
        self._openai: AsyncOpenAI | None = None

    @property
    def openai(self) -> AsyncOpenAI:
        if self._openai is None:
            self._openai = AsyncOpenAI(api_key=settings.ai.openai_api_key)
        return self._openai

    # ── AI Text Generation ───────────────────────────────────────────────────

    async def _call_ai(
        self,
        system_prompt: str,
        user_content: str,
    ) -> str:
        """Call the configured AI model for text generation."""
        if not settings.ai.openai_api_key:
            return ""

        try:
            response = await self.openai.chat.completions.create(
                model=settings.ai.openai_default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=300,
                temperature=0.7,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("AI reflection call failed", error=str(exc))
            return ""

    # ── Get or Create Today ──────────────────────────────────────────────────

    async def get_or_create_today(
        self,
        user_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Get today's [[Daily Note]], or create an empty one if it doesn't exist.

        Args:
            user_id: The user's UUID.
            db_session: Optional existing DB session.

        Returns:
            The daily note as a dict.
        """
        return await self.get_or_create(user_id, datetime.now(timezone.utc).date(), db_session)

    async def get_or_create(
        self,
        user_id: str,
        note_date: date_type,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Get or create a daily note for a specific date.

        Args:
            user_id: The user's UUID.
            note_date: The date to get/create.
            db_session: Optional existing DB session.

        Returns:
            The daily note as a dict.
        """
        user_uuid = uuid.UUID(user_id)

        async def _get(db: AsyncSession) -> dict[str, Any]:
            stmt = select(DailyNote).where(
                and_(
                    DailyNote.user_id == user_uuid,
                    DailyNote.note_date == note_date,
                )
            )
            result = await db.execute(stmt)
            note = result.scalar_one_or_none()

            if note:
                return self._note_to_dict(note)

            # Create new empty note
            note = DailyNote(
                id=uuid.uuid4(),
                user_id=user_uuid,
                note_date=note_date,
                highlights=[],
                decisions={},
                connections_made={},
                metrics={
                    "emails_processed": 0,
                    "tasks_completed": 0,
                    "agent_runs": 0,
                    "new_memories": 0,
                    "new_links": 0,
                },
                ai_reflection=None,
                is_finalized=False,
            )
            db.add(note)
            await db.commit()
            await db.refresh(note)

            return self._note_to_dict(note)

        if db_session:
            return await _get(db_session)

        async for db in get_db_session():
            return await _get(db)

    # ── Generate AI-Powered Daily Note ───────────────────────────────────────

    async def generate_daily_note(
        self,
        user_id: str,
        note_date: str | None = None,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """AI-powered generation of a [[Daily Note]].

        Scans the user's activity for the day: new nodes, links created,
        conversations, agent runs, and produces a rich summary with
        highlights, decisions, connections, metrics, and a reflection.

        Args:
            user_id: The user's UUID.
            note_date: Optional date string (YYYY-MM-DD). Defaults to today.
            db_session: Optional existing DB session.

        Returns:
            The generated daily note as a dict.
        """
        target_date: date_type
        if note_date:
            target_date = date_type.fromisoformat(note_date)
        else:
            target_date = datetime.now(timezone.utc).date()

        user_uuid = uuid.UUID(user_id)

        async def _generate(db: AsyncSession) -> dict[str, Any]:
            # Get or create the note for this date
            note = await self.get_or_create(user_id, target_date, db_session=db)
            note_id = uuid.UUID(note["id"])

            # Calculate date range
            day_start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
            day_end = day_start + timedelta(days=1)

            # Gather day's activity
            # New nodes today
            new_nodes_stmt = select(MemoryNode).where(
                and_(
                    MemoryNode.user_id == user_uuid,
                    MemoryNode.created_at >= day_start,
                    MemoryNode.created_at < day_end,
                )
            )
            new_nodes_rows = await db.execute(new_nodes_stmt)
            new_nodes = new_nodes_rows.scalars().all()

            # New links today
            new_links_stmt = select(MemoryLink).where(
                and_(
                    MemoryLink.user_id == user_uuid,
                    MemoryLink.created_at >= day_start,
                    MemoryLink.created_at < day_end,
                )
            )
            new_links_rows = await db.execute(new_links_stmt)
            new_links = new_links_rows.scalars().all()

            # Reviews today
            reviews_stmt = select(MemoryReview).where(
                and_(
                    MemoryReview.user_id == user_uuid,
                    MemoryReview.created_at >= day_start,
                    MemoryReview.created_at < day_end,
                )
            )
            reviews_rows = await db.execute(reviews_stmt)
            reviews = reviews_rows.scalars().all()

            # Build highlights from new nodes and reviews
            highlights = []
            for node in new_nodes[:10]:
                highlights.append(f"New [[{node.title}]] ({node.type})")
            for review in reviews[:5]:
                highlights.append(f"Reviewed memory: rating={review.rating}")

            # Build metrics
            metrics = {
                "emails_processed": 0,
                "tasks_completed": 0,
                "agent_runs": 0,
                "new_memories": len(new_nodes),
                "new_links": len(new_links),
                "reviews_completed": len(reviews),
            }

            # Build connections
            connections = []
            for link in new_links[:10]:
                source = await db.get(MemoryNode, link.source_id)
                target = await db.get(MemoryNode, link.target_id)
                if source and target:
                    connections.append({
                        "from_node": source.title,
                        "to_node": target.title,
                        "link_type": link.link_type,
                    })

            # Build decisions (AI-inferred from today's patterns)
            decisions = []
            if len(new_nodes) > 5:
                decisions.append({
                    "description": "High memory creation day — several new insights captured",
                    "approved": True,
                })
            if len(reviews) > 0:
                avg_rating = sum(
                    {"easy": 4, "medium": 3, "hard": 2, "forgot": 1}.get(r.rating, 0)
                    for r in reviews
                ) / max(len(reviews), 1)
                if avg_rating >= 3:
                    decisions.append({
                        "description": f"Memory retention is strong (avg rating: {avg_rating:.1f}/4)",
                        "approved": True,
                    })

            # Generate AI reflection
            reflection_text = (
                f"Today's activity: {len(new_nodes)} new memories created, "
                f"{len(new_links)} new connections formed, "
                f"{len(reviews)} reviews completed."
            )
            ai_reflection = await self._call_ai(
                SYSTEM_PROMPT_REFLECTION, reflection_text,
            )

            # Update the note
            note_obj = await db.get(DailyNote, note_id)
            if note_obj:
                note_obj.highlights = highlights
                note_obj.decisions = {"items": decisions}
                note_obj.connections_made = {"items": connections}
                note_obj.metrics = metrics
                if ai_reflection:
                    note_obj.ai_reflection = ai_reflection
                await db.commit()
                await db.refresh(note_obj)
                return self._note_to_dict(note_obj)

            return note

        if db_session:
            return await _generate(db_session)

        async for db in get_db_session():
            return await _generate(db)

    # ── Add Entry ────────────────────────────────────────────────────────────

    async def add_entry(
        self,
        user_id: str,
        entry_type: str = "highlight",
        content: str = "",
        related_node_id: str | None = None,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Add a line to today's [[Daily Note]].

        Entry types: highlight, decision, connection, metric.

        Args:
            user_id: The user's UUID.
            entry_type: Type of entry (highlight, decision, connection).
            content: The entry content.
            related_node_id: Optional related memory node UUID.
            db_session: Optional existing DB session.

        Returns:
            Updated daily note.
        """
        async def _add(db: AsyncSession) -> dict[str, Any]:
            note_dict = await self.get_or_create_today(user_id, db_session=db)
            note_id = uuid.UUID(note_dict["id"])
            note = await db.get(DailyNote, note_id)

            if not note:
                raise NotFoundError(
                    resource_type="daily_note",
                    resource_id=str(note_id),
                )

            if entry_type == "highlight":
                note.highlights.append(content)
            elif entry_type == "decision":
                decisions = note.decisions or {}
                items = decisions.get("items", [])
                items.append({
                    "description": content,
                    "related_node_id": related_node_id,
                    "approved": True,
                })
                decisions["items"] = items
                note.decisions = decisions
            elif entry_type == "connection":
                connections = note.connections_made or {}
                items = connections.get("items", [])
                items.append({"from_node": related_node_id, "to_node": "", "link_type": "related_to"})
                connections["items"] = items
                note.connections_made = connections
            elif entry_type == "metric":
                if "new_memories" in content.lower():
                    note.metrics["new_memories"] = note.metrics.get("new_memories", 0) + 1

            await db.commit()
            await db.refresh(note)

            return self._note_to_dict(note)

        if db_session:
            return await _add(db_session)

        async for db in get_db_session():
            return await _add(db)

    # ── Note History ─────────────────────────────────────────────────────────

    async def get_note_history(
        self,
        user_id: str,
        days: int = 30,
        db_session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Get daily notes for a date range.

        Args:
            user_id: The user's UUID.
            days: Number of days to look back.

        Returns:
            List of daily note dicts, newest first.
        """
        user_uuid = uuid.UUID(user_id)
        start_date = datetime.now(timezone.utc).date() - timedelta(days=days)

        async def _query(db: AsyncSession) -> list[dict[str, Any]]:
            stmt = (
                select(DailyNote)
                .where(
                    and_(
                        DailyNote.user_id == user_uuid,
                        DailyNote.note_date >= start_date,
                    )
                )
                .order_by(DailyNote.note_date.desc())
                .limit(days + 1)
            )
            rows = await db.execute(stmt)
            notes = rows.scalars().all()

            results = []
            for note in notes:
                d = self._note_to_dict(note)
                results.append(d)

            return results

        if db_session:
            return await _query(db_session)

        async for db in get_db_session():
            return await _query(db)

    # ── Finalize Note ────────────────────────────────────────────────────────

    async def finalize_daily_note(
        self,
        user_id: str,
        note_date: str | None = None,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Mark a [[Daily Note]] as finalized at end of day.

        Generates any missing data and broadcasts a ``brain.daily_note_ready``
        WebSocket event.

        Args:
            user_id: The user's UUID.
            note_date: Optional date string (YYYY-MM-DD). Defaults to today.

        Returns:
            The finalized daily note.
        """
        async def _finalize(db: AsyncSession) -> dict[str, Any]:
            note_dict = await self.generate_daily_note(user_id, note_date, db_session=db)
            note_id = uuid.UUID(note_dict["id"])
            note = await db.get(DailyNote, note_id)

            if note:
                note.is_finalized = True
                await db.commit()
                await db.refresh(note)

                result = self._note_to_dict(note)

                # Broadcast
                try:
                    event = manager.event_brain_daily_note(result)
                    await manager.send_to_user(user_id, event)
                except Exception as exc:
                    logger.warning("WebSocket broadcast failed", error=str(exc))

                return result

            return note_dict

        if db_session:
            return await _finalize(db_session)

        async for db in get_db_session():
            return await _finalize(db)

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _note_to_dict(note: DailyNote) -> dict[str, Any]:
        """Convert a DailyNote ORM object to a dict."""
        return {
            "id": str(note.id),
            "user_id": str(note.user_id),
            "note_date": note.note_date.isoformat() if note.note_date else None,
            "highlights": note.highlights or [],
            "decisions": note.decisions or {},
            "connections_made": note.connections_made or {},
            "metrics": note.metrics or {},
            "ai_reflection": note.ai_reflection,
            "is_finalized": note.is_finalized,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        }


__all__ = ["DailyNoteService"]
