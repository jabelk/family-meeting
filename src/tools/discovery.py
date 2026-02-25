"""Feature discovery, help menu, contextual tips, and usage tracking."""

import json
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Help categories — 6 groups matching data-model.md
# ---------------------------------------------------------------------------

HELP_CATEGORIES = [
    {
        "key": "recipes",
        "icon": "\U0001f373",  # frying pan
        "name": "Recipes & Cooking",
        "capabilities": "Search Downshiftology for new recipes, browse your saved collection, or import favorites.",
        "static_examples": [
            "find me a chicken dinner recipe",
            "search for keto breakfast ideas",
        ],
        "personalize_from": "list_cookbooks",
    },
    {
        "key": "budget",
        "icon": "\U0001f4b0",  # money bag
        "name": "Budget & Spending",
        "capabilities": "Check your YNAB budget, search transactions, or move money between categories.",
        "static_examples": [
            "what did we spend at Costco?",
            "how's our Groceries budget?",
        ],
        "personalize_from": "get_budget_summary",
    },
    {
        "key": "calendar",
        "icon": "\U0001f4c5",  # calendar
        "name": "Calendar & Reminders",
        "capabilities": "View upcoming events, create shared reminders, or generate your daily plan.",
        "static_examples": [
            "what's on our calendar this week?",
            "remind Jason to pick up dog at 12:30",
        ],
        "personalize_from": None,
    },
    {
        "key": "groceries",
        "icon": "\U0001f6d2",  # shopping cart
        "name": "Groceries & Meal Planning",
        "capabilities": "Generate meal plans, build grocery lists, and push to AnyList for delivery.",
        "static_examples": [
            "what's for dinner this week?",
            "order groceries",
        ],
        "personalize_from": "get_staple_items",
    },
    {
        "key": "chores",
        "icon": "\U0001f3e0",  # house
        "name": "Chores & Home",
        "capabilities": "Track chores, set a laundry timer, customize preferences, or view your history.",
        "static_examples": [
            "started laundry",
            "what chores have I done this week?",
        ],
        "personalize_from": None,
    },
    {
        "key": "family_management",
        "icon": "\U0001f4cb",  # clipboard
        "name": "Family Management",
        "capabilities": "Manage action items, backlog projects, meeting agendas, and family profile.",
        "static_examples": [
            "add to backlog: organize garage",
            "what action items are overdue?",
        ],
        "personalize_from": None,
    },
    {
        "key": "big_picture",
        "icon": "\U0001f9e0",  # brain
        "name": "Big Picture & Strategy",
        "capabilities": "Ask broad questions and I'll connect the dots across budget, calendar, meals, and tasks to give you strategic advice.",
        "static_examples": [
            "how's our week looking?",
            "prep me for our family meeting",
        ],
        "personalize_from": None,
    },
]

# ---------------------------------------------------------------------------
# Tool-to-category mapping — maps every tool name to a category key
# ---------------------------------------------------------------------------

TOOL_TO_CATEGORY: dict[str, str] = {
    # recipes
    "search_downshiftology": "recipes",
    "get_downshiftology_details": "recipes",
    "import_downshiftology_recipe": "recipes",
    "extract_and_save_recipe": "recipes",
    "search_recipes": "recipes",
    "get_recipe_details": "recipes",
    "recipe_to_grocery_list": "recipes",
    "list_cookbooks": "recipes",
    # budget
    "get_budget_summary": "budget",
    "search_transactions": "budget",
    "recategorize_transaction": "budget",
    "create_transaction": "budget",
    "update_category_budget": "budget",
    "move_money": "budget",
    # calendar
    "get_calendar_events": "calendar",
    "get_outlook_events": "calendar",
    "write_calendar_blocks": "calendar",
    "create_quick_event": "calendar",
    # groceries
    "get_grocery_history": "groceries",
    "get_staple_items": "groceries",
    "push_grocery_list": "groceries",
    "generate_meal_plan": "groceries",
    "handle_meal_swap": "groceries",
    "save_meal_plan": "groceries",
    "get_meal_plan": "groceries",
    "check_reorder_items": "groceries",
    "confirm_groceries_ordered": "groceries",
    # chores
    "complete_chore": "chores",
    "skip_chore": "chores",
    "start_laundry": "chores",
    "advance_laundry": "chores",
    "cancel_laundry": "chores",
    "set_chore_preference": "chores",
    "get_chore_history": "chores",
    "set_quiet_day": "chores",
    # family_management
    "get_action_items": "family_management",
    "add_action_item": "family_management",
    "complete_action_item": "family_management",
    "add_topic": "family_management",
    "get_family_profile": "family_management",
    "update_family_profile": "family_management",
    "create_meeting": "family_management",
    "rollover_incomplete_items": "family_management",
    "get_backlog_items": "family_management",
    "add_backlog_item": "family_management",
    "complete_backlog_item": "family_management",
    "get_routine_templates": "family_management",
    # big_picture — cross-domain questions use multiple tools; map the ones
    # most associated with holistic queries so usage tracking picks them up.
    "get_help": "big_picture",
}

