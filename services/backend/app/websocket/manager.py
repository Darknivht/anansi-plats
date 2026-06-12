"""
Anansi WebSocket Manager — Connection tracking, broadcasting, and event routing.

Manages WebSocket connections keyed by user_id, supports broadcasting to
user channels, and handles heartbeat/ping keepalive.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Coroutine
from uuid import uuid4

from fastapi import WebSocket
from pydantic import BaseModel
from structlog import get_logger

logger = get_logger(__name__)


# ─── Event Types ─────────────────────────────────────────────────────────────────


class WSClientEvent(BaseModel):
    """Event sent from the client to the server."""
    type: str
    payload: dict[str, Any] = {}
    id: str = ""


class WSServerEvent(BaseModel):
    """Event sent from the server to the client."""
    type: str
    payload: dict[str, Any] = {}
    id: str = ""
    timestamp: float = 0.0


# ─── Connection Manager ──────────────────────────────────────────────────────────


class WebSocketManager:
    """Manages WebSocket connections grouped by user_id.

    Tracks user connections, supports broadcasting to users and specific
    channels, and handles keepalive with ping/pong.
    """

    def __init__(self) -> None:
        # user_id -> list of WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}
        # connection_id -> user_id (reverse lookup)
        self._reverse_map: dict[str, str] = {}
        # event handlers: event_type -> callable
        self._handlers: dict[str, Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]] = {}
        self._total_connections: int = 0

    # ── Connection Lifecycle ──────────────────────────────────────────────────────

    async def connect(self, user_id: str, websocket: WebSocket) -> str:
        """Register a new WebSocket connection for a user.

        Args:
            user_id: The authenticated user's ID.
            websocket: The WebSocket connection.

        Returns:
            A unique connection ID.
        """
        conn_id = str(uuid4())

        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        self._reverse_map[conn_id] = user_id
        self._total_connections += 1

        logger.info(
            "WebSocket connected",
            user_id=user_id,
            connection_id=conn_id,
            total_connections=self._total_connections,
        )

        return conn_id

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection for a user.

        Args:
            user_id: The user's ID.
            websocket: The connection to remove.
        """
        if user_id in self._connections:
            try:
                self._connections[user_id].remove(websocket)
            except ValueError:
                pass

            if not self._connections[user_id]:
                del self._connections[user_id]

        # Clean reverse map
        stale_ids = [
            cid for cid, uid in self._reverse_map.items()
            if uid == user_id and websocket not in self._connections.get(user_id, [])
        ]
        for cid in stale_ids:
            del self._reverse_map[cid]

        self._total_connections = max(0, self._total_connections - 1)

        logger.info(
            "WebSocket disconnected",
            user_id=user_id,
            total_connections=self._total_connections,
        )

    async def disconnect_all(self, user_id: str) -> int:
        """Close and remove all connections for a user.

        Args:
            user_id: The user's ID.

        Returns:
            Number of connections closed.
        """
        connections = self._connections.pop(user_id, [])
        for ws in connections:
            try:
                await ws.close(code=1000, reason="User disconnected")
            except Exception:
                pass

        # Clean reverse map
        stale_ids = [cid for cid, uid in self._reverse_map.items() if uid == user_id]
        for cid in stale_ids:
            del self._reverse_map[cid]

        count = len(connections)
        self._total_connections = max(0, self._total_connections - count)

        logger.info("All WebSocket connections closed", user_id=user_id, count=count)
        return count

    # ── Connection Info ───────────────────────────────────────────────────────────

    def is_connected(self, user_id: str) -> bool:
        """Check if a user has any active WebSocket connections."""
        return user_id in self._connections and bool(self._connections[user_id])

    def get_connection_count(self, user_id: str) -> int:
        """Get the number of active connections for a user."""
        return len(self._connections.get(user_id, []))

    @property
    def total_connections(self) -> int:
        """Total active WebSocket connections across all users."""
        return self._total_connections

    @property
    def connected_users(self) -> list[str]:
        """List of user IDs with active connections."""
        return list(self._connections.keys())

    # ── Sending Messages ──────────────────────────────────────────────────────────

    async def send_to_user(self, user_id: str, event: WSServerEvent) -> int:
        """Send an event to all connections of a specific user.

        Args:
            user_id: Target user ID.
            event: The server event to send.

        Returns:
            Number of recipients the message was sent to.
        """
        connections = self._connections.get(user_id, [])
        if not connections:
            return 0

        event.timestamp = time.time()
        data = event.model_dump_json()

        sent = 0
        for ws in connections:
            try:
                await ws.send_text(data)
                sent += 1
            except Exception as exc:
                logger.warning(
                    "Failed to send WebSocket message",
                    user_id=user_id,
                    error=str(exc),
                )

        return sent

    async def broadcast(
        self,
        event: WSServerEvent,
        user_ids: list[str] | None = None,
    ) -> int:
        """Broadcast an event to specific users or all connected users.

        Args:
            event: The server event to broadcast.
            user_ids: Optional list of target user IDs. If None, sends to all.

        Returns:
            Total number of recipients.
        """
        targets = user_ids or list(self._connections.keys())
        total_sent = 0

        for uid in targets:
            total_sent += await self.send_to_user(uid, event)

        return total_sent

    # ── Event Handler Registration ────────────────────────────────────────────────

    def on(self, event_type: str) -> Callable:
        """Decorator to register a handler for a client event type.

        Usage:
            @manager.on("ai.send_message")
            async def handle_message(user_id, payload):
                ...
        """
        def decorator(
            handler: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]],
        ) -> Callable:
            self._handlers[event_type] = handler
            logger.debug("WebSocket handler registered", event_type=event_type)
            return handler
        return decorator

    async def handle_client_event(
        self,
        user_id: str,
        event: WSClientEvent,
    ) -> WSServerEvent | None:
        """Route a client event to the appropriate handler.

        Args:
            user_id: The authenticated user's ID.
            event: The parsed client event.

        Returns:
            Optional response event to send back to the client.
        """
        handler = self._handlers.get(event.type)
        if handler:
            try:
                await handler(user_id, event.payload)
            except Exception as exc:
                logger.error("WebSocket handler error", event_type=event.type, error=str(exc))
                return WSServerEvent(
                    type="error",
                    payload={"message": f"Handler error: {exc}", "original_event": event.type},
                    id=event.id,
                )
        else:
            logger.warning("No handler for event type", event_type=event.type)
            return WSServerEvent(
                type="error",
                payload={"message": f"Unknown event type: {event.type}"},
                id=event.id,
            )

        return None

    # ── Heartbeat / Ping ──────────────────────────────────────────────────────────

    async def send_ping(self, user_id: str) -> bool:
        """Send a ping to the user's first connection.

        Args:
            user_id: The user to ping.

        Returns:
            True if at least one connection received the ping.
        """
        event = WSServerEvent(
            type="ping",
            payload={"timestamp": time.time()},
        )
        sent = await self.send_to_user(user_id, event)
        return sent > 0

    async def handle_pong(self, user_id: str) -> None:
        """Handle a pong response from a client."""
        logger.debug("Pong received", user_id=user_id)

    # ── Common Event Builders ─────────────────────────────────────────────────────

    @staticmethod
    def event_agent_running(agent_id: str, agent_name: str, **kwargs: Any) -> WSServerEvent:
        return WSServerEvent(
            type="agent.running",
            payload={"agent_id": agent_id, "agent_name": agent_name, **kwargs},
        )

    @staticmethod
    def event_agent_completed(agent_id: str, agent_name: str, result: dict[str, Any], **kwargs: Any) -> WSServerEvent:
        return WSServerEvent(
            type="agent.completed",
            payload={"agent_id": agent_id, "agent_name": agent_name, "result": result, **kwargs},
        )

    @staticmethod
    def event_agent_error(agent_id: str, agent_name: str, error: str, **kwargs: Any) -> WSServerEvent:
        return WSServerEvent(
            type="agent.error",
            payload={"agent_id": agent_id, "agent_name": agent_name, "error": error, **kwargs},
        )

    @staticmethod
    def event_agent_step(agent_id: str, step: dict[str, Any], **kwargs: Any) -> WSServerEvent:
        return WSServerEvent(
            type="agent.step",
            payload={"agent_id": agent_id, "step": step, **kwargs},
        )

    @staticmethod
    def event_ai_chunk(text: str, conversation_id: str, **kwargs: Any) -> WSServerEvent:
        return WSServerEvent(
            type="ai.message_chunk",
            payload={"text": text, "conversation_id": conversation_id, **kwargs},
        )

    @staticmethod
    def event_ai_briefing(data: dict[str, Any], **kwargs: Any) -> WSServerEvent:
        return WSServerEvent(
            type="ai.morning_briefing",
            payload={"data": data, **kwargs},
        )

    @staticmethod
    def event_notification(notification: dict[str, Any]) -> WSServerEvent:
        return WSServerEvent(
            type="notification",
            payload=notification,
        )

    @staticmethod
    def event_brain_node_created(node: dict[str, Any]) -> WSServerEvent:
        return WSServerEvent(
            type="brain.node_created",
            payload=node,
        )

    @staticmethod
    def event_brain_node_updated(node: dict[str, Any]) -> WSServerEvent:
        return WSServerEvent(
            type="brain.node_updated",
            payload=node,
        )

    @staticmethod
    def event_brain_link_created(link: dict[str, Any]) -> WSServerEvent:
        return WSServerEvent(
            type="brain.link_created",
            payload=link,
        )

    @staticmethod
    def event_brain_review_due(count: int, **kwargs: Any) -> WSServerEvent:
        return WSServerEvent(
            type="brain.review_due",
            payload={"count": count, **kwargs},
        )

    @staticmethod
    def event_brain_daily_note(note: dict[str, Any]) -> WSServerEvent:
        return WSServerEvent(
            type="brain.daily_note_ready",
            payload=note,
        )


# ─── Singleton ───────────────────────────────────────────────────────────────────

manager = WebSocketManager()

__all__ = [
    "manager",
    "WebSocketManager",
    "WSClientEvent",
    "WSServerEvent",
]
