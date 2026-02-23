"""WhatsApp message send/receive helpers via Meta Cloud API."""

import base64
import logging
import httpx
from src.config import WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN

logger = logging.getLogger(__name__)

GRAPH_API_URL = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
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


async def send_template_message(to: str, template_name: str, parameters: list[str] | None = None) -> None:
    """Send a pre-approved template message via WhatsApp.

    Used as fallback when the 24-hour messaging window has expired.
    """
    components = []
    if parameters:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in parameters],
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_US"},
            "components": components,
        },
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GRAPH_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code != 200:
            logger.error("Template message failed: %s %s", resp.status_code, resp.text)


async def send_message_with_template_fallback(
    to: str, text: str, template_name: str = "", template_params: list[str] | None = None
) -> None:
    """Send a free-form message; fall back to template if outside 24h window.

    If Meta returns error 131026 (outside service window) and a template_name
    is provided, retries with the template message.
    """
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
            if resp.status_code != 200:
                # Check for "outside service window" error
                try:
                    err = resp.json()
                    error_code = err.get("error", {}).get("code", 0)
                except Exception:
                    error_code = 0

                if error_code == 131026 and template_name:
                    logger.info("Outside 24h window — falling back to template: %s", template_name)
                    await send_template_message(to, template_name, template_params)
                    return
                logger.error("WhatsApp send failed: %s %s", resp.status_code, resp.text)


async def download_media(media_id: str) -> tuple[bytes, str]:
    """Download media from WhatsApp by media ID.

    Two-step process: get download URL, then download binary data.
    Media URLs expire in 5 minutes — call immediately after webhook receipt.

    Returns:
        Tuple of (image_bytes, mime_type).
    """
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    async with httpx.AsyncClient() as client:
        # Step 1: Get media download URL
        meta_resp = await client.get(f"{GRAPH_API_BASE}/{media_id}", headers=headers)
        if meta_resp.status_code != 200:
            raise RuntimeError(f"Failed to get media URL: {meta_resp.status_code} {meta_resp.text}")
        meta = meta_resp.json()
        download_url = meta["url"]
        mime_type = meta.get("mime_type", "image/jpeg")

        # Step 2: Download actual binary data (URL expires in 5 min)
        data_resp = await client.get(download_url, headers=headers)
        if data_resp.status_code != 200:
            raise RuntimeError(f"Failed to download media: {data_resp.status_code}")

        logger.info("Downloaded media %s (%s, %d bytes)", media_id, mime_type, len(data_resp.content))
        return data_resp.content, mime_type


def extract_message(payload: dict) -> dict | None:
    """Extract message data from a Meta webhook payload.

    Returns a dict with keys:
        - phone: sender phone number
        - name: sender display name
        - type: 'text' or 'image'
        - text: message text (for text messages) or caption (for images)
        - media_id: WhatsApp media ID (for image messages only)
        - mime_type: image MIME type (for image messages only)

    Returns None if the payload doesn't contain a supported message.
    """
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages")
        if not messages:
            return None
        msg = messages[0]
        phone = msg["from"]
        contacts = value.get("contacts", [])
        name = contacts[0]["profile"]["name"] if contacts else phone
        msg_type = msg.get("type")

        if msg_type == "text":
            return {
                "phone": phone,
                "name": name,
                "type": "text",
                "text": msg["text"]["body"],
            }
        elif msg_type == "image":
            return {
                "phone": phone,
                "name": name,
                "type": "image",
                "text": msg.get("image", {}).get("caption", ""),
                "media_id": msg["image"]["id"],
                "mime_type": msg["image"].get("mime_type", "image/jpeg"),
            }
        else:
            logger.info("Unsupported message type: %s", msg_type)
            return None
    except (KeyError, IndexError):
        logger.warning("Could not parse WhatsApp webhook payload")
        return None
