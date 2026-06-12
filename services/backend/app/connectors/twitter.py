"""
Anansi Twitter/X Connector — Read tweets, post, search.

Auth: OAuth 2.0 (OAuth 2.0 PKCE for Twitter API v2).
Scopes: tweet.read, tweet.write, users.read, offline.access
Docs: https://developer.twitter.com/en/docs/twitter-api
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class TwitterConnector(BaseConnector):
    """Connect to Twitter/X — read, post tweets, search."""

    key: ClassVar[str] = "twitter"
    name: ClassVar[str] = "Twitter / X"
    description: ClassVar[str] = "Read, post, and search tweets."
    icon_url: ClassVar[str] = "/icons/twitter.svg"
    category: ClassVar[str] = "social"
    auth_type: ClassVar[str] = "oauth2"
    auth_url: ClassVar[str] = "https://twitter.com/i/oauth2/authorize"
    token_url: ClassVar[str] = "https://api.twitter.com/2/oauth2/token"
    api_base_url: ClassVar[str] = "https://api.twitter.com/2"
    scopes: ClassVar[list[str]] = [
        "tweet.read",
        "tweet.write",
        "users.read",
        "offline.access",
    ]

    async def test_connection(self) -> bool:
        """Verify Twitter connection by fetching current user."""
        try:
            client = await self._get_client()
            resp = await client.get("/users/me", params={"user.fields": "id"})
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("data", {}).get("id"))
        except Exception as exc:
            logger.warning("Twitter connection test failed", error=str(exc))
            return False

    # ── User ────────────────────────────────────────────────────────────────

    async def get_me(self) -> dict[str, Any]:
        """Get the authenticated user's profile.

        Returns:
            User object with id, name, username.
        """
        client = await self._get_client()
        resp = await client.get(
            "/users/me",
            params={"user.fields": "id,name,username,profile_image_url,description,public_metrics"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {})

    async def get_user_by_username(self, username: str) -> dict[str, Any]:
        """Get a user by their @username.

        Args:
            username: Twitter username (without @).

        Returns:
            User object.
        """
        client = await self._get_client()
        resp = await client.get(
            f"/users/by/username/{username}",
            params={"user.fields": "id,name,username,description,public_metrics"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {})

    # ── Tweets ──────────────────────────────────────────────────────────────

    async def post_tweet(self, text: str, reply_to: str | None = None) -> dict[str, Any]:
        """Post a tweet.

        Args:
            text: Tweet text (up to 280 chars for basic access).
            reply_to: Tweet ID to reply to.

        Returns:
            Created tweet data with id and text.
        """
        payload: dict[str, Any] = {"text": text}
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}

        client = await self._get_client()
        resp = await client.post("/tweets", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {})

    async def get_tweet(self, tweet_id: str) -> dict[str, Any]:
        """Get a single tweet by ID.

        Args:
            tweet_id: Tweet ID.

        Returns:
            Tweet object with text, author, metrics.
        """
        client = await self._get_client()
        resp = await client.get(
            f"/tweets/{tweet_id}",
            params={
                "tweet.fields": "created_at,public_metrics,attachments,referenced_tweets",
                "expansions": "author_id",
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_tweet(self, tweet_id: str) -> bool:
        """Delete a tweet.

        Args:
            tweet_id: Tweet ID to delete.

        Returns:
            True if deleted.
        """
        client = await self._get_client()
        resp = await client.delete(f"/tweets/{tweet_id}")
        return resp.status_code == 200

    async def get_user_tweets(
        self,
        user_id: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Get tweets from a user's timeline.

        Args:
            user_id: Twitter user ID.
            max_results: Max tweets (5-100).

        Returns:
            List of tweet objects.
        """
        client = await self._get_client()
        resp = await client.get(
            f"/users/{user_id}/tweets",
            params={
                "max_results": min(max_results, 100),
                "tweet.fields": "created_at,public_metrics",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    async def get_home_timeline(self, max_results: int = 20) -> list[dict[str, Any]]:
        """Get the authenticated user's home timeline.

        Args:
            max_results: Max tweets (5-100).

        Returns:
            List of recent tweets from the home timeline.
        """
        me = await self.get_me()
        user_id = me.get("id")
        if not user_id:
            return []
        return await self.get_user_tweets(user_id, max_results)

    # ── Search ──────────────────────────────────────────────────────────────

    async def search_tweets(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search recent tweets.

        Args:
            query: Search query (supports standard Twitter operators).
            max_results: Max results (10-100).

        Returns:
            List of matching tweets.
        """
        client = await self._get_client()
        resp = await client.get(
            "/tweets/search/recent",
            params={
                "query": query,
                "max_results": min(max_results, 100),
                "tweet.fields": "created_at,public_metrics,author_id",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
