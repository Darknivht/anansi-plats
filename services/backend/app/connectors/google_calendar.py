"""
Anansi Google Calendar Connector — Read, create, update events; get agenda.

Scopes:
    - https://www.googleapis.com/auth/calendar.readonly
    - https://www.googleapis.com/auth/calendar.events
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar

from structlog import get_logger

from app.connectors import register_connector
from app.connectors.google_base import GoogleBaseConnector

logger = get_logger(__name__)


@register_connector
class GoogleCalendarConnector(GoogleBaseConnector):
    """Connect to Google Calendar — read/create/update events, get agenda."""

    key: ClassVar[str] = "google_calendar"
    name: ClassVar[str] = "Google Calendar"
    description: ClassVar[str] = "Read, create, and update calendar events. Get daily agenda."
    icon_url: ClassVar[str] = "/icons/google-calendar.svg"
    category: ClassVar[str] = "productivity"
    scopes: ClassVar[list[str]] = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    async def test_connection(self) -> bool:
        """Verify Calendar connection by listing primary calendar."""
        try:
            client = await self._get_client()
            resp = await client.get("/calendar/v3/users/me/calendarList/primary")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Calendar connection test failed", error=str(exc))
            return False

    # ── Events ──────────────────────────────────────────────────────────────

    async def list_events(
        self,
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 50,
        query: str | None = None,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> list[dict[str, Any]]:
        """List events from a calendar.

        Args:
            calendar_id: Calendar ID (default: 'primary').
            time_min: RFC3339 start time (default: now).
            time_max: RFC3339 end time.
            max_results: Maximum events (1-2500).
            query: Free-text search term.
            single_events: Expand recurring events into instances.
            order_by: 'startTime' or 'updated'.

        Returns:
            List of calendar events.
        """
        params: dict[str, Any] = {
            "maxResults": min(max_results, 2500),
            "singleEvents": str(single_events).lower(),
            "orderBy": order_by,
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        if query:
            params["q"] = query

        client = await self._get_client()
        resp = await client.get(f"/calendar/v3/calendars/{calendar_id}/events", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", [])

    async def get_event(self, event_id: str, calendar_id: str = "primary") -> dict[str, Any]:
        """Get a single event by ID.

        Args:
            event_id: Google Calendar event ID.
            calendar_id: Calendar ID (default: 'primary').

        Returns:
            Full event data.
        """
        client = await self._get_client()
        resp = await client.get(f"/calendar/v3/calendars/{calendar_id}/events/{event_id}")
        resp.raise_for_status()
        return resp.json()

    async def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str | None = None,
        location: str | None = None,
        calendar_id: str = "primary",
        attendees: list[str] | None = None,
        timezone: str = "UTC",
    ) -> dict[str, Any]:
        """Create a new calendar event.

        Args:
            summary: Event title.
            start_time: RFC3339 start datetime.
            end_time: RFC3339 end datetime.
            description: Optional description.
            location: Optional location string.
            calendar_id: Calendar to create in.
            attendees: List of attendee email addresses.
            timezone: IANA timezone for the event.

        Returns:
            Created event data.
        """
        event_body: dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": timezone},
            "end": {"dateTime": end_time, "timeZone": timezone},
        }
        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location
        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        client = await self._get_client()
        resp = await client.post(
            f"/calendar/v3/calendars/{calendar_id}/events",
            json=event_body,
        )
        resp.raise_for_status()
        return resp.json()

    async def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        **updates: Any,
    ) -> dict[str, Any]:
        """Update an existing calendar event.

        Args:
            event_id: Event ID to update.
            calendar_id: Calendar ID.
            **updates: Fields to update (summary, description, start, end, etc.).

        Returns:
            Updated event data.
        """
        client = await self._get_client()
        resp = await client.patch(
            f"/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            json=updates,
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """Delete a calendar event.

        Args:
            event_id: Event ID to delete.
            calendar_id: Calendar ID.

        Returns:
            True if deleted.
        """
        client = await self._get_client()
        resp = await client.delete(f"/calendar/v3/calendars/{calendar_id}/events/{event_id}")
        return resp.status_code == 204

    # ── Agenda / Today ──────────────────────────────────────────────────────

    async def get_today_agenda(self, calendar_id: str = "primary") -> list[dict[str, Any]]:
        """Get all events for today.

        Returns:
            List of today's events sorted by start time.
        """
        now = datetime.now(timezone.utc)
        time_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        time_max = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

        return await self.list_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            order_by="startTime",
        )

    async def get_upcoming_events(
        self,
        calendar_id: str = "primary",
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Get upcoming events from now.

        Args:
            calendar_id: Calendar ID.
            max_results: Max events to return.

        Returns:
            List of upcoming events.
        """
        now = datetime.now(timezone.utc).isoformat()
        return await self.list_events(
            calendar_id=calendar_id,
            time_min=now,
            max_results=max_results,
            order_by="startTime",
        )

    # ── Calendars ───────────────────────────────────────────────────────────

    async def list_calendars(self) -> list[dict[str, Any]]:
        """List all calendars the user has access to.

        Returns:
            List of calendar entries.
        """
        client = await self._get_client()
        resp = await client.get("/calendar/v3/users/me/calendarList")
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", [])
