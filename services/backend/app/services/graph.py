"""
Anansi Graph Service — Knowledge web queries, visualization data,
cluster detection, and Obsidian vault export.

Provides the data layer for the interactive [[Graph View]] and all
graph-level operations on the user's [[Second Brain]].
"""

from __future__ import annotations

import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from neo4j import AsyncGraphDatabase
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_db_session, get_neo4j
from app.core.exceptions import NotFoundError
from app.models.brain import MemoryLink, MemoryNode, DailyNote
from app.models.user import User

logger = get_logger(__name__)


class GraphService:
    """Service for graph-level operations on the [[Second Brain]] knowledge web.

    Provides data for the interactive [[Graph View]], cluster analysis,
    orphan detection, growth metrics, and Obsidian vault export.
    """

    # ── Full Graph ───────────────────────────────────────────────────────────

    async def get_full_graph(
        self,
        user_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Get all nodes and edges for graph visualization.

        Returns a ``{nodes, edges}`` structure suitable for rendering
        in the interactive [[Graph View]].

        Args:
            user_id: The user's UUID.
            db_session: Optional existing DB session.

        Returns:
            Dict with ``nodes`` (list) and ``edges`` (list).
        """
        user_uuid = uuid.UUID(user_id)

        async def _query(db: AsyncSession) -> dict[str, Any]:
            # Get all non-archived nodes
            nodes_stmt = (
                select(MemoryNode)
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                    )
                )
                .options(selectinload(MemoryNode.outgoing_links))
                .order_by(MemoryNode.created_at.desc())
            )
            rows = await db.execute(nodes_stmt)
            nodes = rows.scalars().all()

            node_list = []
            node_ids = set()

            for node in nodes:
                node_ids.add(node.id)
                node_list.append({
                    "id": str(node.id),
                    "title": node.title,
                    "type": node.type,
                    "tags": node.tags or [],
                    "links_count": node.links_count,
                    "is_orphan": node.is_orphan,
                    "para_category": node.para_category,
                    "created_at": node.created_at.isoformat() if node.created_at else None,
                    "summary": (node.layers or {}).get("l1_summary", ""),
                })

            # Get all links between these nodes
            edges = []
            edge_ids = set()

            for node in nodes:
                for link in (node.outgoing_links or []):
                    if link.target_id in node_ids:
                        edge_key = f"{link.source_id}-{link.target_id}-{link.link_type}"
                        if edge_key not in edge_ids:
                            edge_ids.add(edge_key)
                            edges.append({
                                "id": str(link.id),
                                "source": str(link.source_id),
                                "target": str(link.target_id),
                                "link_type": link.link_type,
                                "label": link.label,
                                "strength": link.strength,
                                "confidence": link.confidence,
                                "is_auto_generated": link.is_auto_generated,
                            })

            return {
                "nodes": node_list,
                "edges": edges,
                "metadata": {
                    "total_nodes": len(node_list),
                    "total_edges": len(edges),
                    "orphan_count": sum(1 for n in node_list if n["is_orphan"]),
                },
            }

        if db_session:
            return await _query(db_session)

        async for db in get_db_session():
            return await _query(db)

    # ── Local Graph (Focus View) ─────────────────────────────────────────────

    async def get_local_graph(
        self,
        node_id: str,
        depth: int = 2,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Get the subgraph around a node using BFS traversal.

        Used for the "focus view" in the graph visualization. Returns
        all nodes and edges within the specified depth.

        Args:
            node_id: The central node's UUID.
            depth: Traversal depth (1, 2, or 3).
            db_session: Optional existing DB session.

        Returns:
            Dict with ``nodes``, ``edges``, and ``metadata``.

        Raises:
            NotFoundError: If the central node doesn't exist.
        """
        uid = uuid.UUID(node_id)
        depth = max(1, min(depth, 3))  # Clamp between 1 and 3

        async def _query(db: AsyncSession) -> dict[str, Any]:
            central = await db.get(MemoryNode, uid)
            if not central:
                raise NotFoundError(
                    resource_type="memory_node",
                    resource_id=node_id,
                )

            # BFS traversal
            visited_nodes: set[uuid.UUID] = {uid}
            visited_edges: set[str] = set()
            queue: deque[tuple[uuid.UUID, int]] = deque([(uid, 0)])

            nodes_dict: dict[str, dict[str, Any]] = {
                str(uid): {
                    "id": str(central.id),
                    "title": central.title,
                    "type": central.type,
                    "tags": central.tags or [],
                    "links_count": central.links_count,
                    "is_orphan": central.is_orphan,
                    "para_category": central.para_category,
                    "created_at": central.created_at.isoformat() if central.created_at else None,
                    "summary": (central.layers or {}).get("l1_summary", ""),
                    "depth": 0,
                }
            }
            edges_list: list[dict[str, Any]] = []

            while queue:
                current_id, current_depth = queue.popleft()

                if current_depth >= depth:
                    continue

                # Get node and its links
                current_node = await db.get(
                    MemoryNode,
                    current_id,
                    options=[selectinload(MemoryNode.outgoing_links)],
                )
                if not current_node:
                    continue

                for link in (current_node.outgoing_links or []):
                    edge_key = f"{link.source_id}-{link.target_id}"
                    if edge_key not in visited_edges:
                        visited_edges.add(edge_key)
                        edges_list.append({
                            "id": str(link.id),
                            "source": str(link.source_id),
                            "target": str(link.target_id),
                            "link_type": link.link_type,
                            "label": link.label,
                            "strength": link.strength,
                            "confidence": link.confidence,
                            "is_auto_generated": link.is_auto_generated,
                        })

                    # Add the linked node to traversal if not visited
                    linked_id = link.target_id if link.source_id == current_id else link.source_id
                    linked_id_str = str(linked_id)

                    if linked_id not in visited_nodes:
                        visited_nodes.add(linked_id)
                        linked_node = await db.get(MemoryNode, linked_id)
                        if linked_node and linked_node.type != "archived":
                            nodes_dict[linked_id_str] = {
                                "id": linked_id_str,
                                "title": linked_node.title,
                                "type": linked_node.type,
                                "tags": linked_node.tags or [],
                                "links_count": linked_node.links_count,
                                "is_orphan": linked_node.is_orphan,
                                "para_category": linked_node.para_category,
                                "created_at": linked_node.created_at.isoformat() if linked_node.created_at else None,
                                "summary": (linked_node.layers or {}).get("l1_summary", ""),
                                "depth": current_depth + 1,
                            }
                            queue.append((linked_id, current_depth + 1))

                # Also check incoming links (other nodes that point to this one)
                incoming_stmt = select(MemoryLink).where(
                    MemoryLink.target_id == current_id,
                )
                inc_rows = await db.execute(incoming_stmt)
                for link in inc_rows.scalars().all():
                    edge_key = f"{link.source_id}-{link.target_id}"
                    if edge_key not in visited_edges:
                        visited_edges.add(edge_key)
                        edges_list.append({
                            "id": str(link.id),
                            "source": str(link.source_id),
                            "target": str(link.target_id),
                            "link_type": link.link_type,
                            "label": link.label,
                            "strength": link.strength,
                            "confidence": link.confidence,
                            "is_auto_generated": link.is_auto_generated,
                        })

                    src_id_str = str(link.source_id)
                    if link.source_id not in visited_nodes:
                        visited_nodes.add(link.source_id)
                        src_node = await db.get(MemoryNode, link.source_id)
                        if src_node and src_node.type != "archived":
                            nodes_dict[src_id_str] = {
                                "id": src_id_str,
                                "title": src_node.title,
                                "type": src_node.type,
                                "tags": src_node.tags or [],
                                "links_count": src_node.links_count,
                                "is_orphan": src_node.is_orphan,
                                "para_category": src_node.para_category,
                                "created_at": src_node.created_at.isoformat() if src_node.created_at else None,
                                "summary": (src_node.layers or {}).get("l1_summary", ""),
                                "depth": current_depth + 1,
                            }
                            queue.append((link.source_id, current_depth + 1))

            return {
                "center_node_id": node_id,
                "nodes": list(nodes_dict.values()),
                "edges": edges_list,
                "metadata": {
                    "depth": depth,
                    "total_nodes": len(nodes_dict),
                    "total_edges": len(edges_list),
                    "center_title": central.title,
                },
            }

        if db_session:
            return await _query(db_session)

        async for db in get_db_session():
            return await _query(db)

    # ── Clusters ─────────────────────────────────────────────────────────────

    async def get_clusters(
        self,
        user_id: str,
        db_session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Identify topic clusters in the user's knowledge web.

        Uses tag-based clustering and link density analysis to group
        related nodes into topic clusters.

        Args:
            user_id: The user's UUID.
            db_session: Optional existing DB session.

        Returns:
            List of cluster dicts with name, node_count, and nodes.
        """
        user_uuid = uuid.UUID(user_id)

        async def _query(db: AsyncSession) -> list[dict[str, Any]]:
            # Get all non-archived nodes with their tags
            nodes_stmt = select(MemoryNode).where(
                and_(
                    MemoryNode.user_id == user_uuid,
                    MemoryNode.type != "archived",
                )
            )
            rows = await db.execute(nodes_stmt)
            all_nodes = rows.scalars().all()

            # Cluster by PARA category
            para_clusters: dict[str, list[dict[str, Any]]] = {}
            for node in all_nodes:
                cat = node.para_category or "uncategorized"
                if cat not in para_clusters:
                    para_clusters[cat] = []
                para_clusters[cat].append({
                    "id": str(node.id),
                    "title": node.title,
                    "tags": node.tags or [],
                })

            # Cluster by shared top-level tag
            tag_clusters: dict[str, list[dict[str, Any]]] = {}
            for node in all_nodes:
                for tag in (node.tags or []):
                    # Get top-level tag (e.g. #work/client → work)
                    top_tag = tag.split("/")[0].lstrip("#")
                    if not top_tag:
                        continue
                    if top_tag not in tag_clusters:
                        tag_clusters[top_tag] = []
                    tag_clusters[top_tag].append({
                        "id": str(node.id),
                        "title": node.title,
                    })

            # Build cluster response
            clusters = []

            for cat, nodes_list in para_clusters.items():
                if len(nodes_list) >= 2:
                    link_count = 0
                    nids = {n["id"] for n in nodes_list}
                    # Count internal links
                    for nid in nids:
                        node = next((n for n in all_nodes if str(n.id) == nid), None)
                        if node:
                            for link in (node.outgoing_links or []):
                                if str(link.target_id) in nids:
                                    link_count += 1

                    clusters.append({
                        "name": cat.capitalize(),
                        "type": "para",
                        "node_count": len(nodes_list),
                        "internal_links": link_count,
                    })

            for tag, nodes_list in tag_clusters.items():
                if len(nodes_list) >= 3:  # Only significant clusters
                    clusters.append({
                        "name": f"#{tag}",
                        "type": "tag",
                        "node_count": len(nodes_list),
                    })

            # Sort by size descending
            clusters.sort(key=lambda c: -c["node_count"])

            return clusters[:20]  # Top 20 clusters

        if db_session:
            return await _query(db_session)

        async for db in get_db_session():
            return await _query(db)

    # ── Orphans ──────────────────────────────────────────────────────────────

    async def get_orphans(
        self,
        user_id: str,
        db_session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Get nodes with <2 links, flagged for attention.

        These are "orphan" nodes that need linking to be fully integrated
        into the knowledge web.

        Args:
            user_id: The user's UUID.
            db_session: Optional existing DB session.

        Returns:
            List of orphan node dicts.
        """
        user_uuid = uuid.UUID(user_id)

        async def _query(db: AsyncSession) -> list[dict[str, Any]]:
            stmt = (
                select(MemoryNode)
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                        MemoryNode.links_count < 2,
                    )
                )
                .order_by(MemoryNode.created_at.desc())
                .limit(100)
            )
            rows = await db.execute(stmt)
            nodes = rows.scalars().all()

            return [
                {
                    "id": str(n.id),
                    "title": n.title,
                    "type": n.type,
                    "tags": n.tags or [],
                    "links_count": n.links_count,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                    "summary": (n.layers or {}).get("l1_summary", ""),
                }
                for n in nodes
            ]

        if db_session:
            return await _query(db_session)

        async for db in get_db_session():
            return await _query(db)

    # ── Brain Growth ─────────────────────────────────────────────────────────

    async def get_brain_growth(
        self,
        user_id: str,
        period: str = "week",
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Get brain growth metrics over time.

        Args:
            user_id: The user's UUID.
            period: Time period ('day', 'week', 'month').
            db_session: Optional existing DB session.

        Returns:
            Dict with growth metrics for the period.
        """
        user_uuid = uuid.UUID(user_id)
        now = datetime.now(timezone.utc)

        if period == "day":
            delta = timedelta(days=1)
            interval_label = "daily"
        elif period == "month":
            delta = timedelta(days=30)
            interval_label = "monthly"
        else:  # week
            delta = timedelta(days=7)
            interval_label = "weekly"

        start = now - delta

        async def _query(db: AsyncSession) -> dict[str, Any]:
            # New nodes in period
            nodes_result = await db.execute(
                select(func.count(MemoryNode.id)).where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                        MemoryNode.created_at >= start,
                    )
                )
            )
            new_nodes = nodes_result.scalar() or 0

            # New links
            links_result = await db.execute(
                select(func.count(MemoryLink.id)).where(
                    and_(
                        MemoryLink.user_id == user_uuid,
                        MemoryLink.created_at >= start,
                    )
                )
            )
            new_links = links_result.scalar() or 0

            # Total nodes
            total_result = await db.execute(
                select(func.count(MemoryNode.id)).where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                    )
                )
            )
            total_nodes = total_result.scalar() or 0

            # Growth rate
            growth_rate = 0.0
            if total_nodes > 0:
                growth_rate = round(new_nodes / total_nodes * 100, 2)

            # Daily breakdown
            breakpoints = []
            for i in range(7):
                day_start = now - timedelta(days=i + 1)
                day_end = now - timedelta(days=i)
                day_result = await db.execute(
                    select(func.count(MemoryNode.id)).where(
                        and_(
                            MemoryNode.user_id == user_uuid,
                            MemoryNode.type != "archived",
                            MemoryNode.created_at >= day_start,
                            MemoryNode.created_at < day_end,
                        )
                    )
                )
                count = day_result.scalar() or 0
                breakpoints.append({
                    "date": day_start.date().isoformat(),
                    "new_nodes": count,
                })

            breakpoints.reverse()

            return {
                "period": interval_label,
                "new_nodes": new_nodes,
                "new_links": new_links,
                "total_nodes": total_nodes,
                "growth_rate_percent": growth_rate,
                "daily_breakdown": breakpoints,
            }

        if db_session:
            return await _query(db_session)

        async for db in get_db_session():
            return await _query(db)

    # ── Obsidian Vault Export ────────────────────────────────────────────────

    async def export_obsidian_vault(
        self,
        user_id: str,
        output_dir: str | None = None,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Export the user's [[Second Brain]] as an [[Obsidian]] vault.

        Creates a folder structure following the PARA method with:
        - YAML frontmatter for metadata
        - [[wikilinks]] preserved between nodes
        - #tags maintained
        - Obsidian theme config for the "Night Web" look
        - Daily notes in their own folder

        Args:
            user_id: The user's UUID.
            output_dir: Optional output directory path. Defaults to a temp dir.
            db_session: Optional existing DB session.

        Returns:
            Dict with export path and stats.
        """
        user_uuid = uuid.UUID(user_id)
        export_root = Path(output_dir or f"/tmp/anansi-export-{user_id[:8]}")
        export_root.mkdir(parents=True, exist_ok=True)

        async def _export(db: AsyncSession) -> dict[str, Any]:
            user = await db.get(User, user_uuid)
            user_name = user.display_name if user else "User"

            # Get all nodes
            nodes_stmt = (
                select(MemoryNode)
                .where(
                    and_(
                        MemoryNode.user_id == user_uuid,
                        MemoryNode.type != "archived",
                    )
                )
                .options(selectinload(MemoryNode.outgoing_links))
            )
            rows = await db.execute(nodes_stmt)
            all_nodes = rows.scalars().all()

            # Build a lookup of node ID → title for wikilinks
            node_titles: dict[str, str] = {}
            for n in all_nodes:
                node_titles[str(n.id)] = n.title

            # Build a lookup of wikilink path → content for backlinks
            wiki_paths: dict[str, MemoryNode] = {}
            for n in all_nodes:
                wiki_paths[n.title] = n

            # Create folder structure
            folders = {
                "00 - Daily Notes": [],
                "10 - Projects": [],
                "20 - Areas": [],
                "30 - Resources": [],
                "40 - Archives": [],
                "50 - People": [],
                "60 - Agents": [],
                "90 - Tags": [],
            }

            # Categorize nodes
            para_map: dict[str, str] = {
                "projects": "10 - Projects",
                "areas": "20 - Areas",
                "resources": "30 - Resources",
                "archives": "40 - Archives",
            }

            for folder in folders:
                (export_root / folder).mkdir(parents=True, exist_ok=True)

            # Write nodes as markdown files
            files_created = 0
            for node in all_nodes:
                folder = para_map.get(node.para_category or "", "30 - Resources")

                # Safe filename
                safe_title = "".join(
                    c if c.isalnum() or c in " -_" else "_"
                    for c in node.title
                ).strip() or "untitled"
                filepath = export_root / folder / f"{safe_title}.md"

                # Convert [[wikilinks]] — replace internal references
                content_with_links = node.content
                for nid, title in node_titles.items():
                    content_with_links = content_with_links.replace(
                        f"[[{nid}]]", f"[[{title}]]"
                    )

                # Build YAML frontmatter
                layers = node.layers or {}
                frontmatter_lines = [
                    "---",
                    f"id: {node.id}",
                    f"title: \"{node.title}\"",
                    f"type: {node.type}",
                    f"created: {node.created_at.isoformat() if node.created_at else ''}",
                    f"modified: {node.updated_at.isoformat() if node.updated_at else ''}",
                    f"source: {node.source}",
                    f"confidence: {node.confidence}",
                    f"para_category: {node.para_category or ''}",
                    f"links_count: {node.links_count}",
                    "tags:",
                ]
                for tag in (node.tags or []):
                    frontmatter_lines.append(f"  - {tag}")
                if layers.get("l1_summary"):
                    frontmatter_lines.append(f"summary: \"{layers['l1_summary']}\"")
                frontmatter_lines.append("---")
                frontmatter_lines.append("")

                # Build full markdown
                md_lines = frontmatter_lines
                md_lines.append(f"# {node.title}")
                md_lines.append("")
                md_lines.append(content_with_links)
                md_lines.append("")

                # Add links section
                if node.outgoing_links:
                    md_lines.append("## Links")
                    md_lines.append("")
                    for link in node.outgoing_links:
                        link_title = node_titles.get(str(link.target_id), str(link.target_id))
                        md_lines.append(f"- [[{link_title}]] — {link.link_type}")
                    md_lines.append("")

                # Add layers section if any
                if layers.get("l1_summary") or layers.get("l2_highlights") or layers.get("l4_compressed"):
                    md_lines.append("## Progressive Summarization")
                    md_lines.append("")
                    if layers.get("l1_summary"):
                        md_lines.append(f"**L1 Summary:** {layers['l1_summary']}")
                        md_lines.append("")
                    if layers.get("l2_highlights"):
                        md_lines.append("**L2 Highlights:**")
                        for h in layers["l2_highlights"]:
                            md_lines.append(f"- **{h}**")
                        md_lines.append("")
                    if layers.get("l4_compressed"):
                        md_lines.append(f"**L4 Compressed:** {layers['l4_compressed']}")
                        md_lines.append("")

                filepath.write_text("\n".join(md_lines), encoding="utf-8")
                files_created += 1

            # Write daily notes
            daily_stmt = (
                select(DailyNote)
                .where(DailyNote.user_id == user_uuid)
                .order_by(DailyNote.note_date.desc())
            )
            daily_rows = await db.execute(daily_stmt)
            daily_notes = daily_rows.scalars().all()

            for note in daily_notes:
                date_str = note.note_date.isoformat() if note.note_date else "unknown"
                filepath = export_root / "00 - Daily Notes" / f"{date_str}.md"

                md_lines = [
                    "---",
                    f"id: {note.id}",
                    f"date: {date_str}",
                    f"finalized: {str(note.is_finalized).lower()}",
                    "---",
                    "",
                    f"# Daily Note — {date_str}",
                    "",
                ]

                if note.metrics:
                    md_lines.append("## Metrics")
                    md_lines.append("")
                    for key, value in note.metrics.items():
                        md_lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
                    md_lines.append("")

                if note.highlights:
                    md_lines.append("## Highlights")
                    md_lines.append("")
                    for h in note.highlights:
                        md_lines.append(f"- {h}")
                    md_lines.append("")

                if note.ai_reflection:
                    md_lines.append("## AI Reflection")
                    md_lines.append("")
                    md_lines.append(note.ai_reflection)
                    md_lines.append("")

                filepath.write_text("\n".join(md_lines), encoding="utf-8")
                files_created += 1

            # Write tag index pages
            tag_index: dict[str, list[str]] = {}
            for node in all_nodes:
                for tag in (node.tags or []):
                    clean_tag = tag.lstrip("#").replace("/", "_")
                    if clean_tag not in tag_index:
                        tag_index[clean_tag] = []
                    tag_index[clean_tag].append(node.title)

            for tag, titles in tag_index.items():
                filepath = export_root / "90 - Tags" / f"tag_{tag}.md"
                md_lines = [
                    f"# #{tag}",
                    "",
                    f"Nodes tagged with #{tag}:",
                    "",
                ]
                for t in titles:
                    md_lines.append(f"- [[{t}]]")
                filepath.write_text("\n".join(md_lines), encoding="utf-8")
                files_created += 1

            # Write Obsidian theme configuration
            obsidian_dir = export_root / ".obsidian"
            obsidian_dir.mkdir(exist_ok=True)

            # Theme config
            theme_config = {
                "theme": "obsidian",
                "cssTheme": "Anansi Night Web",
                "baseFontSize": 15,
                "accentColor": "#D97706",
                "showFrontmatter": False,
                "showInlineTitle": True,
                "spellcheck": True,
                "vimMode": False,
            }
            import json
            (obsidian_dir / "appearance.json").write_text(
                json.dumps(theme_config, indent=2)
            )

            # Community theme snippet
            css_content = """/* Anansi Night Web — Obsidian Theme */
/* Auto-generated from your Anansi [[Second Brain]] */

body {
  --background-primary: #0C0A09;
  --background-secondary: #1C1917;
  --background-modifier-border: #44403C;
  --text-normal: #FAFAF9;
  --text-muted: #A8A29E;
  --text-accent: #D97706;
  --text-accent-hover: #F59E0B;
  --interactive-accent: #D97706;
  --interactive-accent-hover: #F59E0B;
  --link-color: #D97706;
  --link-color-hover: #F59E0B;
  --tag-color: #D97706;
  --tag-background: rgba(217, 119, 6, 0.1);
  --graph-node: #D6D3D1;
  --graph-node-focused: #D97706;
  --graph-node-tag: #8B5CF6;
  --graph-node-attachment: #14B8A6;
  --graph-line: #44403C;
  --graph-line-highlight: #D97706;
}
"""
            (obsidian_dir / "obsidian.css").write_text(css_content)

            # Core plugin settings
            core_plugins = {
                "alwaysUpdateLinks": True,
                "newFileLocation": "current",
                "newLinkFormat": "shortest",
                "useMarkdownLinks": False,
                "showUnsupportedFiles": False,
                "attachmentFolderPath": "./attachments",
                "spellcheck": True,
            }
            (obsidian_dir / "core-plugins.json").write_text(
                json.dumps(core_plugins, indent=2)
            )

            logger.info(
                "Obsidian vault exported",
                user_id=user_id,
                path=str(export_root),
                files=files_created,
            )

            return {
                "export_path": str(export_root),
                "files_created": files_created,
                "nodes_exported": len(all_nodes),
                "daily_notes_exported": len(daily_notes),
                "tags_exported": len(tag_index),
                "format": "obsidian_vault",
            }

        if db_session:
            return await _export(db_session)

        async for db in get_db_session():
            return await _export(db)


__all__ = ["GraphService"]