# ---------------------------------------------------------------------------
# Tip definitions — contextual "did you know?" tips (data-model.md)
# ---------------------------------------------------------------------------

TIP_DEFINITIONS: list[dict] = [
    {
        "id": "tip_recipe_search",
        "trigger_tools": ["generate_meal_plan", "save_meal_plan", "get_meal_plan"],
        "text": "You can say 'find me a keto dinner recipe' to search Downshiftology for new ideas!",
        "related_category": "recipes",
    },
    {
        "id": "tip_grocery_push",
        "trigger_tools": ["get_downshiftology_details", "get_recipe_details", "generate_meal_plan"],
        "text": "Say 'order groceries' to push your meal plan ingredients to AnyList for delivery.",
        "related_category": "groceries",
    },
    {
        "id": "tip_budget_search",
        "trigger_tools": ["push_grocery_list", "confirm_groceries_ordered"],
        "text": "Wondering where the money went? Say 'what did we spend at Costco?' to search transactions.",
        "related_category": "budget",
    },
    {
        "id": "tip_reminder",
        "trigger_tools": ["get_calendar_events"],
        "text": "You can say 'remind Jason to pick up dog at 12:30' to create a shared calendar reminder.",
        "related_category": "calendar",
    },
    {
        "id": "tip_chore_timer",
        "trigger_tools": ["complete_chore"],
        "text": "Starting laundry? Say 'started laundry' and I'll remind you when it's time to move it to the dryer.",
        "related_category": "chores",
    },
    {
        "id": "tip_recipe_import",
        "trigger_tools": ["search_downshiftology"],
        "text": "Found a recipe you love? Say 'save number 2' to import it to your recipe catalogue.",
        "related_category": "recipes",
    },
    {
        "id": "tip_backlog",
        "trigger_tools": ["write_calendar_blocks", "get_routine_templates"],
        "text": "Got a project in mind? Say 'add to backlog: organize garage' and I'll track it for you.",
        "related_category": "family_management",
    },
    {
        "id": "tip_meal_swap",
        "trigger_tools": ["generate_meal_plan", "save_meal_plan"],
        "text": "Don't feel like what's planned? Say 'swap Wednesday for tacos' to change the meal plan.",
        "related_category": "groceries",
    },
    {
        "id": "tip_chore_pref",
        "trigger_tools": ["complete_chore", "skip_chore"],
        "text": "Want to customize? Say 'I like to vacuum on Wednesdays' and I'll remember your preferences.",
        "related_category": "chores",
    },
    {
        "id": "tip_quiet_day",
        "trigger_tools": ["complete_chore", "skip_chore", "start_laundry"],
        "text": "Need a break? Say 'quiet day' to pause all proactive reminders for today.",
        "related_category": "chores",
    },
    {
        "id": "tip_big_picture",
        "trigger_tools": ["get_budget_summary", "get_calendar_events", "get_action_items"],
        "text": "Try asking 'how's our week looking?' and I'll connect budget, calendar, meals, and tasks into one big picture.",
        "related_category": "big_picture",
    },
    {
        "id": "tip_meeting_prep",
        "trigger_tools": ["get_action_items", "rollover_incomplete_items", "create_meeting"],
        "text": "Say 'prep me for our family meeting' and I'll build a full agenda with budget, calendar, action items, and priorities.",
        "related_category": "big_picture",
    },
    {
        "id": "tip_afford",
        "trigger_tools": ["search_transactions", "get_budget_summary"],
        "text": "Wondering about a purchase? Ask 'can we afford to eat out this weekend?' and I'll check budget, calendar, and meal plan together.",
        "related_category": "big_picture",
    },
]

# ---------------------------------------------------------------------------
# Usage counter persistence
# ---------------------------------------------------------------------------

_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
_COUNTERS_FILE = _DATA_DIR / "usage_counters.json"
_usage_counters: dict[str, dict] = {}

_CATEGORY_KEYS = [cat["key"] for cat in HELP_CATEGORIES]


def _load_counters() -> None:
    """Load usage counters from JSON file."""
    global _usage_counters
    try:
        if _COUNTERS_FILE.exists():
            _usage_counters = json.loads(_COUNTERS_FILE.read_text())
    except Exception as e:
        logger.warning("Failed to load usage counters: %s", e)
        _usage_counters = {}


