"""Claude AI assistant core — system prompt, tool definitions, and message handling."""

import json
import logging
from datetime import datetime

import httpx

from src import context, conversation, drive_times, preferences, routines
from src.ai_provider import create_message as ai_create_message
from src.config import (
    ALL_CALENDAR_NAMES,
    DEFAULT_CALENDAR,
    ENABLED_INTEGRATIONS,
    FAMILY_CONFIG,
    PHONE_TO_NAME,
    TIMEZONE,
)
from src.integrations import get_tools_for_integrations
from src.prompts import render_system_prompt, render_tool_descriptions
from src.tool_resilience import audit_tool_result, execute_with_retry
from src.tools import (
    amazon_sync,
    calendar,
    chores,
    discovery,
    downshiftology,
    email_sync,
    laundry,
    notion,
    nudges,
    outlook,
    proactive,
    receipt,
    recipes,
    ynab,
)

logger = logging.getLogger(__name__)

# Module-level storage for images in the current conversation.
# Set by handle_message, consumed by extract_and_save_recipe tool handler.
# This avoids passing the large base64 payload through Claude's tool-call JSON.
# For multi-page recipes, images accumulate until the tool is called.
_current_image_data: dict | None = None  # most recent image (single-page fast path)
_buffered_images: list[dict] = []  # accumulated images for multi-page recipes

# Track phones that have received the welcome message (resets on container restart)
_welcomed_phones: set[str] = set()


# ---------------------------------------------------------------------------
# Tool definitions for Claude
# ---------------------------------------------------------------------------

# Compute enabled tools from integration registry
_enabled_tool_names: set[str] = set(get_tools_for_integrations(ENABLED_INTEGRATIONS))
_enabled_tools_frozen = frozenset(_enabled_tool_names)

_tool_descs = render_tool_descriptions(FAMILY_CONFIG, enabled_tools=_enabled_tools_frozen) if FAMILY_CONFIG else {}

