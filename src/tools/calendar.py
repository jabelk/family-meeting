"""Google Calendar API wrapper — read from multiple calendars + write events."""

import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.config import (
    CALENDAR_IDS,
    DEFAULT_CALENDAR,
    GOOGLE_CREDENTIALS_JSON,
    GOOGLE_TOKEN_JSON,
    TIMEZONE,
    TIMEZONE_STR,
)

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
]
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "credentials.json")

# Color coding for assistant-created events (Google Calendar colorId values)
COLOR_CHORES = "6"  # Tangerine
COLOR_REST = "2"  # Sage
COLOR_DEVELOPMENT = "10"  # Basil
COLOR_EXERCISE = "3"  # Grape
COLOR_SIDE_WORK = "5"  # Banana
COLOR_BACKLOG = "1"  # Lavender

CREATED_BY_TAG = "family-meeting-assistant"

# Safety thresholds for destructive operations
MAX_CALENDAR_DELETES = 50  # refuse to delete more than this in a single call
MAX_CALENDAR_CREATES = 50  # refuse to create more than this in a single call


_VOLUME_TOKEN_PATH = Path("/app/data/token.json")


def _get_service():
    """Build and return an authenticated Google Calendar service.

    Credential loading priority:
    1. GOOGLE_TOKEN_JSON env var (Railway / containerized deployments)
    2. Volume-backed token file at /app/data/token.json (persists refreshed tokens)
    3. Local token.json file (development)
    4. Interactive OAuth flow via credentials.json (initial local setup only)
    """
    creds = None

    # 1. Try env var first (Railway deployment)
    if GOOGLE_TOKEN_JSON:
        try:
            token_data = json.loads(GOOGLE_TOKEN_JSON)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            logger.info("Google credentials loaded from GOOGLE_TOKEN_JSON env var")
        except Exception as e:
            logger.error("Failed to load GOOGLE_TOKEN_JSON: %s", e)

    # 2. Try volume-backed token file (persists across redeploys)
    if not creds and _VOLUME_TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(_VOLUME_TOKEN_PATH), SCOPES)
            logger.info("Google credentials loaded from volume token file")
        except Exception as e:
            logger.warning("Failed to load volume token file: %s", e)

    # 3. Try local token file (development)
    if not creds and os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Refresh if expired (with retry for transient network failures)
    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            for attempt in range(3):
                try:
                    creds.refresh(Request())
                    logger.info("Google credentials refreshed successfully")
                    break
                except Exception as e:
                    if attempt < 2:
                        logger.warning("Token refresh attempt %d failed: %s", attempt + 1, e)
                        time.sleep(2**attempt)
                    else:
                        logger.error("Token refresh failed after 3 attempts: %s", e)
                        raise
        else:
            creds = None  # Can't refresh, need new auth

    # 4. Interactive OAuth flow (local development only)
    if not creds:
        cred_path = CREDENTIALS_PATH
        if GOOGLE_CREDENTIALS_JSON:
            # Write credentials from env var to temp file for the flow
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(GOOGLE_CREDENTIALS_JSON)
                cred_path = f.name
        flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
        creds = flow.run_local_server(port=0)

    # Persist refreshed/new token to volume (survives redeploys) and local file
    token_json = creds.to_json()
    if _VOLUME_TOKEN_PATH.parent.exists():
        _VOLUME_TOKEN_PATH.write_text(token_json)
    with open(TOKEN_PATH, "w") as f:
        f.write(token_json)

    return build("calendar", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# Read: get events from one or more calendars
# ---------------------------------------------------------------------------


def get_calendar_events(
    days_ahead: int = 7,
    calendar_names: list[str] | None = None,
) -> str:
    """Fetch upcoming events from specified Google Calendars.

    Args:
        days_ahead: Number of days to look ahead.
        calendar_names: List of calendar keys (from CALENDAR_IDS).
                       Defaults to all 3 calendars.

    Returns formatted text list of events labeled by source calendar.
    """
    if calendar_names is None:
        calendar_names = list(CALENDAR_IDS.keys())

    try:
        service = _get_service()
        now = datetime.now(tz=timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days_ahead)).isoformat()

        all_events = []
        for name in calendar_names:
            cal_id = CALENDAR_IDS.get(name)
            if not cal_id:
                continue
            try:
                result = (
                    service.events()
                    .list(
                        calendarId=cal_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )
                for event in result.get("items", []):
                    event["_calendar_source"] = name
                    all_events.append(event)
            except Exception as e:
                logger.warning("Failed to read %s calendar: %s", name, e)

        if not all_events:
            return "No events scheduled for the upcoming week."

        # Sort all events by start time
        all_events.sort(key=lambda e: e["start"].get("dateTime", e["start"].get("date", "")))

        lines = []
        for event in all_events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            summary = event.get("summary", "Untitled event")
            source = event["_calendar_source"]
            label = f" [{source}]" if len(calendar_names) > 1 else ""

            if "T" in start:
                dt = datetime.fromisoformat(start)
                day = dt.strftime("%A")
                time_str = dt.strftime("%-I:%M %p")
                lines.append(f"- {day}: {summary} at {time_str}{label}")
            else:
                dt = datetime.strptime(start, "%Y-%m-%d")
                day = dt.strftime("%A")
                lines.append(f"- {day}: {summary} (all day){label}")
        return "\n".join(lines)
    except Exception as e:
        logger.error("Google Calendar API error: %s", e)
        return f"Error reading Google Calendar: {e}"


def get_events_for_date(
    target_date: datetime,
    calendar_names: list[str] | None = None,
) -> list[dict]:
    """Fetch events for a specific date. Returns raw event dicts.

    Useful for daily plan generation where we need structured data, not text.
    """
    if calendar_names is None:
        calendar_names = list(CALENDAR_IDS.keys())

    service = _get_service()
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    events = []
    for name in calendar_names:
        cal_id = CALENDAR_IDS.get(name)
        if not cal_id:
            continue
        try:
            result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            for event in result.get("items", []):
                event["_calendar_source"] = name
                events.append(event)
        except Exception as e:
            logger.warning("Failed to read %s calendar for date: %s", name, e)

    events.sort(key=lambda e: e["start"].get("dateTime", e["start"].get("date", "")))
    return events


# ---------------------------------------------------------------------------
# Read: raw events for nudge processing (Feature 003)
# ---------------------------------------------------------------------------


def get_events_for_date_raw(
    target_date: date,
    calendar_names: list[str] | None = None,
) -> list[dict]:
    """Fetch full event dicts for a specific date, including conferenceData.

    Returns raw Google Calendar event dicts with all fields (conferenceData,
    description, creator, extendedProperties, etc.) needed for nudge processing.
    Defaults to Erin's and family calendars.
    """
    if calendar_names is None:
        calendar_names = [DEFAULT_CALENDAR, "family"]

    service = _get_service()
    pacific = TIMEZONE
    start_of_day = datetime(target_date.year, target_date.month, target_date.day, tzinfo=pacific)
    end_of_day = start_of_day + timedelta(days=1)

    events = []
    for name in calendar_names:
        cal_id = CALENDAR_IDS.get(name)
        if not cal_id:
            continue
        try:
            result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            for event in result.get("items", []):
                event["_calendar_source"] = name
                events.append(event)
        except Exception as e:
            logger.warning("Failed to read %s calendar for date: %s", name, e)

    events.sort(key=lambda e: e["start"].get("dateTime", e["start"].get("date", "")))
    return events


# ---------------------------------------------------------------------------
# Write: create events on Erin's calendar
# ---------------------------------------------------------------------------


def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    color_id: str = COLOR_CHORES,
    calendar_name: str = DEFAULT_CALENDAR,
) -> str:
    """Create a single event on a Google Calendar.

    Args:
        summary: Event title (e.g., "Chore block")
        start_time: ISO datetime string (e.g., "2026-02-23T09:30:00-08:00")
        end_time: ISO datetime string
        color_id: Google Calendar colorId for visual coding
        calendar_name: Which calendar to write to
    """
    cal_id = CALENDAR_IDS.get(calendar_name)
    if not cal_id:
        return f"Unknown calendar: {calendar_name}"

    service = _get_service()
    event_body = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": TIMEZONE_STR},
        "end": {"dateTime": end_time, "timeZone": TIMEZONE_STR},
        "colorId": color_id,
        "extendedProperties": {"private": {"createdBy": CREATED_BY_TAG}},
    }
    event = service.events().insert(calendarId=cal_id, body=event_body).execute()
    return f"Created event: {summary} ({event.get('id', '')})"


