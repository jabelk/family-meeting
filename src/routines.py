"""Persistent per-user routine storage for the family assistant.

Stores per-phone-number routines (ordered step checklists) in a JSON file
so the bot remembers morning routines, bedtime routines, etc. across
conversations and container restarts.

Persistence: data/routines.json (local) or /app/data/routines.json (Docker).
Pattern: in-memory dict + atomic JSON file writes (same as preferences.py).
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

MAX_ROUTINES_PER_USER = 20
MAX_STEPS_PER_ROUTINE = 30

# ---------------------------------------------------------------------------
# File paths (Docker vs local dev)
# ---------------------------------------------------------------------------

_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
_ROUTINES_FILE = _DATA_DIR / "routines.json"

# ---------------------------------------------------------------------------
# In-memory routine cache
# ---------------------------------------------------------------------------

_routines: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# File I/O (atomic writes)
# ---------------------------------------------------------------------------

def _load_routines() -> None:
    """Load routines from JSON file into memory."""
    global _routines
    try:
        if _ROUTINES_FILE.exists():
            _routines = json.loads(_ROUTINES_FILE.read_text())
            total = sum(len(v.get("routines", [])) for v in _routines.values())
            logger.info("Loaded routines for %d phone(s) (%d total)", len(_routines), total)
        else:
            _routines = {}
    except Exception as e:
        logger.warning("Failed to load routines: %s — starting with empty set", e)
        _routines = {}


def _save_routines() -> None:
    """Save routines atomically (write to .tmp then rename)."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _ROUTINES_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_routines, indent=2))
        tmp.replace(_ROUTINES_FILE)
    except Exception as e:
        logger.error("Failed to save routines: %s", e)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_routine(phone: str, name: str, steps: list[str]) -> str:
    """Create or overwrite a routine for a phone number.

    Name is normalized to lowercase for matching. Steps are stored as
    position/description dicts. Uses rtn_ + secrets.token_hex(4) for IDs.

    Returns a confirmation string.
    Raises ValueError if steps exceed MAX_STEPS_PER_ROUTINE or routines
    exceed MAX_ROUTINES_PER_USER (when creating new).
    """
    if len(steps) > MAX_STEPS_PER_ROUTINE:
        raise ValueError(
            f"Routines can have at most {MAX_STEPS_PER_ROUTINE} steps. "
            f"You provided {len(steps)}."
        )

    name_lower = name.lower()
    now = datetime.now().isoformat()

    # Ensure phone entry exists
    if phone not in _routines:
        _routines[phone] = {"routines": []}

    routines = _routines[phone]["routines"]

    # Build steps list
    step_dicts = [
        {"position": i + 1, "description": s}
        for i, s in enumerate(steps)
    ]

    # Check if routine with this name already exists — overwrite it
    for i, existing in enumerate(routines):
        if existing.get("name", "").lower() == name_lower:
            routines[i] = {
                "id": existing["id"],  # keep same ID
                "name": name_lower,
                "steps": step_dicts,
                "created": existing["created"],
                "modified": now,
            }
            _save_routines()
            logger.info("Updated routine '%s' for %s (%d steps)", name_lower, phone, len(steps))
            return (
                f"Saved your {name_lower} routine ({len(steps)} steps). "
                f"Say 'show me my {name_lower} routine' anytime to see it."
            )

    # New routine — check cap
    if len(routines) >= MAX_ROUTINES_PER_USER:
        raise ValueError(
            f"You've reached the maximum of {MAX_ROUTINES_PER_USER} routines. "
            "Please delete some before adding new ones."
        )

    # Create new routine
    routine = {
        "id": f"rtn_{secrets.token_hex(4)}",
        "name": name_lower,
        "steps": step_dicts,
        "created": now,
        "modified": now,
    }
    routines.append(routine)
    _save_routines()
    logger.info("Created routine '%s' for %s (%d steps)", name_lower, phone, len(steps))
    return (
        f"Saved your {name_lower} routine ({len(steps)} steps). "
        f"Say 'show me my {name_lower} routine' anytime to see it."
    )


def get_routine(phone: str, name: str) -> str:
    """Return a formatted numbered checklist for a routine.

    Name lookup is case-insensitive. Returns a not-found message with a
    helpful prompt if no matching routine exists.
    """
    entry = _routines.get(phone)
    if not entry:
        return f"No routine named '{name}' found. Want to create one? Just tell me the steps."

    name_lower = name.lower()
    for routine in entry.get("routines", []):
        if routine.get("name", "").lower() == name_lower:
            lines = [f"**{routine['name']}**"]
            for step in routine.get("steps", []):
                lines.append(f"{step['position']}. {step['description']}")
            return "\n".join(lines)

    return f"No routine named '{name}' found. Want to create one? Just tell me the steps."


def list_routines(phone: str) -> str:
    """Return a summary of all saved routines for a phone number.

    Returns a bullet list with routine names and step counts,
    or a friendly empty-state message.
    """
    entry = _routines.get(phone)
    if not entry:
        return "No routines saved yet."

    routines = entry.get("routines", [])
    if not routines:
        return "No routines saved yet."

    lines = ["Your saved routines:"]
    for routine in routines:
        step_count = len(routine.get("steps", []))
        lines.append(f"\u2022 {routine['name']} ({step_count} steps)")
    return "\n".join(lines)


def delete_routine(phone: str, name: str) -> str:
    """Remove a routine by name (case-insensitive).

    Returns a confirmation string, or a not-found message.
    """
    entry = _routines.get(phone)
    if not entry:
        return f"No routine named '{name}' found."

    name_lower = name.lower()
    routines = entry.get("routines", [])
    for i, routine in enumerate(routines):
        if routine.get("name", "").lower() == name_lower:
            routines.pop(i)
            _save_routines()
            logger.info("Deleted routine '%s' for %s", name_lower, phone)
            return f"Deleted your {name_lower} routine."

    return f"No routine named '{name}' found."


# ---------------------------------------------------------------------------
# Auto-load on module import
# ---------------------------------------------------------------------------

_load_routines()
