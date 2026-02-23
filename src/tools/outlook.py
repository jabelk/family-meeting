"""Outlook ICS feed reader — fetch Jason's work calendar events."""

import logging
from datetime import datetime, date, timedelta, timezone
import httpx
import icalendar
import recurring_ical_events
from src.config import OUTLOOK_CALENDAR_ICS_URL

logger = logging.getLogger(__name__)


def get_outlook_events(target_date: str = "") -> str:
    """Fetch Jason's work calendar events for a given date.

    Args:
        target_date: ISO date string (e.g., "2026-02-23"). Defaults to today.

    Returns formatted text list of work meetings with times.
    Falls back gracefully if ICS URL not configured or fetch fails.
    """
    if not OUTLOOK_CALENDAR_ICS_URL:
        return "Jason's work calendar is not configured."

    if target_date:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        dt = date.today()

    try:
        response = httpx.get(OUTLOOK_CALENDAR_ICS_URL, timeout=10.0)
        response.raise_for_status()
    except Exception as e:
        logger.warning("Failed to fetch Outlook ICS feed: %s", e)
        return "Couldn't check Jason's work calendar — you may want to ask him about morning meetings."

    try:
        cal = icalendar.Calendar.from_ical(response.text)
        start = datetime.combine(dt, datetime.min.time(), tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        events = recurring_ical_events.of(cal).between(start, end)

        if not events:
            return f"Jason has no work meetings on {dt.strftime('%A, %b %d')}."

        lines = []
        for event in events:
            summary = str(event.get("SUMMARY", "Work meeting"))
            event_start = event.get("DTSTART").dt
            event_end = event.get("DTEND")
            event_end = event_end.dt if event_end else None

            if hasattr(event_start, "hour"):
                start_str = event_start.strftime("%-I:%M %p")
                if event_end and hasattr(event_end, "hour"):
                    end_str = event_end.strftime("%-I:%M %p")
                    lines.append(f"- {start_str}-{end_str}: {summary}")
                else:
                    lines.append(f"- {start_str}: {summary}")
            else:
                lines.append(f"- All day: {summary}")

        # Sort by time
        lines.sort()
        header = f"Jason's work meetings on {dt.strftime('%A, %b %d')}:"
        return header + "\n" + "\n".join(lines)

    except Exception as e:
        logger.warning("Failed to parse Outlook ICS feed: %s", e)
        return "Couldn't parse Jason's work calendar — you may want to ask him about morning meetings."


def get_outlook_busy_windows(target_date: str = "") -> list[tuple[str, str, str]]:
    """Get Jason's busy windows as structured data for daily plan generation.

    Returns list of (summary, start_time, end_time) tuples.
    """
    if not OUTLOOK_CALENDAR_ICS_URL:
        return []

    if target_date:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        dt = date.today()

    try:
        response = httpx.get(OUTLOOK_CALENDAR_ICS_URL, timeout=10.0)
        response.raise_for_status()
        cal = icalendar.Calendar.from_ical(response.text)
        start = datetime.combine(dt, datetime.min.time(), tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        events = recurring_ical_events.of(cal).between(start, end)

        windows = []
        for event in events:
            summary = str(event.get("SUMMARY", "Work meeting"))
            event_start = event.get("DTSTART").dt
            event_end = event.get("DTEND")
            event_end = event_end.dt if event_end else event_start

            if hasattr(event_start, "strftime"):
                windows.append((
                    summary,
                    event_start.strftime("%-I:%M %p"),
                    event_end.strftime("%-I:%M %p") if hasattr(event_end, "strftime") else "",
                ))
        return windows
    except Exception as e:
        logger.warning("Failed to get Outlook busy windows: %s", e)
        return []