_ALL_TOOLS = [
    {
        "name": "get_calendar_events",
        "description": _tool_descs.get("get_calendar_events", "get_calendar_events"),
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days to look ahead. Default 7.",
                    "default": 7,
                },
                "calendar_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        f"Which calendars to read: '{FAMILY_CONFIG.get('partner1_name_lower', 'partner1')}', "
                        f"'{FAMILY_CONFIG.get('partner2_name_lower', 'partner2')}', 'family'. Default all."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_outlook_events",
        "description": _tool_descs.get("get_outlook_events", "get_outlook_events"),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format. Defaults to today.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_action_items",
        "description": _tool_descs.get("get_action_items", "get_action_items"),
        "input_schema": {
            "type": "object",
            "properties": {
                "assignee": {
                    "type": "string",
                    "description": (
                        f"Filter by assignee name (e.g., "
                        f"'{FAMILY_CONFIG.get('partner1_name', 'Partner1')}', "
                        f"'{FAMILY_CONFIG.get('partner2_name', 'Partner2')}'). Empty for all."
                    ),
                },
                "status": {
                    "type": "string",
                    "description": (
                        "Filter by status: 'Not Started', 'In Progress', 'Done', or 'open' for all non-done items."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "add_action_item",
        "description": _tool_descs.get("add_action_item", "add_action_item"),
        "input_schema": {
            "type": "object",
            "properties": {
                "assignee": {
                    "type": "string",
                    "description": (
                        f"Who this is assigned to "
                        f"({FAMILY_CONFIG.get('partner1_name', 'Partner1')} or "
                        f"{FAMILY_CONFIG.get('partner2_name', 'Partner2')})."
                    ),
                },
                "description": {"type": "string", "description": "What needs to be done."},
                "due_context": {
                    "type": "string",
                    "description": "When: 'This Week', 'Ongoing', or 'Someday'. Default 'This Week'.",
                    "default": "This Week",
                },
            },
            "required": ["assignee", "description"],
        },
    },
    {
        "name": "complete_action_item",
        "description": _tool_descs.get("complete_action_item", "complete_action_item"),
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": (
                        "The Notion page UUID of the action item, or its "
                        "description text (e.g., 'Call preschool'). UUIDs "
                        "are preferred — use get_action_items to find them."
                    ),
                },
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "add_topic",
        "description": _tool_descs.get("add_topic", "add_topic"),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "The topic to discuss."},
            },
            "required": ["description"],
        },
    },
    {
        "name": "get_family_profile",
        "description": _tool_descs.get("get_family_profile", "get_family_profile"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "update_family_profile",
        "description": _tool_descs.get("update_family_profile", "update_family_profile"),
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": (
                        "Which section to update: 'Preferences', "
                        "'Recurring Agenda Topics', 'Members', "
                        "'Childcare Schedule', 'Routine Templates', "
                        "or 'Configuration'."
                    ),
                },
                "content": {"type": "string", "description": "The information to add."},
            },
            "required": ["section", "content"],
        },
    },
    {
        "name": "create_meeting",
        "description": _tool_descs.get("create_meeting", "create_meeting"),
        "input_schema": {
            "type": "object",
            "properties": {
                "meeting_date": {"type": "string", "description": "Date in YYYY-MM-DD format. Defaults to today."},
            },
            "required": [],
        },
    },
    {
        "name": "rollover_incomplete_items",
        "description": _tool_descs.get("rollover_incomplete_items", "rollover_incomplete_items"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "save_meal_plan",
        "description": _tool_descs.get("save_meal_plan", "save_meal_plan"),
        "input_schema": {
            "type": "object",
            "properties": {
                "week_start": {"type": "string", "description": "Monday date in YYYY-MM-DD format."},
                "plan_content": {"type": "string", "description": "The meal plan text (one line per day)."},
                "grocery_list": {"type": "string", "description": "Grocery list items, one per line."},
            },
            "required": ["week_start", "plan_content", "grocery_list"],
        },
    },
    {
        "name": "get_meal_plan",
        "description": _tool_descs.get("get_meal_plan", "get_meal_plan"),
        "input_schema": {
            "type": "object",
            "properties": {
                "week_start": {
                    "type": "string",
                    "description": ("Monday date in YYYY-MM-DD format. Empty for most recent."),
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_budget_summary",
        "description": _tool_descs.get("get_budget_summary", "get_budget_summary"),
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {
                    "type": "string",
                    "description": ("Month in YYYY-MM-DD format (first of month). Defaults to current month."),
                },
                "category": {
                    "type": "string",
                    "description": ("Optional category name to filter to (e.g., 'Dining Out', 'Groceries')."),
                },
            },
            "required": [],
        },
    },
    # --- YNAB transaction tools (US1) ---
    {
        "name": "search_transactions",
        "description": _tool_descs.get("search_transactions", "search_transactions"),
        "input_schema": {
            "type": "object",
            "properties": {
                "payee": {"type": "string", "description": "Payee name to search for (fuzzy match)."},
                "category": {"type": "string", "description": "Category name to filter by."},
                "since_date": {"type": "string", "description": "ISO date floor (default: first of current month)."},
                "uncategorized_only": {
                    "type": "boolean",
                    "description": ("If true, return only uncategorized transactions."),
                },
            },
            "required": [],
        },
    },
    {
        "name": "recategorize_transaction",
        "description": _tool_descs.get("recategorize_transaction", "recategorize_transaction"),
        "input_schema": {
            "type": "object",
            "properties": {
                "payee": {"type": "string", "description": "Payee name to find the transaction."},
                "amount": {"type": "number", "description": "Dollar amount to match (helps disambiguate)."},
                "date": {"type": "string", "description": "Date to match (ISO format)."},
                "new_category": {"type": "string", "description": "Target category name (fuzzy matched)."},
            },
            "required": ["new_category"],
        },
    },
    {
        "name": "create_transaction",
        "description": _tool_descs.get("create_transaction", "create_transaction"),
        "input_schema": {
            "type": "object",
            "properties": {
                "payee": {"type": "string", "description": "Payee/merchant name."},
                "amount": {
                    "type": "number",
                    "description": ("Dollar amount (positive number — system makes it negative for outflow)."),
                },
                "category": {"type": "string", "description": "Category name (fuzzy matched)."},
                "date": {"type": "string", "description": "ISO date (default: today)."},
                "memo": {"type": "string", "description": "Optional memo/note."},
                "account": {"type": "string", "description": "Account name (default: primary checking)."},
            },
            "required": ["payee", "amount", "category"],
        },
    },
    # --- YNAB budget rebalancing tools (US3) ---
    {
        "name": "update_category_budget",
        "description": _tool_descs.get("update_category_budget", "update_category_budget"),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category name (fuzzy matched)."},
                "amount": {"type": "number", "description": "Dollar amount to add (positive) or subtract (negative)."},
            },
            "required": ["category", "amount"],
        },
    },
    {
        "name": "move_money",
        "description": _tool_descs.get("move_money", "move_money"),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_category": {"type": "string", "description": "Source category name (fuzzy matched)."},
                "to_category": {"type": "string", "description": "Destination category name (fuzzy matched)."},
                "amount": {"type": "number", "description": "Dollar amount to move (positive number)."},
            },
            "required": ["from_category", "to_category", "amount"],
        },
    },
    # --- Backlog tools (US5) ---
    {
        "name": "get_backlog_items",
        "description": _tool_descs.get("get_backlog_items", "get_backlog_items"),
        "input_schema": {
            "type": "object",
            "properties": {
                "assignee": {
                    "type": "string",
                    "description": "Filter by assignee. Default empty (all).",
                },
                "status": {
                    "type": "string",
                    "description": ("Filter by status: 'Not Started', 'In Progress', 'Done', or 'open'."),
                },
            },
            "required": [],
        },
    },
    {
        "name": "add_backlog_item",
        "description": _tool_descs.get("add_backlog_item", "add_backlog_item"),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "What needs to be done."},
                "category": {
                    "type": "string",
                    "description": (
                        "Category: 'Home Improvement', 'Personal Growth', 'Side Work', 'Exercise', or 'Other'."
                    ),
                    "default": "Other",
                },
                "assignee": {
                    "type": "string",
                    "description": f"Who this is for. Default '{FAMILY_CONFIG.get('partner2_name', 'Partner2')}'.",
                    "default": FAMILY_CONFIG.get("partner2_name", "Partner2"),
                },
                "priority": {
                    "type": "string",
                    "description": ("'High', 'Medium', or 'Low'. Default 'Medium'."),
                    "default": "Medium",
                },
            },
            "required": ["description"],
        },
    },
    {
        "name": "complete_backlog_item",
        "description": _tool_descs.get("complete_backlog_item", "complete_backlog_item"),
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": (
                        "The Notion page UUID of the backlog item, or "
                        "its description text. UUIDs are preferred — "
                        "use get_backlog_items to find them."
                    ),
                },
            },
            "required": ["page_id"],
        },
    },
    # --- Routine templates (US5) ---
    {
        "name": "get_routine_templates",
        "description": _tool_descs.get("get_routine_templates", "get_routine_templates"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # --- Calendar write (US5) ---
    {
        "name": "write_calendar_blocks",
        "description": _tool_descs.get("write_calendar_blocks", "write_calendar_blocks"),
        "input_schema": {
            "type": "object",
            "properties": {
                "blocks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": ("Event title (e.g., 'Chore block', 'Rest time')"),
                            },
                            "start_time": {
                                "type": "string",
                                "description": (
                                    "ISO datetime in 24-hour format with "
                                    "TZ offset. 1 PM=13, 2 PM=14, etc. "
                                    "Example: '2026-02-23T14:30:00-08:00' "
                                    "for 2:30 PM PT."
                                ),
                            },
                            "end_time": {
                                "type": "string",
                                "description": (
                                    "ISO datetime in 24-hour format with TZ offset (same rules as start_time)."
                                ),
                            },
                            "color_category": {
                                "type": "string",
                                "description": (
                                    "Category for color coding: "
                                    "'chores', 'rest', 'development', "
                                    "'exercise', 'side_work', "
                                    "or 'backlog'."
                                ),
                            },
                        },
                        "required": ["summary", "start_time", "end_time", "color_category"],
                    },
                    "description": "List of time blocks to create as calendar events.",
                },
            },
            "required": ["blocks"],
        },
    },
    # --- Quick reminder/event tool ---
    {
        "name": "create_quick_event",
        "description": _tool_descs.get("create_quick_event", "create_quick_event"),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": (
                        "Event title. Format as 'Sender -> Assignee: "
                        f"task' (e.g., '{FAMILY_CONFIG.get('partner2_name', 'Partner2')} -> "
                        f"{FAMILY_CONFIG.get('partner1_name', 'Partner1')}: pick up dog'). "
                        "If self-reminder, use "
                        f"'{FAMILY_CONFIG.get('partner2_name', 'Partner2')}: dentist appointment'."
                    ),
                },
                "start_time": {
                    "type": "string",
                    "description": (
                        "ISO datetime in 24-hour format with TZ offset. "
                        "1 PM=13, 2 PM=14. Example: "
                        "'2026-02-24T14:30:00-08:00' for 2:30 PM PT. "
                        "Use the date shown at the top of the system "
                        "prompt if not specified."
                    ),
                },
                "end_time": {
                    "type": "string",
                    "description": (
                        "ISO datetime in 24-hour format with TZ offset. Defaults to start + 30 min if omitted."
                    ),
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Original message text for context (e.g., "
                        f"'{FAMILY_CONFIG.get('partner2_name', 'Partner2')} said: remind "
                        f"{FAMILY_CONFIG.get('partner1_name', 'Partner1')} to pick up the "
                        "dog at 12:30')."
                    ),
                },
                "reminder_minutes": {
                    "type": "number",
                    "description": ("Minutes before event to send popup reminder. Default 15."),
                    "default": 15,
                },
                "recurrence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "RRULE strings for recurring events. Examples: "
                        "['RRULE:FREQ=WEEKLY;BYDAY=MO'] for weekly Monday, "
                        "['RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU'] for biweekly Tuesday, "
                        "['RRULE:FREQ=MONTHLY;BYDAY=1FR'] for first Friday of month, "
                        "['RRULE:FREQ=WEEKLY;BYDAY=TU,TH'] for Tuesdays and Thursdays, "
                        "['RRULE:FREQ=DAILY'] for every day. "
                        "Add COUNT=N for N occurrences or UNTIL=YYYYMMDDT235959Z for end date. "
                        "Omit this parameter entirely for one-time events."
                    ),
                },
                "calendar_name": {
                    "type": "string",
                    "enum": ALL_CALENDAR_NAMES,
                    "description": "Target calendar. Default: family.",
                    "default": "family",
                },
                "location": {
                    "type": "string",
                    "description": (
                        "Physical address or place name for the event. "
                        "Shown in calendar event details and enables map links on mobile."
                    ),
                },
            },
            "required": ["summary", "start_time"],
        },
    },
    # --- Delete / manage calendar events ---
    {
        "name": "delete_calendar_event",
        "description": _tool_descs.get("delete_calendar_event", "delete_calendar_event"),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": (
                        "Google Calendar event ID. Get this from get_calendar_events or get_events_for_date results."
                    ),
                },
                "calendar_name": {
                    "type": "string",
                    "enum": ALL_CALENDAR_NAMES,
                    "description": "Target calendar. Default: family.",
                    "default": "family",
                },
                "cancel_mode": {
                    "type": "string",
                    "enum": ["single", "all_following"],
                    "description": (
                        "'single' to cancel just this occurrence. "
                        "'all_following' to delete the entire recurring series. "
                        "Default: single."
                    ),
                    "default": "single",
                },
            },
            "required": ["event_id"],
        },
    },
    # --- List recurring events ---
    {
        "name": "list_recurring_events",
        "description": _tool_descs.get("list_recurring_events", "list_recurring_events"),
        "input_schema": {
            "type": "object",
            "properties": {
                "calendar_name": {
                    "type": "string",
                    "enum": ALL_CALENDAR_NAMES,
                    "description": "Calendar to check. Default: family.",
                    "default": "family",
                },
            },
        },
    },
    # --- Grocery tools (US3 + US6) ---
    {
        "name": "get_grocery_history",
        "description": _tool_descs.get("get_grocery_history", "get_grocery_history"),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": (
                        "Filter by category: 'Produce', 'Meat', "
                        "'Dairy', 'Pantry', 'Frozen', 'Bakery', "
                        "'Beverages'. Empty for all."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_staple_items",
        "description": _tool_descs.get("get_staple_items", "get_staple_items"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "push_grocery_list",
        "description": _tool_descs.get("push_grocery_list", "push_grocery_list"),
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "List of grocery items to add (e.g., ['Chicken breast', 'Rice', 'Stir-fry veggies'])."
                    ),
                },
            },
            "required": ["items"],
        },
    },
    # --- Recipe tools (US1) ---
    {
        "name": "extract_and_save_recipe",
        "description": _tool_descs.get("extract_and_save_recipe", "extract_and_save_recipe"),
        "input_schema": {
            "type": "object",
            "properties": {
                "cookbook_name": {
                    "type": "string",
                    "description": ("Name of the cookbook (e.g., 'The Keto Book'). Defaults to 'Uncategorized'."),
                },
            },
            "required": [],
        },
    },
    {
        "name": "search_recipes",
        "description": _tool_descs.get("search_recipes", "search_recipes"),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (recipe name, ingredient, or description)."},
                "cookbook_name": {"type": "string", "description": "Filter by cookbook name. Empty for all."},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Filter by tags: Keto, Kid-Friendly, Quick, "
                        "Vegetarian, Comfort Food, Soup, Salad, "
                        "Pasta, Meat, Seafood."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_recipe_details",
        "description": _tool_descs.get("get_recipe_details", "get_recipe_details"),
        "input_schema": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string", "description": "The Notion page ID of the recipe."},
            },
            "required": ["recipe_id"],
        },
    },
    {
        "name": "recipe_to_grocery_list",
        "description": _tool_descs.get("recipe_to_grocery_list", "recipe_to_grocery_list"),
        "input_schema": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string", "description": "The Notion page ID of the recipe."},
                "servings_multiplier": {
                    "type": "number",
                    "description": "Multiply ingredient quantities (e.g., 2.0 for double). Default 1.0.",
                    "default": 1.0,
                },
            },
            "required": ["recipe_id"],
        },
    },
    {
        "name": "list_cookbooks",
        "description": _tool_descs.get("list_cookbooks", "list_cookbooks"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # --- Downshiftology recipe tools (Feature 005) ---
    {
        "name": "search_downshiftology",
        "description": _tool_descs.get("search_downshiftology", "search_downshiftology"),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": ("Free-text search term (e.g., 'chicken', 'sweet potato')."),
                },
                "course": {
                    "type": "string",
                    "description": (
                        "Course type: dinner, breakfast, appetizer, side-dish, salad, soup, snack, dessert, drinks."
                    ),
                },
                "cuisine": {
                    "type": "string",
                    "description": (
                        "Cuisine: american, mexican, italian, "
                        "mediterranean, asian, french, indian, "
                        "greek, middle-eastern."
                    ),
                },
                "dietary": {
                    "type": "string",
                    "description": (
                        "Dietary preference: keto, paleo, whole30, gluten-free, dairy-free, vegan, vegetarian."
                    ),
                },
                "max_time": {
                    "type": "number",
                    "description": ("Maximum total time in minutes (e.g., 30 for quick meals)."),
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_downshiftology_details",
        "description": _tool_descs.get("get_downshiftology_details", "get_downshiftology_details"),
        "input_schema": {
            "type": "object",
            "properties": {
                "result_number": {
                    "type": "number",
                    "description": ("Number from the most recent Downshiftology search results (1-based)."),
                },
            },
            "required": ["result_number"],
        },
    },
    {
        "name": "import_downshiftology_recipe",
        "description": _tool_descs.get("import_downshiftology_recipe", "import_downshiftology_recipe"),
        "input_schema": {
            "type": "object",
            "properties": {
                "result_number": {
                    "type": "number",
                    "description": ("Number from most recent search results (e.g., 2)."),
                },
                "recipe_name": {
                    "type": "string",
                    "description": ("Recipe name to search and import (alternative to number)."),
                },
            },
            "required": [],
        },
    },
    # --- Nudge tools (Feature 003) ---
    {
        "name": "set_quiet_day",
        "description": _tool_descs.get("set_quiet_day", "set_quiet_day"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "complete_chore",
        "description": _tool_descs.get("complete_chore", "complete_chore"),
        "input_schema": {
            "type": "object",
            "properties": {
                "chore_name": {
                    "type": "string",
                    "description": ("Name of the completed chore (matched against Chores DB)."),
                },
            },
            "required": ["chore_name"],
        },
    },
    {
        "name": "skip_chore",
        "description": _tool_descs.get("skip_chore", "skip_chore"),
        "input_schema": {
            "type": "object",
            "properties": {
                "chore_name": {"type": "string", "description": "Name of the skipped chore."},
            },
            "required": ["chore_name"],
        },
    },
    {
        "name": "start_laundry",
        "description": _tool_descs.get("start_laundry", "start_laundry"),
        "input_schema": {
            "type": "object",
            "properties": {
                "washer_minutes": {
                    "type": "integer",
                    "description": "Washer cycle duration in minutes. Default 45.",
                    "default": 45,
                },
                "dryer_minutes": {
                    "type": "integer",
                    "description": "Dryer cycle duration in minutes. Default 60.",
                    "default": 60,
                },
            },
            "required": [],
        },
    },
    {
        "name": "advance_laundry",
        "description": _tool_descs.get("advance_laundry", "advance_laundry"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "cancel_laundry",
        "description": _tool_descs.get("cancel_laundry", "cancel_laundry"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "set_chore_preference",
        "description": _tool_descs.get("set_chore_preference", "set_chore_preference"),
        "input_schema": {
            "type": "object",
            "properties": {
                "chore_name": {"type": "string", "description": "Chore to update preferences for."},
                "preference": {
                    "type": "string",
                    "description": (
                        "'like', 'neutral', or 'dislike'. Use 'like' for 'I enjoy...', 'dislike' for 'I hate...', etc."
                    ),
                    "enum": ["like", "neutral", "dislike"],
                },
                "preferred_days": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Preferred days of the week (e.g., ['Monday', 'Wednesday']).",
                },
                "frequency": {
                    "type": "string",
                    "description": "How often: 'daily', 'every_other_day', 'weekly', 'biweekly', 'monthly'.",
                    "enum": ["daily", "every_other_day", "weekly", "biweekly", "monthly"],
                },
            },
            "required": ["chore_name"],
        },
    },
    {
        "name": "get_chore_history",
        "description": _tool_descs.get("get_chore_history", "get_chore_history"),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back. Default 7.",
                    "default": 7,
                },
            },
            "required": [],
        },
    },
    # --- Proactive tools (US2, US3) ---
    {
        "name": "check_reorder_items",
        "description": _tool_descs.get("check_reorder_items", "check_reorder_items"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "confirm_groceries_ordered",
        "description": _tool_descs.get("confirm_groceries_ordered", "confirm_groceries_ordered"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "generate_meal_plan",
        "description": _tool_descs.get("generate_meal_plan", "generate_meal_plan"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "handle_meal_swap",
        "description": _tool_descs.get("handle_meal_swap", "handle_meal_swap"),
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Current meal plan array (from generate_meal_plan result).",
                },
                "day": {"type": "string", "description": "Day to swap (e.g., 'Wednesday')."},
                "new_meal": {"type": "string", "description": "New meal name (e.g., 'Tacos')."},
            },
            "required": ["plan", "day", "new_meal"],
        },
    },
    # --- Feature discovery (Feature 006) ---
    {
        "name": "get_help",
        "description": _tool_descs.get("get_help", "get_help"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "check_system_logs",
        "description": _tool_descs.get("check_system_logs", "check_system_logs"),
        "input_schema": {
            "type": "object",
            "properties": {
                "minutes": {
                    "type": "integer",
                    "description": "How many minutes of recent logs to check. Default 10.",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
    # Amazon-YNAB Sync (Feature 010)
    {
        "name": "amazon_sync_status",
        "description": _tool_descs.get("amazon_sync_status", "amazon_sync_status"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "amazon_sync_trigger",
        "description": _tool_descs.get("amazon_sync_trigger", "amazon_sync_trigger"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "amazon_spending_breakdown",
        "description": _tool_descs.get("amazon_spending_breakdown", "amazon_spending_breakdown"),
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month in YYYY-MM format. Defaults to current month."},
            },
            "required": [],
        },
    },
    {
        "name": "amazon_set_auto_split",
        "description": _tool_descs.get("amazon_set_auto_split", "amazon_set_auto_split"),
        "input_schema": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "description": "True to enable auto-split, False to disable."},
            },
            "required": ["enabled"],
        },
    },
    {
        "name": "amazon_undo_split",
        "description": _tool_descs.get("amazon_undo_split", "amazon_undo_split"),
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_index": {
                    "type": "integer",
                    "description": "Index of the auto-split to undo (1 = most recent). Default 1.",
                    "default": 1,
                },
            },
            "required": [],
        },
    },
    # Budget Maintenance (Feature 012: Smart Budget Health)
    {
        "name": "budget_health_check",
        "description": _tool_descs.get("budget_health_check", "budget_health_check"),
        "input_schema": {
            "type": "object",
            "properties": {
                "lookback_months": {
                    "type": "integer",
                    "description": ("Number of months to analyze (default 3, max 12). Use 6+ for spiky categories."),
                    "default": 3,
                },
                "drift_threshold": {
                    "type": "number",
                    "description": (
                        "Minimum drift percentage to flag (default 30). Lower values catch smaller misalignments."
                    ),
                    "default": 30,
                },
            },
            "required": [],
        },
    },
    {
        "name": "apply_goal_suggestion",
        "description": _tool_descs.get("apply_goal_suggestion", "apply_goal_suggestion"),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category name (fuzzy matched).",
                },
                "amount": {
                    "type": "number",
                    "description": (
                        "New goal amount in dollars. If omitted, uses "
                        "the recommended amount from the last "
                        "health check."
                    ),
                },
                "apply_all": {
                    "type": "boolean",
                    "description": (
                        "If true, apply all pending suggestions at once. Ignores category and amount params."
                    ),
                    "default": False,
                },
            },
            "required": [],
        },
    },
    {
        "name": "allocate_bonus",
        "description": _tool_descs.get("allocate_bonus", "allocate_bonus"),
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Dollar amount to allocate.",
                },
                "description": {
                    "type": "string",
                    "description": "What the income is from (e.g., 'Q1 bonus', 'stock vesting'). Optional.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "approve_allocation",
        "description": _tool_descs.get("approve_allocation", "approve_allocation"),
        "input_schema": {
            "type": "object",
            "properties": {
                "adjustments": {
                    "type": "string",
                    "description": (
                        "Optional free-text adjustments before executing (e.g., 'put $3000 in emergency fund instead')."
                    ),
                },
            },
            "required": [],
        },
    },
    # Email-YNAB Sync (Feature 011: PayPal, Venmo, Apple)
    {
        "name": "email_sync_trigger",
        "description": _tool_descs.get("email_sync_trigger", "email_sync_trigger"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "email_sync_status",
        "description": _tool_descs.get("email_sync_status", "email_sync_status"),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "email_set_auto_categorize",
        "description": _tool_descs.get("email_set_auto_categorize", "email_set_auto_categorize"),
        "input_schema": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "description": "True to enable auto-categorize, False to disable."},
            },
            "required": ["enabled"],
        },
    },
    {
        "name": "email_undo_categorize",
        "description": _tool_descs.get("email_undo_categorize", "email_undo_categorize"),
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_index": {
                    "type": "integer",
                    "description": "Index of the auto-categorization to undo (1 = most recent). Default 1.",
                    "default": 1,
                },
            },
            "required": [],
        },
    },
    # User Preference Persistence (Feature 013)
    {
        "name": "save_preference",
        "description": _tool_descs.get("save_preference", "save_preference"),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": (
                        "Preference category: 'notification_optout' "
                        "(suppress proactive nudges), 'topic_filter' "
                        "(exclude content from briefings), "
                        "'communication_style' (change how bot "
                        "responds), or 'quiet_hours' "
                        "(time-based suppression)."
                    ),
                    "enum": ["notification_optout", "topic_filter", "communication_style", "quiet_hours"],
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Human-readable summary of the preference (e.g., 'No grocery reminders unless asked')."
                    ),
                },
                "raw_text": {
                    "type": "string",
                    "description": "The user's original words that expressed this preference.",
                },
            },
            "required": ["category", "description", "raw_text"],
        },
    },
    {
        "name": "list_preferences",
        "description": _tool_descs.get("list_preferences", "list_preferences"),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "remove_preference",
        "description": _tool_descs.get("remove_preference", "remove_preference"),
        "input_schema": {
            "type": "object",
            "properties": {
                "search_text": {
                    "type": "string",
                    "description": (
                        "Text to match against stored preferences (fuzzy). Use 'ALL' to clear all preferences."
                    ),
                },
            },
            "required": ["search_text"],
        },
    },
    # Context-Aware Bot (Feature 014)
    {
        "name": "get_daily_context",
        "description": _tool_descs.get("get_daily_context", "get_daily_context"),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "save_routine",
        "description": _tool_descs.get("save_routine", "save_routine"),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Routine name (e.g., 'morning skincare', 'bedtime'). Case-insensitive.",
                },
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ordered list of step descriptions. Example: ['Wash face', 'Toner', 'Moisturizer']",
                },
            },
            "required": ["name", "steps"],
        },
    },
    {
        "name": "get_routine",
        "description": _tool_descs.get("get_routine", "get_routine"),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": (
                        "Routine name to retrieve (e.g., 'morning skincare'). Use 'all' to list all routine names."
                    ),
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "delete_routine",
        "description": _tool_descs.get("delete_routine", "delete_routine"),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Routine name to delete (e.g., 'morning skincare'). Case-insensitive.",
                },
            },
            "required": ["name"],
        },
    },
    # Drive Time Tools (Feature 017)
    {
        "name": "get_drive_times",
        "description": _tool_descs.get("get_drive_times", "get_drive_times"),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "save_drive_time",
        "description": _tool_descs.get("save_drive_time", "save_drive_time"),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": (
                        "Location name (e.g., 'gym', 'school', "
                        "'grandma'). Articles like 'the' are "
                        "stripped automatically."
                    ),
                },
                "minutes": {
                    "type": "integer",
                    "description": "One-way drive time from home in minutes (1-120).",
                },
            },
            "required": ["location", "minutes"],
        },
    },
    {
        "name": "delete_drive_time",
        "description": _tool_descs.get("delete_drive_time", "delete_drive_time"),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location name to remove (e.g., 'gym'). Case-insensitive.",
                },
            },
            "required": ["location"],
        },
    },
    # Receipt → YNAB categorization (Feature 027)
    {
        "name": "process_receipt",
        "description": _tool_descs.get("process_receipt", "process_receipt"),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "confirm_receipt_categorization",
        "description": _tool_descs.get("confirm_receipt_categorization", "confirm_receipt_categorization"),
        "input_schema": {
            "type": "object",
            "properties": {
                "category_override": {
                    "type": "string",
                    "description": (
                        "Different category name if user rejects the suggestion. "
                        "Leave empty to confirm the suggested category."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "retry_receipt_match",
        "description": _tool_descs.get("retry_receipt_match", "retry_receipt_match"),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "split_receipt_transaction",
        "description": _tool_descs.get("split_receipt_transaction", "split_receipt_transaction"),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

# Filter tools to only include those for enabled integrations
TOOLS = [t for t in _ALL_TOOLS if t["name"] in _enabled_tool_names]
logger.info(
    "Tools: %d/%d enabled (integrations: %s)", len(TOOLS), len(_ALL_TOOLS), ", ".join(sorted(ENABLED_INTEGRATIONS))
)

# Color mapping for calendar blocks
_COLOR_MAP = {
    "chores": calendar.COLOR_CHORES,
    "rest": calendar.COLOR_REST,
    "development": calendar.COLOR_DEVELOPMENT,
    "exercise": calendar.COLOR_EXERCISE,
    "side_work": calendar.COLOR_SIDE_WORK,
    "backlog": calendar.COLOR_BACKLOG,
}


def _handle_write_calendar_blocks(**kw) -> str:
    """Handle the write_calendar_blocks tool call."""
    blocks = kw.get("blocks", [])
    if not blocks:
        return "No blocks to write."

    events_data = []
    for block in blocks:
        color_id = _COLOR_MAP.get(block.get("color_category", "chores"), calendar.COLOR_CHORES)
        events_data.append(
            {
                "summary": block["summary"],
                "start_time": block["start_time"],
                "end_time": block["end_time"],
                "color_id": color_id,
            }
        )

    created = calendar.batch_create_events(events_data, calendar_name=DEFAULT_CALENDAR)
    p2 = FAMILY_CONFIG.get("partner2_name", "Partner2")
    return f"Created {created} calendar blocks on {p2}'s calendar."


def _handle_push_grocery_list(**kw) -> str:
    """Handle the push_grocery_list tool call."""
    items = kw.get("items", [])
    if not items:
        return "No items to push."
    try:
        from src.tools import anylist_bridge

        return anylist_bridge.push_grocery_list(items)
    except Exception as e:
        logger.warning("AnyList push failed: %s", e)
        return (
            f"AnyList is unavailable ({e}). Please send the grocery "
            "list as a formatted WhatsApp message organized by "
            "store section instead."
        )


def _handle_extract_recipe(**kw) -> dict | str:
    """Handle extract_and_save_recipe using the stored image data.

    Supports multi-page recipes: if multiple images have been buffered,
    all are sent to the extraction function.
    """
    global _current_image_data, _buffered_images
    if not _buffered_images and not _current_image_data:
        return "No image found in this conversation. Please send a photo of the cookbook page first."

    images = _buffered_images if _buffered_images else [_current_image_data]
    cookbook_name = kw.get("cookbook_name", "")

    result = recipes.extract_and_save_recipe(images, cookbook_name)

    # Clear buffer after extraction
    _buffered_images = []
    _current_image_data = None

    return result


def _handle_amazon_sync_trigger() -> str:
    """Handle manual Amazon sync trigger from WhatsApp.

    Sends the detailed suggestion message directly to Partner 2 via WhatsApp
    (bypassing Claude's summarization), then returns a short status to Claude.
    """
    try:
        # Check YNAB first (fast) — skip email parsing if nothing to process
        txns = amazon_sync.find_amazon_transactions()
        if not txns:
            return "No new Amazon transactions to process — all caught up!"

        orders, auth_failed = amazon_sync.get_amazon_orders()
        if auth_failed:
            return (
                "Error: Amazon sync paused — Gmail OAuth token expired. "
                "Ask the operator to re-run setup_calendar.py."
            )
        if not orders:
            return "No Amazon orders found in the last 30 days."

        matched = amazon_sync.match_orders_to_transactions(txns, orders)
        enriched = amazon_sync.enrich_and_classify(matched)
        message = amazon_sync.format_suggestion_message(enriched)
        amazon_sync.set_pending_suggestions(enriched)

        # Send detailed suggestion message directly to Partner 2 (don't let Claude summarize)
        if message:
            send_sync_message_direct(message)

        # Count results for short status
        auto_count = sum(1 for m in enriched if m.get("sync_record") and m["sync_record"].status == "auto_split")
        pending_count = sum(1 for m in enriched if m.get("sync_record") and m["sync_record"].status == "split_pending")
        unmatched_count = sum(1 for m in enriched if m.get("matched_order") is None)

        parts = [f"Amazon sync complete — processed {len(enriched)} transactions."]
        if auto_count:
            parts.append(f"{auto_count} auto-categorized.")
        if pending_count:
            parts.append(f"{pending_count} sent to {FAMILY_CONFIG.get('partner2_name', 'Partner2')} for review.")
        if unmatched_count:
            parts.append(f"{unmatched_count} unmatched (no email found).")
        return " ".join(parts)
    except Exception as e:
        logger.error("Amazon sync trigger failed: %s", e)
        return f"Amazon sync encountered an error: {e}"


def _handle_email_sync_trigger() -> str:
    """Handle manual email sync trigger from WhatsApp.

    Sends the detailed suggestion message directly to Partner 2 via WhatsApp
    (bypassing Claude's summarization), then returns a short status to Claude.
    """
    try:
        result = email_sync.run_email_sync()
        if result is None:
            return "No new PayPal, Venmo, or Apple transactions to process — all caught up!"
        return result
    except Exception as e:
        logger.error("Email sync trigger failed: %s", e)
        return f"Email sync encountered an error: {e}"


def send_sync_message_direct(message: str) -> None:
    """Send a message directly to the primary phone via WhatsApp API (sync, bypasses Claude)."""
    from src.config import PRIMARY_PHONE, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
    from src.whatsapp import _split_message

    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    for chunk in _split_message(message):
        payload = {
            "messaging_product": "whatsapp",
            "to": PRIMARY_PHONE,
            "type": "text",
            "text": {"body": chunk},
        }
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code != 200:
                logger.error("Direct WhatsApp send failed: %s %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("Direct WhatsApp send error: %s", e)


# Map tool names to functions
TOOL_FUNCTIONS = {
    "get_calendar_events": lambda **kw: calendar.get_calendar_events(kw.get("days_ahead", 7), kw.get("calendar_names")),
    "get_outlook_events": lambda **kw: outlook.get_outlook_events(kw.get("date", "")),
    "get_action_items": lambda **kw: notion.get_action_items(kw.get("assignee", ""), kw.get("status", "")),
    "add_action_item": lambda **kw: notion.add_action_item(
        kw["assignee"], kw["description"], kw.get("due_context", "This Week")
    ),
    "complete_action_item": lambda **kw: notion.complete_action_item(kw["page_id"]),
    "add_topic": lambda **kw: notion.add_topic(kw["description"]),
    "get_family_profile": lambda **kw: notion.get_family_profile(),
    "update_family_profile": lambda **kw: notion.update_family_profile(kw["section"], kw["content"]),
    "create_meeting": lambda **kw: notion.create_meeting(kw.get("meeting_date", "")),
    "rollover_incomplete_items": lambda **kw: notion.rollover_incomplete_items(),
    "save_meal_plan": lambda **kw: notion.save_meal_plan(kw["week_start"], kw["plan_content"], kw["grocery_list"]),
    "get_meal_plan": lambda **kw: notion.get_meal_plan(kw.get("week_start", "")),
    "get_budget_summary": lambda **kw: ynab.get_budget_summary(kw.get("month", ""), kw.get("category", "")),
    "search_transactions": lambda **kw: ynab.search_transactions(
        kw.get("payee", ""), kw.get("category", ""), kw.get("since_date", ""), kw.get("uncategorized_only", False)
    ),
    "recategorize_transaction": lambda **kw: ynab.recategorize_transaction(
        kw.get("payee", ""), kw.get("amount", 0), kw.get("date", ""), kw.get("new_category", "")
    ),
    "create_transaction": lambda **kw: ynab.create_transaction(
        kw.get("payee", ""),
        kw.get("amount", 0),
        kw.get("category", ""),
        kw.get("date", ""),
        kw.get("memo", ""),
        kw.get("account", ""),
    ),
    "update_category_budget": lambda **kw: ynab.update_category_budget(kw.get("category", ""), kw.get("amount", 0)),
    "move_money": lambda **kw: ynab.move_money(
        kw.get("from_category", ""), kw.get("to_category", ""), kw.get("amount", 0)
    ),
    # Backlog
    "get_backlog_items": lambda **kw: notion.get_backlog_items(kw.get("assignee", ""), kw.get("status", "")),
    "add_backlog_item": lambda **kw: notion.add_backlog_item(
        kw["description"],
        kw.get("category", "Other"),
        kw.get("assignee", FAMILY_CONFIG.get("partner2_name", "Partner2")),
        kw.get("priority", "Medium"),
    ),
    "complete_backlog_item": lambda **kw: notion.complete_backlog_item(kw["page_id"]),
    # Routine templates
    "get_routine_templates": lambda **kw: notion.get_routine_templates(),
    # Calendar write
    "write_calendar_blocks": _handle_write_calendar_blocks,
    "create_quick_event": lambda **kw: calendar.create_quick_event(
        kw["summary"],
        kw["start_time"],
        kw.get("end_time", ""),
        kw.get("description", ""),
        int(kw.get("reminder_minutes", 15)),
        kw.get("recurrence"),
        kw.get("calendar_name", "family"),
        kw.get("location", ""),
    ),
    "delete_calendar_event": lambda **kw: calendar.delete_calendar_event(
        kw["event_id"],
        kw.get("calendar_name", "family"),
        kw.get("cancel_mode", "single"),
    ),
    "list_recurring_events": lambda **kw: calendar.list_recurring_events(
        kw.get("calendar_name", "family"),
    ),
    # Grocery
    "get_grocery_history": lambda **kw: notion.get_grocery_history(kw.get("category", "")),
    "get_staple_items": lambda **kw: notion.get_staple_items(),
    "push_grocery_list": _handle_push_grocery_list,
    # Recipes
    "extract_and_save_recipe": lambda **kw: _handle_extract_recipe(**kw),
    "search_recipes": lambda **kw: recipes.search_recipes(
        kw.get("query", ""), kw.get("cookbook_name", ""), kw.get("tags")
    ),
    "get_recipe_details": lambda **kw: recipes.get_recipe_details(kw["recipe_id"]),
    "recipe_to_grocery_list": lambda **kw: recipes.recipe_to_grocery_list(
        kw["recipe_id"], kw.get("servings_multiplier", 1.0)
    ),
    "list_cookbooks": lambda **kw: recipes.list_cookbooks(),
    # Downshiftology
    "search_downshiftology": lambda **kw: downshiftology.search_downshiftology(
        kw.get("query", ""),
        kw.get("course", ""),
        kw.get("cuisine", ""),
        kw.get("dietary", ""),
        int(kw.get("max_time", 0)),
    ),
    "get_downshiftology_details": lambda **kw: downshiftology.get_downshiftology_details(int(kw["result_number"])),
    "import_downshiftology_recipe": lambda **kw: downshiftology.import_downshiftology_recipe(
        int(kw.get("result_number", 0)), kw.get("recipe_name", "")
    ),
    # Nudges (Feature 003)
    "set_quiet_day": lambda **kw: nudges.set_quiet_day(),
    "complete_chore": lambda **kw: chores.complete_chore(kw["chore_name"]),
    "skip_chore": lambda **kw: chores.skip_chore(kw["chore_name"]),
    "set_chore_preference": lambda **kw: chores.set_chore_preference(
        kw["chore_name"], kw.get("preference"), kw.get("preferred_days"), kw.get("frequency")
    ),
    "get_chore_history": lambda **kw: chores.get_chore_history(kw.get("days", 7)),
    "start_laundry": lambda **kw: laundry.start_laundry_session(
        kw.get("washer_minutes", 45), kw.get("dryer_minutes", 60)
    ),
    "advance_laundry": lambda **kw: laundry.advance_laundry(),
    "cancel_laundry": lambda **kw: laundry.cancel_laundry(),
    # Proactive
    "check_reorder_items": lambda **kw: proactive.check_reorder_items(),
    "confirm_groceries_ordered": lambda **kw: proactive.handle_order_confirmation(),
    "generate_meal_plan": lambda **kw: proactive.generate_meal_plan(),
    "handle_meal_swap": lambda **kw: proactive.handle_meal_swap(kw["plan"], kw["day"], kw["new_meal"]),
    # Feature discovery
    "get_help": lambda **kw: discovery.get_help(kw.get("_phone", "")),
    "check_system_logs": lambda **kw: _handle_check_system_logs(**kw),
    # Amazon-YNAB Sync (Feature 010)
    "amazon_spending_breakdown": lambda **kw: amazon_sync.get_amazon_spending_breakdown(kw.get("month", "")),
    "amazon_sync_status": lambda **kw: amazon_sync.get_sync_status(),
    "amazon_sync_trigger": lambda **kw: _handle_amazon_sync_trigger(),
    "amazon_set_auto_split": lambda **kw: amazon_sync.set_auto_split(kw["enabled"]),
    "amazon_undo_split": lambda **kw: amazon_sync.handle_undo(kw.get("transaction_index", 1)),
    # Budget Maintenance (Feature 012)
    "budget_health_check": lambda **kw: ynab.budget_health_check(
        kw.get("lookback_months", 3), kw.get("drift_threshold", 30)
    ),
    "apply_goal_suggestion": lambda **kw: ynab.apply_goal_suggestion(
        kw.get("category", ""), kw.get("amount", 0), kw.get("apply_all", False)
    ),
    "allocate_bonus": lambda **kw: ynab.allocate_bonus(kw.get("amount", 0), kw.get("description", "")),
    "approve_allocation": lambda **kw: ynab.approve_allocation(kw.get("adjustments", "")),
    # Email-YNAB Sync (Feature 011)
    "email_sync_trigger": lambda **kw: _handle_email_sync_trigger(),
    "email_sync_status": lambda **kw: email_sync.get_email_sync_status(),
    "email_set_auto_categorize": lambda **kw: email_sync.set_email_auto_categorize(kw["enabled"]),
    "email_undo_categorize": lambda **kw: email_sync.handle_email_undo(kw.get("transaction_index", 1)),
    # User Preference Persistence (Feature 013)
    "save_preference": lambda **kw: _handle_save_preference(**kw),
    "list_preferences": lambda **kw: _handle_list_preferences(**kw),
    "remove_preference": lambda **kw: _handle_remove_preference(**kw),
    # Context-Aware Bot (Feature 014)
    "get_daily_context": lambda **kw: context.get_daily_context(kw.get("_phone", "")),
    "save_routine": lambda **kw: routines.save_routine(kw.get("_phone", ""), kw["name"], kw["steps"]),
    "get_routine": lambda **kw: (
        routines.list_routines(kw.get("_phone", ""))
        if kw.get("name", "").lower() in ("all", "")
        else routines.get_routine(kw.get("_phone", ""), kw["name"])
    ),
    "delete_routine": lambda **kw: routines.delete_routine(kw.get("_phone", ""), kw["name"]),
    # Drive Time Tools (Feature 017)
    "get_drive_times": lambda **kw: drive_times.get_drive_times(),
    "save_drive_time": lambda **kw: drive_times.save_drive_time(kw["location"], kw["minutes"]),
    "delete_drive_time": lambda **kw: drive_times.delete_drive_time(kw["location"]),
    # Receipt → YNAB categorization (Feature 027)
    "process_receipt": lambda **kw: receipt.process_receipt(
        _current_image_data["base64"] if _current_image_data else "",
        _current_image_data["mime_type"] if _current_image_data else "",
        kw.get("_phone", ""),
    ),
    "confirm_receipt_categorization": lambda **kw: receipt.confirm_receipt_categorization(
        kw.get("_phone", ""), kw.get("category_override", "")
    ),
    "retry_receipt_match": lambda **kw: receipt.retry_receipt_match(kw.get("_phone", "")),
    "split_receipt_transaction": lambda **kw: receipt.split_receipt_transaction(kw.get("_phone", "")),
}

# Filter TOOL_FUNCTIONS to match enabled TOOLS
TOOL_FUNCTIONS = {k: v for k, v in TOOL_FUNCTIONS.items() if k in _enabled_tool_names}


def _handle_save_preference(**kw) -> str:
    """Handle save_preference tool — stores a lasting user preference."""
    phone = kw.get("_phone", "")
    category = kw.get("category", "notification_optout")
    description = kw.get("description", "")
    raw_text = kw.get("raw_text", "")

    if not description:
        return "Please provide a description of the preference to save."

    try:
        pref = preferences.add_preference(phone, category, description, raw_text)
        return (
            f'Saved preference: "{pref["description"]}" ({category.replace("_", " ")}). '
            f"I'll honor this in all future interactions. "
            f"You can remove it anytime by saying something like "
            f"'remove the {description.lower().split()[0]} preference' "
            f"or 'start {description.lower().split()[-1]} again'."
        )
    except ValueError as e:
        return str(e)


def _handle_list_preferences(**kw) -> str:
    """Handle list_preferences tool — returns all stored preferences for the user."""
    phone = kw.get("_phone", "")
    prefs = preferences.get_preferences(phone)

    if not prefs:
        return (
            "You don't have any stored preferences. "
            "You can set them by telling me things like "
            "'don't remind me about groceries unless I ask' or "
            f"'no {FAMILY_CONFIG.get('partner1_name', 'Partner1')} appointment reminders' or "
            "'check the time before making recommendations'."
        )

    lines = []
    for i, pref in enumerate(prefs, 1):
        category_label = pref["category"].replace("_", " ")
        created = pref.get("created", "")
        date_str = ""
        if created:
            try:
                dt = datetime.fromisoformat(created)
                date_str = f", set {dt.strftime('%b %d')}"
            except (ValueError, TypeError):
                pass
        lines.append(f"{i}. {pref['description']} ({category_label}{date_str})")

    return "Your stored preferences:\n" + "\n".join(lines)


def _handle_remove_preference(**kw) -> str:
    """Handle remove_preference tool — removes a preference by fuzzy search or clears all."""
    phone = kw.get("_phone", "")
    search_text = kw.get("search_text", "")

    if not search_text:
        return "Please describe which preference to remove."

    # Handle "ALL" / "clear all"
    if search_text.upper() == "ALL":
        count = preferences.clear_preferences(phone)
        if count == 0:
            return "You don't have any preferences to clear."
        return f"Done — I've cleared all {count} of your preferences. I'll go back to default behavior for everything."

    # Fuzzy match removal
    removed = preferences.remove_preference_by_description(phone, search_text)
    if removed:
        return (
            f"Done — I've removed the preference matching '{search_text}'. I'll resume default behavior for that topic."
        )
    else:
        return (
            f"I couldn't find a preference matching '{search_text}'. "
            "Try 'what are my preferences?' to see your current list."
        )


def _handle_check_system_logs(**kw) -> str:
    """Handle check_system_logs tool — query recent logs for system health."""
    from src.log_diagnostics import check_system_logs

    minutes = int(kw.get("minutes", 10))
    return check_system_logs(minutes=minutes)


def handle_message(sender_phone: str, message_text: str, image_data: dict | None = None) -> str:
    """Process a message from a family member and return the assistant's response.

    Runs the Claude tool-use loop: send message → Claude decides tools → execute
    tools → send results back → Claude formats final response.

    Args:
        sender_phone: Sender's phone number or "system" for automated calls.
        message_text: Text message or image caption.
        image_data: Optional dict with "base64" and "mime_type" for image messages.
    """
    global _current_image_data, _buffered_images
    sender_name = PHONE_TO_NAME.get(sender_phone, "Unknown")

    # Store image data for tool handlers (avoids passing base64 through tool call JSON)
    if image_data:
        _current_image_data = image_data
        _buffered_images.append(image_data)
    # Don't clear on text-only messages — user might send photos then a text command

    # Compute current time early — used for both user message prefix and system prompt
    now = datetime.now(tz=TIMEZONE)
    time_prefix = now.strftime("[Current time: %A, %B %-d, %Y at %-I:%M %p Pacific]")

    if image_data:
        buffer_note = ""
        if len(_buffered_images) > 1:
            buffer_note = (
                f" [SYSTEM: {len(_buffered_images)} recipe photos buffered. "
                "All will be combined when you call extract_and_save_recipe.]"
            )
        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_data["mime_type"],
                    "data": image_data["base64"],
                },
            },
            {"type": "text", "text": f"{time_prefix}\n[From {sender_name}]: {message_text}{buffer_note}"},
        ]
    else:
        user_content = f"{time_prefix}\n[From {sender_name}]: {message_text}"

    # Load conversation history for multi-turn context (skip for system/automated messages)
    history = conversation.get_history(sender_phone) if sender_phone != "system" else []
    messages = history + [{"role": "user", "content": user_content}]
    history_len = len(history)

    # Inject current date/time so Claude knows what day it is
    # P1 fix: place date at BOTH the top and bottom of the system prompt
    # so the model reliably attends to it (GitHub issue #2)
    # P2 fix (Feature 016): also injected into user message above as time_prefix
    date_line = now.strftime("**Right now:** %A, %B %-d, %Y at %-I:%M %p Pacific.")
    system = (
        date_line
        + "\n\n"
        + render_system_prompt(FAMILY_CONFIG, enabled_integrations=frozenset(ENABLED_INTEGRATIONS))
        + "\n\n"
        + date_line
    )

    # Inject user preferences into system prompt so Claude naturally honors them
    user_prefs = preferences.get_preferences(sender_phone)
    if user_prefs:
        pref_lines = []
        for p in user_prefs:
            cat_label = p["category"].replace("_", " ")
            pref_lines.append(f"- [{cat_label}] {p['description']}")
        system += (
            "\n\n**User preferences (MUST honor these — they are lasting rules set by this user):**\n"
            + "\n".join(pref_lines)
            + "\n\nRemember: these opt-outs only suppress PROACTIVE/unsolicited content. "
            "If the user explicitly asks about an opted-out topic, answer normally."
        )

    # First-time welcome: prepend instruction for new users
    if sender_phone != "system" and sender_phone not in _welcomed_phones:
        _welcomed_phones.add(sender_phone)
        _welcome = FAMILY_CONFIG.get("welcome_message", 'Welcome! Say "help" to see what I can do.')
        system += (
            "\n\n[SYSTEM: This is the user's FIRST message. Before your normal "
            f"response, prepend a brief one-line welcome: '{_welcome}' "
            "Then answer their actual request.]"
        )

    # Agentic tool-use loop (capped to prevent runaway API costs)
    MAX_TOOL_ITERATIONS = 25
    iteration = 0
    provider_used = "claude"

    while True:
        iteration += 1
        if iteration > MAX_TOOL_ITERATIONS:
            logger.warning("Tool loop hit max iterations (%d) — stopping", MAX_TOOL_ITERATIONS)
            if sender_phone != "system":
                conversation.save_turn(sender_phone, messages[history_len:])
            return "I hit my processing limit for this request. Please try a simpler question or break it into parts."

        response, provider_used = ai_create_message(
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Collect all tool use blocks and execute them
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    logger.info(
                        "Tool call [%d/%d]: %s(%s)",
                        iteration,
                        MAX_TOOL_ITERATIONS,
                        tool_name,
                        json.dumps(tool_input),
                    )

                    try:
                        func = TOOL_FUNCTIONS.get(tool_name)
                        if func:
                            # Inject phone for tools that need sender context
                            if tool_name in (
                                "get_help",
                                "save_preference",
                                "list_preferences",
                                "remove_preference",
                                "get_daily_context",
                                "save_routine",
                                "get_routine",
                                "delete_routine",
                                "process_receipt",
                                "confirm_receipt_categorization",
                                "retry_receipt_match",
                                "split_receipt_transaction",
                            ):
                                tool_input["_phone"] = sender_phone
                            result = execute_with_retry(func, tool_name, tool_input)
                            # Audit result for hidden error strings
                            _is_error, result = audit_tool_result(tool_name, result)
                            # Track usage for feature discovery suggestions
                            if sender_phone != "system":
                                discovery.record_usage(sender_phone, tool_name)
                        else:
                            result = f"Unknown tool: {tool_name}"
                    except Exception as e:
                        # Safety net — if resilience wrapper itself fails
                        logger.error("Resilience wrapper failed for %s: %s", tool_name, e)
                        result = (
                            f"TOOL FAILED: {tool_name} — unexpected error. "
                            f"DO NOT skip this — tell the user that something went wrong "
                            f"with {tool_name} and their request was NOT completed."
                        )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        }
                    )

            # Add assistant response and tool results to conversation
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        # No more tool calls — extract final text response
        messages.append({"role": "assistant", "content": response.content})
        if sender_phone != "system":
            conversation.save_turn(sender_phone, messages[history_len:])
        text_parts = [block.text for block in response.content if hasattr(block, "text")]
        result_text = "\n".join(text_parts) if text_parts else "I'm not sure how to help with that."
        # Append backup indicator if response came from OpenAI
        if provider_used == "openai":
            result_text += "\n\n_Note: using backup assistant today_"
        return result_text


def generate_daily_plan(target: str = DEFAULT_CALENDAR) -> str:
    """Generate a daily plan programmatically (called by n8n cron endpoint).

    Constructs a prompt that triggers the full daily plan flow through Claude.
    """
    p1 = FAMILY_CONFIG.get("partner1_name", "Partner1")
    p2 = FAMILY_CONFIG.get("partner2_name", "Partner2")
    prompt = (
        f"Generate today's daily plan for {target.title()}. "
        "Start by calling get_daily_context for today's schedule, childcare "
        f"status, and communication mode. Then check routine templates, look at "
        f"{p1}'s work calendar for meeting windows, pick a backlog item to "
        f"suggest, and write the time blocks to {p2}'s Google Calendar. "
        "Also check: tonight's meal plan (does complexity match schedule "
        "density?), and any overdue action items or pending grocery orders. "
        "Weave cross-domain insights into the briefing naturally — don't add "
        "separate sections. Format for WhatsApp. Respect the communication mode."
    )
    return handle_message("system", prompt)


def generate_meeting_prep() -> str:
    """Generate weekly meeting prep agenda (called by n8n or ad-hoc).

    Constructs a prompt that triggers the meeting prep flow through Claude,
    gathering data from all domains and synthesizing into a scannable agenda.
    """
    prompt = (
        "Prep the weekly family meeting agenda. Follow Rule 49 for the "
        "5-section structure. Gather data from all relevant domains: budget "
        "summary, this week's calendar events, action items status, current "
        "meal plan, backlog items, and chore history. Synthesize into a "
        "scannable agenda with headline insights per section. End with top 3 "
        "discussion points. Format for WhatsApp."
    )
    return handle_message("system", prompt)