COLOR_REMINDER = "11"  # Tomato (red — stands out for reminders)


def create_quick_event(
    summary: str,
    start_time: str,
    end_time: str = "",
    description: str = "",
    reminder_minutes: int = 15,
    recurrence: list[str] | None = None,
    calendar_name: str = "family",
    location: str = "",
) -> str:
    """Create a quick reminder/event on a Google Calendar.

    Defaults to the family calendar so both Jason and Erin can see it.
    Supports recurring events via RRULE strings.

    Args:
        summary: Event title (e.g., "Erin → Jason: pick up dog")
        start_time: ISO datetime string
        end_time: ISO datetime string (defaults to start_time + 30 min)
        description: Event body text (original message context)
        reminder_minutes: Minutes before event to send reminder (default 15)
        recurrence: List of RRULE strings for recurring events (e.g.,
            ["RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU"]). None for one-time events.
        calendar_name: Target calendar (from CALENDAR_IDS).
    """
    cal_id = CALENDAR_IDS.get(calendar_name)
    if not cal_id:
        return f"Calendar '{calendar_name}' not configured."

    if not end_time:
        # Default to 30-minute event
        from datetime import datetime as dt

        try:
            start_dt = dt.fromisoformat(start_time)
            end_dt = start_dt + timedelta(minutes=30)
            end_time = end_dt.isoformat()
        except ValueError:
            end_time = start_time

    service = _get_service()
    event_body = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": TIMEZONE_STR},
        "end": {"dateTime": end_time, "timeZone": TIMEZONE_STR},
        "colorId": COLOR_REMINDER,
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": reminder_minutes},
            ],
        },
        "extendedProperties": {"private": {"createdBy": CREATED_BY_TAG}},
    }
    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location
    if recurrence:
        event_body["recurrence"] = recurrence

    event = service.events().insert(calendarId=cal_id, body=event_body).execute()
    kind = "recurring event" if recurrence else "reminder"
    return f"Created {kind} on {calendar_name} calendar: {summary} ({event.get('id', '')})"


