"""
Anansi WebSocket Handler — Endpoint for real-time bidirectional communication.

Handles the /ws/v1 endpoint with JWT authentication, message routing,
heartbeat, and connection lifecycle managed by WebSocketManager.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from structlog import get_logger

from app.core.exceptions import AuthError
from app.core.security import verify_token
from app.websocket.manager import (
    WSClientEvent,
    WSServerEvent,
    manager,
)

logger = get_logger(__name__)

router = APIRouter()


# ─── Auth via Query Param ────────────────────────────────────────────────────────


async def _verify_ws_token(token: str) -> str:
    """Validate a JWT access token provided as a WebSocket query param.

    Args:
        token: The JWT string.

    Returns:
        The authenticated user ID.

    Raises:
        AuthError: If the token is invalid or expired.
    """
    try:
        payload = verify_token(token, expected_type="access")
    except ValueError as exc:
        raise AuthError(message=str(exc), reason="invalid_token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthError(message="Token missing subject", reason="invalid_token")

    return user_id


# ─── WebSocket Endpoint ──────────────────────────────────────────────────────────


@router.websocket("/v1")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token for authentication"),
) -> None:
    """WebSocket endpoint for real-time communication.

    Connection URL: ``wss://api.anansi.ai/ws/v1?token=<jwt>``

    Authentication is via a JWT access token in the query string.
    Once connected, the client can send and receive events.

    **Server → Client events:**
    - ``agent.running``, ``agent.completed``, ``agent.error``, ``agent.step``
    - ``ai.message_chunk``, ``ai.morning_briefing``
    - ``notification``
    - ``brain.node_created``, ``brain.node_updated``, ``brain.link_created``
    - ``brain.review_due``, ``brain.daily_note_ready``
    - ``ping`` (heartbeat)

    **Client → Server events:**
    - ``agent.run`` — Request agent execution
    - ``ai.send_message`` — Send message to AI
    - ``brain.create_node`` — Create memory node
    - ``brain.create_link`` — Create bidirectional link
    - ``pong`` — Heartbeat response

    **Protocol:**
    Messages are JSON with shape ``{"type": "...", "payload": {...}, "id": "..."}``.
    """
    user_id = ""
    conn_id = ""

    try:
        # Authenticate
        user_id = await _verify_ws_token(token)
    except AuthError as exc:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=exc.message)
        return

    # Accept the connection
    await websocket.accept()
    conn_id = await manager.connect(user_id, websocket)

    # Send welcome
    await websocket.send_text(
        WSServerEvent(
            type="connected",
            payload={
                "user_id": user_id,
                "connection_id": conn_id,
                "message": "Connected to Anansi WebSocket",
            },
        ).model_dump_json(),
    )

    logger.info("WebSocket session established", user_id=user_id, connection_id=conn_id)

    try:
        await _message_loop(websocket, user_id)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally", user_id=user_id, connection_id=conn_id)
    except Exception as exc:
        logger.exception(
            "WebSocket error",
            user_id=user_id,
            connection_id=conn_id,
            error=str(exc),
        )
    finally:
        await manager.disconnect(user_id, websocket)


# ─── Message Loop ────────────────────────────────────────────────────────────────


async def _message_loop(websocket: WebSocket, user_id: str) -> None:
    """Read and dispatch WebSocket messages until the client disconnects.

    Args:
        websocket: The active WebSocket connection.
        user_id: The authenticated user ID.
    """
    while True:
        raw = await websocket.receive_text()

        # Parse the message
        try:
            data = json.loads(raw)
            event = WSClientEvent(**data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Invalid WebSocket message", user_id=user_id, error=str(exc))
            await websocket.send_text(
                WSServerEvent(
                    type="error",
                    payload={"message": f"Invalid message format: {exc}"},
                ).model_dump_json(),
            )
            continue

        # Handle built-in events
        if event.type == "pong":
            await manager.handle_pong(user_id)
            continue

        if event.type == "ping":
            await websocket.send_text(
                WSServerEvent(
                    type="pong",
                    payload={"timestamp": __import__("time").time()},
                    id=event.id,
                ).model_dump_json(),
            )
            continue

        # Route to registered handlers
        response = await manager.handle_client_event(user_id, event)
        if response:
            await websocket.send_text(response.model_dump_json())


# ─── Register Default Handlers ───────────────────────────────────────────────────


@manager.on("ai.send_message")
async def handle_ai_send_message(user_id: str, payload: dict[str, Any]) -> None:
    """Handle a client request to send a message to the AI.

    Args:
        user_id: The authenticated user ID.
        payload: Event payload with 'conversation_id' and 'content'.
    """
    conversation_id = payload.get("conversation_id", "")
    content = payload.get("content", "")

    if not content:
        logger.warning("Empty AI message", user_id=user_id)
        return

    logger.info("AI message via WebSocket", user_id=user_id, conversation_id=conversation_id)

    # TODO: Route to AI service, stream response back via WebSocket
    # For now, echo back as a placeholder
    event = WSServerEvent(
        type="ai.message_chunk",
        payload={
            "conversation_id": conversation_id,
            "text": f"Echo: {content}",
        },
    )
    await manager.send_to_user(user_id, event)


@manager.on("agent.run")
async def handle_agent_run(user_id: str, payload: dict[str, Any]) -> None:
    """Handle a client request to execute an agent.

    Args:
        user_id: The authenticated user ID.
        payload: Event payload with 'agent_id' and optional 'input_data'.
    """
    agent_id = payload.get("agent_id", "")
    input_data = payload.get("input_data", {})

    if not agent_id:
        logger.warning("Missing agent_id in agent.run", user_id=user_id)
        return

    logger.info("Agent run via WebSocket", user_id=user_id, agent_id=agent_id)

    # Notify client that agent is starting
    await manager.send_to_user(
        user_id,
        manager.event_agent_running(agent_id=agent_id, agent_name="Unknown"),
    )

    # TODO: Invoke the Agent Engine
    # For now, send a simulated completion
    await manager.send_to_user(
        user_id,
        manager.event_agent_completed(
            agent_id=agent_id,
            agent_name="Unknown",
            result={"status": "completed", "message": "Agent execution simulated"},
        ),
    )


@manager.on("brain.create_node")
async def handle_brain_create_node(user_id: str, payload: dict[str, Any]) -> None:
    """Handle a client request to create a memory node.

    Args:
        user_id: The authenticated user ID.
        payload: Event payload with node data.
    """
    logger.info("Brain node creation via WebSocket", user_id=user_id)

    # TODO: Route to Brain/Memory Service
    # For now, echo back
    response_event = WSServerEvent(
        type="brain.node_created",
        payload={
            "id": f"mem_{user_id[:8]}",
            "title": payload.get("title", "Untitled"),
            "status": "created",
        },
    )
    await manager.send_to_user(user_id, response_event)


@manager.on("brain.create_link")
async def handle_brain_create_link(user_id: str, payload: dict[str, Any]) -> None:
    """Handle a client request to create a bidirectional link between nodes.

    Args:
        user_id: The authenticated user ID.
        payload: Event payload with 'source_id' and 'target_id'.
    """
    source_id = payload.get("source_id", "")
    target_id = payload.get("target_id", "")

    logger.info("Brain link creation via WebSocket", user_id=user_id)

    response_event = WSServerEvent(
        type="brain.link_created",
        payload={
            "source_id": source_id,
            "target_id": target_id,
            "status": "created",
        },
    )
    await manager.send_to_user(user_id, response_event)


__all__ = ["router"]
