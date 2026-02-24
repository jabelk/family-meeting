"""Nudge scanning, scheduling, and delivery for proactive WhatsApp reminders."""

import json
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.config import ERIN_PHONE
from src.tools.calendar import get_events_for_date_raw, CREATED_BY_TAG
from src.tools.notion import (
    create_nudge,
    query_pending_nudges,
    query_nudges_by_type,
    query_nudges_by_event_id,
    update_nudge_status,
    count_sent_today,
    check_quiet_day,
)
from src.whatsapp import send_message_with_template_fallback

logger = logging.getLogger(__name__)

PACIFIC = ZoneInfo("America/Los_Angeles")
DAILY_CAP = 8
BATCH_WINDOW_MINUTES = 5
QUIET_HOURS_START = 7   # 7:00 AM Pacific
QUIET_HOURS_END = 20    # 8:30 PM Pacific (last scan at 8:15 PM, enforce 20:30 cutoff)
QUIET_HOURS_END_MINUTE = 30

# Keywords indicating a virtual/remote event (no departure needed)
VIRTUAL_KEYWORDS = {
    "call", "virtual", "remote", "online", "zoom", "meet", "teams", "webinar",
}


# ---------------------------------------------------------------------------
# T006: Virtual event detection
# ---------------------------------------------------------------------------

def is_virtual_event(event: dict) -> bool:
    """Determine if a calendar event is virtual (no departure needed).

    Returns True if the event:
    - Has conferenceData (Zoom/Meet/Teams link)
    - Contains virtual keywords in title or description
    - Is an all-day event (no specific departure time)
    - Was created by the family-meeting-assistant
    """
    # All-day events have no specific departure time
    if "date" in event.get("start", {}) and "dateTime" not in event.get("start", {}):
        return True

    # Assistant-created events (calendar blocks) don't need departure nudges
    ext_props = event.get("extendedProperties", {}).get("private", {})
    if ext_props.get("createdBy") == CREATED_BY_TAG:
        return True

    # Conference data present (Zoom, Meet, Teams link)
    if event.get("conferenceData"):
        return True

    # Keyword matching in title and description
    title = (event.get("summary") or "").lower()
    description = (event.get("description") or "").lower()
    combined = f"{title} {description}"
    for keyword in VIRTUAL_KEYWORDS:
        if keyword in combined:
            return True

    return False


# ---------------------------------------------------------------------------
# T007: Scan upcoming departures
# ---------------------------------------------------------------------------

def scan_upcoming_departures(hours_ahead: int = 2) -> int:
    """Scan Erin's and family calendars for upcoming events needing departure.

    Creates departure nudge records in the Nudge Queue for events that:
    - Are within the next `hours_ahead` hours
    - Are not virtual events
    - Don't already have a nudge in the queue

    Returns the number of new departure nudges created.
    """
    now = datetime.now(tz=PACIFIC)
    cutoff = now + timedelta(hours=hours_ahead)
    today = now.date()

    events = get_events_for_date_raw(today, calendar_names=["erin", "family"])
    created = 0

    for event in events:
        event_id = event.get("id", "")
        if not event_id:
            continue

        # Skip virtual/all-day/assistant-created events
        if is_virtual_event(event):
            continue

        # Parse event start time
        start_str = event["start"].get("dateTime")
        if not start_str:
            continue
        event_start = datetime.fromisoformat(start_str)
        if event_start.tzinfo is None:
            event_start = event_start.replace(tzinfo=PACIFIC)

        # Only process events within the lookahead window
        if event_start > cutoff or event_start < now - timedelta(minutes=5):
            continue

        # Skip if nudge already exists for this event
        existing = query_nudges_by_event_id(event_id)
        if existing:
            continue

        # Calculate nudge time: 30 min before, or immediate if <15 min away
        time_until = (event_start - now).total_seconds() / 60
        if time_until <= 15:
            scheduled_time = now
        else:
            scheduled_time = event_start - timedelta(minutes=30)

        summary = event.get("summary", "Untitled event")
        source = event.get("_calendar_source", "")
        time_str = event_start.strftime("%-I:%M %p")

        message = f"Time to get ready! {summary} at {time_str}"
        if time_until <= 15:
            message = f"Heads up — {summary} starts at {time_str} (leaving soon!)"

        context = json.dumps({
            "event_title": summary,
            "event_start": event_start.isoformat(),
            "calendar": source,
        })

        create_nudge(
            summary=f"Departure: {summary}",
            nudge_type="departure",
            scheduled_time=scheduled_time.isoformat(),
            event_id=event_id,
            message=message,
            context=context,
        )
        created += 1
        logger.info("Created departure nudge for '%s' at %s", summary, time_str)

    return created


# ---------------------------------------------------------------------------
# T008: Process pending nudges
# ---------------------------------------------------------------------------

