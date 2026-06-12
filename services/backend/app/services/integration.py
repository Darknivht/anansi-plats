"""
Integration Service — Central business logic for all service integrations.

Manages the lifecycle of user connections to third-party services:
- Listing available connectors
- Initiating OAuth flows and handling callbacks
- API key connections
- Disconnecting and revoking tokens
- Testing and refreshing connections
- Reporting connection health

Uses the CONNECTOR_REGISTRY to resolve connector implementations.
Stores encrypted tokens via the Integration model.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.connectors import CONNECTOR_REGISTRY, get_connector, list_connectors
from app.connectors.base import BaseConnector
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.db.session import async_session_factory
from app.models.integration import Connector, Integration
from app.websocket.manager import manager, WSServerEvent

logger = get_logger(__name__)


# ─── Token encryption ───────────────────────────────────────────────────────

# Uses a Fernet key derived from a secret in settings. In production,
# this should come from a dedicated encryption key or KMS.
_ENCRYPTION_KEY: bytes | None = None


def _get_encryption_key() -> bytes:
    """Get or derive the Fernet encryption key for token storage."""
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is None:
        # Derive a 32-byte key from the JWT private key or a dedicated secret
        secret = settings.jwt.private_key or "anansi-dev-encryption-key-change-in-production"
        import hashlib
        key_bytes = hashlib.sha256(secret.encode()).digest()
        _ENCRYPTION_KEY = key_bytes
    return _ENCRYPTION_KEY


def _encrypt_token(data: dict[str, Any]) -> str:
    """Encrypt token data for storage.

    Args:
        data: Token dict to encrypt.

    Returns:
        Encrypted string (Fernet token).
    """
    key = _get_encryption_key()
    cipher = Fernet(key)
    raw = json.dumps(data).encode()
    return cipher.encrypt(raw).decode()


def _decrypt_token(encrypted: str) -> dict[str, Any]:
    """Decrypt stored token data.

    Args:
        encrypted: Fernet-encrypted token string.

    Returns:
        Decrypted token dict.
    """
    key = _get_encryption_key()
    cipher = Fernet(key)
    raw = cipher.decrypt(encrypted.encode())
    return json.loads(raw.decode())


# ─── Integration Service ────────────────────────────────────────────────────


class IntegrationService:
    """Business logic for managing user integrations with third-party services."""

    # ── Connector Discovery ─────────────────────────────────────────────────

    async def list_available(self, user_id: str) -> list[dict[str, Any]]:
        """List all available connector types with the user's connection status.

        Args:
            user_id: The user to check connections for.

        Returns:
            List of connector info dicts with connection status for this user.
        """
        connectors = list_connectors()
        user_connections = await self._get_user_integrations(user_id)
        connected_keys = {ic.connector_type for ic in user_connections}

        results = []
        for key, cls in connectors.items():
            integration = next(
                (ic for ic in user_connections if ic.connector_type == key),
                None,
            )
            results.append({
                "key": cls.key,
                "name": cls.name,
                "description": cls.description,
                "icon_url": cls.icon_url,
                "category": cls.category,
                "auth_type": cls.auth_type,
                "is_connected": integration is not None,
                "status": integration.status if integration else "disconnected",
                "integration_id": str(integration.id) if integration else None,
                "last_sync_at": integration.last_sync_at.isoformat() if integration and integration.last_sync_at else None,
                "error_message": integration.error_message if integration else None,
            })

        return results

    async def get_connector_detail(self, connector_key: str) -> dict[str, Any]:
        """Get detailed info about a specific connector type.

        Args:
            connector_key: Connector key (e.g. 'gmail', 'slack').

        Returns:
            Connector detail dict.

        Raises:
            NotFoundError: If the connector key is unknown.
        """
        try:
            cls = get_connector(connector_key)
        except KeyError:
            raise NotFoundError(
                message=f"Unknown connector: {connector_key}",
                resource_type="connector",
                resource_id=connector_key,
            )

        return {
            "key": cls.key,
            "name": cls.name,
            "description": cls.description,
            "icon_url": cls.icon_url,
            "category": cls.category,
            "auth_type": cls.auth_type,
            "scopes": cls.scopes,
            "is_builtin": True,
        }

    async def get_integration_detail(
        self,
        integration_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Get detailed info about a user's integration, including connector info.

        Args:
            integration_id: UUID of the integration record.
            user_id: User ID for ownership verification.

        Returns:
            Integration detail dict.
        """
        integration = await self._get_integration(integration_id, user_id)
        try:
            cls = get_connector(integration.connector_type)
        except KeyError:
            cls = None

        result = {
            "id": str(integration.id),
            "connector_type": integration.connector_type,
            "display_name": integration.display_name or cls.name if cls else integration.connector_type,
            "status": integration.status,
            "scopes": integration.scopes,
            "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
            "created_at": integration.created_at.isoformat(),
            "error_message": integration.error_message,
            "rate_limit_remaining": integration.rate_limit_remaining,
        }

        if cls:
            result["connector"] = {
                "key": cls.key,
                "name": cls.name,
                "description": cls.description,
                "icon_url": cls.icon_url,
                "category": cls.category,
                "auth_type": cls.auth_type,
                "scopes": cls.scopes,
            }

        return result

    # ── OAuth Flow ──────────────────────────────────────────────────────────

    async def initiate_oauth(
        self,
        connector_key: str,
        user_id: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Start an OAuth flow for a connector.

        Creates a pending integration record and returns the authorization URL.

        Args:
            connector_key: The connector type key.
            user_id: The user initiating the flow.
            redirect_uri: Where the OAuth provider will redirect after auth.

        Returns:
            Dict with 'auth_url' and 'state' parameters.

        Raises:
            ValidationError: If connector doesn't support OAuth.
            NotFoundError: If connector key is unknown.
        """
        try:
            cls = get_connector(connector_key)
        except KeyError:
            raise NotFoundError(
                message=f"Unknown connector: {connector_key}",
                resource_type="connector",
            )

        if cls.auth_type != "oauth2":
            raise ValidationError(
                message=f"Connector '{connector_key}' uses {cls.auth_type} auth, not OAuth2",
            )

        # Check for existing integration
        existing = await self._find_integration(user_id, connector_key)
        if existing:
            raise ConflictError(
                message=f"You already have a {connector_key} connection. Disconnect first.",
            )

        # Create a pending integration to track the OAuth state
        state = str(uuid.uuid4())
        integration = Integration(
            user_id=uuid.UUID(user_id),
            connector_type=connector_key,
            status="pending",
            metadata_={"oauth_state": state, "redirect_uri": redirect_uri},
        )

        async with async_session_factory() as session:
            session.add(integration)
            await session.commit()
            integration_id = str(integration.id)

        # Build the auth URL
        instance = cls()
        auth_url = instance.get_auth_url(redirect_uri=redirect_uri, state=state)

        return {
            "auth_url": auth_url,
            "state": state,
            "integration_id": integration_id,
        }

    async def handle_oauth_callback(
        self,
        connector_key: str,
        code: str,
        state: str,
    ) -> dict[str, Any]:
        """Complete an OAuth flow by exchanging the code for tokens.

        Args:
            connector_key: The connector type key.
            code: The authorization code from the callback.
            state: The state parameter (for verification and finding the integration).

        Returns:
            Dict with connection status.

        Raises:
            NotFoundError: If no pending integration matches the state.
            ValidationError: If there's an issue with the token exchange.
        """
        # Find the pending integration by state
        async with async_session_factory() as session:
            result = await session.execute(
                select(Integration).where(
                    Integration.metadata_["oauth_state"].as_string() == state,
                    Integration.connector_type == connector_key,
                    Integration.status == "pending",
                )
            )
            integration = result.scalar_one_or_none()

        if not integration:
            raise NotFoundError(
                message="OAuth session not found. Please start the connection again.",
                resource_type="integration",
            )

        try:
            cls = get_connector(connector_key)
        except KeyError:
            raise NotFoundError(resource_type="connector", resource_id=connector_key)

        # Exchange code for tokens
        instance = cls()
        redirect_uri = integration.metadata_.get("redirect_uri", "")
        token_data = await instance.exchange_code(code, redirect_uri)

        # Extract scopes from token response
        scopes = token_data.get("scope", " ".join(cls.scopes)).split()

        # Encrypt and store
        encrypted = _encrypt_token(token_data)

        async with async_session_factory() as session:
            # Get a fresh session for the update
            result = await session.execute(
                select(Integration).where(Integration.id == integration.id)
            )
            integration = result.scalar_one_or_none()
            if not integration:
                raise NotFoundError(resource_type="integration")

            integration.status = "active"
            integration.auth_data = {"encrypted_token": encrypted, "token_type": token_data.get("token_type", "Bearer")}
            integration.scopes = scopes
            integration.error_message = None
            await session.commit()

        # Send real-time status update via WebSocket
        await self._notify_status_change(
            user_id=str(integration.user_id),
            connector_key=connector_key,
            status="active",
        )

        logger.info(
            "OAuth callback completed",
            connector=connector_key,
            user_id=str(integration.user_id),
        )

        return {
            "status": "connected",
            "integration_id": str(integration.id),
            "scopes": scopes,
        }

    # ── API Key Auth ────────────────────────────────────────────────────────

    async def connect_api_key(
        self,
        connector_key: str,
        user_id: str,
        api_key: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Connect using an API key.

        Args:
            connector_key: The connector type key.
            user_id: The user's ID.
            api_key: The API key to store.
            config: Additional configuration (e.g. phone_number_id for WhatsApp).

        Returns:
            Dict with connection status.

        Raises:
            ValidationError: If the API key fails validation.
        """
        try:
            cls = get_connector(connector_key)
        except KeyError:
            raise NotFoundError(resource_type="connector", resource_id=connector_key)

        if cls.auth_type == "oauth2":
            raise ValidationError(
                message=f"Connector '{connector_key}' requires OAuth2, not an API key",
            )

        # Validate the API key
        instance = cls()
        try:
            validation = await instance.validate_api_key(api_key)
            if not validation.get("valid", False):
                raise ValidationError(
                    message=f"Invalid API key for {connector_key}: {validation.get('details', {}).get('error', 'Unknown error')}",
                )
        except NotImplementedError:
            # Connector doesn't have custom validation; store and test later
            logger.info(f"API key validation not implemented for {connector_key}, storing directly")
        except httpx.HTTPError as exc:
            raise ValidationError(
                message=f"Could not validate API key: {str(exc)}",
            )

        # Check for existing connection
        existing = await self._find_integration(user_id, connector_key)
        if existing:
            raise ConflictError(
                message=f"You already have a {connector_key} connection. Disconnect first.",
            )

        # Store credentials
        auth_data = {
            "api_key": api_key,
            **(config or {}),
        }
        encrypted = _encrypt_token(auth_data)

        async with async_session_factory() as session:
            integration = Integration(
                user_id=uuid.UUID(user_id),
                connector_type=connector_key,
                display_name=config.get("display_name") if config else None,
                status="active",
                auth_data={"encrypted_token": encrypted, "token_type": "apikey"},
                scopes=cls.scopes if hasattr(cls, "scopes") else [],
                metadata_=config or {},
            )
            session.add(integration)
            await session.commit()
            integration_id = str(integration.id)

        await self._notify_status_change(
            user_id=user_id,
            connector_key=connector_key,
            status="active",
        )

        logger.info(
            "API key connected",
            connector=connector_key,
            user_id=user_id,
        )

        return {
            "status": "connected",
            "integration_id": integration_id,
        }

    # ── Disconnect ──────────────────────────────────────────────────────────

    async def disconnect(self, integration_id: str, user_id: str) -> dict[str, Any]:
        """Remove a connection, revoking tokens if possible.

        Args:
            integration_id: The integration record UUID.
            user_id: The owning user's ID.

        Returns:
            Status dict.
        """
        integration = await self._get_integration(integration_id, user_id)

        # Try to revoke the token
        try:
            cls = get_connector(integration.connector_type)
            if integration.auth_data and "encrypted_token" in integration.auth_data:
                token_data = _decrypt_token(integration.auth_data["encrypted_token"])
                instance = cls()
                await instance.revoke_token(token_data)
                logger.info("Token revoked", connector=integration.connector_type)
        except Exception as exc:
            logger.warning(
                "Token revocation failed (continuing with disconnect)",
                connector=integration.connector_type,
                error=str(exc),
            )

        # Delete the integration record
        async with async_session_factory() as session:
            await session.execute(
                delete(Integration).where(Integration.id == integration.id)
            )
            await session.commit()

        await self._notify_status_change(
            user_id=str(integration.user_id),
            connector_key=integration.connector_type,
            status="disconnected",
        )

        logger.info(
            "Integration disconnected",
            connector=integration.connector_type,
            user_id=user_id,
        )

        return {"status": "disconnected"}

    # ── Test Connection ─────────────────────────────────────────────────────

    async def test_connection(self, integration_id: str, user_id: str) -> dict[str, Any]:
        """Test a connection by calling the service's test endpoint.

        Args:
            integration_id: Integration UUID.
            user_id: User for ownership verification.

        Returns:
            Dict with 'success' bool and optional 'error'.
        """
        integration = await self._get_integration(integration_id, user_id)

        try:
            cls = get_connector(integration.connector_type)
        except KeyError:
            raise NotFoundError(resource_type="connector", resource_id=integration.connector_type)

        # Get decrypted tokens
        token_data = self._get_decrypted_auth(integration)

        # If OAuth, check for token expiry and auto-refresh
        if cls.auth_type == "oauth2":
            instance = cls()
            instance.set_auth_data(token_data)
            if instance.token_is_expired(token_data):
                try:
                    new_tokens = await instance.refresh_token(token_data)
                    # Update stored tokens
                    encrypted = _encrypt_token(new_tokens)
                    async with async_session_factory() as session:
                        result = await session.execute(
                            select(Integration).where(Integration.id == integration.id)
                        )
                        intg = result.scalar_one_or_none()
                        if intg:
                            intg.auth_data = {"encrypted_token": encrypted, "token_type": "Bearer"}
                            await session.commit()
                    token_data = new_tokens
                    instance.set_auth_data(token_data)
                    logger.info("Token auto-refreshed during test", connector=cls.key)
                except Exception as exc:
                    await self._mark_error(integration, f"Token refresh failed: {exc}")
                    return {"success": False, "error": f"Token expired and refresh failed: {exc}"}

        # Run the test
        instance = cls()
        instance.set_auth_data(token_data)
        try:
            result = await instance.test_connection()
            if result:
                await self._mark_healthy(integration)
                logger.info("Connection test passed", connector=cls.key, user_id=user_id)
                return {"success": True}
            else:
                await self._mark_error(integration, "Connection test returned unhealthy")
                return {"success": False, "error": "Connection test failed"}
        except Exception as exc:
            await self._mark_error(integration, str(exc))
            logger.warning("Connection test failed", connector=cls.key, error=str(exc))
            return {"success": False, "error": str(exc)}

    # ── Get Status ──────────────────────────────────────────────────────────

    async def get_status(self, user_id: str) -> dict[str, Any]:
        """Return the health status of all user connections.

        Args:
            user_id: The user to check.

        Returns:
            Dict with summary and per-connection statuses.
        """
        integrations = await self._get_user_integrations(user_id)
        connectors = list_connectors()

        connections = []
        connected_count = 0
        error_count = 0

        for intg in integrations:
            cls_info = connectors.get(intg.connector_type)
            status = intg.status
            if status == "active":
                connected_count += 1
            elif status == "error":
                error_count += 1

            connections.append({
                "integration_id": str(intg.id),
                "connector_type": intg.connector_type,
                "name": cls_info.name if cls_info else intg.connector_type,
                "icon_url": cls_info.icon_url if cls_info else "",
                "category": cls_info.category if cls_info else "",
                "status": status,
                "error_message": intg.error_message,
                "last_sync_at": intg.last_sync_at.isoformat() if intg.last_sync_at else None,
            })

        available_count = len(connectors) - connected_count

        return {
            "summary": {
                "total": len(connectors),
                "connected": connected_count,
                "error": error_count,
                "available": available_count,
            },
            "connections": connections,
        }

    # ── Refresh Token ──────────────────────────────────────────────────────

    async def refresh_token(
        self,
        integration_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Force refresh an OAuth token.

        Args:
            integration_id: Integration UUID.
            user_id: User for verification.

        Returns:
            Status dict.
        """
        integration = await self._get_integration(integration_id, user_id)

        try:
            cls = get_connector(integration.connector_type)
        except KeyError:
            raise NotFoundError(resource_type="connector", resource_id=integration.connector_type)

        if cls.auth_type != "oauth2":
            raise ValidationError(message=f"Connector '{cls.key}' does not use OAuth tokens")

        token_data = self._get_decrypted_auth(integration)
        instance = cls()
        instance.set_auth_data(token_data)

        try:
            new_tokens = await instance.refresh_token(token_data)
            encrypted = _encrypt_token(new_tokens)
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Integration).where(Integration.id == integration.id)
                )
                intg = result.scalar_one_or_none()
                if intg:
                    intg.auth_data = {"encrypted_token": encrypted, "token_type": "Bearer"}
                    await session.commit()

            logger.info("Token refreshed", connector=cls.key, user_id=user_id)
            return {"status": "refreshed"}
        except Exception as exc:
            logger.error("Token refresh failed", connector=cls.key, error=str(exc))
            raise ValidationError(message=f"Token refresh failed: {exc}")

    # ── Internal helpers ────────────────────────────────────────────────────

    @staticmethod
    def _get_decrypted_auth(integration: Integration) -> dict[str, Any]:
        """Decrypt stored auth data from an integration record.

        Args:
            integration: The Integration model instance.

        Returns:
            Decrypted token dict.
        """
        if not integration.auth_data or "encrypted_token" not in integration.auth_data:
            return {}
        return _decrypt_token(integration.auth_data["encrypted_token"])

    @staticmethod
    async def _get_user_integrations(user_id: str) -> list[Integration]:
        """Get all integration records for a user."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(Integration).where(Integration.user_id == uuid.UUID(user_id))
            )
            return list(result.scalars().all())

    @staticmethod
    async def _find_integration(user_id: str, connector_key: str) -> Integration | None:
        """Find a single integration by user and connector type."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(Integration).where(
                    Integration.user_id == uuid.UUID(user_id),
                    Integration.connector_type == connector_key,
                )
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def _get_integration(integration_id: str, user_id: str) -> Integration:
        """Get an integration by ID, verifying ownership.

        Raises:
            NotFoundError: If integration doesn't exist or doesn't belong to user.
        """
        async with async_session_factory() as session:
            result = await session.execute(
                select(Integration).where(Integration.id == uuid.UUID(integration_id))
            )
            integration = result.scalar_one_or_none()

        if not integration:
            raise NotFoundError(resource_type="integration", resource_id=integration_id)

        if str(integration.user_id) != user_id:
            raise NotFoundError(resource_type="integration", resource_id=integration_id)

        return integration

    @staticmethod
    async def _mark_healthy(integration: Integration) -> None:
        """Update integration status to active and clear error."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(Integration).where(Integration.id == integration.id)
            )
            intg = result.scalar_one_or_none()
            if intg:
                intg.status = "active"
                intg.error_message = None
                intg.last_sync_at = datetime.now(timezone.utc)
                await session.commit()

    @staticmethod
    async def _mark_error(integration: Integration, error_message: str) -> None:
        """Update integration status to error."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(Integration).where(Integration.id == integration.id)
            )
            intg = result.scalar_one_or_none()
            if intg:
                intg.status = "error"
                intg.error_message = error_message
                await session.commit()

        await manager.send_to_user(
            str(integration.user_id),
            WSServerEvent(
                type="integration.status",
                payload={
                    "connector_type": integration.connector_type,
                    "status": "error",
                    "error_message": error_message,
                },
            ),
        )

    @staticmethod
    async def _notify_status_change(
        user_id: str,
        connector_key: str,
        status: str,
    ) -> None:
        """Send a real-time WebSocket notification about status change."""
        await manager.send_to_user(
            user_id,
            WSServerEvent(
                type="integration.status",
                payload={
                    "connector_type": connector_key,
                    "status": status,
                },
            ),
        )


# ─── Seed built-in connectors into the database ───────────────────────────


async def seed_connectors() -> int:
    """Upsert all built-in connectors from the registry into the database.

    Should be called during app startup.

    Returns:
        Number of connectors seeded/updated.
    """
    conn_classes = list_connectors()
    count = 0

    async with async_session_factory() as session:
        for key, cls in conn_classes.items():
            # Check if connector already exists
            result = await session.execute(
                select(Connector).where(Connector.key == key)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.name = cls.name
                existing.description = cls.description
                existing.icon_url = cls.icon_url
                existing.category = cls.category
                existing.auth_type = cls.auth_type
                existing.scopes_available = list(cls.scopes)
            else:
                # Insert new
                connector = Connector(
                    key=key,
                    name=cls.name,
                    description=cls.description,
                    icon_url=cls.icon_url,
                    category=cls.category,
                    auth_type=cls.auth_type,
                    scopes_available=list(cls.scopes),
                    auth_url_template=cls.auth_url if hasattr(cls, "auth_url") else "",
                    token_url=cls.token_url if hasattr(cls, "token_url") else "",
                    is_builtin=True,
                    is_active=True,
                )
                session.add(connector)
            count += 1

        await session.commit()

    logger.info("Connectors seeded", count=count)
    return count


# ─── Helper to get the service instance ───────────────────────────────────


async def get_integration_service() -> IntegrationService:
    """Factory for FastAPI dependency injection."""
    return IntegrationService()
