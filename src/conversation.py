"""Conversation history storage for multi-turn WhatsApp conversations.

Stores per-phone conversation history in a JSON file so Claude can
understand follow-up questions and multi-step workflows. History expires
after CONVERSATION_TIMEOUT seconds of inactivity and is capped at
MAX_CONVERSATION_TURNS to control context window usage.

Persistence: data/conversations.json (local) or /app/data/conversations.json (Docker).
Pattern: in-memory dict + atomic JSON file writes (same as discovery.py usage counters).
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONVERSATION_TIMEOUT = 86400  # 24 hours of inactivity before conversation expires
MAX_CONVERSATION_TURNS = 10  # Max turns retained per conversation

# ---------------------------------------------------------------------------
# File paths (Docker vs local dev)
# ---------------------------------------------------------------------------

_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
_CONVERSATIONS_FILE = _DATA_DIR / "conversations.json"

# ---------------------------------------------------------------------------
# In-memory conversation cache
# ---------------------------------------------------------------------------

_conversations: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# File I/O (atomic writes)
# ---------------------------------------------------------------------------

def _load_conversations() -> None:
    """Load conversations from JSON file into memory."""
    global _conversations
    try:
        if _CONVERSATIONS_FILE.exists():
            _conversations = json.loads(_CONVERSATIONS_FILE.read_text())
            logger.info("Loaded conversations for %d phone(s)", len(_conversations))
        else:
            _conversations = {}
    except Exception as e:
        logger.warning("Failed to load conversations: %s", e)
        _conversations = {}


def _save_conversations() -> None:
    """Save conversations atomically (write to .tmp then rename)."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _CONVERSATIONS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_conversations, indent=2))
        tmp.replace(_CONVERSATIONS_FILE)
    except Exception as e:
        logger.error("Failed to save conversations: %s", e)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize_message(msg: dict) -> dict:
    """Serialize a single message for JSON storage.

    Handles:
    - Assistant messages with Anthropic SDK content block objects (TextBlock,
      ToolUseBlock) — serialized via model_dump().
    - User messages with base64 image content — replaced with text placeholder.
    - Plain dicts and strings — passed through unchanged.
    """
    role = msg.get("role", "")
    content = msg.get("content")

    # String content (simple user text) — pass through
    if isinstance(content, str):
        return msg

    # List content — serialize each block
    if isinstance(content, list):
        serialized_blocks = []
        for block in content:
            # Anthropic SDK object (TextBlock, ToolUseBlock) — has model_dump
            if hasattr(block, "model_dump"):
                serialized_blocks.append(
                    block.model_dump(mode="json", exclude_unset=True)
                )
            # Dict with base64 image — replace with placeholder
            elif isinstance(block, dict) and block.get("type") == "image":
                source = block.get("source", {})
                if source.get("type") == "base64":
                    serialized_blocks.append({
                        "type": "text",
                        "text": "[Image sent: photo]",
                    })
                else:
                    serialized_blocks.append(block)
            # Plain dict (tool_result, text block dict, etc.) — pass through
            elif isinstance(block, dict):
                serialized_blocks.append(block)
            else:
                # Unknown type — convert to string as fallback
                serialized_blocks.append({
                    "type": "text",
                    "text": str(block),
                })
        return {"role": role, "content": serialized_blocks}

    # Fallback — return as-is
    return msg


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_history(phone: str) -> list[dict]:
    """Return conversation history for a phone number as a flat messages list.

    Returns an empty list if no conversation exists or it has expired.
    Expired conversations are pruned on access.
    """
    conv = _conversations.get(phone)
    if not conv:
        return []

    # Check expiry
    try:
        last_active = datetime.fromisoformat(conv["last_active"])
        if datetime.now() - last_active > timedelta(seconds=CONVERSATION_TIMEOUT):
            logger.info("Conversation expired for %s (last active: %s)", phone, conv["last_active"])
            del _conversations[phone]
            _save_conversations()
            return []
    except (KeyError, ValueError):
        # Malformed entry — clear it
        del _conversations[phone]
        _save_conversations()
        return []

    # Flatten all turns into a single messages list
    messages = []
    for turn in conv.get("turns", []):
        messages.extend(turn.get("messages", []))
    return messages


def save_turn(phone: str, turn_messages: list[dict]) -> None:
    """Save a completed conversation turn for a phone number.

    A turn includes all messages from the user's input through the final
    bot response (including all tool-use loop iterations).
    """
    if not turn_messages:
        return

    # Serialize each message
    serialized = [_serialize_message(msg) for msg in turn_messages]

    # Create or update phone entry
    if phone not in _conversations:
        _conversations[phone] = {"last_active": "", "turns": []}

    conv = _conversations[phone]
    conv["last_active"] = datetime.now().isoformat()
    conv["turns"].append({"messages": serialized})

    # Trim oldest turns if over limit
    while len(conv["turns"]) > MAX_CONVERSATION_TURNS:
        conv["turns"].pop(0)

    _save_conversations()


def clear_history(phone: str) -> None:
    """Explicitly clear conversation history for a phone number."""
    if phone in _conversations:
        del _conversations[phone]
        _save_conversations()
        logger.info("Cleared conversation history for %s", phone)


# ---------------------------------------------------------------------------
# Auto-load on module import
# ---------------------------------------------------------------------------

_load_conversations()
