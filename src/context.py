"""Dynamic family context module — provides live daily snapshots for the assistant.

Reads from Google Calendar, preferences, and Notion backlog to build a
structured text block that replaces the old hardcoded weekly schedule.
This is a computation module — it stores nothing, only reads from other sources.

Used by the ``get_daily_context`` tool in ``src/assistant.py``.
"""

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from src import preferences
from src.config import PHONE_TO_NAME
from src.tools import notion
from src.tools.calendar import get_events_for_date

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PACIFIC = ZoneInfo("America/Los_Angeles")

# Keywords that indicate someone other than Erin has Zoey
CHILDCARE_KEYWORDS: set[str] = {
    "zoey", "sandy", "preschool", "childcare", "babysit",
    "milestones", "daycare", "nanny",
}

# Communication mode time boundaries (hour in Pacific time)
# morning: 7-12, afternoon: 12-17, evening: 17-21, late_night: 21-7
MODE_BOUNDARIES: list[tuple[int, int, str, str]] = [
    (7, 12, "morning", "energetic, proactive suggestions welcome"),
    (12, 17, "afternoon", "normal, responsive to requests"),
    (17, 21, "evening", "winding down, respond to questions but limit proactive content"),
    (21, 7, "late_night", "direct answers only, no proactive suggestions"),
]


# ---------------------------------------------------------------------------
# Communication Mode (T002)
# ---------------------------------------------------------------------------

def get_communication_mode(phone: str) -> tuple[str, str]:
    """Derive communication mode from current Pacific time and user preferences.

    Checks the user's ``quiet_hours`` preferences for custom overrides by
    parsing patterns like "quiet after 9pm" or "quiet after 8 pm".

    Returns:
        Tuple of (mode_name, mode_description).
        Example: ("morning", "energetic, proactive suggestions welcome")
    """
    now = datetime.now(tz=PACIFIC)
    hour = now.hour

    # Check user preferences for quiet-hours override
    custom_quiet_hour = _parse_quiet_hours(phone)
    if custom_quiet_hour is not None and hour >= custom_quiet_hour:
        return ("late_night", "direct answers only, no proactive suggestions")

    # Default time-based boundaries
    for start_h, end_h, mode, description in MODE_BOUNDARIES:
        if start_h < end_h:
            # Normal range (e.g., 7-12)
            if start_h <= hour < end_h:
                return (mode, description)
        else:
            # Wrapping range (e.g., 21-7 means 21-24 + 0-7)
            if hour >= start_h or hour < end_h:
                return (mode, description)

    # Fallback (should not happen given boundaries cover 0-24)
    return ("afternoon", "normal, responsive to requests")


def _parse_quiet_hours(phone: str) -> int | None:
    """Extract custom quiet-hours start from user preferences.

    Looks for preferences with category ``quiet_hours`` and descriptions
    matching patterns like "quiet after 9pm", "quiet after 10 pm",
    "quiet after 8PM".

    Returns the hour (0-23) or None if no custom override found.
    """
    try:
        user_prefs = preferences.get_preferences(phone)
    except Exception:
        return None

    for pref in user_prefs:
        if pref.get("category") != "quiet_hours":
            continue
        desc = pref.get("description", "").lower()
        # Match "quiet after Xpm" or "quiet after X pm"
        match = re.search(r"quiet\s+after\s+(\d{1,2})\s*pm", desc)
        if match:
            pm_hour = int(match.group(1))
            # Convert 12-hour PM to 24-hour (12pm=12, 1pm=13, ..., 11pm=23)
            if pm_hour == 12:
                return 12
            return pm_hour + 12
        # Also match AM patterns (unlikely but handle gracefully)
        match = re.search(r"quiet\s+after\s+(\d{1,2})\s*am", desc)
        if match:
            am_hour = int(match.group(1))
            return 0 if am_hour == 12 else am_hour

    return None


# ---------------------------------------------------------------------------
# Daily Context (T001)
# ---------------------------------------------------------------------------