def _save_counters() -> None:
    """Save usage counters atomically."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _COUNTERS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_usage_counters, indent=2))
        tmp.replace(_COUNTERS_FILE)
    except Exception as e:
        logger.warning("Failed to save usage counters: %s", e)


def _ensure_phone(phone: str) -> dict:
    """Ensure a phone entry exists in counters and return it."""
    if phone not in _usage_counters:
        _usage_counters[phone] = {k: 0 for k in _CATEGORY_KEYS}
        _usage_counters[phone]["_last_tip"] = ""
    return _usage_counters[phone]


def record_usage(phone: str, tool_name: str) -> None:
    """Record a tool call for usage tracking."""
    category = TOOL_TO_CATEGORY.get(tool_name)
    if not category:
        return
    entry = _ensure_phone(phone)
    entry[category] = entry.get(category, 0) + 1
    _save_counters()


def get_underused_categories(phone: str) -> list[str]:
    """Return category keys with zero usage, in help menu order."""
    entry = _ensure_phone(phone)
    return [k for k in _CATEGORY_KEYS if entry.get(k, 0) == 0]


# ---------------------------------------------------------------------------
# Help menu generation
# ---------------------------------------------------------------------------

def get_help(phone: str = "") -> str:
    """Build the personalized help menu.

    Tries to fetch live data for personalization; falls back to static examples.
    If phone is provided, appends a "Haven't tried yet" section for unused categories.
    """
    lines = ["Here's everything I can help with! Try any of these:\n"]

    for cat in HELP_CATEGORIES:
        examples = cat["static_examples"]

        # Try live personalization
        if cat["personalize_from"]:
            try:
                live = _personalize(cat["personalize_from"], cat["key"])
                if live:
                    examples = live
            except Exception as e:
                logger.debug("Personalization failed for %s: %s", cat["key"], e)

        lines.append(f'{cat["icon"]} *{cat["name"]}*')
        lines.append(cat["capabilities"])
        for ex in examples[:2]:
            lines.append(f'\u2022 "{ex}"')
        lines.append("")

    # Usage-aware "haven't tried" section
    if phone:
        unused = get_underused_categories(phone)
        if unused:
            unused_cats = [c for c in HELP_CATEGORIES if c["key"] in unused]
            if unused_cats:
                lines.append("\u2728 *Haven't tried yet:*")
                for cat in unused_cats:
                    ex = cat["static_examples"][0] if cat["static_examples"] else ""
                    lines.append(f'{cat["icon"]} {cat["name"]} \u2014 try: "{ex}"')
                lines.append("")

    lines.append("Just type any of these or ask me in your own words!")
    return "\n".join(lines)


def _personalize(tool_name: str, category_key: str) -> list[str] | None:
    """Fetch live data for personalized examples. Returns list of example strings or None."""
    if tool_name == "list_cookbooks":
        from src.tools import recipes
        result = recipes.list_cookbooks()
        if isinstance(result, str) and "cookbook" in result.lower():
            return None  # fallback — can't parse
        return None  # static examples are good enough for cookbooks

    if tool_name == "get_budget_summary":
        from src.tools import ynab
        result = ynab.get_budget_summary("", "")
        if isinstance(result, str) and "budget" in result.lower():
            # Extract category names from the result
            return None  # static examples are family-specific enough
        return None

    if tool_name == "get_staple_items":
        from src.tools import notion
        result = notion.get_staple_items()
        if isinstance(result, str) and len(result) > 10:
            return None  # static examples are family-specific enough
        return None

    return None


# ---------------------------------------------------------------------------
# Contextual tips
# ---------------------------------------------------------------------------

def get_contextual_tip(tools_used: list[str], phone: str = "") -> str | None:
    """Return a contextual tip based on tools used, or None.

    Prefers tips about underused categories when phone is provided.
    Avoids repeating the last tip shown to this user.
    """
    # Find all matching tips
    matching = []
    for tip in TIP_DEFINITIONS:
        if any(t in tools_used for t in tip["trigger_tools"]):
            matching.append(tip)

    if not matching:
        return None

    last_tip = ""
    underused = []
    if phone:
        entry = _ensure_phone(phone)
        last_tip = entry.get("_last_tip", "")
        underused = get_underused_categories(phone)

    # Filter out the last tip shown
    if last_tip:
        filtered = [t for t in matching if t["id"] != last_tip]
        if filtered:
            matching = filtered

    # Prefer tips about underused categories
    if underused:
        underused_tips = [t for t in matching if t["related_category"] in underused]
        if underused_tips:
            matching = underused_tips

    tip = random.choice(matching)

    # Save last tip
    if phone:
        entry = _ensure_phone(phone)
        entry["_last_tip"] = tip["id"]
        _save_counters()

    return tip["text"]


# Load counters on module import
_load_counters()
