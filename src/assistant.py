"""Claude AI assistant core — system prompt, tool definitions, and message handling."""

import json
import logging
from anthropic import Anthropic
from src.config import ANTHROPIC_API_KEY, PHONE_TO_NAME
from src.tools import notion, calendar, ynab

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """\
You are the family meeting assistant for Jason and Erin's family. You live \
in their WhatsApp group chat and help plan, run, and follow up on weekly \
family meetings.

**Family:**
- Jason (partner) — works from home at Cisco
- Erin (partner) — stays at home with the kids
- Vienna (daughter, age 5) — kindergarten at Roy Gomm
- Zoey (daughter, age 3)

**Your rules:**
1. ALWAYS format responses as structured checklists with WhatsApp formatting:
   - Use *bold* for section headers
   - Use • or - for bullet lists
   - Use ✅ for completed items, ⬜ for pending items
   - NEVER respond with walls of unformatted prose
2. Keep responses concise and scannable — these are busy parents
3. When generating an agenda, use these sections in order:
   📅 This Week (calendar events)
   ✅ Review Last Week (open action items from prior week)
   🏠 Chores (to be assigned during meeting)
   🍽 Meals (meal plan status)
   💰 Finances (budget summary prompt)
   📌 Custom Topics (user-added items)
   🎯 Goals (long-term items)
4. When parsing action items, identify the assignee (Jason or Erin) and \
create separate items for each task mentioned
5. For meal plans, default to kid-friendly meals. Read family preferences \
from the profile before suggesting.
6. For budget summaries, highlight over-budget categories first
7. If a partner mentions a lasting preference (dietary restriction, recurring \
topic, schedule change), use update_family_profile to save it
8. If an external service (Calendar, YNAB) is unavailable, skip that section \
and note it — never fail the whole response

The current sender's name will be provided with each message.
"""

# ---------------------------------------------------------------------------
# Tool definitions for Claude
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_calendar_events",
        "description": "Fetch upcoming events from Google Calendar for the next N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days to look ahead. Default 7.",
                    "default": 7,
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_action_items",
        "description": "Query action items from Notion. Can filter by assignee and/or status. Use status='open' to get all non-completed items.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignee": {
                    "type": "string",
                    "description": "Filter by assignee name (e.g., 'Jason', 'Erin'). Empty for all.",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status: 'Not Started', 'In Progress', 'Done', or 'open' for all non-done items.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "add_action_item",
        "description": "Create a new action item assigned to a family member.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignee": {"type": "string", "description": "Who this is assigned to (Jason or Erin)."},
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
        "description": "Mark an action item as done. First call get_action_items to find the page_id of the item to complete, then pass that page_id here.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "The Notion page ID of the action item to mark as done."},
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "add_topic",
        "description": "Add a custom topic to the next meeting agenda.",
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
        "description": "Read the family profile including member info, dietary preferences, recurring agenda topics, and configuration.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "update_family_profile",
        "description": "Update the family profile with new persistent information. Use when a partner mentions a lasting preference, dietary restriction, schedule change, or recurring topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "Which section to update: 'Preferences', 'Recurring Agenda Topics', 'Members', or 'Configuration'."},
                "content": {"type": "string", "description": "The information to add."},
            },
            "required": ["section", "content"],
        },
    },
    {
        "name": "create_meeting",
        "description": "Create a new meeting record in Notion for today (or a specific date). Returns the meeting page ID.",
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
        "description": "Mark all incomplete 'This Week' action items as rolled over. Call this when generating a new weekly agenda.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "save_meal_plan",
        "description": "Save a weekly meal plan to Notion with daily meals and a grocery list.",
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
        "description": "Get the current or most recent meal plan from Notion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "week_start": {"type": "string", "description": "Monday date in YYYY-MM-DD format. Empty for most recent."},
            },
            "required": [],
        },
    },
    {
        "name": "get_budget_summary",
        "description": "Get budget summary from YNAB for a given month, optionally filtered to one category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month in YYYY-MM-DD format (first of month). Defaults to current month."},
                "category": {"type": "string", "description": "Optional category name to filter to (e.g., 'Dining Out', 'Groceries')."},
            },
            "required": [],
        },
    },
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "get_calendar_events": lambda **kw: calendar.get_calendar_events(kw.get("days_ahead", 7)),
    "get_action_items": lambda **kw: notion.get_action_items(kw.get("assignee", ""), kw.get("status", "")),
    "add_action_item": lambda **kw: notion.add_action_item(kw["assignee"], kw["description"], kw.get("due_context", "This Week")),
    "complete_action_item": lambda **kw: notion.complete_action_item(kw["page_id"]),
    "add_topic": lambda **kw: notion.add_topic(kw["description"]),
    "get_family_profile": lambda **kw: notion.get_family_profile(),
    "update_family_profile": lambda **kw: notion.update_family_profile(kw["section"], kw["content"]),
    "create_meeting": lambda **kw: notion.create_meeting(kw.get("meeting_date", "")),
    "rollover_incomplete_items": lambda **kw: notion.rollover_incomplete_items(),
    "save_meal_plan": lambda **kw: notion.save_meal_plan(kw["week_start"], kw["plan_content"], kw["grocery_list"]),
    "get_meal_plan": lambda **kw: notion.get_meal_plan(kw.get("week_start", "")),
    "get_budget_summary": lambda **kw: ynab.get_budget_summary(kw.get("month", ""), kw.get("category", "")),
}


def handle_message(sender_phone: str, message_text: str) -> str:
    """Process a message from a family member and return the assistant's response.

    Runs the Claude tool-use loop: send message → Claude decides tools → execute
    tools → send results back → Claude formats final response.
    """
    sender_name = PHONE_TO_NAME.get(sender_phone, "Unknown")
    user_content = f"[From {sender_name}]: {message_text}"

    messages = [{"role": "user", "content": user_content}]

    # Agentic tool-use loop
    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
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
                    logger.info("Tool call: %s(%s)", tool_name, json.dumps(tool_input))

                    try:
                        func = TOOL_FUNCTIONS.get(tool_name)
                        if func:
                            result = func(**tool_input)
                        else:
                            result = f"Unknown tool: {tool_name}"
                    except Exception as e:
                        logger.error("Tool %s failed: %s", tool_name, e)
                        result = f"Error: {tool_name} is currently unavailable. Skip this section."

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })

            # Add assistant response and tool results to conversation
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        # No more tool calls — extract final text response
        text_parts = [block.text for block in response.content if hasattr(block, "text")]
        return "\n".join(text_parts) if text_parts else "I'm not sure how to help with that."