def get_daily_context(phone: str) -> str:
    """Build a structured plain-text snapshot of today's family context.

    Queries Google Calendar for today's events (grouped by person), infers
    childcare status from event keywords, reads user preferences, and counts
    pending backlog items.

    Handles Google Calendar API failures gracefully by returning a degraded
    output with ``calendar_available: false``.

    Args:
        phone: The user's phone number (used for preferences and name lookup).

    Returns:
        Structured plain text block for the assistant's context window.
    """
    now = datetime.now(tz=PACIFIC)
    user_name = PHONE_TO_NAME.get(phone, "User")

    # Header: date and time
    date_line = now.strftime("%A, %B %-d, %Y at %-I:%M %p Pacific")

    # Communication mode
    mode_name, mode_desc = get_communication_mode(phone)

    # --- Calendar events ---
    calendar_available = True
    jason_events: list[dict] = []
    erin_events: list[dict] = []
    family_events: list[dict] = []

    try:
        all_events = get_events_for_date(now, ["jason", "erin", "family"])
        for event in all_events:
            source = event.get("_calendar_source", "")
            if source == "jason":
                jason_events.append(event)
            elif source == "erin":
                erin_events.append(event)
            elif source == "family":
                family_events.append(event)
    except Exception as e:
        logger.error("Google Calendar API failure in get_daily_context: %s", e)
        calendar_available = False

    # --- Build output ---
    lines: list[str] = []

    # Date header
    lines.append(f"\U0001f4c5 {date_line}")
    lines.append("")

    # Communication mode
    lines.append(f"\U0001f550 Communication mode: {mode_name} ({mode_desc})")
    lines.append("")

    if not calendar_available:
        # Degraded output when calendar is down
        lines.append(
            "\u26a0\ufe0f Calendar data unavailable \u2014 Google Calendar API error. "
            "Cannot show today's events or infer childcare status."
        )
        lines.append("")
    else:
        # Jason's events
        lines.append(f"\U0001f464 Jason's events today:")
        if jason_events:
            for event in jason_events:
                lines.append(f"- {_format_event(event)}")
        else:
            lines.append("- No events")
        lines.append("")

        # Erin's events
        lines.append(f"\U0001f464 Erin's events today:")
        if erin_events:
            for event in erin_events:
                lines.append(f"- {_format_event(event)}")
        else:
            lines.append("- No events")
        lines.append("")

        # Family events
        lines.append(f"\U0001f468\u200d\U0001f469\u200d\U0001f467\u200d\U0001f466 Family events today:")
        if family_events:
            for event in family_events:
                lines.append(f"- {_format_event(event)}")
        else:
            lines.append("- No family events")
        lines.append("")

        # Childcare inference
        childcare_status = _infer_childcare(
            jason_events + erin_events + family_events, now
        )
        lines.append(f"\U0001f476 Zoey: {childcare_status}")
        lines.append("")

    # --- Backlog count ---
    backlog_count = _count_backlog_items()
    lines.append(f"\U0001f4cb Pending backlog items: {backlog_count}")

    # --- Preferences ---
    pref_line = _format_preferences(phone)
    lines.append(f"\u2699\ufe0f {pref_line}")

    # --- Drive times ---
    try:
        from src import drive_times as _dt
        dt_text = _dt.get_drive_times()
        lines.append(f"\U0001f697 {dt_text}")
    except Exception as e:
        logger.warning("Could not load drive times: %s", e)

    # --- Calendar status ---
    cal_status = "available" if calendar_available else "unavailable"
    lines.append(f"\U0001f4c5 Calendar: {cal_status}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_event(event: dict) -> str:
    """Format a single calendar event dict into a readable string.

    Handles both timed events (``start.dateTime``) and all-day events
    (``start.date``).
    """
    summary = event.get("summary", "Untitled event")
    start_raw = event.get("start", {})
    end_raw = event.get("end", {})

    start_dt_str = start_raw.get("dateTime")
    end_dt_str = end_raw.get("dateTime")

    if start_dt_str:
        start_dt = datetime.fromisoformat(start_dt_str)
        start_time = start_dt.strftime("%-I:%M %p")

        if end_dt_str:
            end_dt = datetime.fromisoformat(end_dt_str)
            end_time = end_dt.strftime("%-I:%M %p")
            return f"{start_time} \u2013 {end_time}: {summary}"
        return f"{start_time}: {summary}"

    # All-day event
    return f"{summary} (all day)"


def _infer_childcare(events: list[dict], now: datetime) -> str:
    """Infer who has Zoey based on event keywords and current time.

    Scans all events for childcare-related keywords. If a matching event's
    time window overlaps with ``now``, reports who has Zoey and until when.

    Falls back to "With Erin (no childcare event detected)" if no match.
    """
    for event in events:
        summary = (event.get("summary") or "").lower()
        matched_keywords = CHILDCARE_KEYWORDS & set(summary.split())

        if not matched_keywords:
            # Also check for substring matches (e.g., "Sandy's house")
            if not any(kw in summary for kw in CHILDCARE_KEYWORDS):
                continue

        # We have a childcare-related event — check time overlap
        start_raw = event.get("start", {})
        end_raw = event.get("end", {})

        start_dt_str = start_raw.get("dateTime")
        end_dt_str = end_raw.get("dateTime")

        if start_dt_str and end_dt_str:
            start_dt = datetime.fromisoformat(start_dt_str)
            end_dt = datetime.fromisoformat(end_dt_str)

            if start_dt <= now <= end_dt:
                # Currently in this childcare window
                end_time = end_dt.strftime("%-I:%M %p")
                caregiver = _extract_caregiver(summary)
                return f"With {caregiver} until {end_time}"
            elif start_dt > now:
                # Upcoming childcare event today
                start_time = start_dt.strftime("%-I:%M %p")
                end_time = end_dt.strftime("%-I:%M %p")
                caregiver = _extract_caregiver(summary)
                return (
                    f"With Erin now; {caregiver} from {start_time}\u2013{end_time}"
                )
        elif start_raw.get("date"):
            # All-day childcare event — assume active all day
            caregiver = _extract_caregiver(summary)
            return f"With {caregiver} (all day)"

    return "With Erin (no childcare event detected)"


def _extract_caregiver(summary: str) -> str:
    """Extract a human-readable caregiver name from an event summary.

    Maps keywords to friendly names. Falls back to the raw summary if
    no specific caregiver keyword is found.
    """
    summary_lower = summary.lower()

    if "sandy" in summary_lower:
        return "Sandy"
    if "preschool" in summary_lower or "milestones" in summary_lower:
        return "preschool"
    if "daycare" in summary_lower:
        return "daycare"
    if "nanny" in summary_lower:
        return "nanny"
    if "babysit" in summary_lower:
        return "babysitter"

    # Generic fallback — use the event summary itself
    return summary.strip().title()


def _count_backlog_items() -> int:
    """Count pending (non-done) backlog items from Notion.

    Calls ``notion.get_backlog_items()`` and counts lines starting with "- ".
    Returns 0 on any error.
    """
    try:
        result = notion.get_backlog_items()
        if not result or result.startswith("No backlog") or result.startswith("Backlog database"):
            return 0
        return sum(1 for line in result.splitlines() if line.startswith("- "))
    except Exception as e:
        logger.warning("Failed to count backlog items: %s", e)
        return 0


def _format_preferences(phone: str) -> str:
    """Format the active preferences summary line.

    Returns a string like "Active preferences: 2 (no grocery reminders, quiet after 9pm)"
    or "Active preferences: 0" if none.
    """
    try:
        user_prefs = preferences.get_preferences(phone)
    except Exception:
        user_prefs = []

    count = len(user_prefs)
    if count == 0:
        return "Active preferences: 0"

    descriptions = [p.get("description", "unknown") for p in user_prefs]
    summary = ", ".join(descriptions)
    return f"Active preferences: {count} ({summary})"
