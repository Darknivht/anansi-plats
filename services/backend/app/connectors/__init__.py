"""
Anansi Connectors — Service integration adapters.

Each connector is a subclass of BaseConnector that implements the
authentication, data access, and health-check logic for a specific
external service (Gmail, Slack, Notion, etc.).

Connectors are registered via CONNECTOR_REGISTRY for discovery by
the IntegrationService.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.connectors.base import BaseConnector

# Registry: connector_key -> connector class
CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {}


def register_connector(cls: type[BaseConnector]) -> type[BaseConnector]:
    """Decorator to register a connector class by its key."""
    key = getattr(cls, "key", None)
    if not key:
        raise ValueError(f"Connector {cls.__name__} must define a 'key' class attribute")
    CONNECTOR_REGISTRY[key] = cls
    return cls


def get_connector(key: str) -> type[BaseConnector]:
    """Get a connector class by its key.

    Raises:
        KeyError: If the connector key is not registered.
    """
    if key not in CONNECTOR_REGISTRY:
        raise KeyError(f"Unknown connector: {key}. Available: {list(CONNECTOR_REGISTRY)}")
    return CONNECTOR_REGISTRY[key]


def list_connectors() -> dict[str, type[BaseConnector]]:
    """Return a copy of the registry."""
    return dict(CONNECTOR_REGISTRY)


# ── Import all built-in connectors so they register themselves ──
from app.connectors.gmail import GmailConnector  # noqa: E402, F401
from app.connectors.google_calendar import GoogleCalendarConnector  # noqa: E402, F401
from app.connectors.google_drive import GoogleDriveConnector  # noqa: E402, F401
from app.connectors.slack import SlackConnector  # noqa: E402, F401
from app.connectors.notion import NotionConnector  # noqa: E402, F401
from app.connectors.github import GitHubConnector  # noqa: E402, F401
from app.connectors.linear import LinearConnector  # noqa: E402, F401
from app.connectors.stripe import StripeConnector  # noqa: E402, F401
from app.connectors.paystack import PaystackConnector  # noqa: E402, F401
from app.connectors.google_keep import GoogleKeepConnector  # noqa: E402, F401
from app.connectors.twitter import TwitterConnector  # noqa: E402, F401
from app.connectors.outlook import OutlookConnector  # noqa: E402, F401
# WhatsApp & Telegram connectors — placeholder imports for registration
from app.connectors.whatsapp import WhatsAppConnector  # noqa: E402, F401
from app.connectors.telegram import TelegramConnector  # noqa: E402, F401
# Discord
from app.connectors.discord import DiscordConnector  # noqa: E402, F401

__all__ = [
    "CONNECTOR_REGISTRY",
    "register_connector",
    "get_connector",
    "list_connectors",
]
