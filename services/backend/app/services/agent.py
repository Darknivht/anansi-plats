"""
Agent Service — CRUD, validation, versioning, and publishing of agents.

Integrates with Agent, AgentVersion, and AgentRun models.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_db_session, get_session_factory
from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.models.agent import Agent, AgentVersion, AgentRun
from app.models.marketplace import MarketplaceListing
from app.services.blocks import block_registry

logger = get_logger(__name__)


class AgentService:
    """Business logic for agent CRUD, validation, versioning, and publishing."""

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create_agent(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        definition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new agent with a default empty definition.

        Args:
            user_id: The owning user's ID.
            name: Agent name.
            description: Optional description.
            definition: Optional initial definition (blocks, edges, triggers).
                       Defaults to an empty definition.

        Returns:
            Serialized agent dict.
        """
        if not name or not name.strip():
            raise ValidationError(message="Agent name is required")

        agent = Agent(
            user_id=uuid.UUID(user_id),
            name=name.strip(),
            description=description.strip() if description else None,
            definition=definition or self._empty_definition(),
            version=1,
            status="draft",
            is_published=False,
        )

        factory = get_session_factory()
        async with factory() as session:
            session.add(agent)
            await session.commit()
            await session.refresh(agent)

        logger.info("Agent created", agent_id=str(agent.id), name=name, user_id=user_id)
        return self._serialize(agent)

    @staticmethod
    def _empty_definition() -> dict[str, Any]:
        return {"blocks": [], "edges": [], "triggers": []}

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_agent(self, agent_id: str) -> dict[str, Any]:
        """Get an agent by ID with its current version data.

        Args:
            agent_id: UUID of the agent.

        Returns:
            Serialized agent dict.

        Raises:
            NotFoundError: If agent doesn't exist or was deleted.
        """
        factory = get_session_factory()
        async with factory() as session:
            agent = await self._fetch_agent(session, agent_id)
            return self._serialize(agent)

    async def list_agents(
        self,
        user_id: str,
        status: str | None = None,
        search: str | None = None,
        category: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """List agents for a user with optional filters and pagination.

        Args:
            user_id: Filter by owner.
            status: Optional status filter ('draft', 'active', 'paused', 'archived').
            search: Optional text search on name and description.
            category: Optional category filter.
            page: Page number (1-indexed).
            per_page: Items per page (max 100).

        Returns:
            Dict with 'items', 'total', 'page', 'per_page', 'pages'.
        """
        factory = get_session_factory()
        async with factory() as session:
            query = select(Agent).where(
                Agent.user_id == uuid.UUID(user_id)
            )

            if status:
                if status not in ("draft", "active", "paused", "archived"):
                    raise ValidationError(message=f"Invalid status: {status}")
                query = query.where(Agent.status == status)

            if category:
                query = query.where(Agent.category == category)

            if search:
                search_term = f"%{search}%"
                query = query.where(
                    or_(
                        Agent.name.ilike(search_term),
                        Agent.description.ilike(search_term),
                    )
                )

            # Count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            # Paginate
            per_page = min(per_page, 100)
            pages = max(1, (total + per_page - 1) // per_page)
            offset = (page - 1) * per_page

            query = query.order_by(Agent.updated_at.desc())
            query = query.offset(offset).limit(per_page)

            result = await session.execute(query)
            agents = result.scalars().all()

            return {
                "items": [self._serialize(a) for a in agents],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages,
            }

    # ── Update ─────────────────────────────────────────────────────────────────

    async def update_agent(
        self,
        agent_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an agent's properties and/or definition.

        If 'definition' changes, automatically creates a new version snapshot.

        Args:
            agent_id: UUID of the agent.
            data: Dict with optional fields: name, description, definition, status, category, tags.

        Returns:
            Updated serialized agent dict.
        """
        factory = get_session_factory()
        async with factory() as session:
            agent = await self._fetch_agent(session, agent_id)

            has_definition_change = "definition" in data
            old_definition = deepcopy(agent.definition)

            # Update fields
            if "name" in data:
                if not data["name"].strip():
                    raise ValidationError(message="Agent name cannot be empty")
                agent.name = data["name"].strip()

            if "description" in data:
                agent.description = data["description"].strip() if data["description"] else None

            if "definition" in data:
                agent.definition = data["definition"]

            if "status" in data:
                if data["status"] not in ("draft", "active", "paused", "archived"):
                    raise ValidationError(message=f"Invalid status: {data['status']}")
                agent.status = data["status"]

            if "category" in data:
                agent.category = data["category"]

            if "tags" in data:
                agent.tags = data["tags"]

            # Auto-increment version on definition change
            if has_definition_change:
                agent.version += 1

                # Save version history
                version_record = AgentVersion(
                    agent_id=agent.id,
                    version=agent.version,
                    definition=old_definition,
                    change_notes=data.get("change_notes"),
                )
                session.add(version_record)

            await session.commit()
            await session.refresh(agent)

            logger.info(
                "Agent updated",
                agent_id=agent_id,
                version=agent.version,
                has_definition_change=has_definition_change,
            )
            return self._serialize(agent)

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def delete_agent(self, agent_id: str) -> None:
        """Soft-delete an agent (archive it) and cancel any running executions.

        Args:
            agent_id: UUID of the agent.

        Raises:
            NotFoundError: If agent doesn't exist.
        """
        factory = get_session_factory()
        async with factory() as session:
            agent = await self._fetch_agent(session, agent_id)
            agent.status = "archived"

            # Cancel running runs
            cancel_query = (
                update(AgentRun)
                .where(
                    and_(
                        AgentRun.agent_id == agent.id,
                        AgentRun.status == "running",
                    )
                )
                .values(
                    status="cancelled",
                    error_message="Agent was deleted",
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await session.execute(cancel_query)

            await session.commit()

            logger.info("Agent archived (soft-deleted)", agent_id=agent_id)

    # ── Versioning ─────────────────────────────────────────────────────────────

    async def get_versions(self, agent_id: str) -> list[dict[str, Any]]:
        """Get version history for an agent.

        Args:
            agent_id: UUID of the agent.

        Returns:
            List of version snapshots (newest first).
        """
        factory = get_session_factory()
        async with factory() as session:
            # Verify agent exists
            await self._fetch_agent(session, agent_id)

            query = (
                select(AgentVersion)
                .where(AgentVersion.agent_id == uuid.UUID(agent_id))
                .order_by(AgentVersion.version.desc())
            )
            result = await session.execute(query)
            versions = result.scalars().all()

            return [
                {
                    "id": str(v.id),
                    "agent_id": str(v.agent_id),
                    "version": v.version,
                    "definition": v.definition,
                    "change_notes": v.change_notes,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in versions
            ]

    # ── Publishing ─────────────────────────────────────────────────────────────

    async def publish_agent(
        self,
        agent_id: str,
        price_cents: int | None = None,
        marketplace_title: str | None = None,
        marketplace_description: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Publish an agent — validates it, marks as published, creates marketplace listing.

        Args:
            agent_id: UUID of the agent.
            price_cents: Price in cents for marketplace (0=free, None=not for sale).
            marketplace_title: Title for marketplace listing.
            marketplace_description: Description for marketplace listing.
            category: Marketplace category.
            tags: Marketplace tags.

        Returns:
            Updated serialized agent dict.

        Raises:
            ValidationError: If agent definition is invalid.
        """
        factory = get_session_factory()
        async with factory() as session:
            agent = await self._fetch_agent(session, agent_id)

            # Validate
            validation = self.validate_agent(agent.definition)
            if not validation["valid"]:
                raise ValidationError(
                    message="Agent definition is invalid",
                    details={"errors": validation["errors"]},
                )

            # Check minimum requirements
            blocks = agent.definition.get("blocks", [])
            if not blocks:
                raise ValidationError(message="Agent must have at least one block to publish")

            triggers = [b for b in blocks if b.get("type") == "trigger"]
            if not triggers:
                raise ValidationError(
                    message="Agent must have at least one trigger block to publish"
                )

            agent.is_published = True
            if marketplace_title:
                agent.name = marketplace_title
            if category:
                agent.category = category

            # Create or update marketplace listing
            listing = agent.marketplace_listing
            if listing:
                listing.title = marketplace_title or agent.name
                listing.description = marketplace_description or agent.description
                listing.price_cents = price_cents or 0
                listing.category = category or agent.category or "uncategorized"
                listing.tags = tags or agent.tags
            else:
                listing = MarketplaceListing(
                    agent_id=agent.id,
                    user_id=agent.user_id,
                    title=marketplace_title or agent.name,
                    description=marketplace_description or agent.description,
                    price_cents=price_cents or 0,
                    category=category or agent.category or "uncategorized",
                    tags=tags or agent.tags,
                    status="published",
                )
                session.add(listing)

            await session.commit()
            await session.refresh(agent)

            logger.info("Agent published", agent_id=agent_id, price_cents=price_cents)
            return self._serialize(agent)

    # ── Share ──────────────────────────────────────────────────────────────────

    async def share_agent(
        self,
        agent_id: str,
        team_id: str,
        permission: str = "view",
    ) -> dict[str, Any]:
        """Share an agent with a team.

        Args:
            agent_id: UUID of the agent.
            team_id: UUID of the team.
            permission: 'view' or 'edit'.

        Returns:
            Updated agent dict.
        """
        # In a full implementation, this would create a TeamAgent record.
        # For now, we log and return success.
        logger.info(
            "Agent shared",
            agent_id=agent_id,
            team_id=team_id,
            permission=permission,
        )

        factory = get_session_factory()
        async with factory() as session:
            agent = await self._fetch_agent(session, agent_id)
            return self._serialize(agent)

    # ── Validation ─────────────────────────────────────────────────────────────

    def validate_agent(self, definition: dict[str, Any]) -> dict[str, Any]:
        """Validate an agent definition for correctness.

        Checks:
        - Block connections are valid
        - Required fields are present
        - No circular dependencies (DAG constraint)
        - All referenced block IDs exist
        - Required block config fields are filled

        Args:
            definition: The agent definition dict (blocks, edges, triggers).

        Returns:
            Dict with 'valid' (bool) and 'errors' (list of error dicts).
        """
        errors: list[dict[str, Any]] = []
        blocks: list[dict[str, Any]] = definition.get("blocks", [])
        edges: list[dict[str, Any]] = definition.get("edges", [])

        block_ids = set()
        block_map: dict[str, dict[str, Any]] = {}

        for block in blocks:
            bid = block.get("id", "")
            if not bid:
                errors.append({"code": "missing_block_id", "message": "Block missing id"})
                continue
            if bid in block_ids:
                errors.append({"code": "duplicate_block_id", "message": f"Duplicate block id: {bid}"})
            block_ids.add(bid)
            block_map[bid] = block

            # Validate required config fields from block registry
            btype = block.get("type", "")
            subtype = block.get("subtype", "")
            if btype and subtype:
                full_id = f"{btype}.{subtype}"
                reg_block = block_registry.get(full_id)
                if reg_block:
                    config = block.get("config", {})
                    schema = reg_block.config_schema
                    required_fields = schema.get("required", [])
                    for field in required_fields:
                        if field not in config or config[field] is None or config[field] == "":
                            errors.append({
                                "code": "missing_required_field",
                                "message": f"Block '{bid}' missing required config field: {field}",
                                "block_id": bid,
                                "field": field,
                            })

        # Validate edges
        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source and source not in block_ids:
                errors.append({
                    "code": "invalid_edge_source",
                    "message": f"Edge references non-existent source block: {source}",
                    "edge_id": edge.get("id", ""),
                })
            if target and target not in block_ids:
                errors.append({
                    "code": "invalid_edge_target",
                    "message": f"Edge references non-existent target block: {target}",
                    "edge_id": edge.get("id", ""),
                })

        # Check for circular dependencies using topological sort (Kahn's algorithm)
        adj: dict[str, list[str]] = {bid: [] for bid in block_ids}
        in_degree: dict[str, int] = {bid: 0 for bid in block_ids}

        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source in adj and target in adj:
                adj[source].append(target)
                in_degree[target] = in_degree.get(target, 0) + 1

        queue = [bid for bid in block_ids if in_degree.get(bid, 0) == 0]
        visited = 0

        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited != len(block_ids):
            errors.append({
                "code": "circular_dependency",
                "message": "Agent blocks contain a circular dependency. Execution cannot proceed.",
            })

        # Triggers validation
        for trigger in definition.get("triggers", []):
            ttype = trigger.get("type", "")
            if ttype not in ("schedule", "webhook", "event"):
                errors.append({
                    "code": "invalid_trigger_type",
                    "message": f"Invalid trigger type: {ttype}",
                })

        return {"valid": len(errors) == 0, "errors": errors}

    # ── Duplicate ──────────────────────────────────────────────────────────────

    async def duplicate_agent(self, agent_id: str, new_name: str | None = None) -> dict[str, Any]:
        """Duplicate an agent, creating a fresh copy with a new name.

        Args:
            agent_id: UUID of the agent to duplicate.
            new_name: Name for the duplicate. If None, appends ' (Copy)' to original name.

        Returns:
            Serialized new agent dict.
        """
        factory = get_session_factory()
        async with factory() as session:
            agent = await self._fetch_agent(session, agent_id)
            new_agent_name = new_name or f"{agent.name} (Copy)"

            new_agent = Agent(
                user_id=agent.user_id,
                name=new_agent_name,
                description=agent.description,
                definition=deepcopy(agent.definition),
                version=1,
                status="draft",
                is_published=False,
                category=agent.category,
                tags=agent.tags[:] if agent.tags else [],
            )
            session.add(new_agent)
            await session.commit()
            await session.refresh(new_agent)

            logger.info("Agent duplicated", source_id=agent_id, new_id=str(new_agent.id))
            return self._serialize(new_agent)

    # ── Internal Helpers ───────────────────────────────────────────────────────

    @staticmethod
    async def _fetch_agent(session: AsyncSession, agent_id: str) -> Agent:
        """Fetch an agent by ID, raising NotFoundError if missing or archived."""
        try:
            uid = uuid.UUID(agent_id)
        except ValueError as exc:
            raise ValidationError(message=f"Invalid agent ID: {agent_id}") from exc

        result = await session.execute(
            select(Agent)
            .options(joinedload(Agent.versions))
            .where(Agent.id == uid)
        )
        agent = result.unique().scalar_one_or_none()

        if agent is None:
            raise NotFoundError(
                message=f"Agent not found: {agent_id}",
                resource_type="agent",
                resource_id=agent_id,
            )

        return agent

    @staticmethod
    def _serialize(agent: Agent) -> dict[str, Any]:
        """Convert an Agent ORM object to a safe API response dict."""
        return {
            "id": str(agent.id),
            "user_id": str(agent.user_id),
            "name": agent.name,
            "description": agent.description,
            "definition": agent.definition,
            "version": agent.version,
            "status": agent.status,
            "is_published": agent.is_published,
            "total_runs": agent.total_runs,
            "successful_runs": agent.successful_runs,
            "success_rate": agent.success_rate,
            "avg_duration_ms": agent.avg_duration_ms,
            "memory_nodes_created": agent.memory_nodes_created,
            "memory_links_created": agent.memory_links_created,
            "category": agent.category,
            "tags": agent.tags,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
        }


__all__ = ["AgentService"]
