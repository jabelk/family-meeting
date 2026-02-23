"""Google Calendar API wrapper — read from 3 calendars + write to Erin's calendar."""

import os
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from src.config import CALENDAR_IDS

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "credentials.json")

# Color coding for assistant-created events (Google Calendar colorId values)
COLOR_CHORES = "6"       # Tangerine
COLOR_REST = "2"          # Sage
COLOR_DEVELOPMENT = "10"  # Basil
COLOR_EXERCISE = "3"      # Grape
COLOR_SIDE_WORK = "5"     # Banana
COLOR_BACKLOG = "1"       # Lavender

CREATED_BY_TAG = "family-meeting-assistant"

# Safety thresholds for destructive operations
MAX_CALENDAR_DELETES = 50  # refuse to delete more than this in a single call
MAX_CALENDAR_CREATES = 50  # refuse to create more than this in a single call


def _get_service():
    """Build and return an authenticated Google Calendar service."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
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
        calendar_names: List of calendar keys ("jason", "erin", "family").
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
        calendar_names = ["erin", "family"]

    service = _get_service()
    pacific = ZoneInfo("America/Los_Angeles")
    start_of_day = datetime(
        target_date.year, target_date.month, target_date.day, tzinfo=pacific
    )
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

    events.sort(
        key=lambda e: e["start"].get("dateTime", e["start"].get("date", ""))
    )
    return events


# ---------------------------------------------------------------------------
# Write: create events on Erin's calendar
# ---------------------------------------------------------------------------

def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    color_id: str = COLOR_CHORES,
    calendar_name: str = "erin",
) -> str:
    """Create a single event on a Google Calendar.

    Args:
        summary: Event title (e.g., "Chore block")
        start_time: ISO datetime string (e.g., "2026-02-23T09:30:00-08:00")
        end_time: ISO datetime string
        color_id: Google Calendar colorId for visual coding
        calendar_name: Which calendar to write to (default: erin)
    """
    cal_id = CALENDAR_IDS.get(calendar_name)
    if not cal_id:
        return f"Unknown calendar: {calendar_name}"

    service = _get_service()
    event_body = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "America/Los_Angeles"},
        "end": {"dateTime": end_time, "timeZone": "America/Los_Angeles"},
        "colorId": color_id,
        "extendedProperties": {
            "private": {"createdBy": CREATED_BY_TAG}
        },
    }
    event = service.events().insert(calendarId=cal_id, body=event_body).execute()
    return f"Created event: {summary} ({event.get('id', '')})"


def batch_create_events(events_data: list[dict], calendar_name: str = "erin") -> int:
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
            len(events_data), MAX_CALENDAR_CREATES,
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
                "start": {"dateTime": evt["start_time"], "timeZone": "America/Los_Angeles"},
                "end": {"dateTime": evt["end_time"], "timeZone": "America/Los_Angeles"},
                "colorId": evt.get("color_id", COLOR_CHORES),
                "extendedProperties": {
                    "private": {"createdBy": CREATED_BY_TAG}
                },
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
    calendar_name: str = "erin",
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
            "SAFEGUARD: Refusing to delete %d calendar events (max %d). "
            "Date range %s to %s on calendar '%s'.",
            len(events), MAX_CALENDAR_DELETES, start_date, end_date, calendar_name,
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
