"""
Anansi Base Connector — Abstract base class for all service integrations.

All connectors inherit from BaseConnector and implement the required
abstract methods. Connectors define their own auth_type, scopes, and
data-access methods while sharing common OAuth / API-key infrastructure.

Lifecycle:
    instantiate(key) -> set_auth_data(token_dict) -> call methods -> test_connection()
"""

from __future__ import annotations

import abc
import hashlib
import hmac
import json
import time
from typing import Any, ClassVar

import httpx
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)


class BaseConnector(abc.ABC):
    """Abstract connector that every integration adapter must subclass.

    Class-level attributes (override in subclass):
        key          — Unique string identifier (e.g. 'gmail', 'slack')
        name         — Human-readable name (e.g. 'Gmail')
        description  — One-line description of the service
        icon_url     — Relative or absolute icon URL
        auth_type    — one of 'oauth2', 'apikey', 'basic'
        auth_url     — OAuth authorize endpoint
        token_url    — OAuth token endpoint
        scopes       — List of OAuth scopes required
        api_base_url — Base URL for API calls
    """

    key: ClassVar[str] = ""
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    icon_url: ClassVar[str] = ""
    auth_type: ClassVar[str] = "oauth2"  # 'oauth2' | 'apikey' | 'basic'
    auth_url: ClassVar[str] = ""
    token_url: ClassVar[str] = ""
    scopes: ClassVar[list[str]] = []
    api_base_url: ClassVar[str] = ""
    category: ClassVar[str] = "general"

    def __init__(self) -> None:
        self._auth_data: dict[str, Any] = {}
        self._client: httpx.AsyncClient | None = None

    # ── Auth data management ─────────────────────────────────────────────────

    def set_auth_data(self, auth_data: dict[str, Any]) -> None:
        """Set the stored authentication data (tokens, api keys, etc.)."""
        self._auth_data = auth_data

    def get_auth_data(self) -> dict[str, Any]:
        """Return current auth data."""
        return self._auth_data

    # ── HTTP client ──────────────────────────────────────────────────────────

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init an httpx client with auth headers already injected."""
        if self._client is None:
            headers: dict[str, str] = {
                "User-Agent": f"Anansi-Connector/{self.key}",
                "Accept": "application/json",
            }
            self._inject_auth_headers(headers)
            self._client = httpx.AsyncClient(
                base_url=self.api_base_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    def _inject_auth_headers(self, headers: dict[str, str]) -> None:
        """Inject authentication into request headers.

        Override for services that need special header formats.
        """
        if self.auth_type == "oauth2":
            access_token = self._auth_data.get("access_token", "")
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
        elif self.auth_type == "apikey":
            api_key = self._auth_data.get("api_key", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        elif self.auth_type == "basic":
            username = self._auth_data.get("username", "")
            password = self._auth_data.get("password", "")
            if username and password:
                import base64
                raw = f"{username}:{password}"
                encoded = base64.b64encode(raw.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── OAuth helpers ────────────────────────────────────────────────────────

    def get_auth_url(self, redirect_uri: str, state: str, **kwargs: Any) -> str:
        """Build the OAuth authorization URL.

        Args:
            redirect_uri: Callback URL after auth.
            state: Anti-CSRF state parameter.

        Returns:
            Full authorize URL.
        """
        if self.auth_type != "oauth2":
            raise NotImplementedError(f"{self.key} does not use OAuth2")
        client_id = self._get_client_id()
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        params.update(kwargs)
        query = "&".join(f"{k}={httpx.utils.quote(str(v), safe='')}" for k, v in params.items())
        return f"{self.auth_url}?{query}"

    def _get_client_id(self) -> str:
        """Get OAuth client ID for this connector.

        Google connectors share a single Google Cloud Project OAuth client.
        Override for services with separate client IDs.
        """
        if self.key.startswith("google_"):
            return settings.oauth.google_client_id
        # Fallback: try connector-specific env vars
        key_upper = self.key.upper().replace("-", "_")
        client_id = getattr(settings.oauth, f"{key_upper}_client_id", None)
        if client_id:
            return client_id
        return getattr(settings.oauth, f"{self.key}_client_id", "")

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange an authorization code for tokens.

        Args:
            code: The authorization code from the OAuth callback.
            redirect_uri: Must match the redirect_uri used in get_auth_url.

        Returns:
            Token dict with at least 'access_token', and optionally
            'refresh_token', 'expires_in', 'scope', etc.
        """
        if self.auth_type != "oauth2":
            raise NotImplementedError(f"{self.key} does not use OAuth2")
        client_id = self._get_client_id()
        client_secret = self._get_client_secret()

        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            return resp.json()

    def _get_client_secret(self) -> str:
        """Get OAuth client secret for this connector."""
        if self.key.startswith("google_"):
            return settings.oauth.google_client_secret
        key_upper = self.key.upper().replace("-", "_")
        secret = getattr(settings.oauth, f"{key_upper}_client_secret", None)
        if secret:
            return secret
        return getattr(settings.oauth, f"{self.key}_client_secret", "")

    async def refresh_token(self, token_data: dict[str, Any]) -> dict[str, Any]:
        """Refresh an expired OAuth access token.

        Args:
            token_data: The current token data containing 'refresh_token'.

        Returns:
            New token data from the provider.
        """
        if self.auth_type != "oauth2":
            raise NotImplementedError(f"{self.key} does not support token refresh")
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise ValueError(f"No refresh_token available for {self.key}")
        client_id = self._get_client_id()
        client_secret = self._get_client_secret()

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            return resp.json()

    async def revoke_token(self, token_data: dict[str, Any]) -> bool:
        """Revoke the OAuth token on disconnect.

        Args:
            token_data: Token data containing 'access_token' to revoke.

        Returns:
            True if revocation was successful (or not needed).
        """
        # Default is a no-op — override for services with revocation endpoints
        logger.info(f"Token revocation not implemented for {self.key}")
        return True

    # ── API key helpers ──────────────────────────────────────────────────────

    async def validate_api_key(self, api_key: str) -> dict[str, Any]:
        """Validate an API key by making a test call to the service.

        Args:
            api_key: The API key to validate.

        Returns:
            Dict with 'valid': bool and optionally 'details'.
        """
        # Override in subclasses that support API-key auth
        raise NotImplementedError(f"{self.key} does not support API key validation")

    # ── Abstract methods ─────────────────────────────────────────────────────

    @abc.abstractmethod
    async def test_connection(self) -> bool:
        """Verify the connection is working by calling a lightweight endpoint.

        Returns:
            True if the connection is healthy.
        """
        ...

    # ── Utility ──────────────────────────────────────────────────────────────

    def token_is_expired(self, token_data: dict[str, Any]) -> bool:
        """Check if the access token is expired based on 'expires_at' or 'expires_in'.

        Args:
            token_data: Token dict, should contain 'expires_at' (unix timestamp)
                       or 'expires_in' (seconds from now).

        Returns:
            True if the token is expired or close to expiry (within 60s).
        """
        expires_at = token_data.get("expires_at")
        if expires_at:
            return time.time() + 60 >= float(expires_at)
        expires_in = token_data.get("expires_in")
        if expires_in:
            return int(expires_in) <= 60
        # If we can't determine, assume it's valid (will fail on next call)
        return False

    def __repr__(self) -> str:
        return f"<{type(self).__name__} key={self.key} auth={self.auth_type}>"


# ── Webhook verification utility ─────────────────────────────────────────────


def verify_webhook_signature(
    payload: bytes | str,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """Verify an HMAC-signed webhook payload.

    Args:
        payload: Raw request body (bytes or string).
        signature: The signature header value.
        secret: The shared secret key.
        algorithm: Hash algorithm ('sha256' or 'sha1').

    Returns:
        True if the signature matches.
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    hash_func = hashlib.sha256 if algorithm == "sha256" else hashlib.sha1
    expected = hmac.new(secret.encode("utf-8"), payload, hash_func).hexdigest()
    return hmac.compare_digest(f"sha256={expected}" if algorithm == "sha256" else f"sha1={expected}", signature)


__all__ = [
    "BaseConnector",
    "verify_webhook_signature",
]
