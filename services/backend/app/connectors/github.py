"""
Anansi GitHub Connector — Issues, PRs, repos, search code.

Auth: OAuth (GitHub App or OAuth App) or personal access token.
Scopes: repo, read:user, issues, pull_requests
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class GitHubConnector(BaseConnector):
    """Connect to GitHub — issues, PRs, repos, search code."""

    key: ClassVar[str] = "github"
    name: ClassVar[str] = "GitHub"
    description: ClassVar[str] = "Manage issues, pull requests, repositories, and search code."
    icon_url: ClassVar[str] = "/icons/github.svg"
    category: ClassVar[str] = "developer"
    auth_type: ClassVar[str] = "oauth2"
    auth_url: ClassVar[str] = "https://github.com/login/oauth/authorize"
    token_url: ClassVar[str] = "https://github.com/login/oauth/access_token"
    api_base_url: ClassVar[str] = "https://api.github.com"
    scopes: ClassVar[list[str]] = [
        "repo",
        "read:user",
        "issues:read",
        "issues:write",
        "pull_requests:read",
    ]

    async def test_connection(self) -> bool:
        """Verify GitHub connection by fetching current user."""
        try:
            client = await self._get_client()
            resp = await client.get("/user")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("GitHub connection test failed", error=str(exc))
            return False

    async def get_current_user(self) -> dict[str, Any]:
        """Get the authenticated user's profile."""
        client = await self._get_client()
        resp = await client.get("/user")
        resp.raise_for_status()
        return resp.json()

    # ── Repositories ────────────────────────────────────────────────────────

    async def list_repos(
        self,
        type: str = "all",
        sort: str = "updated",
        direction: str = "desc",
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """List repositories for the authenticated user.

        Args:
            type: 'all', 'owner', 'public', 'private', 'member'.
            sort: 'created', 'updated', 'pushed', 'full_name'.
            direction: 'asc' or 'desc'.
            per_page: Results per page (1-100).

        Returns:
            List of repository objects.
        """
        params = {"type": type, "sort": sort, "direction": direction, "per_page": min(per_page, 100)}
        client = await self._get_client()
        resp = await client.get("/user/repos", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Get a repository by owner and name."""
        client = await self._get_client()
        resp = await client.get(f"/repos/{owner}/{repo}")
        resp.raise_for_status()
        return resp.json()

    # ── Issues ──────────────────────────────────────────────────────────────

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
        labels: str | None = None,
    ) -> list[dict[str, Any]]:
        """List issues for a repository.

        Args:
            owner: Repo owner.
            repo: Repo name.
            state: 'open', 'closed', 'all'.
            sort: 'created', 'updated', 'comments'.
            direction: 'asc' or 'desc'.
            per_page: Max results (1-100).
            labels: Comma-separated label names.

        Returns:
            List of issue objects.
        """
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": min(per_page, 100),
        }
        if labels:
            params["labels"] = labels

        client = await self._get_client()
        resp = await client.get(f"/repos/{owner}/{repo}/issues", params=params)
        resp.raise_for_status()
        return resp.json()

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new issue.

        Args:
            owner: Repo owner.
            repo: Repo name.
            title: Issue title.
            body: Issue body (Markdown).
            labels: List of label names.
            assignees: List of usernames to assign.

        Returns:
            Created issue object.
        """
        payload: dict[str, Any] = {"title": title}
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees

        client = await self._get_client()
        resp = await client.post(f"/repos/{owner}/{repo}/issues", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        **updates: Any,
    ) -> dict[str, Any]:
        """Update an issue.

        Args:
            owner: Repo owner.
            repo: Repo name.
            issue_number: Issue number.
            **updates: Fields to update (title, body, state, labels, etc.).

        Returns:
            Updated issue object.
        """
        client = await self._get_client()
        resp = await client.patch(f"/repos/{owner}/{repo}/issues/{issue_number}", json=updates)
        resp.raise_for_status()
        return resp.json()

    # ── Pull Requests ───────────────────────────────────────────────────────

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """List pull requests for a repository."""
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": min(per_page, 100),
        }
        client = await self._get_client()
        resp = await client.get(f"/repos/{owner}/{repo}/pulls", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_pull_request(self, owner: str, repo: str, pull_number: int) -> dict[str, Any]:
        """Get details of a specific pull request."""
        client = await self._get_client()
        resp = await client.get(f"/repos/{owner}/{repo}/pulls/{pull_number}")
        resp.raise_for_status()
        return resp.json()

    # ── Search ──────────────────────────────────────────────────────────────

    async def search_code(self, query: str, per_page: int = 10) -> dict[str, Any]:
        """Search code across all repositories.

        Args:
            query: GitHub code search query.
            per_page: Results per page.

        Returns:
            Search results with 'items' list.
        """
        client = await self._get_client()
        resp = await client.get("/search/code", params={"q": query, "per_page": min(per_page, 100)})
        resp.raise_for_status()
        return resp.json()

    async def search_issues(self, query: str, per_page: int = 10) -> dict[str, Any]:
        """Search issues and pull requests.

        Args:
            query: GitHub issues search query.
            per_page: Results per page.

        Returns:
            Search results.
        """
        client = await self._get_client()
        resp = await client.get("/search/issues", params={"q": query, "per_page": min(per_page, 100)})
        resp.raise_for_status()
        return resp.json()
