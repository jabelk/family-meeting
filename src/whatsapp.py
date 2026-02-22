"""WhatsApp message send/receive helpers via Meta Cloud API."""

import logging
import httpx
from src.config import WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN

logger = logging.getLogger(__name__)

GRAPH_API_URL = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
MAX_MESSAGE_LENGTH = 1600


async def send_message(to: str, text: str) -> None:
    """Send a text message via WhatsApp. Splits long messages automatically."""
    chunks = _split_message(text)
    async with httpx.AsyncClient() as client:
        for chunk in chunks:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": chunk},
            }
            resp = await client.post(
                GRAPH_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 429:
                logger.warning("WhatsApp rate limit hit, message may be delayed")
            elif resp.status_code != 200:
                logger.error("WhatsApp send failed: %s %s", resp.status_code, resp.text)


def _split_message(text: str) -> list[str]:
    """Split a long message into chunks that fit WhatsApp's 1600 char limit.

    Tries to split on double newlines (section breaks) first, then single
    newlines, to keep formatting intact.
    """
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > MAX_MESSAGE_LENGTH:
        # Try to split at a section break (double newline)
        split_at = remaining.rfind("\n\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            # Fall back to single newline
            split_at = remaining.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            # Last resort: hard cut
            split_at = MAX_MESSAGE_LENGTH
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def extract_message(payload: dict) -> tuple[str, str, str] | None:
    """Extract (phone_number, sender_name, message_text) from a Meta webhook payload.

    Returns None if the payload doesn't contain a text message.
    """
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages")
        if not messages:
            return None
        msg = messages[0]
        if msg.get("type") != "text":
            return None
        phone = msg["from"]
        text = msg["text"]["body"]
        contacts = value.get("contacts", [])
        name = contacts[0]["profile"]["name"] if contacts else phone
        return phone, name, text
    except (KeyError, IndexError):
        logger.warning("Could not parse WhatsApp webhook payload")
        return None
