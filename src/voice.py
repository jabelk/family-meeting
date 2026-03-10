"""Voice access module — Siri Shortcut request/response models and helpers."""

import asyncio
import logging
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models (per data-model.md)
# ---------------------------------------------------------------------------


class VoiceRequest(BaseModel):
    """Inbound voice request from an Apple Shortcut."""

    text: Optional[str] = Field(None, max_length=1000, description="Transcribed voice input")
    channel: str = Field(..., description="Source channel: 'siri' or 'preset'")
    preset_action: Optional[str] = Field(
        None,
        description="Preset action type (calendar, grocery_add, dinner, remind)",
    )


class VoiceResponse(BaseModel):
    """Outbound response formatted for Shortcut consumption."""

    success: bool
    message: str = ""
    error: Optional[str] = None
    sent_to_whatsapp: bool = False


# ---------------------------------------------------------------------------
# Response formatting
# ---------------------------------------------------------------------------

MAX_VOICE_WORDS = 150  # ~150 words max for spoken output


def format_voice_response(full_text: str) -> tuple[str, bool]:
    """Truncate assistant response to ~150 words for voice output.

    Returns:
        (voice_text, was_truncated) — truncated text and whether it was cut.
    """
    words = full_text.split()
    if len(words) <= MAX_VOICE_WORDS:
        return full_text.strip(), False

    truncated = " ".join(words[:MAX_VOICE_WORDS])
    # Try to end at sentence boundary
    for sep in [". ", "! ", "? "]:
        last = truncated.rfind(sep)
        if last > len(truncated) // 2:  # only if we keep at least half
            truncated = truncated[: last + 1]
            break
    return truncated.strip(), True


# ---------------------------------------------------------------------------
# Async timeout wrapper for handle_message
# ---------------------------------------------------------------------------

VOICE_TIMEOUT_SECONDS = 18  # Apple Shortcuts times out at ~25s; leave margin


async def run_with_voice_timeout(
    handler_func,
    sender_phone: str,
    message_text: str,
    send_whatsapp_func=None,
) -> VoiceResponse:
    """Run handle_message with an 18-second timeout.

    Fast path: if handle_message completes in time, return formatted voice response.
    Slow path: if timeout fires, return acknowledgment and spawn background task
    to complete processing and send result via WhatsApp.

    Args:
        handler_func: The handle_message function (sync — run in executor).
        sender_phone: Phone number of the requesting user.
        message_text: The user's transcribed voice input.
        send_whatsapp_func: Async function to send WhatsApp message (for fallback).
    """
    loop = asyncio.get_event_loop()

    try:
        # Run synchronous handle_message in a thread pool with timeout
        reply = await asyncio.wait_for(
            loop.run_in_executor(None, handler_func, sender_phone, message_text),
            timeout=VOICE_TIMEOUT_SECONDS,
        )

        voice_text, was_truncated = format_voice_response(reply)

        if was_truncated and send_whatsapp_func:
            # Send full response to WhatsApp in background
            asyncio.create_task(_send_whatsapp_fallback(send_whatsapp_func, sender_phone, reply))
            return VoiceResponse(
                success=True,
                message=voice_text + " I sent the full details to WhatsApp.",
                sent_to_whatsapp=True,
            )

        return VoiceResponse(success=True, message=voice_text)

    except asyncio.TimeoutError:
        logger.warning("Voice request timed out after %ds for %s", VOICE_TIMEOUT_SECONDS, sender_phone)

        # Spawn background task to complete processing and send via WhatsApp
        if send_whatsapp_func:
            asyncio.create_task(
                _complete_and_send_whatsapp(handler_func, sender_phone, message_text, send_whatsapp_func)
            )

        return VoiceResponse(
            success=True,
            message="Working on that — I'll send the answer to WhatsApp.",
            sent_to_whatsapp=True,
        )

    except Exception:
        logger.exception("Voice request failed for %s", sender_phone)
        return VoiceResponse(
            success=False,
            error="I couldn't process that request right now. Try again in a moment.",
        )


async def _send_whatsapp_fallback(send_func, phone: str, text: str) -> None:
    """Send full response text to WhatsApp."""
    try:
        await send_func(phone, text)
    except Exception:
        logger.exception("Failed to send WhatsApp fallback to %s", phone)


async def _complete_and_send_whatsapp(handler_func, phone: str, text: str, send_func) -> None:
    """Complete a timed-out voice request in background and send result via WhatsApp."""
    try:
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, handler_func, phone, text)
        await send_func(phone, reply)
        logger.info("Sent timed-out voice response to WhatsApp for %s (%d chars)", phone, len(reply))
    except Exception:
        logger.exception("Failed to complete background voice request for %s", phone)
