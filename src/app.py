"""FastAPI app — WhatsApp webhook endpoint."""

import logging
import time
from fastapi import FastAPI, Request, Response, BackgroundTasks
from src.config import WHATSAPP_VERIFY_TOKEN, PHONE_TO_NAME
from src.whatsapp import extract_message, send_message
from src.assistant import handle_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Family Meeting Assistant")


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
