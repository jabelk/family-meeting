"""Chore suggestions, free window detection, and preference tracking."""

import json
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.tools.calendar import get_events_for_date_raw
from src.tools.notion import (
    query_all_chores,
    update_chore_completion,
    update_chore_preference,
    seed_default_chores,
    create_nudge,
    query_nudges_by_type,
    update_nudge_status,
    get_family_profile,
)

logger = logging.getLogger(__name__)

PACIFIC = ZoneInfo("America/Los_Angeles")

# Frequency in days for overdue score calculation
FREQUENCY_DAYS = {
    "daily": 1,
    "every_other_day": 2,
    "weekly": 7,
    "biweekly": 14,
    "monthly": 30,
}

# Track skipped chores for the day (reset on scan)
_skipped_today: set[str] = set()
_skipped_date: date | None = None


def _reset_skipped_if_new_day() -> None:
    """Reset the skipped chores set if it's a new day."""
    global _skipped_today, _skipped_date
    today = date.today()
    if _skipped_date != today:
        _skipped_today = set()
        _skipped_date = today


# ---------------------------------------------------------------------------
# T017: Free window detection
# ---------------------------------------------------------------------------

def detect_free_windows(target_date: date) -> list[dict]:
    """Find free windows in Erin's day by comparing calendar events against time boundaries.

    Returns list of {start: datetime, end: datetime, duration_minutes: int}
    for gaps >= 15 minutes between 7:00 AM and 8:30 PM.
    """
    events = get_events_for_date_raw(target_date, calendar_names=["erin", "family"])

    # Define day boundaries (7 AM to 8:30 PM Pacific)
    day_start = datetime(
        target_date.year, target_date.month, target_date.day,
        hour=7, minute=0, tzinfo=PACIFIC,
    )
    day_end = datetime(
        target_date.year, target_date.month, target_date.day,
        hour=20, minute=30, tzinfo=PACIFIC,
    )

    # Collect all busy periods
    busy_periods: list[tuple[datetime, datetime]] = []
    for event in events:
        start_str = event["start"].get("dateTime")
        end_str = event.get("end", {}).get("dateTime")
        if not start_str:
            # All-day event — skip (doesn't block specific windows)
            continue

        event_start = datetime.fromisoformat(start_str)
        if event_start.tzinfo is None:
            event_start = event_start.replace(tzinfo=PACIFIC)

        if end_str:
            event_end = datetime.fromisoformat(end_str)
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=PACIFIC)
        else:
            event_end = event_start + timedelta(hours=1)

        busy_periods.append((event_start, event_end))

    # Sort by start time
    busy_periods.sort(key=lambda p: p[0])

    # Find gaps between busy periods
    windows: list[dict] = []
    current_time = day_start

    for busy_start, busy_end in busy_periods:
        # Clamp to day boundaries
        busy_start = max(busy_start, day_start)
        busy_end = min(busy_end, day_end)

        if busy_start > current_time:
            gap_minutes = int((busy_start - current_time).total_seconds() / 60)
            if gap_minutes >= 15:
                windows.append({
                    "start": current_time,
                    "end": busy_start,
                    "duration_minutes": gap_minutes,
                })

        current_time = max(current_time, busy_end)

    # Check gap between last event and end of day
    if current_time < day_end:
        gap_minutes = int((day_end - current_time).total_seconds() / 60)
        if gap_minutes >= 15:
            windows.append({
                "start": current_time,
                "end": day_end,
                "duration_minutes": gap_minutes,
            })

    return windows


# ---------------------------------------------------------------------------
# T018: Chore suggestion algorithm
# ---------------------------------------------------------------------------

def suggest_chore(free_window_minutes: int) -> list[dict]:
    """Suggest 1-2 chores that fit within the available time window.

    Uses the chore selection algorithm from data-model.md:
    1. Filter by Duration <= free_window_minutes
    2. Prioritize by overdue score (days_since_last / frequency_days)
    3. Boost if today matches a Preferred Day
    4. Deprioritize disliked chores (still suggest if overdue > 2x)
    5. Return top 1-2 suggestions
    """
    _reset_skipped_if_new_day()
    chores = query_all_chores()
    if not chores:
        return []

    today = date.today()
    day_name = today.strftime("%A")  # e.g., "Monday"
    scored: list[tuple[float, dict]] = []

    for chore in chores:
        # Skip chores that don't fit in the window
        duration = chore.get("duration", 0) or 0
        if duration > free_window_minutes or duration == 0:
            continue

        # Skip chores already skipped today
        if chore["name"] in _skipped_today:
            continue

        # Calculate overdue score
        frequency = chore.get("frequency", "weekly")
        freq_days = FREQUENCY_DAYS.get(frequency, 7)

        last_completed = chore.get("last_completed")
        if last_completed:
            try:
                last_date = date.fromisoformat(last_completed)
                days_since = (today - last_date).days
            except (ValueError, TypeError):
                days_since = freq_days  # Assume due if can't parse
        else:
            days_since = freq_days * 2  # Never done = very overdue

        overdue_score = days_since / freq_days

        # Boost if today matches a preferred day
        preferred_days = chore.get("preferred_days", [])
        if preferred_days and day_name in preferred_days:
            overdue_score *= 1.5

        # Handle preference
        preference = chore.get("preference", "neutral")
        if preference == "dislike":
            if overdue_score < 2.0:
                continue  # Skip disliked unless very overdue
            overdue_score *= 0.7  # Still deprioritize somewhat
        elif preference == "like":
            overdue_score *= 1.2

        scored.append((overdue_score, chore))

    # Sort by score descending (most overdue first)
    scored.sort(key=lambda x: x[0], reverse=True)

    # Return top 1-2
    suggestions = []
    for score, chore in scored[:2]:
        suggestions.append({
            "id": chore["id"],
            "name": chore["name"],
            "duration": chore["duration"],
            "category": chore.get("category", ""),
            "overdue_score": round(score, 1),
        })

    return suggestions


