"""
Anansi Brain API — [[Second Brain]] RESTful endpoints.

Implements all endpoints from spec section 8.2 [[Second Brain]] Endpoints:
- Memory Nodes CRUD ([[Atomic Notes]])
- Bidirectional Links ([[wikilinks]])
- Graph queries
- Progressive Summarization
- Daily Notes
- Spaced Repetition Review
- Tags management
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Path, Query, Body
from sqlalchemy import and_, or_, select

from app.core.config import settings
from app.core.dependencies import (
    CurrentUser,
    get_current_user,
    require_plan,
    rate_limit,
)

from app.services.brain import MemoryService
from app.services.linking import LinkingService
from app.services.summarization import SummarizationService
from app.services.dailynote import DailyNoteService
from app.services.review import ReviewService
from app.services.graph import GraphService

# ─── Router ──────────────────────────────────────────────────────────────────────

router = APIRouter(
    tags=["brain"],
    dependencies=[Depends(rate_limit(key="brain", max_requests=200, window=60))],
)


# ─── Service instances (lazy-initialised) ────────────────────────────────────────

def get_memory_service() -> MemoryService:
    return MemoryService()


def get_linking_service() -> LinkingService:
    return LinkingService()


def get_summarization_service() -> SummarizationService:
    return SummarizationService()


def get_daily_note_service() -> DailyNoteService:
    return DailyNoteService()


def get_review_service() -> ReviewService:
    return ReviewService()


def get_graph_service() -> GraphService:
    return GraphService()


# ═══════════════════════════════════════════════════════════════════════════════════
# MEMORY NODES ([[Atomic Notes]])
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/nodes", summary="List all memory nodes")
async def list_nodes(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    type: Optional[str] = Query(None, alias="node_type", description="Filter by node type"),
    search: Optional[str] = Query(None, description="Full-text search query"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    svc: MemoryService = Depends(get_memory_service),
):
    """List memory nodes with optional filtering and search.

    Returns paginated nodes. Supports full-text search, tag and type filtering.
    """
    tags = [f"#{tag}"] if tag else None
    types = [type] if type else None

    nodes = await svc.search_nodes(
        user_id=current_user.id,
        query=search or "",
        tags=tags,
        types=types,
        limit=limit,
        offset=offset,
    )
    return {"nodes": nodes, "total": len(nodes), "limit": limit, "offset": offset}


@router.post("/nodes", summary="Create a new memory node")
async def create_node(
    body: dict[str, Any] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: MemoryService = Depends(get_memory_service),
):
    """Create a new [[Atomic Note]] in the user's Second Brain.

    Required fields: title, content
    Optional: type, tags, source, para_category, confidence
    """
    node = await svc.create_node(
        user_id=current_user.id,
        type=body.get("type", "fact"),
        title=body.get("title", ""),
        content=body.get("content", ""),
        tags=body.get("tags", []),
        source=body.get("source", "explicit"),
        para_category=body.get("para_category"),
        confidence=body.get("confidence", 0.7),
    )
    return {"node": node}


@router.get("/nodes/{id}", summary="Get a specific memory node")
async def get_node(
    id: str = Path(..., description="Node UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: MemoryService = Depends(get_memory_service),
):
    """Get a single memory node with full content, links, layers, and reviews."""
    node = await svc.get_node(node_id=id)
    return {"node": node}


@router.patch("/nodes/{id}", summary="Update a memory node")
async def update_node(
    id: str = Path(..., description="Node UUID"),
    body: dict[str, Any] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: MemoryService = Depends(get_memory_service),
):
    """Update a memory node's fields. Content changes trigger re-embedding."""
    node = await svc.update_node(node_id=id, data=body)
    return {"node": node}


