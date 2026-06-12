"""
Agent API Endpoints — REST API for agent CRUD, execution, testing, and publishing.

From spec section 8.2:
- GET/POST /api/v1/agents — List/create agents
- GET/PATCH/DELETE /api/v1/agents/:id — CRUD
- POST /api/v1/agents/:id/run — Execute agent
- POST /api/v1/agents/:id/test — Test with sample data
- POST /api/v1/agents/:id/duplicate — Duplicate agent
- GET /api/v1/agents/:id/versions — Version history
- POST /api/v1/agents/:id/publish — Publish
- POST /api/v1/agents/:id/share — Share with team
- POST /api/v1/agents/:id/triggers/register — Register triggers
- POST /api/v1/agents/:id/triggers/unregister — Unregister triggers
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from structlog import get_logger

from app.core.dependencies import CurrentUser, get_current_user, rate_limit
from app.core.exceptions import ValidationError
from app.services.agent import AgentService
from app.services.execution import execution_engine
from app.services.trigger import trigger_service

logger = get_logger(__name__)

router = APIRouter()
agent_service = AgentService()


# ─── Pydantic Schemas (inline for simplicity) ──────────────────────────────────


def _validate_uuid(value: str, field_name: str = "id") -> None:
    """Validate a UUID string."""
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise ValidationError(
            message=f"Invalid {field_name}: {value}",
            details={"field": field_name, "value": value},
        ) from exc


# ─── List / Create ─────────────────────────────────────────────────────────────


@router.get("")
async def list_agents(
    status: str | None = Query(None, description="Filter by status: draft, active, paused, archived"),
    search: str | None = Query(None, description="Search by name or description"),
    category: str | None = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all agents for the current user."""
    return await agent_service.list_agents(
        user_id=current_user.id,
        status=status,
        search=search,
        category=category,
        page=page,
        per_page=per_page,
    )


