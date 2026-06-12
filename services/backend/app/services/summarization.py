"""
Anansi Progressive Summarization Engine — Multi-layer knowledge distillation.

Implements Tiago Forte's [[Progressive Summarization]] method with 4 layers:
- Layer 1: One-sentence AI summary
- Layer 2: Bold highlights (key sentences)
- Layer 3: The original full content
- Layer 4: Compressed re-summary after a period

Automatically processes new nodes and re-summarises old ones.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from openai import AsyncOpenAI
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_db_session
from app.core.exceptions import NotFoundError
from app.models.brain import MemoryNode

logger = get_logger(__name__)


# ─── Default prompts for AI summarisation ─────────────────────────────────────


SYSTEM_PROMPT_SUMMARIZE = """You are Anansi's [[Progressive Summarization]] Engine.
Your job is to distill information into concise, accurate summaries.

Given the content of a memory node from the user's [[Second Brain]],
produce a Layer 1 summary — a single sentence that captures the essential
insight. Be specific, factual, and avoid vague language.

Respond with ONLY the summary sentence, no prefix or explanation."""


SYSTEM_PROMPT_HIGHLIGHT = """You are Anansi's [[Progressive Summarization]] Engine.
Given the full content of a memory node, extract the 2-5 most important
sentences as bold highlights (Layer 2). These should be the key takeaways
that someone would want to remember at a glance.

Return each highlight on a new line, numbered 1. 2. 3. etc.
Be concise — each highlight should be at most one sentence."""


SYSTEM_PROMPT_COMPRESS = """You are Anansi's [[Progressive Summarization]] Engine.
This memory node was originally created some time ago. Please produce
a Layer 4 compressed summary that:

1. Distills the ORIGINAL content into 2-3 sentences (max)
2. Preserves all factual claims and key numbers
3. Removes redundant or time-sensitive context
4. Makes the information as portable and timeless as possible

Also note if any information in this node may be outdated or require updating.

Respond with ONLY the compressed summary."""


SYSTEM_PROMPT_CROSS_NODES = """You are Anansi's [[Second Brain]] synthesis engine.
Given multiple related memory nodes, synthesise them into a new
higher-level insight. Identify patterns, contradictions, or connections
that aren't obvious from any single node.

Structure your response as:
- **Synthesis**: 2-3 sentence overview connecting the nodes
- **Key Pattern**: The main insight that emerges
- **Gap**: What's missing or uncertain