# ---------------------------------------------------------------------------
# T019: Complete and skip chores
# ---------------------------------------------------------------------------

def complete_chore(chore_name: str) -> str:
    """Mark a chore as completed. Updates Chores DB and associated nudge."""
    chores = query_all_chores()
    match = _fuzzy_match_chore(chore_name, chores)
    if not match:
        return f"Couldn't find a chore matching '{chore_name}'. Check the name and try again."

    today_str = date.today().isoformat()
    result = update_chore_completion(match["id"], today_str)

    # Mark associated chore nudge as Done
    chore_nudges = query_nudges_by_type("chore", statuses=["Sent", "Pending"])
    for nudge in chore_nudges:
        ctx = nudge.get("context", "")
        if ctx:
            try:
                ctx_data = json.loads(ctx)
                if ctx_data.get("chore_id") == match["id"]:
                    update_nudge_status(nudge["id"], "Done")
                    break
            except (json.JSONDecodeError, TypeError):
                pass

    logger.info("Chore completed: %s", match["name"])
    return f"Nice work! '{match['name']}' marked as done."


def skip_chore(chore_name: str) -> str:
    """Skip a suggested chore. Won't be re-suggested today."""
    _reset_skipped_if_new_day()
    chores = query_all_chores()
    match = _fuzzy_match_chore(chore_name, chores)
    if not match:
        return f"Couldn't find a chore matching '{chore_name}'."

    _skipped_today.add(match["name"])

    # Mark associated chore nudge as Dismissed
    chore_nudges = query_nudges_by_type("chore", statuses=["Sent", "Pending"])
    for nudge in chore_nudges:
        ctx = nudge.get("context", "")
        if ctx:
            try:
                ctx_data = json.loads(ctx)
                if ctx_data.get("chore_id") == match["id"]:
                    update_nudge_status(nudge["id"], "Dismissed")
                    break
            except (json.JSONDecodeError, TypeError):
                pass

    logger.info("Chore skipped: %s", match["name"])
    return f"No problem — skipping '{match['name']}' for today."


def _fuzzy_match_chore(name: str, chores: list[dict]) -> dict | None:
    """Match a chore name against the chores list (case-insensitive, partial match)."""
    name_lower = name.lower().strip()

    # Exact match first
    for chore in chores:
        if chore["name"].lower() == name_lower:
            return chore

    # Partial match
    for chore in chores:
        if name_lower in chore["name"].lower() or chore["name"].lower() in name_lower:
            return chore

    return None


# ---------------------------------------------------------------------------
# T022: Set chore preference (US4 — implemented here for chores.py coherence)
# ---------------------------------------------------------------------------

def set_chore_preference(
    chore_name: str,
    preference: str | None = None,
    preferred_days: list[str] | None = None,
    frequency: str | None = None,
) -> str:
    """Update chore preferences (like/dislike, preferred days, frequency)."""
    chores = query_all_chores()
    match = _fuzzy_match_chore(chore_name, chores)
    if not match:
        return f"Couldn't find a chore matching '{chore_name}'. Available chores: {', '.join(c['name'] for c in chores[:5])}"

    result = update_chore_preference(
        match["id"],
        preference=preference,
        preferred_days=preferred_days,
        frequency=frequency,
    )

    parts = []
    if preference:
        parts.append(f"preference={preference}")
    if preferred_days:
        parts.append(f"preferred days={', '.join(preferred_days)}")
    if frequency:
        parts.append(f"frequency={frequency}")

    logger.info("Chore preference updated: %s → %s", match["name"], ", ".join(parts))
    return f"Updated '{match['name']}': {', '.join(parts)}."


# ---------------------------------------------------------------------------
# T023: Chore history (US4)
# ---------------------------------------------------------------------------

def get_chore_history(days: int = 7) -> str:
    """Get a summary of completed chores over the past N days."""
    chore_nudges = query_nudges_by_type("chore", statuses=["Done"])
    chores = query_all_chores()
    chore_map = {c["id"]: c for c in chores}

    cutoff = date.today() - timedelta(days=days)
    history: dict[str, list[str]] = {}

    for nudge in chore_nudges:
        scheduled = nudge.get("scheduled_time", "")
        if not scheduled:
            continue
        try:
            nudge_date = datetime.fromisoformat(scheduled).date()
        except (ValueError, TypeError):
            continue

        if nudge_date < cutoff:
            continue

        ctx = nudge.get("context", "")
        chore_name = nudge.get("summary", "Unknown chore")
        duration = ""
        if ctx:
            try:
                ctx_data = json.loads(ctx)
                chore_id = ctx_data.get("chore_id", "")
                if chore_id in chore_map:
                    chore_name = chore_map[chore_id]["name"]
                    duration = f" ({chore_map[chore_id]['duration']} min)"
            except (json.JSONDecodeError, TypeError):
                pass

        day_str = nudge_date.strftime("%A %b %d")
        if day_str not in history:
            history[day_str] = []
        history[day_str].append(f"{chore_name}{duration}")

    if not history:
        return f"No chores completed in the past {days} days."

    lines = [f"*Chores completed (past {days} days):*\n"]
    for day, items in sorted(history.items()):
        lines.append(f"*{day}:*")
        for item in items:
            lines.append(f"  • {item}")

    total = sum(len(items) for items in history.values())
    lines.append(f"\n{total} chore(s) total — great work!")
    return "\n".join(lines)
