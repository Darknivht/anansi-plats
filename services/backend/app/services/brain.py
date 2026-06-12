"""
Anansi Core Brain Service — Memory management, search, and brain analytics.

The heart of the [[Second Brain]] system. Handles creation, retrieval,
updating, and deletion of [[Atomic Notes]] with vector embeddings,
auto-linking, and WebSocket broadcasting.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from openai import AsyncOpenAI
from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, Text, and_, func, or_, select, text, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.models.brain import MemoryLink, MemoryNode, DailyNote, MemoryReview
from app.websocket.manager import manager

logger = get_logger(__name__)


class MemoryService:
    """Core service for managing [[Atomic Notes]] in the Second Brain.

    Provides CRUD operations, semantic + full-text search, review queue
    management, and brain analytics.
    """

    def __init__(self) -> None:
        self._openai: AsyncOpenAI | None = None

    # ── OpenAI Embeddings ─────────────────────────────────────────────────────

    @property
    def openai(self) -> AsyncOpenAI:
        if self._openai is None:
            self._openai = AsyncOpenAI(api_key=settings.ai.openai_api_key)
        return self._openai

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Uses the configured embedding model (default: text-embedding-3-small).
        Falls back gracefully if the API key is not set.

        Args:
            text: The text to embed.

        Returns:
            A 1536-dimensional embedding vector (list of floats).
        """
        if not settings.ai.openai_api_key:
            logger.warning("No OpenAI API key set — returning zero embedding")
            return [0.0] * settings.ai.embedding_dimensions

        try:
            response = await self.openai.embeddings.create(
                model=settings.ai.embedding_model,
                input=text,
                dimensions=settings.ai.embedding_dimensions,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.error("Embedding generation failed", error=str(exc))
            return [0.0] * settings.ai.embedding_dimensions

    # ── Node CRUD ─────────────────────────────────────────────────────────────

    async def create_node(
        self,
        user_id: str,
        type: str = "fact",
        title: str = "",
        content: str = "",
        tags: list[str] | None = None,
        source: str = "explicit",
        para_category: str | None = None,
        confidence: float = 0.7,
    ) -> dict[str, Any]:
        """Create an [[Atomic Note]] in the user's Second Brain.

        Generates embedding via OpenAI, auto-links to semantically similar
        nodes (>0.85 automatic, >0.75 propose), creates a [[Daily Note]]
        entry, and broadcasts a ``brain.node_created`` WebSocket event.

        Args:
            user_id: The owning user's UUID.
            type: Node type (fact, preference, pattern, relation, etc.).
            title: Short descriptive title.
            content: Full atomic note content.
            tags: Hierarchical tags (e.g. ['#work/client', '#finance']).
            source: Provenance (explicit, inferred, learned).
            para_category: PARA category (projects, areas, resources, archives).
            confidence: Confidence score 0.0-1.0.

        Returns:
            The created node as a serialisable dict.
        """
        tags = tags or []
        node_id = uuid.uuid4()
        user_uuid = uuid.UUID(user_id)

        # Generate embedding
        embed_text = f"{title}\n{content}"
        embedding = await self._generate_embedding(embed_text)

        async for db in get_db_session():
            node = MemoryNode(
                id=node_id,
                user_id=user_uuid,
                type=type,
                title=title,
                content=content,
                tags=tags,
                source=source,
                confidence=confidence,
                para_category=para_category,
                layers={
                    "l1_summary": None,
                    "l2_highlights": [],
                    "l3_full": content,
                    "l4_compressed": None,
                },
                embedding=embedding,
                review_interval=86400,  # 1 day
                next_review_at=datetime.now(timezone.utc),
                is_orphan=True,
                links_count=0,
                metadata_={
                    "created_via": source,
                    "access_count": 0,
                },
            )
            db.add(node)
            await db.flush()

            # Auto-link: find semantically similar nodes
            similar = await self._find_semantic_similar(
                db, embedding, node_id, user_uuid, threshold=0.75,
            )
            auto_links = 0
            proposed_links = []

            for sim_node_id, score in similar:
                from app.services.linking import LinkingService

                linking = LinkingService()
                if score >= 0.85:
                    await linking.create_link(
                        source_id=str(node_id),
                        target_id=str(sim_node_id),
                        link_type="related_to",
                        label="Semantic match",
                        context=f"Auto-linked with similarity {score:.2f}",
                        confidence=score,
                        is_auto_generated=True,
                        db_session=db,
                    )
                    auto_links += 1
                elif score >= 0.75:
                    proposed_links.append({
                        "node_id": str(sim_node_id),
                        "score": score,
                    })

            # Update orphan status
            node.is_orphan = node.links_count < 2

            await db.commit()
            await db.refresh(node)

            # Add entry to today's daily note
            try:
                from app.services.dailynote import DailyNoteService
                daily = DailyNoteService()
                await daily.add_entry(
                    user_id=user_id,
                    entry_type="connection",
                    content=f"Created new node: [[{title}]]",
                    related_node_id=str(node.id),
                    db_session=db,
                )
            except Exception as exc:
                logger.warning("Failed to add daily note entry", error=str(exc))

            # Build response
            result = self._node_to_dict(node)
            result["auto_links_created"] = auto_links
            result["proposed_links"] = proposed_links

            # Broadcast WebSocket event
            try:
                event = manager.event_brain_node_created(result)
                await manager.send_to_user(user_id, event)
            except Exception as exc:
                logger.warning("WebSocket broadcast failed", error=str(exc))

            return result

    async def get_node(self, node_id: str) -> dict[str, Any]:
        """Retrieve an [[Atomic Note]] with all its data.

        Returns the node with summarisation layers, both incoming and
        outgoing links with context, review history, and metadata.
        Increments the access counter.

        Args:
            node_id: The node's UUID.

        Returns:
            Full node data as a dict.

        Raises:
            NotFoundError: If the node does not exist.
        """
        uid = uuid.UUID(node_id)

        async for db in get_db_session():
            node = await db.get(
                MemoryNode,
                uid,
                options=[
                    selectinload(MemoryNode.outgoing_links),
                    selectinload(MemoryNode.incoming_links),
                    selectinload(MemoryNode.reviews),
                ],
            )
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            # Increment access count
            node.access_count += 1
            await db.commit()

            return self._node_to_dict(node, include_links=True, include_reviews=True)

    async def update_node(
        self,
        node_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an [[Atomic Note]].

        Regenerates the embedding if content or title changed, re-runs
        auto-linking, and broadcasts a ``brain.node_updated`` event.

        Args:
            node_id: The node's UUID.
            data: Fields to update (title, content, tags, type, etc.).

        Returns:
            Updated node data.
        """
        uid = uuid.UUID(node_id)

        async for db in get_db_session():
            node = await db.get(MemoryNode, uid)
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            # Track if content changed for re-embedding
            content_changed = False

            for key, value in data.items():
                if key == "embedding":
                    continue  # Never set embedding directly
                if key in ("title", "content"):
                    content_changed = True
                if key == "tags" and isinstance(value, list):
                    node.tags = value
                elif key == "metadata":
                    node.metadata_.update(value)
                elif hasattr(node, key):
                    setattr(node, key, value)

            # Re-generate embedding if content changed
            if content_changed:
                embed_text = f"{node.title}\n{node.content}"
                node.embedding = await self._generate_embedding(embed_text)

                # Re-run auto-linking
                from app.services.linking import LinkingService
                linking = LinkingService()
                await linking.batch_auto_link(
                    user_id=str(node.user_id),
                    db_session=db,
                )

            await db.commit()
            await db.refresh(node)

            result = self._node_to_dict(node, include_links=True)

            # Broadcast
            try:
                event = manager.event_brain_node_updated(result)
                await manager.send_to_user(str(node.user_id), event)
            except Exception:
                pass

            return result

    async def delete_node(self, node_id: str) -> None:
        """Soft-delete an [[Atomic Note]].

        Removes all associated links, marks the node as archived, updates
        the daily note entry.

        Args:
            node_id: The node's UUID.
        """
        uid = uuid.UUID(node_id)

        async for db in get_db_session():
            node = await db.get(MemoryNode, uid)
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            # Remove all links
            await db.execute(
                select(MemoryLink).where(
                    or_(
                        MemoryLink.source_id == uid,
                        MemoryLink.target_id == uid,
                    )
                )
            )

            # Soft delete: archive the node
            node.type = "archived"
            node.tags = [t for t in node.tags if t != "#active"]
            node.metadata_["archived_at"] = datetime.now(timezone.utc).isoformat()

            await db.commit()

            # Update daily note
            try:
                from app.services.dailynote import DailyNoteService
                daily = DailyNoteService()
                async for db2 in get_db_session():
                    await daily.add_entry(
                        user_id=str(node.user_id),
                        entry_type="highlight",
                        content=f"Deleted node: [[{node.title}]]",
                        db_session=db2,
                    )
            except Exception:
                pass

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_nodes(
        self,
        user_id: str,
        query: str = "",
        tags: list[str] | None = None,
        types: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Combined full-text + semantic search across the user's brain.

        Returns results ranked by relevance. Uses PostgreSQL FTS (tsvector)
        for keyword matching and pgvector cosine similarity for semantic
        search, then merges and deduplicates.

        Args:
            user_id: The user's UUID.
            query: Free-text search query.
            tags: Filter by tags.
            types: Filter by node types.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            List of matching nodes ranked by relevance.
        """
        user_uuid = uuid.UUID(user_id)
        results: list[dict[str, Any]] = []

        async for db in get_db_session():
            # Base conditions
            conditions = [MemoryNode.user_id == user_uuid]

            if tags:
                conditions.append(MemoryNode.tags.contains(tags))

            if types:
                conditions.append(MemoryNode.type.in_(types))

            if query:
                # Full-text search via tsvector
                ts_query = func.plainto_tsquery("english", query)
                ts_vector = func.to_tsvector("english", MemoryNode.title + " " + MemoryNode.content)
                rank = func.ts_rank(ts_vector, ts_query).label("rank")

                fts_condition = ts_vector.op("@@")(ts_query)
                conditions.append(fts_condition)

                stmt = (
                    select(MemoryNode, rank)
                    .where(and_(*conditions))
                    .order_by(desc(rank))
                    .limit(limit)
                    .offset(offset)
                )
            else:
                stmt = (
                    select(MemoryNode)
                    .where(and_(*conditions))
                    .order_by(desc(MemoryNode.created_at))
                    .limit(limit)
                    .offset(offset)
                )

            rows = await db.execute(stmt)

            for row in rows.unique().all():
                if isinstance(row, tuple):
                    node = row[0]
                else:
                    node = row
                node_dict = self._node_to_dict(node)
                results.append(node_dict)

            # If query is provided, also do semantic search and merge
            if query and settings.ai.openai_api_key:
                try:
                    q_embedding = await self._generate_embedding(query)
                    vec = Vector(settings.ai.embedding_dimensions)
                    similarity = MemoryNode.embedding.cosine_distance(q_embedding).label("distance")

                    sem_stmt = (
                        select(MemoryNode, similarity)
                        .where(
                            and_(
                                MemoryNode.user_id == user_uuid,
                                MemoryNode.embedding.isnot(None),
                                *[
                                    MemoryNode.tags.contains(tags)
                                    for _ in [1] if tags
                                ],
                                *[
                                    MemoryNode.type.in_(types)
                                    for _ in [1] if types
                                ],
                            )
                        )
                        .order_by(similarity)
                        .limit(limit)
                    )
                    sem_rows = await db.execute(sem_stmt)
                    existing_ids = {r["id"] for r in results}
                    for row in sem_rows.unique().all():
                        node, distance = row
                        node_dict = self._node_to_dict(node)
                        node_dict["semantic_distance"] = round(float(distance), 4)
                        if node_dict["id"] not in existing_ids:
                            results.append(node_dict)
                except Exception as exc:
                    logger.warning("Semantic search failed", error=str(exc))

        return results[:limit]

    # ── Review Queue ──────────────────────────────────────────────────────────

    async def get_review_queue(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get nodes due for [[Spaced Repetition]] review.

        Returns nodes where ``next_review_at <= NOW()``, ordered by
        ``review_interval ASC`` (most urgent first).

        Args:
            user_id: The user's UUID.
            limit: Max results.

        Returns:
            List of nodes due for review.
        """
        user_uuid = uuid.UUID(user_id)
        now = datetime.now(timezone.utc)

        async for db in get_db_session():
            stmt = (
                select(MemoryNode)
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.next_review_at <= now,
                        MemoryNode.type != "archived",
                    )
                )
                .order_by(MemoryNode.review_interval.asc())
                .limit(limit)
            )
            rows = await db.execute(stmt)
            nodes = rows.scalars().all()

            return [self._node_to_dict(n) for n in nodes]

    # ── Brain Stats ───────────────────────────────────────────────────────────

    async def get_brain_stats(self, user_id: str) -> dict[str, Any]:
        """Get comprehensive brain health statistics.

        Returns total nodes, links, clusters, orphan count, graph density,
        and weekly growth metrics.

        Args:
            user_id: The user's UUID.

        Returns:
            Dict with brain statistics.
        """
        user_uuid = uuid.UUID(user_id)
        now = datetime.now(timezone.utc)

        async for db in get_db_session():
            # Total nodes (non-archived)
            total_nodes_result = await db.execute(
                select(func.count(MemoryNode.id)).where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                    )
                )
            )
            total_nodes = total_nodes_result.scalar() or 0

            # Total links
            total_links_result = await db.execute(
                select(func.count(MemoryLink.id)).where(
                    MemoryLink.user_id == user_uuid,
                )
            )
            total_links = total_links_result.scalar() or 0

            # Orphan count (nodes with <2 links, non-archived)
            orphan_result = await db.execute(
                select(func.count(MemoryNode.id)).where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                        MemoryNode.links_count < 2,
                    )
                )
            )
            orphan_count = orphan_result.scalar() or 0

            # Nodes created this week
            week_ago = now - __import__("datetime").timedelta(days=7)
            weekly_nodes_result = await db.execute(
                select(func.count(MemoryNode.id)).where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.created_at >= week_ago,
                    )
                )
            )
            weekly_nodes = weekly_nodes_result.scalar() or 0

            # Links created this week
            weekly_links_result = await db.execute(
                select(func.count(MemoryLink.id)).where(
                    and_(
                        MemoryLink.user_id == user_uuid,
                        MemoryLink.created_at >= week_ago,
                    )
                )
            )
            weekly_links = weekly_links_result.scalar() or 0

            # Reviews completed this week
            weekly_reviews_result = await db.execute(
                select(func.count(MemoryReview.id)).where(
                    and_(
                        MemoryReview.user_id == user_uuid,
                        MemoryReview.created_at >= week_ago,
                    )
                )
            )
            weekly_reviews = weekly_reviews_result.scalar() or 0

            # Graph density
            density = 0.0
            if total_nodes > 1:
                max_possible = total_nodes * (total_nodes - 1) / 2
                density = round(total_links / max_possible, 4) if max_possible > 0 else 0.0

            # Tag distribution
            tag_query = select(MemoryNode.tags).where(
                and_(
                    MemoryNode.user_id == user_uuid,
                    MemoryNode.type != "archived",
                )
            )
            tag_rows = await db.execute(tag_query)
            all_tags: list[str] = []
            for row in tag_rows:
                all_tags.extend(row[0] if row[0] else [])
            tag_counts: dict[str, int] = {}
            for t in all_tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1
            top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:20]

            # Node type distribution
            type_query = (
                select(MemoryNode.type, func.count(MemoryNode.id))
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                    )
                )
                .group_by(MemoryNode.type)
            )
            type_rows = await db.execute(type_query)
            type_distribution = {row[0]: row[1] for row in type_rows}

            return {
                "total_nodes": total_nodes,
                "total_links": total_links,
                "orphan_count": orphan_count,
                "graph_density": density,
                "weekly_growth": {
                    "new_nodes": weekly_nodes,
                    "new_links": weekly_links,
                    "reviews_completed": weekly_reviews,
                },
                "tags": [{"tag": t, "count": c} for t, c in top_tags],
                "type_distribution": type_distribution,
                "health_score": self._calculate_health_score(
                    total_nodes, total_links, orphan_count, density,
                ),
            }

    # ── Internal Helpers ─────────────────────────────────────────────────────

    async def _find_semantic_similar(
        self,
        db: AsyncSession,
        embedding: list[float],
        node_id: uuid.UUID,
        user_id: uuid.UUID,
        threshold: float = 0.75,
        limit: int = 20,
    ) -> list[tuple[str, float]]:
        """Find semantically similar nodes using cosine similarity.

        Args:
            db: Database session.
            embedding: Query embedding vector.
            node_id: Exclude this node from results.
            user_id: Only search within this user's brain.
            threshold: Minimum similarity threshold.
            limit: Max results.

        Returns:
            List of (node_id, similarity_score) tuples.
        """
        try:
            distance_func = MemoryNode.embedding.cosine_distance(embedding)
            stmt = (
                select(MemoryNode.id, distance_func)
                .where(
                    and_(
                        MemoryNode.user_id == user_id,
                        MemoryNode.id != node_id,
                        MemoryNode.embedding.isnot(None),
                        MemoryNode.type != "archived",
                    )
                )
                .order_by(distance_func)
                .limit(limit)
            )
            rows = await db.execute(stmt)
            results = []
            for row in rows:
                sim_id, distance = row
                similarity = 1.0 - float(distance) if distance is not None else 0.0
                if similarity >= threshold:
                    results.append((str(sim_id), similarity))
            return results
        except Exception as exc:
            logger.warning("Semantic similarity search failed", error=str(exc))
            return []

    @staticmethod
    def _calculate_health_score(
        total_nodes: int,
        total_links: int,
        orphan_count: int,
        density: float,
    ) -> float:
        """Calculate a brain health score from 0.0 to 1.0."""
        if total_nodes == 0:
            return 0.0

        # Density score: aim for 0.1+ density
        density_score = min(density * 10, 1.0)

        # Orphan penalty
        orphan_ratio = orphan_count / total_nodes if total_nodes > 0 else 1.0
        orphan_score = 1.0 - orphan_ratio

        # Link coverage: each node should have at least 2 links
        # Approximate by comparing total links to nodes
        link_ratio = total_links / total_nodes if total_nodes > 0 else 0
        link_score = min(link_ratio / 2, 1.0)

        return round(
            (density_score * 0.3 + orphan_score * 0.35 + link_score * 0.35),
            4,
        )

    @staticmethod
    def _node_to_dict(
        node: MemoryNode,
        include_links: bool = False,
        include_reviews: bool = False,
    ) -> dict[str, Any]:
        """Convert a MemoryNode ORM object to a serialisable dict."""
        result: dict[str, Any] = {
            "id": str(node.id),
            "user_id": str(node.user_id),
            "type": node.type,
            "title": node.title,
            "content": node.content,
            "layers": node.layers or {},
            "tags": node.tags or [],
            "metadata": {
                "confidence": node.confidence,
                "access_count": node.access_count,
                "source": node.source,
                "review_status": node.review_status,
            },
            "review_interval": node.review_interval,
            "next_review_at": node.next_review_at.isoformat() if node.next_review_at else None,
            "last_reviewed_at": node.last_reviewed_at.isoformat() if node.last_reviewed_at else None,
            "is_orphan": node.is_orphan,
            "links_count": node.links_count,
            "para_category": node.para_category,
            "created_at": node.created_at.isoformat() if node.created_at else None,
            "updated_at": node.updated_at.isoformat() if node.updated_at else None,
        }

        if include_links:
            links = []
            if hasattr(node, "outgoing_links") and node.outgoing_links:
                for link in node.outgoing_links:
                    links.append({
                        "id": str(link.id),
                        "source_id": str(link.source_id),
                        "target_id": str(link.target_id),
                        "link_type": link.link_type,
                        "label": link.label,
                        "context": link.context,
                        "strength": link.strength,
                        "confidence": link.confidence,
                        "is_auto_generated": link.is_auto_generated,
                        "created_at": link.created_at.isoformat() if link.created_at else None,
                        "direction": "outgoing",
                    })
            if hasattr(node, "incoming_links") and node.incoming_links:
                for link in node.incoming_links:
                    links.append({
                        "id": str(link.id),
                        "source_id": str(link.source_id),
                        "target_id": str(link.target_id),
                        "link_type": link.link_type,
                        "label": link.label,
                        "context": link.context,
                        "strength": link.strength,
                        "confidence": link.confidence,
                        "is_auto_generated": link.is_auto_generated,
                        "created_at": link.created_at.isoformat() if link.created_at else None,
                        "direction": "incoming",
                    })
            result["links"] = links

        if include_reviews and hasattr(node, "reviews") and node.reviews:
            result["reviews"] = [
                {
                    "id": str(r.id),
                    "rating": r.rating,
                    "interval_before": r.interval_before,
                    "interval_after": r.interval_after,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in node.reviews[-20:]
            ]

        return result


__all__ = ["MemoryService"]
