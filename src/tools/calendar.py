"""Google Calendar API wrapper — read upcoming events."""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from src.config import GOOGLE_CALENDAR_ID

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "credentials.json")


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


def get_calendar_events(days_ahead: int = 7) -> str:
    """Fetch upcoming events from Google Calendar for the next N days.

    Returns a formatted text list of events with dates and times.
    """
    try:
        service = _get_service()
        now = datetime.now(tz=timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days_ahead)).isoformat()

        result = (
            service.events()
            .list(
                calendarId=GOOGLE_CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = result.get("items", [])
        if not events:
            return "No events scheduled for the upcoming week."

        lines = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            summary = event.get("summary", "Untitled event")
            if "T" in start:
                dt = datetime.fromisoformat(start)
                day = dt.strftime("%A")
                time_str = dt.strftime("%-I:%M %p")
                lines.append(f"- {day}: {summary} at {time_str}")
            else:
                dt = datetime.strptime(start, "%Y-%m-%d")
                day = dt.strftime("%A")
                lines.append(f"- {day}: {summary} (all day)")
        return "\n".join(lines)
    except Exception as e:
        logger.error("Google Calendar API error: %s", e)
        raise
