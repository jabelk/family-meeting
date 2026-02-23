"""Laundry workflow management — timed washer/dryer reminders with calendar awareness."""

import json
import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.tools.calendar import get_events_for_date_raw
from src.tools.notion import (
    create_nudge,
    query_nudges_by_type,
    update_nudge_status,
)

logger = logging.getLogger(__name__)

PACIFIC = ZoneInfo("America/Los_Angeles")

# Laundry nudge types for session grouping
LAUNDRY_TYPES = ["laundry_washer", "laundry_dryer", "laundry_followup"]


def _get_active_session() -> tuple[str | None, list[dict]]:
    """Find the active laundry session (Pending or Sent laundry nudges).

    Returns (session_id, nudges) where session_id is from the Event ID field.
    """
    all_nudges: list[dict] = []
    for ltype in LAUNDRY_TYPES:
        all_nudges.extend(
            query_nudges_by_type(ltype, statuses=["Pending", "Sent"])
        )

    if not all_nudges:
        return None, []

    # Group by session_id (stored in Event ID field)
    session_id = all_nudges[0].get("event_id", "")
    session_nudges = [n for n in all_nudges if n.get("event_id") == session_id]
    return session_id, session_nudges


def _check_calendar_conflicts(target_time: datetime) -> str:
    """Check if a calendar event conflicts with the target time.

    Returns a warning string if there's a conflict, empty string otherwise.
    """
    today = target_time.date()
    events = get_events_for_date_raw(today, calendar_names=["erin", "family"])

    for event in events:
        start_str = event["start"].get("dateTime")
        if not start_str:
            continue
        event_start = datetime.fromisoformat(start_str)
        if event_start.tzinfo is None:
            event_start = event_start.replace(tzinfo=PACIFIC)

        end_str = event.get("end", {}).get("dateTime")
        if end_str:
            event_end = datetime.fromisoformat(end_str)
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=PACIFIC)
        else:
            event_end = event_start + timedelta(hours=1)

        # Check if target time falls during the event
        if event_start <= target_time <= event_end:
            summary = event.get("summary", "an event")
            time_str = event_start.strftime("%-I:%M %p")
            return f" Heads up: this overlaps with '{summary}' at {time_str}."

    return ""


# ---------------------------------------------------------------------------
# T013: Start laundry session
# ---------------------------------------------------------------------------

def start_laundry_session(
    washer_minutes: int = 45, dryer_minutes: int = 60
) -> str:
    """Start a new laundry session with timed washer and follow-up nudges.

    Creates:
    - laundry_washer nudge: now + washer_minutes
    - laundry_followup nudge: now + 2h45m (in case she forgets to move to dryer)

    Stores dryer_minutes in context JSON for advance_laundry().
    """
    now = datetime.now(tz=PACIFIC)

    # Cancel any existing active laundry session
    existing_id, existing_nudges = _get_active_session()
    if existing_nudges:
        for nudge in existing_nudges:
            if nudge.get("status") == "Pending":
                update_nudge_status(nudge["id"], "Cancelled")
        logger.info("Cancelled previous laundry session: %s", existing_id)

    session_id = str(uuid.uuid4())[:8]
    washer_done = now + timedelta(minutes=washer_minutes)
    followup_time = now + timedelta(hours=2, minutes=45)

    context = json.dumps({
        "session_id": session_id,
        "dryer_minutes": dryer_minutes,
        "started_at": now.isoformat(),
    })

    # Check for calendar conflicts during expected dryer window
    dryer_done_estimate = washer_done + timedelta(minutes=dryer_minutes)
    conflict_warning = _check_calendar_conflicts(dryer_done_estimate)

    # Create washer-done nudge
    create_nudge(
        summary="Washer done — time to move to dryer!",
        nudge_type="laundry_washer",
        scheduled_time=washer_done.isoformat(),
        event_id=session_id,
        message=f"Washer should be done! Time to move clothes to the dryer.",
        context=context,
    )

    # Create follow-up nudge (in case she forgets)
    create_nudge(
        summary="Laundry still in washer?",
        nudge_type="laundry_followup",
        scheduled_time=followup_time.isoformat(),
        event_id=session_id,
        message="Hey — did you move the laundry to the dryer? It's been a while!",
        context=context,
    )

    washer_time_str = washer_done.strftime("%-I:%M %p")
    dryer_est_str = dryer_done_estimate.strftime("%-I:%M %p")

    response = (
        f"Laundry started! Here's the plan:\n"
        f"• Washer reminder at {washer_time_str} (~{washer_minutes} min)\n"
        f"• Dryer should be done ~{dryer_est_str}\n"
        f"Just tell me when you move it to the dryer!"
    )
    if conflict_warning:
        response += f"\n{conflict_warning}"

    logger.info("Laundry session %s started (washer: %dm, dryer: %dm)", session_id, washer_minutes, dryer_minutes)
    return response


