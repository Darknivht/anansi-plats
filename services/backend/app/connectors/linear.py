"""
Anansi Linear Connector — Issues, projects, cycles.

Auth: Personal API key (Linear uses API keys for auth).
Docs: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class LinearConnector(BaseConnector):
    """Connect to Linear — issues, projects, cycles via GraphQL API."""

    key: ClassVar[str] = "linear"
    name: ClassVar[str] = "Linear"
    description: ClassVar[str] = "Manage issues, projects, and cycles."
    icon_url: ClassVar[str] = "/icons/linear.svg"
    category: ClassVar[str] = "developer"
    auth_type: ClassVar[str] = "apikey"
    api_base_url: ClassVar[str] = "https://api.linear.app/graphql"

    def _inject_auth_headers(self, headers: dict[str, str]) -> None:
        api_key = self._auth_data.get("api_key", "")
        if api_key:
            headers["Authorization"] = api_key

    async def test_connection(self) -> bool:
        """Verify Linear connection by fetching viewer info."""
        try:
            result = await self._graphql(
                """
                query {
                    viewer {
                        id
                        name
                    }
                }
                """
            )
            return bool(result.get("data", {}).get("viewer", {}).get("id"))
        except Exception as exc:
            logger.warning("Linear connection test failed", error=str(exc))
            return False

    async def validate_api_key(self, api_key: str) -> dict[str, Any]:
        """Validate a Linear API key."""
        headers = {"Authorization": api_key, "Content-Type": "application/json"}
        query = "query { viewer { id name email } }"
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.api_base_url, json={"query": query}, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                viewer = data.get("data", {}).get("viewer", {})
                if viewer.get("id"):
                    return {"valid": True, "details": {"name": viewer.get("name", "")}}
            return {"valid": False, "details": {"error": resp.text}}

    async def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query against the Linear API."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        client = await self._get_client()
        resp = await client.post("", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ── Issues ──────────────────────────────────────────────────────────────

    async def list_issues(
        self,
        first: int = 50,
        team_id: str | None = None,
        status: str | None = None,
        assignee_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List issues for the authenticated user's teams.

        Args:
            first: Max results (1-100).
            team_id: Filter by team.
            status: Filter by status name.
            assignee_id: Filter by assignee.

        Returns:
            List of issue objects.
        """
        filters: list[str] = []
        if team_id:
            filters.append(f'team: {{id: {{eq: "{team_id}"}}}}')
        if status:
            filters.append(f'state: {{name: {{eq: "{status}"}}}}')
        if assignee_id:
            filters.append(f'assignee: {{id: {{eq: "{assignee_id}"}}}}')

        filter_str = f"filter: {{{' '.join(filters)}}}" if filters else ""

        query = f"""
        {{
            issues(first: {min(first, 100)}) {filter_str} {{
                nodes {{
                    id
                    title
                    description
                    priority
                    estimate
                    url
                    createdAt
                    updatedAt
                    state {{ id name color type }}
                    assignee {{ id name displayName }}
                    team {{ id name key }}
                    labels {{ nodes {{ id name color }} }}
                }}
            }}
        }}
        """
        result = await self._graphql(query)
        return result.get("data", {}).get("issues", {}).get("nodes", [])

    async def get_issue(self, issue_id: str) -> dict[str, Any]:
        """Get a single issue by ID."""
        query = f"""
        {{
            issue(id: "{issue_id}") {{
                id
                title
                description
                priority
                estimate
                url
                createdAt
                updatedAt
                dueDate
                state {{ id name color type }}
                assignee {{ id name displayName }}
                team {{ id name key }}
                cycle {{ id name number }}
                parent {{ id title }}
                children {{ nodes {{ id title }} }}
                labels {{ nodes {{ id name color }} }}
                comments {{ nodes {{ id body createdAt user {{ id name }} }} }}
            }}
        }}
        """
        result = await self._graphql(query)
        return result.get("data", {}).get("issue", {})

    async def create_issue(
        self,
        team_id: str,
        title: str,
        description: str | None = None,
        priority: int | None = None,
        assignee_id: str | None = None,
        state_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new issue.

        Args:
            team_id: Team to create in.
            title: Issue title.
            description: Markdown description.
            priority: 0-4 (no priority, urgent, high, medium, low).
            assignee_id: User to assign.
            state_id: Workflow state ID.

        Returns:
            Created issue data.
        """
        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    title
                    url
                    createdAt
                }
            }
        }
        """
        variables: dict[str, Any] = {
            "input": {
                "teamId": team_id,
                "title": title,
            }
        }
        if description:
            variables["input"]["description"] = description
        if priority is not None:
            variables["input"]["priority"] = priority
        if assignee_id:
            variables["input"]["assigneeId"] = assignee_id
        if state_id:
            variables["input"]["stateId"] = state_id

        result = await self._graphql(mutation, variables)
        return result.get("data", {}).get("issueCreate", {})

    async def update_issue(self, issue_id: str, **updates: Any) -> dict[str, Any]:
        """Update an issue.

        Args:
            issue_id: Issue ID to update.
            **updates: Fields to update (title, description, priority, stateId, etc.).

        Returns:
            Updated issue data.
        """
        mutation = """
        mutation UpdateIssue($input: IssueUpdateInput!, $id: String!) {
            issueUpdate(input: $input, id: $id) {
                success
                issue { id title url }
            }
        }
        """
        result = await self._graphql(mutation, {"id": issue_id, "input": updates})
        return result.get("data", {}).get("issueUpdate", {})

    # ── Teams ───────────────────────────────────────────────────────────────

    async def list_teams(self) -> list[dict[str, Any]]:
        """List teams accessible by the user."""
        query = """
        {
            teams { nodes { id name key description icon } }
        }
        """
        result = await self._graphql(query)
        return result.get("data", {}).get("teams", {}).get("nodes", [])

    # ── Projects ────────────────────────────────────────────────────────────

    async def list_projects(self, first: int = 50) -> list[dict[str, Any]]:
        """List projects."""
        query = f"""
        {{
            projects(first: {min(first, 100)}) {{
                nodes {{
                    id
                    name
                    description
                    state
                    url
                    startDate
                    targetDate
                    teams {{ nodes {{ id name }} }}
                }}
            }}
        }}
        """
        result = await self._graphql(query)
        return result.get("data", {}).get("projects", {}).get("nodes", [])

    # ── Cycles ──────────────────────────────────────────────────────────────

    async def current_cycle(self, team_id: str) -> dict[str, Any]:
        """Get the current active cycle for a team."""
        query = f"""
        {{
            team(id: "{team_id}") {{
                currentCycle {{
                    id
                    name
                    number
                    startsAt
                    endsAt
                    completedAt
                }}
            }}
        }}
        """
        result = await self._graphql(query)
        return result.get("data", {}).get("team", {}).get("currentCycle", {})
