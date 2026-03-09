"""Outlook / work calendar reader — ICS feed or iOS Shortcut pushed data."""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import icalendar
import recurring_ical_events

from src.config import OUTLOOK_CALENDAR_ICS_URL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Work calendar file storage (iOS Shortcut push — Feature 015)
# ---------------------------------------------------------------------------

_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
_WORK_CALENDAR_FILE = _DATA_DIR / "work_calendar.json"
_EXPIRY_DAYS = 3


def _load_work_calendar_file() -> dict:
    """Load the entire work calendar JSON file. Returns empty dict if missing."""
    if not _WORK_CALENDAR_FILE.exists():
        return {}
    try:
        return json.loads(_WORK_CALENDAR_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read work calendar file: %s", e)
        return {}


def _load_work_calendar(target_date: str) -> list[dict] | None:
    """Load pushed work events for a specific date.

    Returns:
        list[dict] — events for that date (may be empty = "no meetings")
        None — no data was pushed for that date, or data is expired
    """
    data = _load_work_calendar_file()
    entry = data.get(target_date)
    if entry is None:
        return None

    # Check expiration
    received_at = entry.get("received_at", "")
    if received_at:
        try:
            received_dt = datetime.fromisoformat(received_at)
            if received_dt.tzinfo is None:
                received_dt = received_dt.replace(tzinfo=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            if (now - received_dt).days > _EXPIRY_DAYS:
                logger.info("Work calendar data for %s is expired (received %s)", target_date, received_at)
                return None
        except (ValueError, TypeError):
            pass

    return entry.get("events", [])


def save_work_calendar(events_by_date: dict[str, list[dict]]) -> None:
    """Save work calendar events grouped by date. Auto-prunes expired entries.

    Args:
        events_by_date: {"2026-03-03": [{"title": ..., "start": ..., "end": ...}, ...]}
    """
    data = _load_work_calendar_file()
    now_iso = datetime.now(tz=timezone.utc).isoformat()

    # Update with new data
    for date_str, events in events_by_date.items():
        data[date_str] = {
            "events": events,
            "received_at": now_iso,
        }

    # Prune expired entries
    now = datetime.now(tz=timezone.utc)
    pruned_keys = []
    for date_str, entry in list(data.items()):
        received_at = entry.get("received_at", "")
        if received_at:
            try:
                received_dt = datetime.fromisoformat(received_at)
                if received_dt.tzinfo is None:
                    received_dt = received_dt.replace(tzinfo=timezone.utc)
                if (now - received_dt).days > _EXPIRY_DAYS:
                    pruned_keys.append(date_str)
            except (ValueError, TypeError):
                pass
    for key in pruned_keys:
        del data[key]
        logger.info("Pruned expired work calendar entry: %s", key)

    # Atomic write
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = _WORK_CALENDAR_FILE.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(data, indent=2))
    tmp_file.rename(_WORK_CALENDAR_FILE)
    logger.info("Saved work calendar: %d dates", len(events_by_date))


def _format_pushed_events(dt: date, events: list[dict]) -> str:
    """Format pushed work calendar events into display text."""
    if not events:
        return f"Jason has no work meetings on {dt.strftime('%A, %b %d')}."

    lines = []
    for event in events:
        title = event.get("title", "Work meeting")
        start_str = event.get("start", "")
        end_str = event.get("end", "")
        try:
            start_dt = datetime.fromisoformat(start_str)
            s = start_dt.strftime("%-I:%M %p")
            if end_str:
                end_dt = datetime.fromisoformat(end_str)
                e = end_dt.strftime("%-I:%M %p")
                lines.append(f"- {s}-{e}: {title}")
            else:
                lines.append(f"- {s}: {title}")
        except (ValueError, TypeError):
            lines.append(f"- {title}")

    lines.sort()
    header = f"Jason's work meetings on {dt.strftime('%A, %b %d')}:"
    return header + "\n" + "\n".join(lines)


def get_outlook_events(target_date: str = "") -> str:
    """Fetch Jason's work calendar events for a given date.

    Args:
        target_date: ISO date string (e.g., "2026-02-23"). Defaults to today.

    Returns formatted text list of work meetings with times.
    Priority: pushed data (iOS Shortcut) → ICS URL (if configured) → "unavailable".
    """
    if target_date:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        dt = date.today()

    # Try pushed data first (iOS Shortcut — most authoritative)
    pushed = _load_work_calendar(dt.isoformat())
    if pushed is not None:
        return _format_pushed_events(dt, pushed)

    # Fall back to ICS feed (if configured)
    if OUTLOOK_CALENDAR_ICS_URL:
        try:
            response = httpx.get(OUTLOOK_CALENDAR_ICS_URL, timeout=10.0)
            response.raise_for_status()
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

            lines.sort()
            header = f"Jason's work meetings on {dt.strftime('%A, %b %d')}:"
            return header + "\n" + "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to fetch/parse Outlook ICS feed: %s", e)

    return "Jason's work calendar is not available — you may want to ask him about his meetings."


def get_outlook_busy_windows(target_date: str = "") -> list[tuple[str, str, str]]:
    """Get Jason's busy windows as structured data for daily plan generation.

    Returns list of (summary, start_time, end_time) tuples.
    Priority: pushed data (iOS Shortcut) → ICS URL (if configured) → empty list.
    """
    if target_date:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        dt = date.today()

    # Try pushed data first (iOS Shortcut — most authoritative)
    pushed = _load_work_calendar(dt.isoformat())
    if pushed is not None:
        windows = []
        for event in pushed:
            title = event.get("title", "Work meeting")
            try:
                start_dt = datetime.fromisoformat(event.get("start", ""))
                end_dt = datetime.fromisoformat(event.get("end", ""))
                windows.append(
                    (
                        title,
                        start_dt.strftime("%-I:%M %p"),
                        end_dt.strftime("%-I:%M %p"),
                    )
                )
            except (ValueError, TypeError):
                continue
        return windows

    # Fall back to ICS feed (if configured)
    if OUTLOOK_CALENDAR_ICS_URL:
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
                    windows.append(
                        (
                            summary,
                            event_start.strftime("%-I:%M %p"),
                            event_end.strftime("%-I:%M %p") if hasattr(event_end, "strftime") else "",
                        )
                    )
            return windows
        except Exception as e:
            logger.warning("Failed to get Outlook busy windows via ICS: %s", e)

    return []
