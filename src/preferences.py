"""Persistent per-user preference storage for the family assistant.

Stores per-phone-number preferences in a JSON file so the bot remembers
opt-outs, topic filters, communication style, and quiet hours across
conversations and container restarts.

Persistence: data/user_preferences.json (local) or /app/data/user_preferences.json (Docker).
Pattern: in-memory dict + atomic JSON file writes (same as conversation.py).
"""

import json
import logging
import secrets
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_PREFERENCES_PER_USER = 50
VALID_CATEGORIES = {
    "notification_optout",
    "topic_filter",
    "communication_style",
    "quiet_hours",
}

# ---------------------------------------------------------------------------
# File paths (Docker vs local dev)
# ---------------------------------------------------------------------------

_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
_PREFERENCES_FILE = _DATA_DIR / "user_preferences.json"

# ---------------------------------------------------------------------------
# In-memory preference cache
# ---------------------------------------------------------------------------

_preferences: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# File I/O (atomic writes)
# ---------------------------------------------------------------------------


def _load_preferences() -> None:
    """Load preferences from JSON file into memory."""
    global _preferences
    try:
        if _PREFERENCES_FILE.exists():
            _preferences = json.loads(_PREFERENCES_FILE.read_text())
            total = sum(len(v.get("preferences", [])) for v in _preferences.values())
            logger.info("Loaded preferences for %d phone(s) (%d total)", len(_preferences), total)
        else:
            _preferences = {}
    except Exception as e:
        logger.warning("Failed to load preferences: %s — starting with empty set", e)
        _preferences = {}


def _save_preferences() -> None:
    """Save preferences atomically (write to .tmp then rename)."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _PREFERENCES_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_preferences, indent=2))
        tmp.replace(_PREFERENCES_FILE)
    except Exception as e:
        logger.error("Failed to save preferences: %s", e)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_preferences(phone: str) -> list[dict]:
    """Return all active preferences for a phone number.

    Returns an empty list if no preferences exist for this phone.
    """
    entry = _preferences.get(phone)
    if not entry:
        return []
    return [p for p in entry.get("preferences", []) if p.get("active", True)]


def add_preference(phone: str, category: str, description: str, raw_text: str) -> dict:
    """Add a new preference for a phone number.

    If a preference with a similar description already exists for the same
    category, replaces it (conflicting preference handling).

    Returns the created/updated preference dict.
    Raises ValueError if the user has hit the preference cap.
    """
    if category not in VALID_CATEGORIES:
        category = "notification_optout"  # safe default

    # Ensure phone entry exists
    if phone not in _preferences:
        _preferences[phone] = {"preferences": []}

    prefs = _preferences[phone]["preferences"]

    # Check for duplicate/conflicting preference — same category + overlapping description
    _stop_words = {
        "no",
        "not",
        "don't",
        "dont",
        "the",
        "a",
        "an",
        "me",
        "my",
        "i",
        "about",
        "from",
        "for",
        "in",
        "of",
        "to",
        "unless",
        "asked",
        "again",
        "start",
        "stop",
        "remind",
        "reminders",
        "preference",
        "preferences",
    }
    description_lower = description.lower()
    for i, existing in enumerate(prefs):
        if existing.get("category") == category:
            existing_desc = existing.get("description", "").lower()
            # Overlap check using meaningful words (exclude stop words)
            desc_words = set(description_lower.split()) - _stop_words
            existing_words = set(existing_desc.split()) - _stop_words
            overlap = desc_words & existing_words
            # Need at least 1 meaningful overlap word, AND >50% of meaningful words match
            min_meaningful = min(len(desc_words), len(existing_words))
            if min_meaningful > 0 and len(overlap) >= 1 and len(overlap) >= min_meaningful * 0.5:
                old_desc = existing["description"]
                prefs[i] = {
                    "id": existing["id"],  # keep same ID
                    "category": category,
                    "description": description,
                    "raw_text": raw_text,
                    "created": datetime.now().isoformat(),
                    "active": True,
                }
                _save_preferences()
                logger.info("Updated preference for %s: '%s' -> '%s'", phone, old_desc, description)
                return prefs[i]

    # Check cap
    active_count = len([p for p in prefs if p.get("active", True)])
    if active_count >= MAX_PREFERENCES_PER_USER:
        raise ValueError(
            f"You've reached the maximum of {MAX_PREFERENCES_PER_USER} preferences. "
            "Please remove some before adding new ones."
        )

    # Create new preference
    pref = {
        "id": f"pref_{secrets.token_hex(4)}",
        "category": category,
        "description": description,
        "raw_text": raw_text,
        "created": datetime.now().isoformat(),
        "active": True,
    }
    prefs.append(pref)
    _save_preferences()
    logger.info("Added preference for %s: '%s' (%s)", phone, description, category)
    return pref


def remove_preference(phone: str, preference_id: str) -> bool:
    """Remove a preference by its ID.

    Returns True if the preference was found and removed, False otherwise.
    """
    entry = _preferences.get(phone)
    if not entry:
        return False

    prefs = entry.get("preferences", [])
    original_len = len(prefs)
    entry["preferences"] = [p for p in prefs if p.get("id") != preference_id]

    if len(entry["preferences"]) < original_len:
        _save_preferences()
        logger.info("Removed preference %s for %s", preference_id, phone)
        return True
    return False


def remove_preference_by_description(phone: str, search_text: str) -> bool:
    """Remove a preference by fuzzy-matching against description and raw_text.

    Returns True if a matching preference was found and removed.
    """
    entry = _preferences.get(phone)
    if not entry:
        return False

    search_lower = search_text.lower()
    search_words = set(search_lower.split())
    prefs = entry.get("preferences", [])

    best_match_idx = -1
    best_match_score = 0

    for i, pref in enumerate(prefs):
        desc = pref.get("description", "").lower()
        raw = pref.get("raw_text", "").lower()
        combined = f"{desc} {raw}"
        combined_words = set(combined.split())

        # Score: how many search words appear in the preference text
        matching_words = search_words & combined_words
        score = len(matching_words)

        # Also check substring match
        if search_lower in desc or search_lower in raw:
            score += 5  # Boost for substring match

        if score > best_match_score:
            best_match_score = score
            best_match_idx = i

    if best_match_idx >= 0 and best_match_score >= 1:
        removed = prefs.pop(best_match_idx)
        _save_preferences()
        logger.info(
            "Removed preference by description for %s: '%s' (search: '%s')",
            phone,
            removed.get("description"),
            search_text,
        )
        return True

    return False


def clear_preferences(phone: str) -> int:
    """Remove all preferences for a phone number.

    Returns the number of preferences removed.
    """
    entry = _preferences.get(phone)
    if not entry:
        return 0

    count = len(entry.get("preferences", []))
    if count > 0:
        entry["preferences"] = []
        _save_preferences()
        logger.info("Cleared %d preferences for %s", count, phone)
    return count


# ---------------------------------------------------------------------------
# Auto-load on module import
# ---------------------------------------------------------------------------

_load_preferences()
