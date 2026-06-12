"""
Anansi Google Base Connector — Shared infrastructure for Google APIs.

All Google-service connectors (Gmail, Calendar, Drive, Keep) share:
- OAuth client credentials from a single Google Cloud Project
- Google-scoped token exchange and refresh
- Common HTTP client with Google API base URL
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from structlog import get_logger

from app.connectors.base import BaseConnector
from app.core.config import settings

logger = get_logger(__name__)


class GoogleBaseConnector(BaseConnector):
    """Base for all Google API connectors.

    Google's OAuth flow uses:
    - Auth URL: https://accounts.google.com/o/oauth2/v2/auth
    - Token URL: https://oauth2.googleapis.com/token
    - Revocation: https://oauth2.googleapis.com/revoke
    """

    auth_url: ClassVar[str] = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: ClassVar[str] = "https://oauth2.googleapis.com/token"
    api_base_url: ClassVar[str] = "https://www.googleapis.com"

    def _get_client_id(self) -> str:
        return settings.oauth.google_client_id

    def _get_client_secret(self) -> str:
        return settings.oauth.google_client_secret

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange Google auth code for tokens."""
        data = {
            "code": code,
            "client_id": self._get_client_id(),
            "client_secret": self._get_client_secret(),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            result = resp.json()
            # Add expires_at for easier expiry checking
            if "expires_in" in result:
                import time
                result["expires_at"] = int(time.time()) + int(result["expires_in"])
            return result

    async def refresh_token(self, token_data: dict[str, Any]) -> dict[str, Any]:
        """Refresh a Google access token."""
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise ValueError("No refresh_token available for Google connector")

        data = {
            "client_id": self._get_client_id(),
            "client_secret": self._get_client_secret(),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, data=data)
            resp.raise_for_status()
            result = resp.json()
            # Preserve the original refresh_token if not returned
            if "refresh_token" not in result:
                result["refresh_token"] = refresh_token
            if "expires_in" in result:
                import time
                result["expires_at"] = int(time.time()) + int(result["expires_in"])
            return result

    async def revoke_token(self, token_data: dict[str, Any]) -> bool:
        """Revoke a Google OAuth token."""
        access_token = token_data.get("access_token")
        if not access_token:
            return True
        revoke_url = "https://oauth2.googleapis.com/revoke"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(revoke_url, params={"token": access_token})
                return resp.status_code == 200
            except Exception as exc:
                logger.warning(f"Token revocation failed for {self.key}", error=str(exc))
                return False

    def _inject_auth_headers(self, headers: dict[str, str]) -> None:
        """Inject Google Bearer token."""
        access_token = self._auth_data.get("access_token", "")
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
