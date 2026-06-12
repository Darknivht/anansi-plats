"""
Anansi Auto-Linking Engine — Intelligent link creation and suggestion.

Handles semantic similarity matching, temporal proximity linking,
entity overlap detection, and batch auto-linking passes for orphan nodes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog import get_logger

from app.core.events import get_db_session
from app.core.exceptions import NotFoundError, ConflictError
from app.models.brain import MemoryLink, MemoryNode
from app.websocket.manager import manager

logger = get_logger(__name__)

# Link type taxonomy from the spec
LINK_TYPES = [
    "related_to",
    "categorized_as",
    "causes",
    "contradicts",
    "mentioned_in",
    "supports",
    "follows_from",
    "user_defined",
]


class LinkingService:
    """Service for managing [[bidirectional links]] between memory nodes.

    Handles auto-linking via semantic similarity, link proposals,
    and batch processing for orphan nodes.
    """

    async def find_similar_nodes(
        self,
        node_id: str,
        threshold: float = 0.75,
        limit: int = 20,
        db_session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Find semantically similar nodes using pgvector.

        Args:
            node_id: Source node UUID.
            threshold: Minimum cosine similarity (0.0-1.0).
            limit: Max number of results.
            db_session: Optional existing DB session.

        Returns:
            List of {node_id, title, similarity} dicts.

        Raises:
            NotFoundError: If the node doesn't exist or has no embedding.
        """
        uid = uuid.UUID(node_id)

        async def _query(db: AsyncSession) -> list[dict[str, Any]]:
            node = await db.get(MemoryNode, uid)
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )
            if not node.embedding:
                return []

            # Cosine distance using pgvector
            distance_func = MemoryNode.embedding.cosine_distance(node.embedding)
            stmt = (
                select(MemoryNode.id, MemoryNode.title, distance_func)
                .where(
                    and_(
                        MemoryNode.user_id == node.user_id,
                        MemoryNode.id != uid,
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
                sim_id, title, distance = row
                similarity = 1.0 - float(distance) if distance is not None else 0.0
                if similarity >= threshold:
                    # Check if link already exists
                    existing = await self._link_exists(db, uid, sim_id)
                    results.append({
                        "node_id": str(sim_id),
                        "title": title,
                        "similarity": round(similarity, 4),
                        "already_linked": existing,
                    })
            return results

        if db_session:
            return await _query(db_session)

        async for db in get_db_session():
            return await _query(db)

    async def propose_links(
        self,
        node_id: str,
        db_session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Generate link suggestions for a node.

        Combines three strategies:
        1. **Semantic**: Cosine similarity >0.75
        2. **Entity overlap**: Shared tags/entities
        3. **Temporal proximity**: Nodes created within 1 hour of each other

        Args:
            node_id: The node to find link suggestions for.
            db_session: Optional existing DB session.

        Returns:
            List of proposed link objects with reason and score.
        """
        uid = uuid.UUID(node_id)
        proposals: list[dict[str, Any]] = []

        async def _query(db: AsyncSession) -> list[dict[str, Any]]:
            nonlocal proposals
            node = await db.get(MemoryNode, uid)
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            # 1. Semantic proposals (from find_similar_nodes)
            semantic = await self.find_similar_nodes(
                node_id, threshold=0.75, limit=10, db_session=db,
            )
            for s in semantic:
                if not s["already_linked"]:
                    proposals.append({
                        "target_id": s["node_id"],
                        "target_title": s["title"],
                        "link_type": "related_to",
                        "reason": f"Semantic similarity ({s['similarity']:.2f})",
                        "confidence": s["similarity"],
                        "strategy": "semantic",
                    })

            # 2. Entity/tag overlap
            if node.tags:
                tag_condition = MemoryNode.tags.overlap(node.tags)
                tag_stmt = (
                    select(MemoryNode.id, MemoryNode.title, MemoryNode.tags)
                    .where(
                        and_(
                            MemoryNode.user_id == node.user_id,
                            MemoryNode.id != uid,
                            tag_condition,
                            MemoryNode.type != "archived",
                        )
                    )
                    .limit(10)
                )
                tag_rows = await db.execute(tag_stmt)
                tag_proposals = set()
                for row in tag_rows:
                    nid, title, ntags = row
                    nid_str = str(nid)
                    shared_tags = set(node.tags or []) & set(ntags or [])
                    # Skip if already proposed semantically or linked
                    already_proposed = any(
                        p["target_id"] == nid_str for p in proposals
                    )
                    if already_proposed:
                        continue
                    existing = await self._link_exists(db, uid, nid)
                    if not existing and nid_str not in tag_proposals:
                        tag_proposals.add(nid_str)
                        proposals.append({
                            "target_id": nid_str,
                            "target_title": title,
                            "link_type": "categorized_as",
                            "reason": f"Shared tags: {', '.join(shared_tags)}",
                            "confidence": min(len(shared_tags) * 0.1 + 0.6, 0.95),
                            "strategy": "tag_overlap",
                        })

            # 3. Temporal proximity (same hour creation)
            if node.created_at:
                hour_start = node.created_at.replace(
                    minute=0, second=0, microsecond=0,
                )
                hour_end = hour_start.replace(hour=hour_start.hour + 1)
                time_stmt = (
                    select(MemoryNode.id, MemoryNode.title)
                    .where(
                        and_(
                            MemoryNode.user_id == node.user_id,
                            MemoryNode.id != uid,
                            MemoryNode.created_at >= hour_start,
                            MemoryNode.created_at < hour_end,
                            MemoryNode.type != "archived",
                        )
                    )
                    .limit(5)
                )
                time_rows = await db.execute(time_stmt)
                for row in time_rows:
                    nid_str = str(row[0])
                    already_proposed = any(
                        p["target_id"] == nid_str for p in proposals
                    )
                    if already_proposed:
                        continue
                    existing = await self._link_exists(db, uid, uuid.UUID(nid_str))
                    if not existing:
                        proposals.append({
                            "target_id": nid_str,
                            "target_title": row[1],
                            "link_type": "mentioned_in",
                            "reason": "Created within the same hour",
                            "confidence": 0.5,
                            "strategy": "temporal_proximity",
                        })

            # Sort by confidence descending
            proposals.sort(key=lambda p: -p["confidence"])
            return proposals[:20]

        if db_session:
            return await _query(db_session)

        async for db in get_db_session():
            return await _query(db)

    async def create_link(
        self,
        source_id: str,
        target_id: str,
        link_type: str = "related_to",
        label: str | None = None,
        context: str | None = None,
        confidence: float = 0.7,
        strength: float = 0.5,
        is_auto_generated: bool = False,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Create a [[bidirectional link]] between two memory nodes.

        Updates both nodes' link counts and orphan status, and broadcasts
        a ``brain.link_created`` WebSocket event.

        Args:
            source_id: Source node UUID.
            target_id: Target node UUID.
            link_type: Type of link (related_to, categorized_as, etc.).
            label: Human-readable label for the link.
            context: Explanation of why the link exists.
            confidence: Confidence score 0.0-1.0.
            strength: Link strength 0.0-1.0 (increases with use).
            is_auto_generated: Whether the AI created this link.
            db_session: Optional existing DB session.

        Returns:
            The created link as a dict.

        Raises:
            NotFoundError: If either node doesn't exist.
            ConflictError: If the link already exists.
        """
        src_uuid = uuid.UUID(source_id)
        tgt_uuid = uuid.UUID(target_id)

        if link_type not in LINK_TYPES:
            link_type = "user_defined"

        async def _create(db: AsyncSession) -> dict[str, Any]:
            # Verify both nodes exist
            source_node = await db.get(MemoryNode, src_uuid)
            if not source_node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=source_id,
                )
            target_node = await db.get(MemoryNode, tgt_uuid)
            if not target_node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=target_id,
                )

            # Check for existing link
            existing = await self._link_exists(db, src_uuid, tgt_uuid, link_type)
            if existing:
                raise ConflictError(
                    message=f"Link already exists between {source_id} and {target_id} with type {link_type}",
                )

            link = MemoryLink(
                id=uuid.uuid4(),
                user_id=source_node.user_id,
                source_id=src_uuid,
                target_id=tgt_uuid,
                link_type=link_type,
                label=label,
                context=context,
                confidence=confidence,
                strength=strength,
                is_auto_generated=is_auto_generated,
            )
            db.add(link)

            # Update link counts on both nodes
            source_node.links_count = await self._count_links(db, src_uuid)
            target_node.links_count = await self._count_links(db, tgt_uuid)

            # Update orphan status
            source_node.is_orphan = source_node.links_count < 2
            target_node.is_orphan = target_node.links_count < 2

            await db.commit()
            await db.refresh(link)

            result = {
                "id": str(link.id),
                "source_id": str(link.source_id),
                "target_id": str(link.target_id),
                "link_type": link.link_type,
                "label": link.label,
                "context": link.context,
                "confidence": link.confidence,
                "strength": link.strength,
                "is_auto_generated": link.is_auto_generated,
                "created_at": link.created_at.isoformat() if link.created_at else None,
            }

            # Broadcast
            try:
                event = manager.event_brain_link_created(result)
                await manager.send_to_user(str(link.user_id), event)
            except Exception as exc:
                logger.warning("WebSocket broadcast failed", error=str(exc))

            return result

        if db_session:
            return await _create(db_session)

        async for db in get_db_session():
            return await _create(db)

    async def remove_link(
        self,
        link_id: str,
        db_session: AsyncSession | None = None,
    ) -> None:
        """Remove a [[bidirectional link]].

        Updates the link counts and orphan status of both connected nodes.

        Args:
            link_id: The link's UUID.
            db_session: Optional existing DB session.
        """
        uid = uuid.UUID(link_id)

        async def _remove(db: AsyncSession) -> None:
            link = await db.get(MemoryLink, uid)
            if not link:
                raise NotFoundError(
                    resource_type="memory_link",
                    resource_id=link_id,
                )

            source_id = link.source_id
            target_id = link.target_id
            user_id = link.user_id

            await db.delete(link)

            # Update link counts
            for nid in (source_id, target_id):
                node = await db.get(MemoryNode, nid)
                if node:
                    node.links_count = await self._count_links(db, nid)
                    node.is_orphan = node.links_count < 2

            await db.commit()

        if db_session:
            return await _remove(db_session)

        async for db in get_db_session():
            return await _remove(db)

    async def get_links_for_node(
        self,
        node_id: str,
        db_session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Get all links (outgoing + incoming) for a node with context.

        Args:
            node_id: The node's UUID.
            db_session: Optional existing DB session.

        Returns:
            List of link dicts with direction metadata.
        """
        uid = uuid.UUID(node_id)

        async def _query(db: AsyncSession) -> list[dict[str, Any]]:
            node = await db.get(
                MemoryNode,
                uid,
                options=[
                    selectinload(MemoryNode.outgoing_links),
                    selectinload(MemoryNode.incoming_links),
                ],
            )
            if not node:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            links = []
            for link in node.outgoing_links:
                target = await db.get(MemoryNode, link.target_id)
                links.append({
                    "id": str(link.id),
                    "source_id": str(link.source_id),
                    "target_id": str(link.target_id),
                    "target_title": target.title if target else "Unknown",
                    "link_type": link.link_type,
                    "label": link.label,
                    "context": link.context,
                    "strength": link.strength,
                    "confidence": link.confidence,
                    "is_auto_generated": link.is_auto_generated,
                    "direction": "outgoing",
                    "created_at": link.created_at.isoformat() if link.created_at else None,
                })
            for link in node.incoming_links:
                source = await db.get(MemoryNode, link.source_id)
                links.append({
                    "id": str(link.id),
                    "source_id": str(link.source_id),
                    "source_title": source.title if source else "Unknown",
                    "target_id": str(link.target_id),
                    "link_type": link.link_type,
                    "label": link.label,
                    "context": link.context,
                    "strength": link.strength,
                    "confidence": link.confidence,
                    "is_auto_generated": link.is_auto_generated,
                    "direction": "incoming",
                    "created_at": link.created_at.isoformat() if link.created_at else None,
                })

            return links

        if db_session:
            return await _query(db_session)

        async for db in get_db_session():
            return await _query(db)

    async def batch_auto_link(
        self,
        user_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Run a full auto-linking pass across all orphan nodes.

        Finds all nodes with <2 links and attempts to link them to
        semantically similar nodes (>0.85 threshold).

        Args:
            user_id: The user's UUID.
            db_session: Optional existing DB session.

        Returns:
            Dict with summary of links created and nodes processed.
        """
        user_uuid = uuid.UUID(user_id)

        async def _batch(db: AsyncSession) -> dict[str, Any]:
            # Find all orphan or low-link nodes
            stmt = (
                select(MemoryNode)
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                        MemoryNode.links_count < 2,
                        MemoryNode.embedding.isnot(None),
                    )
                )
                .limit(100)
            )
            rows = await db.execute(stmt)
            orphan_nodes = rows.scalars().all()

            total_processed = 0
            total_links_created = 0

            for node in orphan_nodes:
                similar = await self.find_similar_nodes(
                    str(node.id), threshold=0.85, limit=5, db_session=db,
                )
                for match in similar:
                    if match["already_linked"]:
                        continue
                    link_id = match["node_id"]
                    try:
                        await self.create_link(
                            source_id=str(node.id),
                            target_id=link_id,
                            link_type="related_to",
                            label="Semantic match",
                            context=f"Auto-linked with similarity {match['similarity']:.2f}",
                            confidence=match["similarity"],
                            is_auto_generated=True,
                            db_session=db,
                        )
                        total_links_created += 1
                    except ConflictError:
                        continue
                    except Exception as exc:
                        logger.warning(
                            "Auto-link failed",
                            node_id=str(node.id),
                            target_id=link_id,
                            error=str(exc),
                        )
                total_processed += 1

            logger.info(
                "Batch auto-link complete",
                user_id=user_id,
                processed=total_processed,
                links_created=total_links_created,
            )

            return {
                "nodes_processed": total_processed,
                "links_created": total_links_created,
            }

        if db_session:
            return await _batch(db_session)

        async for db in get_db_session():
            return await _batch(db)

    # ── Internal Helpers ─────────────────────────────────────────────────────

    async def _link_exists(
        self,
        db: AsyncSession,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        link_type: str | None = None,
    ) -> bool:
        """Check if a link already exists between two nodes."""
        conditions = [
            or_(
                and_(
                    MemoryLink.source_id == source_id,
                    MemoryLink.target_id == target_id,
                ),
                and_(
                    MemoryLink.source_id == target_id,
                    MemoryLink.target_id == source_id,
                ),
            )
        ]
        if link_type:
            conditions.append(MemoryLink.link_type == link_type)

        stmt = select(MemoryLink.id).where(and_(*conditions)).limit(1)
        result = await db.execute(stmt)
        return result.scalar() is not None

    async def _count_links(
        self,
        db: AsyncSession,
        node_id: uuid.UUID,
    ) -> int:
        """Count total links (outgoing + incoming) for a node."""
        stmt = select(func.count(MemoryLink.id)).where(
            or_(
                MemoryLink.source_id == node_id,
                MemoryLink.target_id == node_id,
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or 0


__all__ = ["LinkingService", "LINK_TYPES"]
