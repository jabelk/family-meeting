"""Notion API wrapper — CRUD for action items, meals, meetings, and family profile."""

import logging
from datetime import date, datetime, timedelta
from notion_client import Client
from src.config import (
    NOTION_TOKEN,
    NOTION_ACTION_ITEMS_DB,
    NOTION_MEAL_PLANS_DB,
    NOTION_MEETINGS_DB,
    NOTION_FAMILY_PROFILE_PAGE,
)

logger = logging.getLogger(__name__)

notion = Client(auth=NOTION_TOKEN)


# ---------------------------------------------------------------------------
# Family Profile (T010 + T011)
# ---------------------------------------------------------------------------

def get_family_profile() -> str:
    """Read the Family Profile page and return its content as plain text."""
    blocks = notion.blocks.children.list(block_id=NOTION_FAMILY_PROFILE_PAGE)
    return _blocks_to_text(blocks["results"])


def update_family_profile(section: str, content: str) -> str:
    """Append content to a section of the Family Profile page.

    Finds the heading matching `section` and appends a bullet block after it.
    If the section isn't found, appends at the end of the page.
    """
    blocks = notion.blocks.children.list(block_id=NOTION_FAMILY_PROFILE_PAGE)
    target_id = NOTION_FAMILY_PROFILE_PAGE
    for block in blocks["results"]:
        block_text = _get_block_text(block)
        if block_text and section.lower() in block_text.lower():
            target_id = block["id"]
            break

    notion.blocks.children.append(
        block_id=target_id,
        children=[{
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": content}}]
            },
        }],
    )
    return f"Added to {section}: {content}"


# ---------------------------------------------------------------------------
# Action Items (T015 for get, T020 for add, T021 for complete, T022 for rollover)
# ---------------------------------------------------------------------------

def get_action_items(assignee: str = "", status: str = "") -> str:
    """Query action items with optional filters. Returns formatted text."""
    filters = []
    if assignee:
        filters.append({"property": "Assignee", "select": {"equals": assignee}})
    if status:
        if status.lower() == "open":
            filters.append({"property": "Status", "status": {"does_not_equal": "Done"}})
        else:
            filters.append({"property": "Status", "status": {"equals": status}})

    query_filter = {"and": filters} if len(filters) > 1 else (filters[0] if filters else None)
    kwargs = {"database_id": NOTION_ACTION_ITEMS_DB}
    if query_filter:
        kwargs["filter"] = query_filter

    results = notion.databases.query(**kwargs)
    items = []
    for page in results["results"]:
        props = page["properties"]
        desc = _get_title(props.get("Description", {}))
        assignee_val = _get_select(props.get("Assignee", {}))
        status_val = _get_status(props.get("Status", {}))
        rolled = props.get("Rolled Over", {}).get("checkbox", False)
        items.append(
            f"- {'✅' if status_val == 'Done' else '⬜'} {assignee_val}: {desc}"
            + (" (rolled over)" if rolled else "")
        )
    if not items:
        return "No action items found."
    return "\n".join(items)


def add_action_item(
    assignee: str,
    description: str,
    due_context: str = "This Week",
    meeting_id: str = "",
) -> str:
    """Create a new action item in the Action Items database."""
    properties: dict = {
        "Description": {"title": [{"text": {"content": description}}]},
        "Assignee": {"select": {"name": assignee}},
        "Status": {"status": {"name": "Not Started"}},
        "Due Context": {"select": {"name": due_context}},
        "Created": {"date": {"start": date.today().isoformat()}},
    }
    if meeting_id:
        properties["Meeting"] = {"relation": [{"id": meeting_id}]}

    notion.pages.create(parent={"database_id": NOTION_ACTION_ITEMS_DB}, properties=properties)
    return f"Added action item for {assignee}: {description}"


def complete_action_item(page_id: str) -> str:
    """Mark an action item as Done by its Notion page ID."""
    notion.pages.update(
        page_id=page_id,
        properties={"Status": {"status": {"name": "Done"}}},
    )
    return "Marked as done."


def rollover_incomplete_items() -> str:
    """Find incomplete 'This Week' items and mark them as rolled over."""
    results = notion.databases.query(
        database_id=NOTION_ACTION_ITEMS_DB,
        filter={
            "and": [
                {"property": "Status", "status": {"does_not_equal": "Done"}},
                {"property": "Due Context", "select": {"equals": "This Week"}},
            ]
        },
    )
    count = 0
    for page in results["results"]:
        notion.pages.update(page_id=page["id"], properties={"Rolled Over": {"checkbox": True}})
        count += 1
    return f"Rolled over {count} incomplete items."


# ---------------------------------------------------------------------------
# Custom Topics (T016)
# ---------------------------------------------------------------------------