def batch_create_events(events_data: list[dict], calendar_name: str = DEFAULT_CALENDAR) -> int:
    """Create multiple events on a calendar. Returns count of events created.

    Each item in events_data should have: summary, start_time, end_time, color_id.
    Uses individual insert calls (Google Batch API requires http library changes).
    For 25-40 events this takes ~10-15 seconds which is acceptable for weekly population.
    """
    cal_id = CALENDAR_IDS.get(calendar_name)
    if not cal_id:
        return 0

    if len(events_data) > MAX_CALENDAR_CREATES:
        logger.error(
            "SAFEGUARD: Refusing to create %d calendar events (max %d).",
            len(events_data),
            MAX_CALENDAR_CREATES,
        )
        raise ValueError(
            f"Safety limit: refusing to create {len(events_data)} events "
            f"(max {MAX_CALENDAR_CREATES}). Split into smaller batches."
        )

    service = _get_service()
    created = 0
    for evt in events_data:
        try:
            event_body = {
                "summary": evt["summary"],
                "start": {"dateTime": evt["start_time"], "timeZone": TIMEZONE_STR},
                "end": {"dateTime": evt["end_time"], "timeZone": TIMEZONE_STR},
                "colorId": evt.get("color_id", COLOR_CHORES),
                "extendedProperties": {"private": {"createdBy": CREATED_BY_TAG}},
            }
            service.events().insert(calendarId=cal_id, body=event_body).execute()
            created += 1
        except Exception as e:
            logger.warning("Failed to create event '%s': %s", evt.get("summary"), e)
    logger.info("Created %d events on '%s'", created, calendar_name)
    return created


