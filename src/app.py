"""FastAPI app — WhatsApp webhook + n8n automation endpoints."""

import logging
import time
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, Response, BackgroundTasks
from pydantic import BaseModel
from src.config import WHATSAPP_VERIFY_TOKEN, PHONE_TO_NAME, ERIN_PHONE
from src.whatsapp import extract_message, send_message
from src.assistant import handle_message, generate_daily_plan
from src.tools.calendar import delete_assistant_events, batch_create_events, get_events_for_date
from src.tools.notion import get_routine_templates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Family Meeting Assistant")


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
    payload = await request.json()
    parsed = extract_message(payload)

    if not parsed:
        return {"status": "ok"}

    phone, sender_name, text = parsed

    # Reject unrecognized phone numbers
    if phone not in PHONE_TO_NAME:
        logger.warning("Message from unrecognized number: %s (%s)", phone, sender_name)
        return {"status": "ok"}

    logger.info("Message from %s: %s", PHONE_TO_NAME[phone], text[:100])

    # Process asynchronously so we return 200 immediately
    background_tasks.add_task(_process_and_reply, phone, text)
    return {"status": "ok"}


async def _process_and_reply(phone: str, text: str):
    """Process the message through Claude and send the reply via WhatsApp."""
    start = time.time()
    try:
        reply = handle_message(phone, text)
        elapsed = time.time() - start
        logger.info("Response generated in %.1fs (%d chars)", elapsed, len(reply))
        await send_message(phone, reply)
    except Exception:
        logger.exception("Error processing message from %s", phone)
        await send_message(phone, "Sorry, something went wrong. Please try again.")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# n8n automation endpoints (T021-T023)
# ---------------------------------------------------------------------------

@app.post("/api/v1/briefing/daily")
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


@app.post("/api/v1/calendar/populate-week")
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


@app.post("/api/v1/prompt/grandma-schedule")
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
