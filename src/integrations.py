"""Centralized integration registry.

Maps each integration to its env vars, tools, and prompt tags.
Drives tool filtering, prompt filtering, health checks, and validation.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Integration:
    """An external service integration."""

    name: str
    display_name: str
    required: bool
    env_vars: tuple[str, ...]
    tools: tuple[str, ...]
    prompt_tag: str
    always_enabled: bool = False


# ---------------------------------------------------------------------------
# Registry — single source of truth for all integrations
# ---------------------------------------------------------------------------

INTEGRATION_REGISTRY: dict[str, Integration] = {
    "core": Integration(
        name="core",
        display_name="Core",
        required=False,
        env_vars=(),
        tools=(
            "get_daily_context",
            "save_preference",
            "list_preferences",
            "remove_preference",
            "get_drive_times",
            "save_drive_time",
            "delete_drive_time",
            "save_routine",
            "get_routine",
            "delete_routine",
            "get_help",
        ),
        prompt_tag="core",
        always_enabled=True,
    ),
    "whatsapp": Integration(
        name="whatsapp",
        display_name="WhatsApp",
        required=True,
        env_vars=(
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_VERIFY_TOKEN",
            "WHATSAPP_APP_SECRET",
        ),
        tools=(),
        prompt_tag="whatsapp",
    ),
    "ai_api": Integration(
        name="ai_api",
        display_name="Anthropic AI",
        required=True,
        env_vars=("ANTHROPIC_API_KEY",),
        tools=(),
        prompt_tag="ai_api",
    ),
    "notion": Integration(
        name="notion",
        display_name="Notion",
        required=False,
        env_vars=(
            "NOTION_TOKEN",
            "NOTION_ACTION_ITEMS_DB",
            "NOTION_MEAL_PLANS_DB",
            "NOTION_MEETINGS_DB",
            "NOTION_FAMILY_PROFILE_PAGE",
        ),
        tools=(
            "get_action_items",
            "add_action_item",
            "complete_action_item",
            "add_topic",
            "get_family_profile",
            "update_family_profile",
            "create_meeting",
            "rollover_incomplete_items",
            "save_meal_plan",
            "get_meal_plan",
            "get_backlog_items",
            "add_backlog_item",
            "complete_backlog_item",
            "get_routine_templates",
            "generate_meal_plan",
            "handle_meal_swap",
            "set_quiet_day",
            "complete_chore",
            "skip_chore",
            "set_chore_preference",
            "get_chore_history",
            "check_reorder_items",
            "confirm_groceries_ordered",
            "start_laundry",
            "advance_laundry",
            "cancel_laundry",
        ),
        prompt_tag="notion",
    ),
    "google_calendar": Integration(
        name="google_calendar",
        display_name="Google Calendar",
        required=False,
        env_vars=("GOOGLE_CALENDAR_FAMILY_ID",),
        tools=(
            "get_calendar_events",
            "write_calendar_blocks",
            "create_quick_event",
            "delete_calendar_event",
            "list_recurring_events",
        ),
        prompt_tag="google_calendar",
    ),
    "outlook": Integration(
        name="outlook",
        display_name="Outlook Calendar",
        required=False,
        env_vars=("OUTLOOK_CALENDAR_ICS_URL",),
        tools=("get_outlook_events",),
        prompt_tag="outlook",
    ),
    "ynab": Integration(
        name="ynab",
        display_name="YNAB",
        required=False,
        env_vars=("YNAB_ACCESS_TOKEN", "YNAB_BUDGET_ID"),
        tools=(
            "get_budget_summary",
            "search_transactions",
            "recategorize_transaction",
            "create_transaction",
            "update_category_budget",
            "move_money",
            "budget_health_check",
            "apply_goal_suggestion",
            "allocate_bonus",
            "approve_allocation",
            "amazon_sync_status",
            "amazon_sync_trigger",
            "amazon_spending_breakdown",
            "amazon_set_auto_split",
            "amazon_undo_split",
            "email_sync_trigger",
            "email_sync_status",
            "email_set_auto_categorize",
            "email_undo_categorize",
            "process_receipt",
            "confirm_receipt_categorization",
            "retry_receipt_match",
            "split_receipt_transaction",
        ),
        prompt_tag="ynab",
    ),
    "anylist": Integration(
        name="anylist",
        display_name="AnyList",
        required=False,
        env_vars=("ANYLIST_SIDECAR_URL",),
        tools=(
            "push_grocery_list",
            "get_grocery_history",
            "get_staple_items",
        ),
        prompt_tag="anylist",
    ),
    "recipes": Integration(
        name="recipes",
        display_name="Recipes",
        required=False,
        env_vars=("NOTION_RECIPES_DB", "NOTION_COOKBOOKS_DB", "R2_ACCOUNT_ID"),
        tools=(
            "extract_and_save_recipe",
            "search_recipes",
            "get_recipe_details",
            "recipe_to_grocery_list",
            "list_cookbooks",
            "search_downshiftology",
            "get_downshiftology_details",
            "import_downshiftology_recipe",
        ),
        prompt_tag="recipes",
    ),
    "voice_access": Integration(
        name="voice_access",
        display_name="Voice Access (Siri)",
        required=False,
        env_vars=("PARTNER1_API_TOKEN", "PARTNER2_API_TOKEN"),
        tools=(),  # Voice is a transport, not a tool provider
        prompt_tag="voice_access",
    ),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _check_env_vars(env_vars: tuple[str, ...]) -> str:
    """Check env var status: 'enabled', 'disabled', or 'partial'."""
    if not env_vars:
        return "enabled"
    set_vars = [v for v in env_vars if os.environ.get(v)]
    if len(set_vars) == len(env_vars):
        return "enabled"
    if len(set_vars) == 0:
        return "disabled"
    return "partial"


def get_enabled_integrations() -> set[str]:
    """Return set of integration names that are fully configured.

    An integration is enabled if:
    - It is always_enabled (core), OR
    - All of its env_vars are set in the environment
    """
    enabled = set()
    for name, integration in INTEGRATION_REGISTRY.items():
        if integration.always_enabled:
            enabled.add(name)
        elif _check_env_vars(integration.env_vars) == "enabled":
            enabled.add(name)
    return enabled


def get_tools_for_integrations(enabled: set[str]) -> list[str]:
    """Return flat list of tool names for enabled integrations."""
    tools = []
    for name in enabled:
        if name in INTEGRATION_REGISTRY:
            tools.extend(INTEGRATION_REGISTRY[name].tools)
    return tools


def is_integration_enabled(name: str) -> bool:
    """Check if a specific integration is enabled."""
    integration = INTEGRATION_REGISTRY.get(name)
    if not integration:
        return False
    if integration.always_enabled:
        return True
    return _check_env_vars(integration.env_vars) == "enabled"


def get_integration_status(name: str) -> str:
    """Return status of an integration: 'enabled', 'disabled', or 'partial'."""
    integration = INTEGRATION_REGISTRY.get(name)
    if not integration:
        return "disabled"
    if integration.always_enabled:
        return "enabled"
    return _check_env_vars(integration.env_vars)


# Reverse map: tool_name → integration display_name (built once at import time)
_TOOL_TO_INTEGRATION: dict[str, str] = {}
for _integ_name, _integ in INTEGRATION_REGISTRY.items():
    for _tool in _integ.tools:
        _TOOL_TO_INTEGRATION[_tool] = _integ.display_name


def get_integration_for_tool(tool_name: str) -> str:
    """Return the display name of the integration that owns a tool.

    E.g. "create_quick_event" → "Google Calendar", "add_action_item" → "Notion".
    Returns "Unknown" for tools not in any integration.
    """
    return _TOOL_TO_INTEGRATION.get(tool_name, "Unknown")