@router.delete("/nodes/{id}", summary="Delete a memory node")
async def delete_node(
    id: str = Path(..., description="Node UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: MemoryService = Depends(get_memory_service),
):
    """Soft-delete a memory node and remove all its links."""
    await svc.delete_node(node_id=id)
    return {"deleted": True, "id": id}


# ═══════════════════════════════════════════════════════════════════════════════════
# BIDIRECTIONAL LINKS ([[wikilinks]])
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/links", summary="List links")
async def list_links(
    source_id: Optional[str] = Query(None, description="Filter by source node"),
    target_id: Optional[str] = Query(None, description="Filter by target node"),
    link_type: Optional[str] = Query(None, description="Filter by link type"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: LinkingService = Depends(get_linking_service),
):
    """List bidirectional links with optional filtering."""
    # Delegate to linking service's get_links_for_node if source_id is given
    if source_id:
        links = await svc.get_links_for_node(node_id=source_id)
        return {"links": links, "total": len(links)}

    # Otherwise return an empty links list (full listing would need dedicated query)
    return {"links": [], "total": 0}


@router.post("/links", summary="Create a link")
async def create_link(
    body: dict[str, Any] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: LinkingService = Depends(get_linking_service),
):
    """Create a [[bidirectional link]] between two memory nodes.

    Required: source_id, target_id
    Optional: link_type, label, context, confidence, strength
    """
    link = await svc.create_link(
        source_id=body["source_id"],
        target_id=body["target_id"],
        link_type=body.get("link_type", "related_to"),
        label=body.get("label"),
        context=body.get("context"),
        confidence=body.get("confidence", 0.7),
        strength=body.get("strength", 0.5),
        is_auto_generated=body.get("is_auto_generated", False),
    )
    return {"link": link}


@router.delete("/links/{id}", summary="Delete a link")
async def delete_link(
    id: str = Path(..., description="Link UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: LinkingService = Depends(get_linking_service),
):
    """Remove a bidirectional link between two nodes."""
    await svc.remove_link(link_id=id)
    return {"deleted": True, "id": id}


@router.get("/nodes/{id}/links", summary="Get all links for a specific node")
async def get_node_links(
    id: str = Path(..., description="Node UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: LinkingService = Depends(get_linking_service),
):
    """Get all links (incoming + outgoing) for a node with context."""
    links = await svc.get_links_for_node(node_id=id)
    return {"links": links, "total": len(links)}


# ═══════════════════════════════════════════════════════════════════════════════════
# GRAPH
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/graph", summary="Get full graph data")
async def get_full_graph(
    current_user: CurrentUser = Depends(get_current_user),
    svc: GraphService = Depends(get_graph_service),
):
    """Get all nodes and edges for graph visualization."""
    graph = await svc.get_full_graph(user_id=current_user.id)
    return graph


@router.get("/graph/local/{id}", summary="Get local subgraph around a node")
async def get_local_graph(
    id: str = Path(..., description="Center node UUID"),
    depth: int = Query(2, ge=1, le=3, description="Traversal depth"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GraphService = Depends(get_graph_service),
):
    """Get the subgraph around a node (focus view) to specified depth."""
    graph = await svc.get_local_graph(node_id=id, depth=depth)
    return graph


@router.post("/graph/search", summary="Full-text + semantic search")
async def graph_search(
    body: dict[str, Any] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: MemoryService = Depends(get_memory_service),
):
    """Combined full-text and semantic search across all nodes.

    Body:
    - query: search string
    - tags: optional tag filter
    - types: optional node type filter
    - limit: max results
    """
    nodes = await svc.search_nodes(
        user_id=current_user.id,
        query=body.get("query", ""),
        tags=body.get("tags"),
        types=body.get("types"),
        limit=body.get("limit", 50),
    )
    return {"nodes": nodes, "total": len(nodes)}


@router.post("/graph/query", summary="Cypher query (admin)")
async def graph_cypher_query(
    body: dict[str, Any] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    _=Depends(require_plan("pro")),
):
    """Execute a Cypher query against the Neo4j graph. Pro plan only."""
    from app.core.events import get_neo4j

    neo4j_driver = get_neo4j()
    query = body.get("query", "")
    params = body.get("params", {})

    async with neo4j_driver.session(database=settings.neo4j.database) as session:
        result = await session.run(query, params)
        records = await result.data()

    return {"records": records, "record_count": len(records)}


# ═══════════════════════════════════════════════════════════════════════════════════
# PROGRESSIVE SUMMARIZATION
# ═══════════════════════════════════════════════════════════════════════════════════


@router.post("/summarize", summary="Request AI summarization")
async def request_summarization(
    body: dict[str, Any] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: SummarizationService = Depends(get_summarization_service),
    _=Depends(require_plan("pro")),
):
    """Request AI summarization of nodes.

    Body:
    - node_ids: list of node UUIDs to synthesize (cross-node)
    - Or single node_id for summarization
    """
    node_ids = body.get("node_ids", [])
    if not node_ids:
        return {"error": "node_ids required"}

    if len(node_ids) == 1:
        result = await svc.summarize_node(node_id=node_ids[0])
    else:
        result = await svc.summarize_cross_nodes(node_ids=node_ids)

    return {"result": result}


@router.get("/nodes/{id}/layers", summary="Get summarization layers")
async def get_node_layers(
    id: str = Path(..., description="Node UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: SummarizationService = Depends(get_summarization_service),
):
    """Get all four [[Progressive Summarization]] layers for a node."""
    layers = await svc.get_node_layers(node_id=id)
    return layers


@router.post("/nodes/{id}/compress", summary="Add compression layer")
async def compress_node(
    id: str = Path(..., description="Node UUID"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: SummarizationService = Depends(get_summarization_service),
    _=Depends(require_plan("pro")),
):
    """Generate a Layer 4 compressed summary for a node (Pro plan)."""
    result = await svc.compress_node(node_id=id)
    return {"result": result}


# ═══════════════════════════════════════════════════════════════════════════════════
# DAILY NOTES
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/daily", summary="Get today's daily note")
async def get_today_note(
    current_user: CurrentUser = Depends(get_current_user),
    svc: DailyNoteService = Depends(get_daily_note_service),
):
    """Get today's [[Daily Note]]. Creates an empty one if it doesn't exist."""
    note = await svc.get_or_create_today(user_id=current_user.id)
    return {"note": note}


@router.get("/daily/{date}", summary="Get daily note for a specific date")
async def get_note_for_date(
    date: str = Path(..., description="Date in YYYY-MM-DD format"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: DailyNoteService = Depends(get_daily_note_service),
):
    """Get the [[Daily Note]] for a specific date."""
    from datetime import date as date_type
    note_date = date_type.fromisoformat(date)
    note = await svc.get_or_create(user_id=current_user.id, note_date=note_date)
    return {"note": note}


@router.post("/daily/generate", summary="Force regenerate daily note")
async def regenerate_daily_note(
    body: dict[str, Any] = Body(default={}),
    current_user: CurrentUser = Depends(get_current_user),
    svc: DailyNoteService = Depends(get_daily_note_service),
):
    """Force AI regeneration of today's (or specified date's) [[Daily Note]]."""
    note_date = body.get("date")
    note = await svc.generate_daily_note(
        user_id=current_user.id,
        note_date=note_date,
    )
    return {"note": note}


# ═══════════════════════════════════════════════════════════════════════════════════
# SPACED REPETITION
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/review", summary="Get review queue")
async def get_review_queue(
    limit: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ReviewService = Depends(get_review_service),
):
    """Get nodes due for [[Spaced Repetition]] review today."""
    queue = await svc.get_queue(user_id=current_user.id, limit=limit)
    return {"queue": queue, "total": len(queue), "limit": limit}


@router.post("/review/{id}", summary="Record a review result")
async def submit_review(
    id: str = Path(..., description="Node UUID being reviewed"),
    body: dict[str, Any] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ReviewService = Depends(get_review_service),
):
    """Record a [[Spaced Repetition]] review.

    Body:
    - rating: 'easy', 'medium', 'hard', or 'forgot'
    - response_time_ms: optional response time
    """
    result = await svc.submit_review(
        user_id=current_user.id,
        node_id=id,
        rating=body.get("rating", "medium"),
        response_time_ms=body.get("response_time_ms"),
    )
    return {"result": result}


@router.get("/review/stats", summary="Get review statistics")
async def get_review_stats(
    current_user: CurrentUser = Depends(get_current_user),
    svc: ReviewService = Depends(get_review_service),
):
    """Get [[Spaced Repetition]] review statistics."""
    stats = await svc.get_review_stats(user_id=current_user.id)
    return {"stats": stats}


# ═══════════════════════════════════════════════════════════════════════════════════
# TAGS
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/tags", summary="List all tags with counts")
async def list_tags(
    current_user: CurrentUser = Depends(get_current_user),
    svc: MemoryService = Depends(get_memory_service),
):
    """List all tags used in the user's brain with node counts."""
    stats = await svc.get_brain_stats(user_id=current_user.id)
    return {"tags": stats.get("tags", [])}


@router.post("/tags", summary="Create/rename a tag")
async def create_tag(
    body: dict[str, Any] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create or rename a tag across all nodes.

    Body:
    - old_tag: existing tag to rename (optional, creates new if omitted)
    - new_tag: the tag name
    """
    old_tag = body.get("old_tag")
    new_tag = body.get("new_tag", "")

    if not new_tag:
        return {"error": "new_tag is required"}

    if not new_tag.startswith("#"):
        new_tag = f"#{new_tag}"

    if old_tag:
        from sqlalchemy import update
        from app.core.events import get_db_session
        from app.models.brain import MemoryNode

        async for db in get_db_session():
            # Find all nodes with the old tag and replace it
            stmt = select(MemoryNode).where(
                and_(
                    MemoryNode.user_id == uuid.UUID(current_user.id),
                    MemoryNode.tags.any(old_tag),
                )
            )
            rows = await db.execute(stmt)
            nodes = rows.scalars().all()

            for node in nodes:
                new_tags = [new_tag if t == old_tag else t for t in (node.tags or [])]
                node.tags = new_tags
            await db.commit()

    return {"tag": new_tag, "renamed_from": old_tag}


@router.delete("/tags/{tag}", summary="Delete a tag")
async def delete_tag(
    tag: str = Path(..., description="Tag to delete (with or without #)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete a tag from all nodes in the user's brain."""
    if not tag.startswith("#"):
        tag = f"#{tag}"

    from sqlalchemy import update
    from app.core.events import get_db_session
    from app.models.brain import MemoryNode

    async for db in get_db_session():
        stmt = select(MemoryNode).where(
            and_(
                MemoryNode.user_id == uuid.UUID(current_user.id),
                MemoryNode.tags.any(tag),
            )
        )
        rows = await db.execute(stmt)
        nodes = rows.scalars().all()

        for node in nodes:
            new_tags = [t for t in (node.tags or []) if t != tag]
            node.tags = new_tags
        await db.commit()

    return {"deleted": True, "tag": tag}


# ═══════════════════════════════════════════════════════════════════════════════════
# BRAIN HEALTH & EXPORT
# ═══════════════════════════════════════════════════════════════════════════════════


@router.get("/stats", summary="Get brain statistics")
async def get_brain_stats(
    current_user: CurrentUser = Depends(get_current_user),
    svc: MemoryService = Depends(get_memory_service),
):
    """Get comprehensive brain health statistics."""
    stats = await svc.get_brain_stats(user_id=current_user.id)
    return {"stats": stats}


@router.post("/export", summary="Export brain as Obsidian vault")
async def export_brain(
    current_user: CurrentUser = Depends(get_current_user),
    svc: GraphService = Depends(get_graph_service),
    _=Depends(require_plan("pro")),
):
    """Export the entire brain as an [[Obsidian]]-compatible vault.

    Pro plan feature.
    """
    result = await svc.export_obsidian_vault(user_id=current_user.id)
    return result


@router.get("/clusters", summary="Get brain clusters")
async def get_clusters(
    current_user: CurrentUser = Depends(get_current_user),
    svc: GraphService = Depends(get_graph_service),
):
    """Identify topic clusters in the user's knowledge web."""
    clusters = await svc.get_clusters(user_id=current_user.id)
    return {"clusters": clusters}


@router.get("/orphans", summary="Get orphan nodes")
async def get_orphans(
    current_user: CurrentUser = Depends(get_current_user),
    svc: GraphService = Depends(get_graph_service),
):
    """Get nodes with <2 links that need attention."""
    orphans = await svc.get_orphans(user_id=current_user.id)
    return {"orphans": orphans, "total": len(orphans)}


@router.get("/growth", summary="Get brain growth metrics")
async def get_brain_growth(
    period: str = Query("week", regex="^(day|week|month)$"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GraphService = Depends(get_graph_service),
):
    """Get brain growth metrics over the specified period."""
    growth = await svc.get_brain_growth(
        user_id=current_user.id, period=period,
    )
    return {"growth": growth}


__all__ = ["router"]