Keep it actionable and insightful."""


class SummarizationService:
    """Handles all four layers of [[Progressive Summarization]].

    Automatically processes new nodes (L1), highlights key content (L2),
    re-summarises old content (L4), and can synthesise across nodes.
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
        model: str = "",
        max_tokens: int = 500,
    ) -> str:
        """Call the configured AI model for text generation.

        Falls back to the default model if the specified model is unavailable.
        Returns an empty string on failure.

        Args:
            system_prompt: The system instruction.
            user_content: The content to process.
            model: Override model name.
            max_tokens: Max tokens in the response.

        Returns:
            The generated text, or empty string on failure.
        """
        if not settings.ai.openai_api_key:
            logger.warning("No OpenAI API key set — skipping AI call")
            return ""

        model = model or settings.ai.openai_default_model

        try:
            response = await self.openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=max_tokens,
                temperature=0.3,  # Low temp for factual distillation
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("AI summarisation call failed", error=str(exc))
            return ""

    # ── Layer 1: Summary ─────────────────────────────────────────────────────

    async def summarize_node(
        self,
        node_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Generate Layer 1 (one-sentence summary) for a node.

        Args:
            node_id: The node's UUID.
            db_session: Optional existing DB session.

        Returns:
            Updated node with the L1 summary populated.
        """
        uid = uuid.UUID(node_id)

        async def _summarize(db: AsyncSession) -> dict[str, Any]:
            node = await db.get(MemoryNode, uid)
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            content = f"Title: {node.title}\n\nContent: {node.content}"
            summary = await self._call_ai(
                SYSTEM_PROMPT_SUMMARIZE, content,
            )

            layers = node.layers or {}
            layers["l1_summary"] = summary.strip() if summary else None
            layers["l3_full"] = node.content
            node.layers = layers

            await db.commit()
            await db.refresh(node)

            return {
                "id": str(node.id),
                "layers": node.layers,
            }

        if db_session:
            return await _summarize(db_session)

        async for db in get_db_session():
            return await _summarize(db)

    # ── Layer 2: Highlights ─────────────────────────────────────────────────

    async def highlight_node(
        self,
        node_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Extract Layer 2 (bold highlights) for a node.

        AI identifies 2-5 key sentences from the content.

        Args:
            node_id: The node's UUID.
            db_session: Optional existing DB session.

        Returns:
            Updated node with L2 highlights populated.
        """
        uid = uuid.UUID(node_id)

        async def _highlight(db: AsyncSession) -> dict[str, Any]:
            node = await db.get(MemoryNode, uid)
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            highlights_text = await self._call_ai(
                SYSTEM_PROMPT_HIGHLIGHT, node.content,
            )

            # Parse numbered highlights into a list
            highlights = []
            if highlights_text:
                for line in highlights_text.strip().split("\n"):
                    line = line.strip()
                    # Remove numbering like "1. " or "- "
                    if line and (line[0].isdigit() or line.startswith("- ")):
                        cleaned = line.split(". ", 1)[-1] if ". " in line else line
                        cleaned = cleaned.lstrip("- ").strip()
                        if cleaned:
                            highlights.append(cleaned)
                    elif line:
                        highlights.append(line)

            layers = node.layers or {}
            layers["l2_highlights"] = highlights
            node.layers = layers

            await db.commit()
            await db.refresh(node)

            return {
                "id": str(node.id),
                "layers": node.layers,
            }

        if db_session:
            return await _highlight(db_session)

        async for db in get_db_session():
            return await _highlight(db)

    # ── Layer 4: Compressed ──────────────────────────────────────────────────

    async def compress_node(
        self,
        node_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Generate Layer 4 (compressed re-summary) for a node.

        Uses both the original content and any existing L1/L2 layers to
        produce a highly condensed, timeless version.

        Args:
            node_id: The node's UUID.
            db_session: Optional existing DB session.

        Returns:
            Updated node with L4 compressed.
        """
        uid = uuid.UUID(node_id)

        async def _compress(db: AsyncSession) -> dict[str, Any]:
            node = await db.get(MemoryNode, uid)
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            layers = node.layers or {}
            context_parts = [f"Title: {node.title}", f"Content: {node.content}"]
            if layers.get("l1_summary"):
                context_parts.append(f"Existing summary: {layers['l1_summary']}")

            content = "\n\n".join(context_parts)
            compressed = await self._call_ai(
                SYSTEM_PROMPT_COMPRESS, content, max_tokens=300,
            )

            layers["l4_compressed"] = compressed.strip() if compressed else None
            node.layers = layers

            await db.commit()
            await db.refresh(node)

            return {
                "id": str(node.id),
                "layers": node.layers,
            }

        if db_session:
            return await _compress(db_session)

        async for db in get_db_session():
            return await _compress(db)

    # ── Cross-Node Synthesis ────────────────────────────────────────────────

    async def summarize_cross_nodes(
        self,
        node_ids: list[str],
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Synthesise multiple related nodes into a higher-level insight.

        Takes the content of multiple nodes and produces a cross-cutting
        synthesis with patterns, connections, and gaps.

        Args:
            node_ids: List of node UUIDs to synthesise.
            db_session: Optional existing DB session.

        Returns:
            Dict with synthesis, key_pattern, and gap fields.
        """
        async def _synthesize(db: AsyncSession) -> dict[str, Any]:
            nodes = []
            for nid in node_ids:
                uid = uuid.UUID(nid)
                node = await db.get(MemoryNode, uid)
                if node and node.type != "archived":
                    layers = node.layers or {}
                    best_content = (
                        layers.get("l4_compressed")
                        or layers.get("l1_summary")
                        or node.content
                    )
                    nodes.append(f"## {node.title}\n{best_content}")

            if not nodes:
                return {
                    "synthesis": "",
                    "key_pattern": "",
                    "gap": "",
                }

            combined = "\n\n---\n\n".join(nodes)
            result_text = await self._call_ai(
                SYSTEM_PROMPT_CROSS_NODES, combined, max_tokens=800,
            )

            # Parse structured response
            synthesis = ""
            key_pattern = ""
            gap = ""

            if result_text:
                parts = result_text.split("**")
                for i, part in enumerate(parts):
                    if "Synthesis" in part and i + 1 < len(parts):
                        synthesis = parts[i + 1].strip().rstrip("*").strip()
                    elif "Key Pattern" in part and i + 1 < len(parts):
                        key_pattern = parts[i + 1].strip().rstrip("*").strip()
                    elif "Gap" in part and i + 1 < len(parts):
                        gap = parts[i + 1].strip().rstrip("*").strip()

            return {
                "synthesis": synthesis,
                "key_pattern": key_pattern,
                "gap": gap,
                "nodes_synthesized": len(nodes),
            }

        if db_session:
            return await _synthesize(db_session)

        async for db in get_db_session():
            return await _synthesize(db)

    # ── Batch Processing ────────────────────────────────────────────────────

    async def batch_process(
        self,
        user_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Process all nodes needing summarisation.

        - New nodes (no L1) get Layer 1 summary
        - Old nodes (>30 days, no L4) get Layer 4 compression
        - Nodes with L1 but no L2 get Layer 2 highlights

        Args:
            user_id: The user's UUID.
            db_session: Optional existing DB session.

        Returns:
            Dict with counts of each layer generated.
        """
        user_uuid = uuid.UUID(user_id)
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        stats = {"l1": 0, "l2": 0, "l4": 0}

        async def _batch(db: AsyncSession) -> dict[str, Any]:
            # 1. Nodes needing L1 summary (no l1_summary)
            l1_stmt = (
                select(MemoryNode)
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                        func.jsonb_extract_path_text(
                            MemoryNode.layers, "l1_summary"
                        ) == None,  # noqa: E711
                    )
                )
                .limit(50)
            )
            l1_rows = await db.execute(l1_stmt)
            for node in l1_rows.scalars().all():
                try:
                    await self.summarize_node(str(node.id), db_session=db)
                    stats["l1"] += 1
                except Exception as exc:
                    logger.warning(
                        "L1 summarisation failed",
                        node_id=str(node.id),
                        error=str(exc),
                    )

            # 2. Nodes needing L2 highlights (have L1, no L2)
            l2_stmt = (
                select(MemoryNode)
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                        func.jsonb_extract_path_text(
                            MemoryNode.layers, "l1_summary"
                        ).isnot(None),
                        func.jsonb_array_length(
                            func.jsonb_extract_path(
                                MemoryNode.layers, "l2_highlights"
                            )
                        ) == 0,  # noqa: E711
                    )
                )
                .limit(50)
            )
            l2_rows = await db.execute(l2_stmt)
            for node in l2_rows.scalars().all():
                try:
                    await self.highlight_node(str(node.id), db_session=db)
                    stats["l2"] += 1
                except Exception as exc:
                    logger.warning(
                        "L2 highlight failed",
                        node_id=str(node.id),
                        error=str(exc),
                    )

            # 3. Old nodes needing L4 compression (>30 days, no L4)
            l4_stmt = (
                select(MemoryNode)
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                        MemoryNode.created_at < thirty_days_ago,
                        func.jsonb_extract_path_text(
                            MemoryNode.layers, "l4_compressed"
                        ) == None,  # noqa: E711
                    )
                )
                .limit(50)
            )
            l4_rows = await db.execute(l4_stmt)
            for node in l4_rows.scalars().all():
                try:
                    await self.compress_node(str(node.id), db_session=db)
                    stats["l4"] += 1
                except Exception as exc:
                    logger.warning(
                        "L4 compression failed",
                        node_id=str(node.id),
                        error=str(exc),
                    )

            logger.info(
                "Batch summarisation complete",
                user_id=user_id,
                stats=stats,
            )
            return stats

        if db_session:
            return await _batch(db_session)

        async for db in get_db_session():
            return await _batch(db)

    # ── Node Layers ─────────────────────────────────────────────────────────

    async def get_node_layers(
        self,
        node_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Get all summarisation layers for a node.

        Returns the full layer data plus metadata about when each was created.

        Args:
            node_id: The node's UUID.
            db_session: Optional existing DB session.

        Returns:
            Dict with layers and node metadata.
        """
        uid = uuid.UUID(node_id)

        async def _get(db: AsyncSession) -> dict[str, Any]:
            node = await db.get(MemoryNode, uid)
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            layers = node.layers or {}
            return {
                "node_id": str(node.id),
                "title": node.title,
                "layers": {
                    "l1_summary": layers.get("l1_summary"),
                    "l2_highlights": layers.get("l2_highlights", []),
                    "l3_full": layers.get("l3_full", node.content),
                    "l4_compressed": layers.get("l4_compressed"),
                },
            }

        if db_session:
            return await _get(db_session)

        async for db in get_db_session():
            return await _get(db)


__all__ = ["SummarizationService"]