async def process_pending_nudges() -> dict:
    """Send all due pending nudges via WhatsApp, respecting daily cap and batching.

    Returns dict with: nudges_sent, nudges_batched, daily_count, errors.
    """
    now = datetime.now(tz=PACIFIC)

    # Enforce quiet hours (7:00 AM - 8:30 PM Pacific)
    current_hour = now.hour
    current_minute = now.minute
    if current_hour < QUIET_HOURS_START or (
        current_hour > QUIET_HOURS_END
        or (current_hour == QUIET_HOURS_END and current_minute >= QUIET_HOURS_END_MINUTE)
    ):
        logger.info("Outside quiet hours (%02d:%02d) — skipping nudge delivery", current_hour, current_minute)
        return {
            "nudges_sent": 0,
            "nudges_batched": 0,
            "daily_count": count_sent_today(),
            "errors": [],
        }

    all_pending = query_pending_nudges(due_before=now.isoformat())
    # Filter out quiet_day markers — they're not real nudges to send
    pending = [n for n in all_pending if n.get("nudge_type") != "quiet_day"]
    if not pending:
        return {
            "nudges_sent": 0,
            "nudges_batched": 0,
            "daily_count": count_sent_today(),
            "errors": [],
        }

    daily_count = count_sent_today()
    errors: list[str] = []
    sent = 0
    batched = 0

    # Group nudges within BATCH_WINDOW_MINUTES into batches
    batches: list[list[dict]] = []
    current_batch: list[dict] = []

    for nudge in pending:
        if not current_batch:
            current_batch.append(nudge)
            continue

        # Check if this nudge is within the batch window of the first nudge
        first_time = current_batch[0].get("scheduled_time", "")
        this_time = nudge.get("scheduled_time", "")
        if first_time and this_time:
            try:
                t1 = datetime.fromisoformat(first_time)
                t2 = datetime.fromisoformat(this_time)
                if abs((t2 - t1).total_seconds()) <= BATCH_WINDOW_MINUTES * 60:
                    current_batch.append(nudge)
                    continue
            except (ValueError, TypeError):
                pass

        batches.append(current_batch)
        current_batch = [nudge]

    if current_batch:
        batches.append(current_batch)

    # Send each batch
    for batch in batches:
        if daily_count >= DAILY_CAP:
            logger.warning("Daily cap reached (%d/%d) — stopping", daily_count, DAILY_CAP)
            break

        # Format message (single or batched)
        if len(batch) == 1:
            message = batch[0].get("message") or batch[0].get("summary", "Nudge reminder")
        else:
            lines = []
            for n in batch:
                lines.append(f"• {n.get('message') or n.get('summary', 'Reminder')}")
            message = "\n".join(lines)

        # Send via WhatsApp
        try:
            await send_message_with_template_fallback(ERIN_PHONE, message)
            for n in batch:
                update_nudge_status(n["id"], "Sent")
                sent += 1
            if len(batch) > 1:
                batched += 1
            daily_count += 1
        except Exception as e:
            logger.error("Failed to send nudge batch: %s", e)
            errors.append(str(e))

    return {
        "nudges_sent": sent,
        "nudges_batched": batched,
        "daily_count": daily_count,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# T009: Quiet day
# ---------------------------------------------------------------------------

def set_quiet_day() -> str:
    """Activate quiet day — suppress all proactive nudges for the rest of today.

    Creates a quiet_day marker and cancels all pending non-laundry nudges.
    """
    now = datetime.now(tz=PACIFIC)
    today_str = now.date().isoformat()

    # Check if already active
    if check_quiet_day():
        return "Quiet day is already active. No proactive nudges will be sent today."

    # Create quiet day marker (use noon Pacific to avoid date boundary issues)
    create_nudge(
        summary="Quiet day activated",
        nudge_type="quiet_day",
        scheduled_time=f"{today_str}T12:00:00-08:00",
        message="Quiet day — no proactive nudges today.",
    )

    # Cancel all pending nudges for today (except laundry — user-initiated)
    pending = query_pending_nudges(due_before=f"{today_str}T23:59:59")
    cancelled = 0
    for nudge in pending:
        nudge_type = nudge.get("nudge_type", "")
        if nudge_type.startswith("laundry"):
            continue
        if nudge_type == "quiet_day":
            continue
        update_nudge_status(nudge["id"], "Cancelled")
        cancelled += 1

    logger.info("Quiet day activated — cancelled %d pending nudges", cancelled)
    return (
        f"Got it — quiet day activated. I cancelled {cancelled} pending nudge(s). "
        "No proactive messages for the rest of today. "
        "I'll still respond if you message me!"
    )


# ---------------------------------------------------------------------------
# Snooze/dismiss helpers (called from assistant tool loop)
# ---------------------------------------------------------------------------

def snooze_nudge(nudge_id: str, minutes: int = 10) -> str:
    """Snooze a nudge — mark original as Snoozed and create new one +N minutes."""
    now = datetime.now(tz=PACIFIC)
    new_time = now + timedelta(minutes=minutes)

    # Get original nudge info via query
    update_nudge_status(nudge_id, "Snoozed")

    # Create a snoozed follow-up nudge
    create_nudge(
        summary="Snoozed reminder",
        nudge_type="departure",
        scheduled_time=new_time.isoformat(),
        message=f"Snoozed reminder — time to head out! (snoozed {minutes} min)",
    )

    return f"Snoozed for {minutes} minutes. I'll remind you again at {new_time.strftime('%-I:%M %p')}."


def dismiss_nudge(nudge_id: str) -> str:
    """Dismiss a nudge — mark as Dismissed, no follow-up."""
    update_nudge_status(nudge_id, "Dismissed")
    return "Dismissed. I won't remind you about this one again."