@router.post("", status_code=201)
async def create_agent(
    body: dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new agent."""
    name = body.get("name", "").strip()
    if not name:
        raise ValidationError(message="Agent name is required")

    return await agent_service.create_agent(
        user_id=current_user.id,
        name=name,
        description=body.get("description"),
        definition=body.get("definition"),
    )


# ─── Get / Update / Delete ────────────────────────────────────────────────────


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get an agent by ID."""
    _validate_uuid(agent_id, "agent_id")
    return await agent_service.get_agent(agent_id)


@router.patch("/{agent_id}")
async def update_agent(
    body: dict[str, Any],
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Update an agent's name, description, definition, or status."""
    _validate_uuid(agent_id, "agent_id")
    return await agent_service.update_agent(agent_id, body)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    """Soft-delete (archive) an agent."""
    _validate_uuid(agent_id, "agent_id")
    await agent_service.delete_agent(agent_id)


# ─── Execute ────────────────────────────────────────────────────────────────────


@router.post("/{agent_id}/run")
async def run_agent(
    body: dict[str, Any] | None = None,
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute an agent with optional input data."""
    _validate_uuid(agent_id, "agent_id")
    input_data = body if body else {}

    return await execution_engine.run_agent(
        agent_id=agent_id,
        trigger_type="manual",
        input_data=input_data,
        user_id=current_user.id,
    )


@router.post("/{agent_id}/test")
async def test_agent(
    body: dict[str, Any] | None = None,
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Test an agent with sample data (dry run — no side effects)."""
    _validate_uuid(agent_id, "agent_id")
    input_data = body if body else {}

    return await execution_engine.test_agent(
        agent_id=agent_id,
        input_data=input_data,
        user_id=current_user.id,
    )


@router.post("/{agent_id}/run/async")
async def run_agent_async(
    body: dict[str, Any] | None = None,
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Queue an agent for background execution via Celery."""
    _validate_uuid(agent_id, "agent_id")
    input_data = body if body else {}

    return await execution_engine.execute_agent_async(
        agent_id=agent_id,
        input_data=input_data,
        user_id=current_user.id,
    )


# ─── Versions ──────────────────────────────────────────────────────────────────


@router.get("/{agent_id}/versions")
async def get_agent_versions(
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get version history for an agent."""
    _validate_uuid(agent_id, "agent_id")
    return await agent_service.get_versions(agent_id)


# ─── Duplicate ────────────────────────────────────────────────────────────────


@router.post("/{agent_id}/duplicate")
async def duplicate_agent(
    body: dict[str, Any] | None = None,
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Duplicate an agent."""
    _validate_uuid(agent_id, "agent_id")
    new_name = body.get("name") if body else None
    return await agent_service.duplicate_agent(agent_id, new_name=new_name)


# ─── Publish ──────────────────────────────────────────────────────────────────


@router.post("/{agent_id}/publish")
async def publish_agent(
    body: dict[str, Any] | None = None,
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Publish an agent to the marketplace."""
    _validate_uuid(agent_id, "agent_id")
    data = body or {}
    return await agent_service.publish_agent(
        agent_id=agent_id,
        price_cents=data.get("price_cents"),
        marketplace_title=data.get("title"),
        marketplace_description=data.get("description"),
        category=data.get("category"),
        tags=data.get("tags"),
    )


# ─── Share ────────────────────────────────────────────────────────────────────


@router.post("/{agent_id}/share")
async def share_agent(
    body: dict[str, Any],
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Share an agent with a team."""
    _validate_uuid(agent_id, "agent_id")
    team_id = body.get("team_id", "")
    permission = body.get("permission", "view")

    if not team_id:
        raise ValidationError(message="team_id is required")

    return await agent_service.share_agent(
        agent_id=agent_id,
        team_id=team_id,
        permission=permission,
    )


# ─── Validate ─────────────────────────────────────────────────────────────────


@router.post("/validate")
async def validate_agent_definition(
    body: dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate an agent definition without saving."""
    definition = body.get("definition", {})
    return agent_service.validate_agent(definition)


# ─── Triggers ─────────────────────────────────────────────────────────────────


@router.post("/{agent_id}/triggers/register")
async def register_agent_triggers(
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Register all triggers for an agent (activates it)."""
    _validate_uuid(agent_id, "agent_id")
    return await trigger_service.register_agent_triggers(agent_id)


@router.post("/{agent_id}/triggers/unregister")
async def unregister_agent_triggers(
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Unregister all triggers for an agent (deactivates it)."""
    _validate_uuid(agent_id, "agent_id")
    return await trigger_service.unregister_agent_triggers(agent_id)


@router.get("/{agent_id}/triggers")
async def list_agent_triggers(
    agent_id: str = Path(..., description="Agent UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all active triggers for an agent."""
    _validate_uuid(agent_id, "agent_id")
    return await trigger_service.list_active_triggers(agent_id)


# ─── Runs ────────────────────────────────────────────────────────────────────


@router.get("/{agent_id}/runs/{run_id}")
async def get_run_log(
    agent_id: str = Path(..., description="Agent UUID"),
    run_id: str = Path(..., description="Run UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the full execution log for an agent run."""
    _validate_uuid(agent_id, "agent_id")
    _validate_uuid(run_id, "run_id")
    return await execution_engine.get_run_log(run_id)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: str = Path(..., description="Run UUID"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Cancel a running agent execution."""
    _validate_uuid(run_id, "run_id")
    return await execution_engine.cancel_run(run_id)


# ─── Block Registry ──────────────────────────────────────────────────────────


@router.get("/blocks")
async def list_blocks(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all available block types for the agent builder."""
    from app.services.blocks import block_registry
    return block_registry.list_all_dicts()


@router.get("/blocks/category/{category}")
async def list_blocks_by_category(
    category: str = Path(..., description="Block category"),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List block types in a specific category."""
    from app.services.blocks import block_registry
    return [b.to_dict() for b in block_registry.get_by_category(category)]


# ─── Memory Impact ────────────────────────────────────────────────────────────


@router.post("/memory-impact")
async def calculate_memory_impact(
    body: dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Estimate memory impact of an agent definition."""
    definition = body.get("definition", {})
    return execution_engine.calculate_memory_impact(definition)


__all__ = ["router"]
