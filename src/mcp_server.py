"""MCP server exposing family meeting assistant tools for Claude Desktop."""

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path for src.* imports
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load .env before importing config (which also calls load_dotenv)
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Configure logging to stderr (stdout is reserved for MCP stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

from mcp.server.fastmcp import FastMCP
from src.tools import notion, calendar, ynab, outlook
from src.tools import anylist_bridge
from src.assistant import _handle_write_calendar_blocks, _handle_push_grocery_list, generate_daily_plan

mcp = FastMCP("family-meeting")

# ---------------------------------------------------------------------------
# Calendar tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_calendar_events(days_ahead: int = 7, calendar_names: list[str] | None = None) -> str:
    """Fetch upcoming events from Google Calendars (Jason personal, Erin personal, Family shared). Use calendar_names to filter: "jason", "erin", "family"."""
    return calendar.get_calendar_events(days_ahead, calendar_names)


@mcp.tool()
def get_outlook_events(target_date: str = "") -> str:
    """Fetch Jason's work calendar events (Outlook/Cisco) for a date. Shows meeting times so Erin can plan around his schedule. Date format: YYYY-MM-DD. Defaults to today."""
    return outlook.get_outlook_events(target_date)


@mcp.tool()
def write_calendar_blocks(blocks: list[dict]) -> str:
    """Write time blocks to Erin's Google Calendar. Each block needs: summary (str), start_time (ISO datetime like "2026-02-23T09:30:00-08:00"), end_time (ISO datetime), color_category ("chores", "rest", "development", "exercise", "side_work", or "backlog")."""
    return _handle_write_calendar_blocks(blocks=blocks)


# ---------------------------------------------------------------------------
# Notion: Action Items
# ---------------------------------------------------------------------------


@mcp.tool()
def get_action_items(assignee: str = "", status: str = "") -> str:
    """Query action items from Notion. Filter by assignee ("Jason" or "Erin") and/or status ("open" for all non-done, or a specific status like "Not Started", "In Progress", "Done")."""
    return notion.get_action_items(assignee, status)


@mcp.tool()
def add_action_item(assignee: str, description: str, due_context: str = "This Week") -> str:
    """Create a new action item assigned to a family member. Due context: "This Week", "Ongoing", or "Someday"."""
    return notion.add_action_item(assignee, description, due_context)


@mcp.tool()
def complete_action_item(page_id: str) -> str:
    """Mark an action item as done by its Notion page ID. Use get_action_items first to find the page_id."""
    return notion.complete_action_item(page_id)


@mcp.tool()
def rollover_incomplete_items() -> str:
    """Mark all incomplete "This Week" action items as rolled over. Call when generating a new weekly agenda."""
    return notion.rollover_incomplete_items()


# ---------------------------------------------------------------------------
# Notion: Family Profile
# ---------------------------------------------------------------------------


@mcp.tool()
def get_family_profile() -> str:
    """Read the family profile: member info, dietary preferences, routine templates, childcare schedule, recurring agenda topics, and configuration."""
    return notion.get_family_profile()


@mcp.tool()
def update_family_profile(section: str, content: str) -> str:
    """Update the family profile with persistent info (preferences, schedule changes, dietary restrictions). Sections: "Preferences", "Recurring Agenda Topics", "Members", "Childcare Schedule", "Routine Templates", "Configuration"."""
    return notion.update_family_profile(section, content)


# ---------------------------------------------------------------------------
# Notion: Topics & Meetings
# ---------------------------------------------------------------------------


@mcp.tool()
def add_topic(description: str) -> str:
    """Add a custom topic to the next meeting agenda."""
    return notion.add_topic(description)


@mcp.tool()
def create_meeting(meeting_date: str = "") -> str:
    """Create a new meeting record in Notion. Returns the meeting page ID. Date format: YYYY-MM-DD. Defaults to today."""
    return notion.create_meeting(meeting_date)


# ---------------------------------------------------------------------------
# Notion: Meal Plans
# ---------------------------------------------------------------------------


@mcp.tool()
def save_meal_plan(week_start: str, plan_content: str, grocery_list: str) -> str:
    """Save a weekly meal plan to Notion. week_start is Monday date (YYYY-MM-DD), plan_content is one line per day, grocery_list is items one per line."""
    return notion.save_meal_plan(week_start, plan_content, grocery_list)


@mcp.tool()
def get_meal_plan(week_start: str = "") -> str:
    """Get the current or most recent meal plan from Notion. Optionally specify week_start (Monday YYYY-MM-DD)."""
    return notion.get_meal_plan(week_start)


# ---------------------------------------------------------------------------
# Notion: Backlog
# ---------------------------------------------------------------------------


@mcp.tool()
def get_backlog_items(assignee: str = "", status: str = "") -> str:
    """Query Erin's personal backlog of one-off tasks (home improvement, personal growth, side work). Filter by assignee and/or status ("open" or specific)."""
    return notion.get_backlog_items(assignee, status)


@mcp.tool()
def add_backlog_item(description: str, category: str = "Other", assignee: str = "Erin", priority: str = "Medium") -> str:
    """Add a one-off task to the backlog (e.g., "reorganize tupperware", "clean garage"). Categories: "Home Improvement", "Personal Growth", "Side Work", "Exercise", "Other". Priority: "High", "Medium", "Low"."""
    return notion.add_backlog_item(description, category, assignee, priority)


@mcp.tool()
def complete_backlog_item(page_id: str) -> str:
    """Mark a backlog item as done by its Notion page ID."""
    return notion.complete_backlog_item(page_id)


# ---------------------------------------------------------------------------
# Notion: Routine Templates
# ---------------------------------------------------------------------------


@mcp.tool()
def get_routine_templates() -> str:
    """Read Erin's daily routine templates. Templates define time blocks for scenarios like "Weekday with Zoey" or "Weekday with Grandma". Used for daily plan generation."""
    return notion.get_routine_templates()


# ---------------------------------------------------------------------------
# Notion: Grocery History
# ---------------------------------------------------------------------------


@mcp.tool()
def get_grocery_history(category: str = "") -> str:
    """Get grocery purchase history from past Whole Foods orders. Filter by category: "Produce", "Meat", "Dairy", "Pantry", "Frozen", "Bakery", "Beverages"."""
    return notion.get_grocery_history(category)


@mcp.tool()
def get_staple_items() -> str:
    """Get frequently purchased grocery items (staples) sorted by frequency. Suggest these when generating grocery lists."""
    return notion.get_staple_items()


# ---------------------------------------------------------------------------
# YNAB
# ---------------------------------------------------------------------------


@mcp.tool()
def get_budget_summary(month: str = "", category: str = "") -> str:
    """Get YNAB budget summary for a month, optionally filtered to one category. Month format: YYYY-MM-DD (first of month). Defaults to current month. Example categories: "Groceries", "Dining Out"."""
    return ynab.get_budget_summary(month, category)


# ---------------------------------------------------------------------------
# Grocery (AnyList)
# ---------------------------------------------------------------------------


@mcp.tool()
def push_grocery_list(items: list[str]) -> str:
    """Push grocery items to AnyList for Whole Foods delivery. Clears the existing list first, then adds new items. Erin opens AnyList -> "Order Pickup or Delivery" -> Whole Foods."""
    return _handle_push_grocery_list(items=items)


# ---------------------------------------------------------------------------
# Daily Plan (orchestrated via internal Claude Haiku)
# ---------------------------------------------------------------------------


@mcp.tool()
def generate_daily_plan_tool(target: str = "erin") -> str:
    """Generate a full daily plan for Erin (or Jason). This triggers an AI-powered planning process that reads routine templates, checks calendars, picks a backlog item, and writes time blocks to Google Calendar. Returns the formatted plan."""
    return generate_daily_plan(target)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting family-meeting MCP server")
    mcp.run(transport="stdio")
