"""Family configuration loader — reads config/family.yaml and provides placeholder dict."""

import logging
import os
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(os.environ.get("FAMILY_CONFIG_PATH", "config/family.yaml"))


def _validate_config(raw: dict) -> None:
    """Validate required fields exist and are valid."""
    bot = raw.get("bot") or {}
    if not bot.get("name"):
        raise ValueError("config/family.yaml: 'bot.name' is required")

    family = raw.get("family") or {}
    if not family.get("name"):
        raise ValueError("config/family.yaml: 'family.name' is required")

    tz = family.get("timezone", "")
    if not tz:
        raise ValueError("config/family.yaml: 'family.timezone' is required")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, KeyError):
        raise ValueError(f"config/family.yaml: invalid timezone '{tz}'")

    partners = family.get("partners") or []
    if len(partners) < 2:
        raise ValueError(
            "config/family.yaml: 'family.partners' must contain at least 2 entries (both partners are required)"
        )
    for i, p in enumerate(partners):
        if not p.get("name"):
            raise ValueError(f"config/family.yaml: 'family.partners[{i}].name' is required")


def _build_placeholder_dict(raw: dict) -> dict:
    """Build the flat placeholder dict used for prompt rendering."""
    bot = raw.get("bot") or {}
    family = raw.get("family") or {}
    prefs = raw.get("preferences") or {}
    calendar = raw.get("calendar") or {}
    childcare_cfg = raw.get("childcare") or {}

    partners = family.get("partners") or []
    children = family.get("children") or []
    caregivers = family.get("caregivers") or []

    # Partner names (up to 4)
    partner_names = [p["name"] for p in partners]

    # Children summary
    children_parts = []
    for c in children:
        details = c.get("details", "")
        detail_str = f" — {details}" if details else ""
        children_parts.append(f"{c['name']} (age {c['age']}){detail_str}")
    children_summary = ", ".join(children_parts)

    # Caregiver names
    caregiver_names = ", ".join(f"{c['name']} ({c.get('role', 'caregiver')})" for c in caregivers)

    # Calendar event mappings as readable text
    event_mappings = calendar.get("event_mappings") or {}
    if event_mappings:
        mapping_parts = [f'"{k}" = {v}' for k, v in event_mappings.items()]
        calendar_event_mappings = ", ".join(mapping_parts)
    else:
        calendar_event_mappings = "none configured"

    # Auto-generate childcare keywords if not provided
    childcare_keywords = childcare_cfg.get("keywords") or []
    if not childcare_keywords:
        childcare_keywords = [c["name"].lower() for c in children]
        for cg in caregivers:
            childcare_keywords.extend(cg.get("keywords", [cg["name"].lower()]))

    # Auto-generate caregiver mappings if not provided
    caregiver_mappings = childcare_cfg.get("caregiver_mappings") or {}
    if not caregiver_mappings:
        for cg in caregivers:
            caregiver_mappings[cg["name"].lower()] = cg["name"]

    # Build welcome message
    bot_name = bot.get("name", "Assistant")
    welcome = bot.get("welcome_message", "")
    if not welcome:
        welcome = (
            f"Welcome to {bot_name}! I can help with recipes, budgets, calendars, "
            f'groceries, chores, and reminders. Say "help" anytime to see everything I can do.'
        )

    result = {
        "bot_name": bot_name,
        "welcome_message": welcome,
        "family_name": family.get("name", ""),
        "timezone": family.get("timezone", "UTC"),
        "location": family.get("location", ""),
        "partner1_name": partner_names[0] if len(partner_names) > 0 else "",
        "partner2_name": partner_names[1] if len(partner_names) > 1 else "",
        "partner3_name": partner_names[2] if len(partner_names) > 2 else "",
        "partner4_name": partner_names[3] if len(partner_names) > 3 else "",
        "partner1_name_lower": partner_names[0].lower() if len(partner_names) > 0 else "",
        "partner2_name_lower": partner_names[1].lower() if len(partner_names) > 1 else "",
        "partner1_work": partners[0].get("work", "") if len(partners) > 0 else "",
        "partner2_work": partners[1].get("work", "") if len(partners) > 1 else "",
        "partner1_has_work_calendar": partners[0].get("has_work_calendar", False) if len(partners) > 0 else False,
        "children_summary": children_summary,
        "child1_name": children[0]["name"] if len(children) > 0 else "",
        "child1_age": children[0].get("age", "") if len(children) > 0 else "",
        "child1_details": children[0].get("details", "") if len(children) > 0 else "",
        "child2_name": children[1]["name"] if len(children) > 1 else "",
        "child2_age": children[1].get("age", "") if len(children) > 1 else "",
        "child2_details": children[1].get("details", "") if len(children) > 1 else "",
        "children_activities_summary": ", ".join(
            f"{c['name']} has {c.get('details', 'activities')}" for c in children if c.get("details")
        )
        if children
        else "check calendar for activity schedule",
        "caregiver_names": caregiver_names,
        "grocery_store": prefs.get("grocery_store", "grocery store"),
        "recipe_source": prefs.get("recipe_source", ""),
        "dietary_restrictions": ", ".join(prefs.get("dietary_restrictions", [])),
        "calendar_event_mappings": calendar_event_mappings,
        # Raw data for Python code that needs structured access
        "_partners": partners,
        "_children": children,
        "_caregivers": caregivers,
        "_childcare_keywords": childcare_keywords,
        "_caregiver_mappings": caregiver_mappings,
        "_event_mappings": event_mappings,
        "_raw": raw,
    }
    return result


@lru_cache(maxsize=1)
def load_family_config() -> dict:
    """Load and validate family config, returning the placeholder dict.

    Raises FileNotFoundError if config/family.yaml is missing.
    Raises ValueError if required fields are absent or invalid.
    """
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Missing {_CONFIG_PATH} — copy config/family.yaml.example and fill in your family's details."
        )

    logger.info("Loading family config from %s", _CONFIG_PATH)
    with open(_CONFIG_PATH) as f:
        raw = yaml.safe_load(f) or {}
    _validate_config(raw)

    return _build_placeholder_dict(raw)
