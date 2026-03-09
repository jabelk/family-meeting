"""Persistent drive time storage for the family assistant.

Stores location-to-drive-time mappings in a JSON file so the bot remembers
how long it takes to drive to common destinations (gym, school, church, etc.)
across conversations and container restarts.

Persistence: data/drive_times.json (local) or /app/data/drive_times.json (Docker).
Pattern: in-memory dict + atomic JSON file writes (same as routines.py, preferences.py).
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.family_config import load_family_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_DRIVE_TIMES = 20
MIN_MINUTES = 1
MAX_MINUTES = 120

# ---------------------------------------------------------------------------
# File paths (Docker vs local dev)
# ---------------------------------------------------------------------------

_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
_DRIVE_TIMES_FILE = _DATA_DIR / "drive_times.json"

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_drive_times: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# File I/O (atomic writes)
# ---------------------------------------------------------------------------


def _load_drive_times() -> None:
    """Load drive times from JSON file into memory."""
    global _drive_times
    try:
        if _DRIVE_TIMES_FILE.exists():
            _drive_times = json.loads(_DRIVE_TIMES_FILE.read_text())
            logger.info("Loaded %d drive time(s)", len(_drive_times))
        else:
            _drive_times = {}
    except Exception as e:
        logger.warning("Failed to load drive times: %s — starting empty", e)
        _drive_times = {}


def _save_drive_times() -> None:
    """Save drive times atomically (write to .tmp then rename)."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _DRIVE_TIMES_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_drive_times, indent=2))
        tmp.replace(_DRIVE_TIMES_FILE)
    except Exception as e:
        logger.error("Failed to save drive times: %s", e)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _normalize_location(location: str) -> str:
    """Normalize location name: lowercase, strip articles."""
    loc = location.strip().lower()
    for prefix in ("the ", "a ", "an "):
        if loc.startswith(prefix):
            loc = loc[len(prefix) :]
    return loc


def get_drive_times() -> str:
    """Return all stored drive times as a formatted string.

    Returns a human-readable list for Claude to use during plan generation,
    or a message indicating no drive times are stored.
    """
    if not _drive_times:
        partner2 = load_family_config()["partner2_name"]
        return f"No drive times stored. {partner2} can add them by saying something like 'the gym is 5 minutes away.'"

    lines = ["Stored drive times (from home):"]
    for location, info in sorted(_drive_times.items()):
        lines.append(f"• {location}: {info['minutes']} min")
    return "\n".join(lines)


def save_drive_time(location: str, minutes: int) -> str:
    """Add or update a drive time for a location.

    Location names are normalized to lowercase with articles stripped.
    Returns a confirmation string.
    """
    loc = _normalize_location(location)
    if not loc:
        return "Please provide a location name."

    if not (MIN_MINUTES <= minutes <= MAX_MINUTES):
        return f"Drive time must be between {MIN_MINUTES} and {MAX_MINUTES} minutes."

    is_update = loc in _drive_times
    _drive_times[loc] = {
        "minutes": minutes,
        "updated": datetime.now().isoformat(),
    }

    # Cap at MAX_DRIVE_TIMES — shouldn't happen with <10 locations but safe
    if len(_drive_times) > MAX_DRIVE_TIMES:
        return f"You've reached the maximum of {MAX_DRIVE_TIMES} stored locations. Please delete some first."

    _save_drive_times()
    action = "Updated" if is_update else "Saved"
    logger.info("%s drive time: %s = %d min", action, loc, minutes)
    return f"{action} drive time: {loc} is {minutes} minutes from home."


def delete_drive_time(location: str) -> str:
    """Remove a stored drive time by location name.

    Returns a confirmation string or a not-found message.
    """
    loc = _normalize_location(location)
    if loc in _drive_times:
        del _drive_times[loc]
        _save_drive_times()
        logger.info("Deleted drive time for %s", loc)
        return f"Removed drive time for {loc}."
    return f"No drive time stored for '{loc}'."


# ---------------------------------------------------------------------------
# Auto-load on module import
# ---------------------------------------------------------------------------

_load_drive_times()