def add_topic(description: str) -> str:
    """Add a custom agenda topic (stored as an action item with Due Context='Custom Topic')."""
    properties = {
        "Description": {"title": [{"text": {"content": description}}]},
        "Assignee": {"select": {"name": "Both"}},
        "Status": {"status": {"name": "Not Started"}},
        "Due Context": {"select": {"name": "Custom Topic"}},
        "Created": {"date": {"start": date.today().isoformat()}},
    }
    notion.pages.create(parent={"database_id": NOTION_ACTION_ITEMS_DB}, properties=properties)
    return f"Added custom topic: {description}"


# ---------------------------------------------------------------------------
# Meetings (T017)
# ---------------------------------------------------------------------------

def create_meeting(meeting_date: str = "") -> str:
    """Create a new Meeting page. Returns the meeting page ID."""
    if not meeting_date:
        meeting_date = date.today().isoformat()

    display_date = datetime.strptime(meeting_date, "%Y-%m-%d").strftime("%b %d, %Y")
    page = notion.pages.create(
        parent={"database_id": NOTION_MEETINGS_DB},
        properties={
            "Date": {"title": [{"text": {"content": display_date}}]},
            "When": {"date": {"start": meeting_date}},
            "Status": {"select": {"name": "Planned"}},
        },
    )
    return page["id"]


def save_meeting_agenda(meeting_id: str, agenda_text: str) -> str:
    """Save agenda content as blocks inside a meeting page."""
    blocks = []
    for line in agenda_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": line}}]
            },
        })
    if blocks:
        notion.blocks.children.append(block_id=meeting_id, children=blocks)
    return "Agenda saved."


# ---------------------------------------------------------------------------
# Meal Plans (T025 + T026)
# ---------------------------------------------------------------------------

def save_meal_plan(week_start: str, plan_content: str, grocery_list: str) -> str:
    """Create a Meal Plan page with daily meals and grocery list."""
    display = f"Week of {datetime.strptime(week_start, '%Y-%m-%d').strftime('%b %d')}"
    page = notion.pages.create(
        parent={"database_id": NOTION_MEAL_PLANS_DB},
        properties={
            "Week Of": {"title": [{"text": {"content": display}}]},
            "Start Date": {"date": {"start": week_start}},
            "Status": {"select": {"name": "Active"}},
        },
    )
    page_id = page["id"]

    # Add plan content and grocery list as blocks
    blocks = []
    for line in plan_content.split("\n"):
        line = line.strip()
        if not line:
            continue
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]},
        })

    if grocery_list:
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Grocery List"}}]},
        })
        for item in grocery_list.split("\n"):
            item = item.strip().lstrip("□-•* ")
            if item:
                blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": item}}],
                        "checked": False,
                    },
                })

    if blocks:
        notion.blocks.children.append(block_id=page_id, children=blocks)
    return f"Meal plan saved: {display}"


def get_meal_plan(week_start: str = "") -> str:
    """Get the meal plan for a given week. Returns formatted text."""
    query_kwargs: dict = {"database_id": NOTION_MEAL_PLANS_DB}
    if week_start:
        query_kwargs["filter"] = {
            "property": "Start Date",
            "date": {"equals": week_start},
        }
    else:
        query_kwargs["sorts"] = [{"property": "Start Date", "direction": "descending"}]
        query_kwargs["page_size"] = 1

    results = notion.databases.query(**query_kwargs)
    if not results["results"]:
        return "No meal plan found for this week."

    page = results["results"][0]
    page_id = page["id"]
    title = _get_title(page["properties"].get("Week Of", {}))
    blocks = notion.blocks.children.list(block_id=page_id)
    content = _blocks_to_text(blocks["results"])
    return f"{title}\n{content}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _blocks_to_text(blocks: list) -> str:
    lines = []
    for block in blocks:
        text = _get_block_text(block)
        if text:
            btype = block["type"]
            if "heading" in btype:
                lines.append(f"\n## {text}")
            elif btype == "bulleted_list_item":
                lines.append(f"- {text}")
            elif btype == "to_do":
                checked = block[btype].get("checked", False)
                lines.append(f"{'☑' if checked else '□'} {text}")
            else:
                lines.append(text)
    return "\n".join(lines)


def _get_block_text(block: dict) -> str:
    btype = block.get("type", "")
    data = block.get(btype, {})
    rich_text = data.get("rich_text", [])
    return "".join(rt.get("plain_text", "") for rt in rich_text)


def _get_title(prop: dict) -> str:
    title = prop.get("title", [])
    return "".join(t.get("plain_text", "") for t in title)


def _get_select(prop: dict) -> str:
    sel = prop.get("select")
    return sel["name"] if sel else ""


def _get_status(prop: dict) -> str:
    st = prop.get("status")
    return st["name"] if st else ""
