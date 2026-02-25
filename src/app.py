"""FastAPI app — WhatsApp webhook + n8n automation endpoints."""

import base64
import hashlib
import hmac
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, Response, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel
from src.config import (
    WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET,
    PHONE_TO_NAME, ERIN_PHONE, N8N_WEBHOOK_SECRET,
)
from src.whatsapp import extract_message, send_message, download_media
from src.assistant import handle_message, generate_daily_plan, generate_meeting_prep
from src.tools.calendar import delete_assistant_events, batch_create_events, get_events_for_date
from src.tools.notion import get_routine_templates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Family Meeting Assistant")


# ---------------------------------------------------------------------------
# Webhook signature verification (security)
# ---------------------------------------------------------------------------

def _verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify X-Hub-Signature-256 from Meta using HMAC-SHA256."""
    if not WHATSAPP_APP_SECRET:
        logger.warning("WHATSAPP_APP_SECRET not set — skipping signature verification")
        return True  # Allow during initial setup, but log warning
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(
        WHATSAPP_APP_SECRET.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


# ---------------------------------------------------------------------------
# Per-phone rate limiting (security)
# ---------------------------------------------------------------------------

RATE_LIMIT_MAX = 5          # max messages per window
RATE_LIMIT_WINDOW = 60.0    # window in seconds

_rate_limit_log: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(phone: str) -> bool:
    """Return True if the phone is within rate limits, False if exceeded."""
    now = time.time()
    # Prune old entries
    _rate_limit_log[phone] = [
        t for t in _rate_limit_log[phone] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(_rate_limit_log[phone]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_log[phone].append(now)
    return True


# ---------------------------------------------------------------------------
# Auth dependency for n8n endpoints (T015)
# ---------------------------------------------------------------------------

async def verify_n8n_auth(x_n8n_auth: str = Header(None)):
    """Verify X-N8N-Auth header for /api/v1/* endpoints."""
    if not N8N_WEBHOOK_SECRET:
        logger.error("N8N_WEBHOOK_SECRET not configured — rejecting request")
        raise HTTPException(status_code=503, detail="n8n authentication not configured")
    if x_n8n_auth != N8N_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing X-N8N-Auth header")


# ---------------------------------------------------------------------------
# Request models for n8n endpoints
# ---------------------------------------------------------------------------

class DailyBriefingRequest(BaseModel):
    target: str = "erin"

class PopulateWeekRequest(BaseModel):
    week_start: str  # YYYY-MM-DD (Monday)

class GrandmaPromptRequest(BaseModel):
    pass


# ---------------------------------------------------------------------------
# WhatsApp webhook
# ---------------------------------------------------------------------------

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Handle Meta webhook verification challenge."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Webhook verification failed: invalid token")
    return Response(content="Forbidden", status_code=403)


@app.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming WhatsApp messages from Meta webhook."""
    # Verify webhook signature from Meta
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_webhook_signature(body, signature):
        logger.warning("Invalid webhook signature — rejecting request")
        return Response(status_code=403, content="Invalid signature")

    payload = await request.json()
    parsed = extract_message(payload)

    if not parsed:
        return {"status": "ok"}

    phone = parsed["phone"]
    sender_name = parsed["name"]

    # Reject unrecognized phone numbers
    if phone not in PHONE_TO_NAME:
        logger.warning("Message from unrecognized number: %s (%s)", phone, sender_name)
        return {"status": "ok"}

    # Per-phone rate limiting
    if not _check_rate_limit(phone):
        logger.warning("Rate limit exceeded for %s (%s)", PHONE_TO_NAME[phone], phone)
        return {"status": "ok"}  # Silently drop — don't waste API calls replying

    if parsed["type"] == "image":
        logger.info("Image from %s (caption: %s)", PHONE_TO_NAME[phone], parsed["text"][:100])
        background_tasks.add_task(_process_image_and_reply, phone, parsed)
    else:
        logger.info("Message from %s: %s", PHONE_TO_NAME[phone], parsed["text"][:100])
        background_tasks.add_task(_process_and_reply, phone, parsed["text"])

    return {"status": "ok"}


async def _process_and_reply(phone: str, text: str):
    """Process a text message through Claude and send the reply via WhatsApp."""
    start = time.time()
    try:
        reply = handle_message(phone, text)
        elapsed = time.time() - start
        logger.info("Response generated in %.1fs (%d chars)", elapsed, len(reply))
        await send_message(phone, reply)
    except Exception:
        logger.exception("Error processing message from %s", phone)
        await send_message(phone, "Sorry, something went wrong. Please try again.")


async def _process_image_and_reply(phone: str, parsed: dict):
    """Process an image message: download media, encode, and pass to Claude with the image."""
    start = time.time()
    try:
        image_bytes, mime_type = await download_media(parsed["media_id"])
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        caption = parsed.get("text", "")

        reply = handle_message(
            phone,
            caption or "I sent you a photo.",
            image_data={"base64": image_b64, "mime_type": mime_type},
        )
        elapsed = time.time() - start
        logger.info("Image response generated in %.1fs (%d chars)", elapsed, len(reply))
        await send_message(phone, reply)
    except Exception:
        logger.exception("Error processing image from %s", phone)
        await send_message(phone, "Sorry, I couldn't process that image. Please try again.")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# n8n automation endpoints (T021-T023)
# ---------------------------------------------------------------------------

@app.post("/api/v1/briefing/daily", dependencies=[Depends(verify_n8n_auth)])
async def daily_briefing(req: DailyBriefingRequest, background_tasks: BackgroundTasks):
    """Generate and send daily briefing via WhatsApp.

    Called by n8n cron at 7am M-F. Constructs a daily plan through Claude,
    which writes calendar blocks and formats the WhatsApp message.
    """
    target = req.target.lower()
    logger.info("Daily briefing triggered for %s", target)

    async def _run():
        try:
            reply = generate_daily_plan(target)
            await send_message(ERIN_PHONE, reply)
            logger.info("Daily briefing sent to %s (%d chars)", target, len(reply))
        except Exception:
            logger.exception("Daily briefing failed for %s", target)

    background_tasks.add_task(_run)
    return {"status": "sent", "target": target}


@app.post("/api/v1/meetings/prep-agenda", dependencies=[Depends(verify_n8n_auth)])
async def meeting_prep_agenda(background_tasks: BackgroundTasks):
    """Generate and send weekly meeting prep agenda via WhatsApp.

    Called by n8n cron Saturday 5pm, or ad-hoc. Gathers cross-domain data
    and synthesizes a scannable family meeting agenda.
    """
    logger.info("Meeting prep agenda triggered")

    async def _run():
        try:
            agenda = generate_meeting_prep()
            await send_message(ERIN_PHONE, agenda)
            logger.info("Meeting prep sent (%d chars)", len(agenda))
        except Exception:
            logger.exception("Meeting prep failed")

    background_tasks.add_task(_run)
    return {"status": "sent"}


@app.post("/api/v1/calendar/populate-week", dependencies=[Depends(verify_n8n_auth)])
async def populate_week(req: PopulateWeekRequest):
    """Delete assistant-created events for the week and repopulate from routine templates.

    Called by n8n cron on Sunday evening. Deletes old assistant events,
    then creates time blocks for Mon-Fri based on routine templates.
    """
    try:
        week_start = datetime.strptime(req.week_start, "%Y-%m-%d")
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}

    week_end = week_start + timedelta(days=5)  # Mon-Fri

    logger.info("Populating week starting %s", req.week_start)

    # Delete old assistant-created events for the week
    start_iso = week_start.replace(tzinfo=timezone.utc).isoformat()
    end_iso = week_end.replace(tzinfo=timezone.utc).isoformat()
    deleted = delete_assistant_events(start_iso, end_iso, calendar_name="erin")
    logger.info("Deleted %d old assistant events", deleted)

    # Use Claude to generate the week's plan from routine templates
    prompt = (
        f"Generate calendar blocks for the week of {req.week_start} (Monday through Friday). "
        "Read the routine templates and existing calendar events for each day. "
        "For each day, adapt the appropriate template (check who has Zoey) and "
        "write the time blocks to Erin's Google Calendar. "
        "Don't send a WhatsApp message — just create the calendar events."
    )
    reply = handle_message("system", prompt)
    logger.info("Week population complete: %s", reply[:200])

    return {"status": "populated", "deleted": deleted, "message": reply[:500]}


@app.post("/api/v1/prompt/grandma-schedule", dependencies=[Depends(verify_n8n_auth)])
async def grandma_schedule_prompt(background_tasks: BackgroundTasks):
    """Send a WhatsApp message asking about grandma's schedule for the week.

    Called by n8n cron on Monday morning. The reply comes back through the
    regular webhook flow and Claude processes it naturally.
    """
    logger.info("Grandma schedule prompt triggered")
    message = (
        "Hi! Quick question for the week — what days is grandma taking Zoey? "
        "Just let me know and I'll update the daily plans. 🗓️"
    )

    async def _send():
        try:
            await send_message(ERIN_PHONE, message)
            logger.info("Grandma schedule prompt sent")
        except Exception:
            logger.exception("Failed to send grandma schedule prompt")

    background_tasks.add_task(_send)
    return {"status": "prompted"}


# ---------------------------------------------------------------------------
# Feature 003: Nudge Scanner (T010)
# ---------------------------------------------------------------------------

@app.post("/api/v1/nudges/scan", dependencies=[Depends(verify_n8n_auth)])
async def nudge_scan():
    """Scan calendar for departure events, process pending nudges.

    Called by n8n every 15 minutes (7am-8:30pm Pacific).
    Creates departure nudges for upcoming events, then delivers all due nudges.
    """
    from src.tools.nudges import scan_upcoming_departures, process_pending_nudges
    from src.tools.notion import check_quiet_day, count_sent_today, seed_default_chores
    from src.tools.notion import create_nudge, get_backlog_for_nudge
    from src.tools.chores import detect_free_windows, suggest_chore

    logger.info("Nudge scan triggered")

    result = {
        "departures_created": 0,
        "chores_suggested": 0,
        "nudges_sent": 0,
        "nudges_batched": 0,
        "daily_count": count_sent_today(),
        "daily_cap": 8,
        "quiet_day": False,
        "errors": [],
    }

    # Check quiet day first
    if check_quiet_day():
        result["quiet_day"] = True
        logger.info("Quiet day active — skipping all nudge processing")
        return result

    # Seed default chores on first run if DB is empty
    try:
        seed_default_chores()
    except Exception as e:
        logger.warning("Chore seed check failed: %s", e)

    # Scan for upcoming departure events
    try:
        result["departures_created"] = scan_upcoming_departures()
    except Exception as e:
        logger.error("Departure scan failed: %s", e)
        result["errors"].append(f"departure_scan: {e}")

    # Detect free windows and suggest chores
    try:
        import json as _json
        from datetime import datetime as _dt
        from zoneinfo import ZoneInfo as _ZI
        _now = _dt.now(tz=_ZI("America/Los_Angeles"))
        windows = detect_free_windows(_now.date())

        # Find the next upcoming free window (starts after now)
        for window in windows:
            if window["start"] > _now and window["duration_minutes"] >= 15:
                suggestions = suggest_chore(window["duration_minutes"])
                for suggestion in suggestions:
                    context = _json.dumps({
                        "chore_id": suggestion["id"],
                        "chore_name": suggestion["name"],
                        "duration": suggestion["duration"],
                        "window_start": window["start"].isoformat(),
                        "window_end": window["end"].isoformat(),
                    })
                    msg = (
                        f"Free window coming up! How about: {suggestion['name']} "
                        f"(~{suggestion['duration']} min)?"
                    )
                    create_nudge(
                        summary=f"Chore: {suggestion['name']}",
                        nudge_type="chore",
                        scheduled_time=window["start"].isoformat(),
                        message=msg,
                        context=context,
                    )
                    result["chores_suggested"] += 1
                break  # Only suggest for the next upcoming window
    except Exception as e:
        logger.error("Chore suggestion failed: %s", e)
        result["errors"].append(f"chore_suggestion: {e}")

    # Surface a backlog item alongside chore suggestions (max 1 per day)
    try:
        from src.tools.notion import query_nudges_by_type
        existing_backlog = query_nudges_by_type("backlog", statuses=["Pending", "Sent"])
        backlog = get_backlog_for_nudge() if not existing_backlog else None
        if backlog:
            msg = f"Backlog reminder: {backlog['description']}"
            if backlog["priority"] == "High":
                msg = f"High priority: {backlog['description']}"
            context = _json.dumps({
                "backlog_id": backlog["id"],
                "description": backlog["description"],
                "category": backlog["category"],
            })
            create_nudge(
                summary=f"Backlog: {backlog['description'][:50]}",
                nudge_type="backlog",
                scheduled_time=_now.isoformat(),
                message=msg,
                context=context,
            )
            result["backlog_surfaced"] = 1
            logger.info("Surfaced backlog item: %s", backlog["description"][:60])
    except Exception as e:
        logger.error("Backlog suggestion failed: %s", e)
        result["errors"].append(f"backlog_suggestion: {e}")

    # Process and deliver pending nudges
    try:
        delivery = await process_pending_nudges()
        result["nudges_sent"] = delivery["nudges_sent"]
        result["nudges_batched"] = delivery["nudges_batched"]
        result["daily_count"] = delivery["daily_count"]
        result["errors"].extend(delivery["errors"])
    except Exception as e:
        logger.error("Nudge delivery failed: %s", e)
        result["errors"].append(f"nudge_delivery: {e}")

    logger.info(
        "Nudge scan complete: %d departures, %d sent, %d/%d daily",
        result["departures_created"],
        result["nudges_sent"],
        result["daily_count"],
        result["daily_cap"],
    )
    return result


# ---------------------------------------------------------------------------
# Budget Scan (Feature 004 — YNAB Smart Budget)
# ---------------------------------------------------------------------------

@app.post("/api/v1/budget/scan", dependencies=[Depends(verify_n8n_auth)])
async def budget_scan():
    """Proactive budget insight scanner — overspending, uncategorized, anomalies, goals.

    Called by n8n daily at 9am Pacific.
    """
    from src.tools.nudges import process_pending_nudges
    from src.tools.notion import check_quiet_day, count_sent_today, create_nudge, query_nudges_by_type
    from src.tools.ynab import (
        check_overspend_warnings, check_uncategorized_pileup,
        check_spending_anomalies, check_savings_goals,
    )
    import json as _json
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _ZI

    logger.info("Budget scan triggered")
    _now = _dt.now(tz=_ZI("America/Los_Angeles"))

    result = {
        "insights_created": 0,
        "uncategorized_count": 0,
        "overspend_warnings": 0,
        "anomalies_detected": 0,
        "goal_gaps": 0,
        "nudges_sent": 0,
        "daily_count": count_sent_today(),
        "daily_cap": 8,
        "quiet_day": False,
        "errors": [],
    }

    # Check quiet day first
    if check_quiet_day():
        result["quiet_day"] = True
        logger.info("Quiet day active — skipping budget scan")
        return result

    budget_nudges_created = 0
    MAX_BUDGET_NUDGES = 2  # NFR-002: cap at 2 per scan

    # Daily: overspend warnings
    try:
        warnings = check_overspend_warnings()
        result["overspend_warnings"] = len(warnings)
        for w in warnings:
            if budget_nudges_created >= MAX_BUDGET_NUDGES:
                break
            # Dedup: check if we already sent an overspend nudge for this category today
            existing = query_nudges_by_type("budget", statuses=["Pending", "Sent"])
            already_warned = any(
                w["category_name"] in (n.get("summary") or "")
                for n in existing
            )
            if already_warned:
                continue

            msg = (
                f"Heads up: *{w['category_name']}* is at {w['percent_used']:.0f}% "
                f"(${w['spent']:,.0f} / ${w['budgeted']:,.0f}) with "
                f"{w['days_remaining']} days left this month."
            )
            context = _json.dumps({
                "insight_type": "overspend_warning",
                "category_name": w["category_name"],
                "spent": w["spent"],
                "budgeted": w["budgeted"],
                "percent_used": w["percent_used"],
            })
            create_nudge(
                summary=f"Overspend: {w['category_name']}",
                nudge_type="budget",
                scheduled_time=_now.isoformat(),
                message=msg,
                context=context,
            )
            budget_nudges_created += 1
            result["insights_created"] += 1
    except Exception as e:
        logger.error("Overspend check failed: %s", e)
        result["errors"].append(f"overspend: {e}")

    # Daily: uncategorized pile-up
    try:
        pileup = check_uncategorized_pileup()
        if pileup and budget_nudges_created < MAX_BUDGET_NUDGES:
            result["uncategorized_count"] = pileup["count"]
            # Dedup
            existing = query_nudges_by_type("budget", statuses=["Pending", "Sent"])
            already_nudged = any("uncategorized" in (n.get("summary") or "").lower() for n in existing)
            if not already_nudged:
                msg = (
                    f"You have {pileup['count']} uncategorized transactions "
                    f"totaling ${pileup['total_amount']:,.2f} (oldest: {pileup['oldest_date']}). "
                    f"Want help categorizing them?"
                )
                context = _json.dumps({
                    "insight_type": "uncategorized_pileup",
                    "count": pileup["count"],
                    "total_amount": pileup["total_amount"],
                    "oldest_date": pileup["oldest_date"],
                })
                create_nudge(
                    summary="Uncategorized transactions pileup",
                    nudge_type="budget",
                    scheduled_time=_now.isoformat(),
                    message=msg,
                    context=context,
                )
                budget_nudges_created += 1
                result["insights_created"] += 1
    except Exception as e:
        logger.error("Uncategorized check failed: %s", e)
        result["errors"].append(f"uncategorized: {e}")

    # Weekly (Monday only): spending anomalies
    if _now.weekday() == 0:  # Monday
        try:
            anomalies = check_spending_anomalies()
            result["anomalies_detected"] = len(anomalies)
            for a in anomalies:
                if budget_nudges_created >= MAX_BUDGET_NUDGES:
                    break
                msg = (
                    f"Spending alert: *{a['category_name']}* is at "
                    f"${a['current_amount']:,.0f} this month — "
                    f"{a['percent_above']:.0f}% above your 3-month average "
                    f"of ${a['average_amount']:,.0f}."
                )
                context = _json.dumps({
                    "insight_type": "spending_anomaly",
                    "category_name": a["category_name"],
                    "current_month": a["current_amount"],
                    "rolling_average": a["average_amount"],
                    "percent_above": a["percent_above"],
                })
                create_nudge(
                    summary=f"Anomaly: {a['category_name']}",
                    nudge_type="budget",
                    scheduled_time=_now.isoformat(),
                    message=msg,
                    context=context,
                )
                budget_nudges_created += 1
                result["insights_created"] += 1
        except Exception as e:
            logger.error("Anomaly check failed: %s", e)
            result["errors"].append(f"anomalies: {e}")

        # Weekly: savings goal gaps
        try:
            gaps = check_savings_goals()
            result["goal_gaps"] = len(gaps)
            for g in gaps:
                if budget_nudges_created >= MAX_BUDGET_NUDGES:
                    break
                msg = (
                    f"Goal check: *{g['category_name']}* is {g['percent_complete']}% funded "
                    f"but should be ~{g['expected_percent']:.0f}% by now. "
                    f"Shortfall: ${g['shortfall']:,.0f}."
                )
                context = _json.dumps({
                    "insight_type": "savings_goal_gap",
                    "goal_name": g["category_name"],
                    "funded": g["funded"],
                    "target": g["goal_target"],
                    "shortfall": g["shortfall"],
                })
                create_nudge(
                    summary=f"Goal gap: {g['category_name']}",
                    nudge_type="budget",
                    scheduled_time=_now.isoformat(),
                    message=msg,
                    context=context,
                )
                budget_nudges_created += 1
                result["insights_created"] += 1
        except Exception as e:
            logger.error("Goal check failed: %s", e)
            result["errors"].append(f"goals: {e}")

    # Process and deliver pending nudges
    try:
        delivery = await process_pending_nudges()
        result["nudges_sent"] = delivery["nudges_sent"]
        result["daily_count"] = delivery["daily_count"]
        result["errors"].extend(delivery["errors"])
    except Exception as e:
        logger.error("Budget nudge delivery failed: %s", e)
        result["errors"].append(f"nudge_delivery: {e}")

    logger.info(
        "Budget scan complete: %d insights, %d overspend, %d uncategorized, %d anomalies, %d goal gaps",
        result["insights_created"], result["overspend_warnings"],
        result["uncategorized_count"], result["anomalies_detected"], result["goal_gaps"],
    )
    return result


# ---------------------------------------------------------------------------
# US2: Grocery Reorder (T029-T030)
# ---------------------------------------------------------------------------

@app.post("/api/v1/grocery/reorder-check", dependencies=[Depends(verify_n8n_auth)])
async def reorder_check(background_tasks: BackgroundTasks):
    """Check for grocery items due for reorder and send suggestions via WhatsApp.

    Called by n8n weekly. Groups suggestions by store.
    """
    from src.tools.proactive import check_reorder_items

    logger.info("Grocery reorder check triggered")
    result = check_reorder_items()

    if result["total"] == 0:
        return {"status": "no_items_due"}

    # Format WhatsApp message
    lines = ["*🛒 Grocery Reorder Suggestions*\n"]
    for store, items in result["items_by_store"].items():
        lines.append(f"*{store}:*")
        for item in items:
            lines.append(f"  • {item['name']} ({item['days_overdue']}d overdue)")
        lines.append("")
    lines.append("Reply with which items to add to AnyList, or 'add all'!")

    message = "\n".join(lines)

    async def _send():
        try:
            await send_message(ERIN_PHONE, message)
            logger.info("Reorder suggestions sent (%d items)", result["total"])
        except Exception:
            logger.exception("Failed to send reorder suggestions")

    background_tasks.add_task(_send)
    return {"status": "sent", "total": result["total"]}


@app.post("/api/v1/reminders/grocery-confirmation", dependencies=[Depends(verify_n8n_auth)])
async def grocery_confirmation_reminder(background_tasks: BackgroundTasks):
    """Check for unconfirmed grocery orders and send reminder if needed.

    Called by n8n daily. Sends gentle reminder if items pending 2+ days.
    """
    from src.tools.proactive import check_grocery_confirmation

    logger.info("Grocery confirmation check triggered")
    result = check_grocery_confirmation()

    if result["status"] != "needs_reminder":
        return {"status": result["status"]}

    async def _send():
        try:
            await send_message(ERIN_PHONE, result["message"])
            logger.info("Grocery confirmation reminder sent")
        except Exception:
            logger.exception("Failed to send grocery confirmation reminder")

    background_tasks.add_task(_send)
    return {"status": "reminder_sent", "overdue_count": len(result["overdue_items"])}


# ---------------------------------------------------------------------------
# US3: Meal Planning (T036)
# ---------------------------------------------------------------------------

@app.post("/api/v1/meals/plan-week", dependencies=[Depends(verify_n8n_auth)])
async def plan_week_meals(background_tasks: BackgroundTasks):
    """Generate 6-night dinner plan + merged grocery list and send via WhatsApp.

    Called by n8n Saturday morning. Combines meal plan with reorder suggestions.
    """
    from src.tools.proactive import generate_meal_plan, merge_grocery_list

    logger.info("Weekly meal plan triggered")

    async def _run():
        try:
            result = generate_meal_plan()
            if not result.get("success"):
                logger.error("Meal plan generation failed: %s", result.get("error"))
                return

            plan = result["plan"]
            grocery = merge_grocery_list(plan)

            # Format combined message
            lines = ["*🍽 Weekly Dinner Plan*\n"]
            for day in plan:
                complexity = {"easy": "⚡", "medium": "👩‍🍳", "involved": "🔥"}.get(
                    day.get("complexity", "medium"), "👩‍🍳"
                )
                source = " (saved recipe)" if day.get("source", "general") != "general" else ""
                lines.append(f"*{day['day']}:* {day['meal_name']} {complexity}{source}")
            lines.append("")

            lines.append("*🛒 Grocery List*\n")
            for store, items in grocery.get("items_by_store", {}).items():
                lines.append(f"*{store}:*")
                for item in items:
                    qty = f" ({item['quantity']})" if item.get("quantity") else ""
                    lines.append(f"  • {item['name']}{qty}")
                lines.append("")

            lines.append("Reply to swap a meal or 'approve and send to AnyList'!")
            message = "\n".join(lines)

            await send_message(ERIN_PHONE, message)
            logger.info("Weekly meal plan sent (%d meals, %d grocery items)", len(plan), grocery["total"])
        except Exception:
            logger.exception("Weekly meal plan failed")

    background_tasks.add_task(_run)
    return {"status": "generating"}


# ---------------------------------------------------------------------------
# US5: Conflict Detection (T044-T045)
# ---------------------------------------------------------------------------

@app.post("/api/v1/calendar/conflict-check", dependencies=[Depends(verify_n8n_auth)])
async def conflict_check(background_tasks: BackgroundTasks, days_ahead: int = 7):
    """Detect calendar conflicts and send report via WhatsApp.

    Called by n8n Sunday evening for weekly scan.
    """
    from src.tools.proactive import detect_conflicts

    logger.info("Conflict check triggered (days_ahead=%d)", days_ahead)

    async def _run():
        try:
            conflicts = detect_conflicts(days_ahead)
            if not conflicts:
                logger.info("No conflicts detected")
                return

            lines = ["*⚠️ Calendar Conflicts Detected*\n"]
            for c in conflicts:
                icon = "🔴" if c.get("type") == "hard" else "🟡"
                lines.append(f"{icon} *{c.get('day', '')}*: {c.get('event', '')}")
                lines.append(f"  ↔ Conflicts with: {c.get('conflict_with', '')}")
                lines.append(f"  💡 {c.get('suggestion', '')}")
                lines.append("")

            message = "\n".join(lines)
            await send_message(ERIN_PHONE, message)
            logger.info("Conflict report sent (%d conflicts)", len(conflicts))
        except Exception:
            logger.exception("Conflict check failed")

    background_tasks.add_task(_run)
    return {"status": "checking", "days_ahead": days_ahead}


# ---------------------------------------------------------------------------
# US6: Action Item Reminders (T048)
# ---------------------------------------------------------------------------

@app.post("/api/v1/reminders/action-items", dependencies=[Depends(verify_n8n_auth)])
async def action_item_reminder(background_tasks: BackgroundTasks):
    """Send mid-week action item progress report via WhatsApp.

    Called by n8n Wednesday noon.
    """
    from src.tools.proactive import check_action_item_progress

    logger.info("Action item reminder triggered")

    async def _run():
        try:
            result = check_action_item_progress()

            if result.get("status") == "all_complete":
                await send_message(ERIN_PHONE, "✅ *All caught up!* Every action item for this week is done. Nice work!")
                return

            if result.get("status") == "error":
                logger.error("Action item check failed: %s", result.get("message"))
                return

            lines = [f"*📋 Mid-Week Check-In*\n"]
            lines.append(f"{result['done']} of {result['total']} items done this week\n")

            for assignee, items in result.get("remaining_by_assignee", {}).items():
                lines.append(f"*{assignee}:*")
                for item in items:
                    rolled = " ⚠️ _rolled over — still relevant?_" if item.get("rolled_over") else ""
                    status_icon = "🔄" if item["status"] == "In Progress" else "⬜"
                    lines.append(f"  {status_icon} {item['title']}{rolled}")
                lines.append("")

            message = "\n".join(lines)
            await send_message(ERIN_PHONE, message)
            logger.info("Action item reminder sent")
        except Exception:
            logger.exception("Action item reminder failed")

    background_tasks.add_task(_run)
    return {"status": "checking"}


# ---------------------------------------------------------------------------
# US7: Budget Summary (T051)
# ---------------------------------------------------------------------------

@app.post("/api/v1/budget/weekly-summary", dependencies=[Depends(verify_n8n_auth)])
async def weekly_budget_summary(background_tasks: BackgroundTasks):
    """Send weekly YNAB budget summary via WhatsApp.

    Called by n8n Sunday afternoon. Uses template fallback for 24h window.
    """
    from src.tools.proactive import format_budget_summary
    from src.whatsapp import send_message_with_template_fallback

    logger.info("Budget summary triggered")

    async def _run():
        try:
            result = format_budget_summary()
            if result.get("status") != "ok":
                logger.error("Budget summary failed: %s", result.get("message"))
                return

            await send_message_with_template_fallback(
                ERIN_PHONE,
                result["message"],
                template_name="budget_summary",
            )
            logger.info("Budget summary sent")
        except Exception:
            logger.exception("Budget summary failed")

    background_tasks.add_task(_run)
    return {"status": "generating"}