def delete_assistant_events(
    start_date: str,
    end_date: str,
    calendar_name: str = DEFAULT_CALENDAR,
) -> int:
    """Delete all assistant-created events in a date range. Returns count deleted.

    Filters by extendedProperties.private.createdBy = CREATED_BY_TAG.
    """
    cal_id = CALENDAR_IDS.get(calendar_name)
    if not cal_id:
        return 0

    service = _get_service()
    result = (
        service.events()
        .list(
            calendarId=cal_id,
            timeMin=start_date,
            timeMax=end_date,
            singleEvents=True,
            privateExtendedProperty=f"createdBy={CREATED_BY_TAG}",
        )
        .execute()
    )

    events = result.get("items", [])
    if len(events) > MAX_CALENDAR_DELETES:
        logger.error(
            "SAFEGUARD: Refusing to delete %d calendar events (max %d). Date range %s to %s on calendar '%s'.",
            len(events),
            MAX_CALENDAR_DELETES,
            start_date,
            end_date,
            calendar_name,
        )
        raise ValueError(
            f"Safety limit: refusing to delete {len(events)} events "
            f"(max {MAX_CALENDAR_DELETES}). Narrow the date range or increase the limit."
        )

    deleted = 0
    for event in events:
        try:
            service.events().delete(calendarId=cal_id, eventId=event["id"]).execute()
            deleted += 1
        except Exception as e:
            logger.warning("Failed to delete event %s: %s", event["id"], e)
    logger.info("Deleted %d assistant events from '%s' (%s to %s)", deleted, calendar_name, start_date, end_date)
    return deleted


def delete_calendar_event(
    event_id: str,
    calendar_name: str = "family",
    cancel_mode: str = "single",
) -> str:
    """Delete a single occurrence or all future occurrences of a calendar event.

    Args:
        event_id: Google Calendar event ID.
        calendar_name: Target calendar (from CALENDAR_IDS).
        cancel_mode: "single" to delete just this instance, "all_following" to
            delete the entire recurring event (all future occurrences).
    """
    cal_id = CALENDAR_IDS.get(calendar_name)
    if not cal_id:
        return f"Calendar '{calendar_name}' not configured."

    service = _get_service()

    try:
        event = service.events().get(calendarId=cal_id, eventId=event_id).execute()
    except Exception as e:
        return f"Could not find event {event_id}: {e}"

    summary = event.get("summary", "Untitled")

    if cancel_mode == "all_following":
        # Delete the entire event (and all its occurrences)
        try:
            service.events().delete(calendarId=cal_id, eventId=event_id).execute()
            return f"Deleted all occurrences of '{summary}' from {calendar_name} calendar."
        except Exception as e:
            return f"Failed to delete event: {e}"
    else:
        # Cancel just this single occurrence — set status to cancelled
        try:
            service.events().delete(calendarId=cal_id, eventId=event_id).execute()
            return f"Cancelled this occurrence of '{summary}' from {calendar_name} calendar."
        except Exception as e:
            return f"Failed to cancel occurrence: {e}"


def list_recurring_events(calendar_name: str = "family") -> str:
    """List all active recurring event series on a calendar.

    Args:
        calendar_name: Target calendar (from CALENDAR_IDS).
    """
    cal_id = CALENDAR_IDS.get(calendar_name)
    if not cal_id:
        return f"Calendar '{calendar_name}' not configured."

    service = _get_service()
    now = datetime.now(TIMEZONE).isoformat()

    try:
        result = (
            service.events()
            .list(
                calendarId=cal_id,
                timeMin=now,
                singleEvents=False,
                maxResults=250,
            )
            .execute()
        )
    except Exception as e:
        return f"Failed to list events: {e}"

    recurring = []
    for event in result.get("items", []):
        if "recurrence" in event:
            recurring.append(
                {
                    "id": event["id"],
                    "summary": event.get("summary", "Untitled"),
                    "recurrence": event["recurrence"],
                    "start": event.get("start", {}),
                }
            )

    if not recurring:
        return f"No recurring events found on {calendar_name} calendar."

    lines = [f"Recurring events on {calendar_name} calendar ({len(recurring)} series):"]
    for ev in recurring:
        rrule = ev["recurrence"][0] if ev["recurrence"] else "unknown pattern"
        start = ev["start"].get("dateTime", ev["start"].get("date", "unknown"))
        lines.append(f"- {ev['summary']} | {rrule} | starts {start} | id: {ev['id']}")

    return "\n".join(lines)
