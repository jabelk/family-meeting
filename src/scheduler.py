"""In-app scheduler — replaces n8n for Railway deployment.

Uses APScheduler AsyncIOScheduler with CronTrigger to call endpoint business
logic directly (no HTTP round-trip). Loads job definitions from
data/schedules.json.

Hard constraint: single uvicorn worker only (multi-worker would duplicate jobs).
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import FAMILY_CONFIG

logger = logging.getLogger(__name__)

_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
_SCHEDULES_PATH = _DATA_DIR / "schedules.json"

# Bundled default (outside /app/data volume mount, survives empty volume)
_BUNDLED_SCHEDULES_PATH = Path("/app/defaults/schedules.json")
# Local dev fallback
_LOCAL_SCHEDULES_PATH = Path("data/schedules.json")


def _load_schedules() -> dict:
    """Load schedule config from volume, bundled default, or local dev."""
    if _SCHEDULES_PATH.exists():
        return json.loads(_SCHEDULES_PATH.read_text())
    # First boot: copy bundled default to volume so it persists
    if _BUNDLED_SCHEDULES_PATH.exists():
        logger.info("First boot: copying bundled schedules.json to volume")
        import shutil

        _SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_BUNDLED_SCHEDULES_PATH, _SCHEDULES_PATH)
        return json.loads(_SCHEDULES_PATH.read_text())
    # Local development
    if _LOCAL_SCHEDULES_PATH.exists():
        return json.loads(_LOCAL_SCHEDULES_PATH.read_text())
    logger.error("No schedules.json found at %s or %s", _SCHEDULES_PATH, _BUNDLED_SCHEDULES_PATH)
    return {"timezone": "America/Los_Angeles", "jobs": []}


# ---------------------------------------------------------------------------
# Job handlers — thin wrappers calling the same business logic as app.py
# endpoints, but without FastAPI request/response overhead.
# ---------------------------------------------------------------------------


async def _run_daily_briefing():
    from src.assistant import generate_daily_plan
    from src.config import ERIN_PHONE
    from src.whatsapp import send_message

    reply = generate_daily_plan("erin")
    await send_message(ERIN_PHONE, reply)


async def _run_nudge_scan():
    """Nudge scan — mirrors app.py nudge_scan() endpoint logic."""
    from src.tools.chores import detect_free_windows, suggest_chore
    from src.tools.notion import (
        check_quiet_day,
        create_nudge,
        get_backlog_for_nudge,
        query_nudges_by_type,
        seed_default_chores,
    )
    from src.tools.nudges import process_pending_nudges, scan_upcoming_departures

    if check_quiet_day():
        logger.info("Quiet day active — skipping nudge scan")
        return

    try:
        seed_default_chores()
    except Exception as e:
        logger.warning("Chore seed check failed: %s", e)

    try:
        scan_upcoming_departures()
    except Exception as e:
        logger.error("Departure scan failed: %s", e)

    # Detect free windows and suggest chores
    try:
        _now = datetime.now(tz=ZoneInfo("America/Los_Angeles"))
        windows = detect_free_windows(_now.date())
        for window in windows:
            if window["start"] > _now and window["duration_minutes"] >= 15:
                suggestions = suggest_chore(window["duration_minutes"])
                for suggestion in suggestions:
                    context = json.dumps(
                        {
                            "chore_id": suggestion["id"],
                            "chore_name": suggestion["name"],
                            "duration": suggestion["duration"],
                            "window_start": window["start"].isoformat(),
                            "window_end": window["end"].isoformat(),
                        }
                    )
                    msg = f"Free window coming up! How about: {suggestion['name']} (~{suggestion['duration']} min)?"
                    create_nudge(
                        summary=f"Chore: {suggestion['name']}",
                        nudge_type="chore",
                        scheduled_time=window["start"].isoformat(),
                        message=msg,
                        context=context,
                    )
                break
    except Exception as e:
        logger.error("Chore suggestion failed: %s", e)

    # Surface a backlog item
    try:
        _now = datetime.now(tz=ZoneInfo("America/Los_Angeles"))
        existing_backlog = query_nudges_by_type("backlog", statuses=["Pending", "Sent"])
        backlog = get_backlog_for_nudge() if not existing_backlog else None
        if backlog:
            msg = f"Backlog reminder: {backlog['description']}"
            if backlog["priority"] == "High":
                msg = f"High priority: {backlog['description']}"
            context = json.dumps(
                {
                    "backlog_id": backlog["id"],
                    "description": backlog["description"],
                    "category": backlog["category"],
                }
            )
            create_nudge(
                summary=f"Backlog: {backlog['description'][:50]}",
                nudge_type="backlog",
                scheduled_time=_now.isoformat(),
                message=msg,
                context=context,
            )
    except Exception as e:
        logger.error("Backlog suggestion failed: %s", e)

    try:
        await process_pending_nudges()
    except Exception as e:
        logger.error("Nudge delivery failed: %s", e)


async def _run_budget_scan():
    """Budget scan — mirrors app.py budget_scan() endpoint logic."""
    from src.tools.notion import (
        check_quiet_day,
        create_nudge,
        query_nudges_by_type,
    )
    from src.tools.nudges import process_pending_nudges
    from src.tools.ynab import (
        check_overspend_warnings,
        check_savings_goals,
        check_spending_anomalies,
        check_uncategorized_pileup,
    )

    if check_quiet_day():
        logger.info("Quiet day active — skipping budget scan")
        return

    _now = datetime.now(tz=ZoneInfo("America/Los_Angeles"))
    budget_nudges_created = 0
    MAX_BUDGET_NUDGES = 2

    try:
        warnings = check_overspend_warnings()
        for w in warnings:
            if budget_nudges_created >= MAX_BUDGET_NUDGES:
                break
            existing = query_nudges_by_type("budget", statuses=["Pending", "Sent"])
            if any(w["category_name"] in (n.get("summary") or "") for n in existing):
                continue
            msg = (
                f"Heads up: *{w['category_name']}* is at {w['percent_used']:.0f}% "
                f"(${w['spent']:,.0f} / ${w['budgeted']:,.0f}) with "
                f"{w['days_remaining']} days left this month."
            )
            context = json.dumps(
                {
                    "insight_type": "overspend_warning",
                    "category_name": w["category_name"],
                    "spent": w["spent"],
                    "budgeted": w["budgeted"],
                    "percent_used": w["percent_used"],
                }
            )
            create_nudge(
                summary=f"Overspend: {w['category_name']}",
                nudge_type="budget",
                scheduled_time=_now.isoformat(),
                message=msg,
                context=context,
            )
            budget_nudges_created += 1
    except Exception as e:
        logger.error("Overspend check failed: %s", e)

    try:
        pileup = check_uncategorized_pileup()
        if pileup and budget_nudges_created < MAX_BUDGET_NUDGES:
            existing = query_nudges_by_type("budget", statuses=["Pending", "Sent"])
            if not any("uncategorized" in (n.get("summary") or "").lower() for n in existing):
                msg = (
                    f"You have {pileup['count']} uncategorized transactions "
                    f"totaling ${pileup['total_amount']:,.2f} (oldest: {pileup['oldest_date']}). "
                    f"Want help categorizing them?"
                )
                context = json.dumps(
                    {
                        "insight_type": "uncategorized_pileup",
                        "count": pileup["count"],
                        "total_amount": pileup["total_amount"],
                        "oldest_date": pileup["oldest_date"],
                    }
                )
                create_nudge(
                    summary="Uncategorized transactions pileup",
                    nudge_type="budget",
                    scheduled_time=_now.isoformat(),
                    message=msg,
                    context=context,
                )
                budget_nudges_created += 1
    except Exception as e:
        logger.error("Uncategorized check failed: %s", e)

    if _now.weekday() == 0:  # Monday only
        try:
            anomalies = check_spending_anomalies()
            for a in anomalies:
                if budget_nudges_created >= MAX_BUDGET_NUDGES:
                    break
                msg = (
                    f"Spending alert: *{a['category_name']}* is at "
                    f"${a['current_amount']:,.0f} this month — "
                    f"{a['percent_above']:.0f}% above your 3-month average "
                    f"of ${a['average_amount']:,.0f}."
                )
                context = json.dumps(
                    {
                        "insight_type": "spending_anomaly",
                        "category_name": a["category_name"],
                        "current_month": a["current_amount"],
                        "rolling_average": a["average_amount"],
                        "percent_above": a["percent_above"],
                    }
                )
                create_nudge(
                    summary=f"Anomaly: {a['category_name']}",
                    nudge_type="budget",
                    scheduled_time=_now.isoformat(),
                    message=msg,
                    context=context,
                )
                budget_nudges_created += 1
        except Exception as e:
            logger.error("Anomaly check failed: %s", e)

        try:
            gaps = check_savings_goals()
            for g in gaps:
                if budget_nudges_created >= MAX_BUDGET_NUDGES:
                    break
                msg = (
                    f"Goal check: *{g['category_name']}* is {g['percent_complete']}% funded "
                    f"but should be ~{g['expected_percent']:.0f}% by now. "
                    f"Shortfall: ${g['shortfall']:,.0f}."
                )
                context = json.dumps(
                    {
                        "insight_type": "savings_goal_gap",
                        "goal_name": g["category_name"],
                        "funded": g["funded"],
                        "target": g["goal_target"],
                        "shortfall": g["shortfall"],
                    }
                )
                create_nudge(
                    summary=f"Goal gap: {g['category_name']}",
                    nudge_type="budget",
                    scheduled_time=_now.isoformat(),
                    message=msg,
                    context=context,
                )
                budget_nudges_created += 1
        except Exception as e:
            logger.error("Goal check failed: %s", e)

    try:
        await process_pending_nudges()
    except Exception as e:
        logger.error("Budget nudge delivery failed: %s", e)


async def _run_populate_week():
    from src.assistant import handle_message
    from src.tools.calendar import delete_assistant_events

    now = datetime.now(tz=ZoneInfo("America/Los_Angeles"))
    # Next Monday
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    monday = now.date() + timedelta(days=days_until_monday)
    week_start = monday.isoformat()
    start_iso = datetime.combine(monday, datetime.min.time(), tzinfo=timezone.utc).isoformat()
    end_iso = datetime.combine(monday + timedelta(days=5), datetime.min.time(), tzinfo=timezone.utc).isoformat()
    deleted = delete_assistant_events(start_iso, end_iso, calendar_name="erin")
    logger.info("Deleted %d old assistant events for week of %s", deleted, week_start)

    prompt = (
        f"Generate calendar blocks for the week of {week_start} (Monday through Friday). "
        "Read the routine templates and existing calendar events for each day. "
        f"For each day, adapt the appropriate template (check who has {FAMILY_CONFIG.get('child2_name', 'Child')}) and "
        f"write the time blocks to {FAMILY_CONFIG.get('partner2_name', 'Partner2')}'s Google Calendar. "
        "Don't send a WhatsApp message — just create the calendar events."
    )
    handle_message("system", prompt)


async def _run_meal_plan():
    from src.config import ERIN_PHONE
    from src.tools.proactive import generate_meal_plan, merge_grocery_list
    from src.whatsapp import send_message

    result = generate_meal_plan()
    if not result.get("success"):
        logger.error("Meal plan generation failed: %s", result.get("error"))
        return

    plan = result["plan"]
    grocery = merge_grocery_list(plan)

    lines = ["*\U0001f37d Weekly Dinner Plan*\n"]
    for day in plan:
        complexity = {"easy": "\u26a1", "medium": "\U0001f469\u200d\U0001f373", "involved": "\U0001f525"}.get(
            day.get("complexity", "medium"), "\U0001f469\u200d\U0001f373"
        )
        source = " (saved recipe)" if day.get("source", "general") != "general" else ""
        lines.append(f"*{day['day']}:* {day['meal_name']} {complexity}{source}")
    lines.append("")

    lines.append("*\U0001f6d2 Grocery List*\n")
    for store, items in grocery.get("items_by_store", {}).items():
        lines.append(f"*{store}:*")
        for item in items:
            qty = f" ({item['quantity']})" if item.get("quantity") else ""
            lines.append(f"  \u2022 {item['name']}{qty}")
        lines.append("")
    lines.append("Reply to swap a meal or 'approve and send to AnyList'!")

    await send_message(ERIN_PHONE, "\n".join(lines))


async def _run_amazon_sync():
    from src.config import ERIN_PHONE
    from src.tools import amazon_sync
    from src.whatsapp import send_message

    message = amazon_sync.run_nightly_sync()
    if message:
        await send_message(ERIN_PHONE, message)


async def _run_email_sync():
    from src.tools import email_sync

    email_sync.run_email_sync()


async def _run_budget_health():
    from src.tools import ynab

    ynab.run_budget_health_check()


async def _run_grandma_prompt():
    from src.config import ERIN_PHONE
    from src.whatsapp import send_message

    child2 = FAMILY_CONFIG.get("child2_name", "Child")
    message = (
        f"Hi! Quick question for the week \u2014 what days is grandma taking {child2}? "
        "Just let me know and I'll update the daily plans. \U0001f5d3\ufe0f"
    )
    await send_message(ERIN_PHONE, message)


async def _run_conflict_check():
    from src.config import ERIN_PHONE
    from src.tools.proactive import detect_conflicts
    from src.whatsapp import send_message

    conflicts = detect_conflicts(7)
    if not conflicts:
        logger.info("No conflicts detected")
        return

    lines = ["*\u26a0\ufe0f Calendar Conflicts Detected*\n"]
    for c in conflicts:
        icon = "\U0001f534" if c.get("type") == "hard" else "\U0001f7e1"
        lines.append(f"{icon} *{c.get('day', '')}*: {c.get('event', '')}")
        lines.append(f"  \u2194 Conflicts with: {c.get('conflict_with', '')}")
        lines.append(f"  \U0001f4a1 {c.get('suggestion', '')}")
        lines.append("")
    await send_message(ERIN_PHONE, "\n".join(lines))


async def _run_action_item_reminder():
    from src.config import ERIN_PHONE
    from src.tools.proactive import check_action_item_progress
    from src.whatsapp import send_message

    result = check_action_item_progress()
    if result.get("status") == "all_complete":
        await send_message(ERIN_PHONE, "\u2705 *All caught up!* Every action item for this week is done. Nice work!")
        return
    if result.get("status") == "error":
        logger.error("Action item check failed: %s", result.get("message"))
        return

    lines = ["*\U0001f4cb Mid-Week Check-In*\n"]
    lines.append(f"{result['done']} of {result['total']} items done this week\n")
    for assignee, items in result.get("remaining_by_assignee", {}).items():
        lines.append(f"*{assignee}:*")
        for item in items:
            rolled = " \u26a0\ufe0f _rolled over \u2014 still relevant?_" if item.get("rolled_over") else ""
            status_icon = "\U0001f504" if item["status"] == "In Progress" else "\u2b1c"
            lines.append(f"  {status_icon} {item['title']}{rolled}")
        lines.append("")
    await send_message(ERIN_PHONE, "\n".join(lines))


async def _run_grocery_reorder():
    from src.config import ERIN_PHONE
    from src.tools.proactive import check_reorder_items
    from src.whatsapp import send_message

    result = check_reorder_items()
    if result["total"] == 0:
        return

    lines = ["*\U0001f6d2 Grocery Reorder Suggestions*\n"]
    for store, items in result["items_by_store"].items():
        lines.append(f"*{store}:*")
        for item in items:
            lines.append(f"  \u2022 {item['name']} ({item['days_overdue']}d overdue)")
        lines.append("")
    lines.append("Reply with which items to add to AnyList, or 'add all'!")
    await send_message(ERIN_PHONE, "\n".join(lines))


async def _run_grocery_confirmation():
    from src.config import ERIN_PHONE
    from src.tools.proactive import check_grocery_confirmation
    from src.whatsapp import send_message

    result = check_grocery_confirmation()
    if result["status"] == "needs_reminder":
        await send_message(ERIN_PHONE, result["message"])


async def _run_budget_summary():
    from src.config import ERIN_PHONE
    from src.tools.proactive import format_budget_summary
    from src.whatsapp import send_message_with_template_fallback

    result = format_budget_summary()
    if result.get("status") != "ok":
        logger.error("Budget summary failed: %s", result.get("message"))
        return
    await send_message_with_template_fallback(
        ERIN_PHONE,
        result["message"],
        template_name="budget_summary",
    )


async def _run_update_check():
    from src.tools.updater import check_for_updates, generate_changelog_summary, notify_update_available

    result = check_for_updates()
    if not result.get("update_available"):
        if result.get("error"):
            logger.warning("Update check failed: %s", result["error"])
        return

    summary = generate_changelog_summary(result["raw_log"], result["commit_count"])
    await notify_update_available(result["upstream_sha"], summary, result["commit_count"])


# ---------------------------------------------------------------------------
# Endpoint path → handler mapping
# ---------------------------------------------------------------------------

ENDPOINT_HANDLERS: dict[str, callable] = {
    "briefing/daily": _run_daily_briefing,
    "nudges/scan": _run_nudge_scan,
    "budget/scan": _run_budget_scan,
    "calendar/populate-week": _run_populate_week,
    "meals/plan-week": _run_meal_plan,
    "amazon/sync": _run_amazon_sync,
    "email/sync": _run_email_sync,
    "budget/health-check": _run_budget_health,
    "prompt/grandma-schedule": _run_grandma_prompt,
    "calendar/conflict-check": _run_conflict_check,
    "reminders/action-items": _run_action_item_reminder,
    "grocery/reorder-check": _run_grocery_reorder,
    "reminders/grocery-confirmation": _run_grocery_confirmation,
    "budget/weekly-summary": _run_budget_summary,
    "updates/check": _run_update_check,
}


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance from schedules.json."""
    config = _load_schedules()
    tz = ZoneInfo(config.get("timezone", "America/Los_Angeles"))
    scheduler = AsyncIOScheduler(timezone=tz)

    enabled_count = 0
    for job in config.get("jobs", []):
        if not job.get("enabled", True):
            logger.info("Skipping disabled job: %s", job["id"])
            continue

        handler = ENDPOINT_HANDLERS.get(job["endpoint"])
        if not handler:
            logger.warning("No handler for endpoint %s (job: %s) — skipping", job["endpoint"], job["id"])
            continue

        trigger = CronTrigger(timezone=tz, **job["schedule"])
        scheduler.add_job(
            _run_job,
            trigger=trigger,
            args=[job["id"], handler],
            id=job["id"],
            name=job["id"],
            replace_existing=True,
        )
        enabled_count += 1

    logger.info("Scheduler configured: %d jobs loaded (timezone: %s)", enabled_count, tz)
    return scheduler


async def _run_job(job_id: str, handler: callable):
    """Wrapper that logs job execution timing and catches errors."""
    start = time.time()
    logger.info("Running scheduled job: %s", job_id)
    try:
        await handler()
        elapsed = time.time() - start
        logger.info("Scheduled job complete: %s (%.1fs)", job_id, elapsed)
    except Exception:
        elapsed = time.time() - start
        logger.exception("Scheduled job failed: %s (%.1fs)", job_id, elapsed)