# ---------------------------------------------------------------------------
# T014: Advance laundry (moved to dryer)
# ---------------------------------------------------------------------------

def advance_laundry() -> str:
    """Advance laundry session to dryer phase.

    Creates a laundry_dryer nudge and cancels the follow-up nudge.
    """
    now = datetime.now(tz=PACIFIC)
    session_id, session_nudges = _get_active_session()

    if not session_nudges:
        return "I don't see an active laundry session. Did you already start one?"

    # Get dryer minutes from session context
    dryer_minutes = 60
    for nudge in session_nudges:
        ctx = nudge.get("context", "")
        if ctx:
            try:
                ctx_data = json.loads(ctx)
                dryer_minutes = ctx_data.get("dryer_minutes", 60)
                break
            except (json.JSONDecodeError, TypeError):
                pass

    dryer_done = now + timedelta(minutes=dryer_minutes)

    # Cancel pending follow-up nudge
    for nudge in session_nudges:
        if nudge.get("nudge_type") == "laundry_followup" and nudge.get("status") == "Pending":
            update_nudge_status(nudge["id"], "Cancelled")

    # Mark washer nudge as Done (if still pending/sent)
    for nudge in session_nudges:
        if nudge.get("nudge_type") == "laundry_washer" and nudge.get("status") in ("Pending", "Sent"):
            update_nudge_status(nudge["id"], "Done")

    # Check for calendar conflicts with dryer completion
    conflict_warning = _check_calendar_conflicts(dryer_done)

    context = json.dumps({
        "session_id": session_id,
        "dryer_minutes": dryer_minutes,
        "phase": "drying",
        "moved_at": now.isoformat(),
    })

    # Create dryer-done nudge
    create_nudge(
        summary="Dryer done — clothes are ready!",
        nudge_type="laundry_dryer",
        scheduled_time=dryer_done.isoformat(),
        event_id=session_id,
        message="Dryer should be done! Time to fold and put away.",
        context=context,
    )

    dryer_time_str = dryer_done.strftime("%-I:%M %p")
    response = f"Moved to dryer! I'll remind you when it's done at ~{dryer_time_str} (~{dryer_minutes} min)."
    if conflict_warning:
        response += f"\n{conflict_warning}"

    logger.info("Laundry session %s advanced to dryer (done at %s)", session_id, dryer_time_str)
    return response


# ---------------------------------------------------------------------------
# T015: Cancel laundry
# ---------------------------------------------------------------------------

def cancel_laundry() -> str:
    """Cancel the active laundry session and all its pending nudges."""
    session_id, session_nudges = _get_active_session()

    if not session_nudges:
        return "No active laundry session to cancel."

    cancelled = 0
    for nudge in session_nudges:
        if nudge.get("status") == "Pending":
            update_nudge_status(nudge["id"], "Cancelled")
            cancelled += 1

    logger.info("Laundry session %s cancelled (%d nudges)", session_id, cancelled)
    return f"Laundry session cancelled. Removed {cancelled} pending reminder(s)."
