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
    NOTION_BACKLOG_DB,
    NOTION_GROCERY_HISTORY_DB,
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
    """Find incomplete 'This Week' items, mark as rolled over, and include backlog review.

    Returns a summary including both rolled-over action items and backlog items
    surfaced this week for inclusion in the weekly meeting agenda.
    """
    # Roll over incomplete action items
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

    summary = f"Rolled over {count} incomplete action items."

    # Add backlog review summary if backlog is configured
    if NOTION_BACKLOG_DB:
        try:
            # Get backlog items surfaced this week (Last Surfaced within last 7 days)
            week_ago = (date.today() - timedelta(days=7)).isoformat()
            surfaced = notion.databases.query(
                database_id=NOTION_BACKLOG_DB,
                filter={
                    "and": [
                        {"property": "Last Surfaced", "date": {"on_or_after": week_ago}},
                    ]
                },
            )
            if surfaced["results"]:
                backlog_lines = []
                for page in surfaced["results"]:
                    props = page["properties"]
                    desc = _get_title(props.get("Description", {}))
                    status_val = _get_status(props.get("Status", {}))
                    icon = "✅" if status_val == "Done" else "⬜"
                    backlog_lines.append(f"  {icon} {desc}")
                summary += f"\n\nBacklog items surfaced this week:\n" + "\n".join(backlog_lines)
            else:
                summary += "\n\nNo backlog items were surfaced this week."
        except Exception as e:
            logger.warning("Failed to get backlog review: %s", e)

    return summary


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
# Backlog (T009)
# ---------------------------------------------------------------------------

def get_backlog_items(assignee: str = "", status: str = "") -> str:
    """Query backlog items with optional filters. Returns formatted text."""
    if not NOTION_BACKLOG_DB:
        return "Backlog database not configured."

    filters = []
    if assignee:
        filters.append({"property": "Assignee", "select": {"equals": assignee}})
    if status:
        if status.lower() == "open":
            filters.append({"property": "Status", "status": {"does_not_equal": "Done"}})
        else:
            filters.append({"property": "Status", "status": {"equals": status}})

    query_filter = {"and": filters} if len(filters) > 1 else (filters[0] if filters else None)
    kwargs: dict = {"database_id": NOTION_BACKLOG_DB}
    if query_filter:
        kwargs["filter"] = query_filter

    results = notion.databases.query(**kwargs)
    items = []
    for page in results["results"]:
        props = page["properties"]
        desc = _get_title(props.get("Description", {}))
        assignee_val = _get_select(props.get("Assignee", {}))
        category = _get_select(props.get("Category", {}))
        priority = _get_select(props.get("Priority", {}))
        status_val = _get_status(props.get("Status", {}))
        items.append(
            f"- {'✅' if status_val == 'Done' else '⬜'} {desc}"
            + (f" [{category}]" if category else "")
            + (f" — {priority}" if priority else "")
            + (f" (assigned: {assignee_val})" if assignee_val else "")
        )
    if not items:
        return "No backlog items found."
    return "\n".join(items)


def add_backlog_item(
    description: str,
    category: str = "Other",
    assignee: str = "Erin",
    priority: str = "Medium",
) -> str:
    """Add a new item to the Backlog database."""
    if not NOTION_BACKLOG_DB:
        return "Backlog database not configured."

    properties: dict = {
        "Description": {"title": [{"text": {"content": description}}]},
        "Category": {"select": {"name": category}},
        "Assignee": {"select": {"name": assignee}},
        "Status": {"status": {"name": "Not Started"}},
        "Priority": {"select": {"name": priority}},
        "Created": {"date": {"start": date.today().isoformat()}},
    }
    notion.pages.create(parent={"database_id": NOTION_BACKLOG_DB}, properties=properties)
    return f"Added to backlog: {description} [{category}]"


def complete_backlog_item(page_id: str) -> str:
    """Mark a backlog item as Done by its Notion page ID."""
    notion.pages.update(
        page_id=page_id,
        properties={"Status": {"status": {"name": "Done"}}},
    )
    return "Backlog item marked as done."


def get_next_backlog_suggestion() -> str:
    """Get the least-recently-surfaced incomplete backlog item for daily plan.

    Returns the item description and updates its Last Surfaced date.
    """
    if not NOTION_BACKLOG_DB:
        return "No backlog items — enjoy the free time!"

    results = notion.databases.query(
        database_id=NOTION_BACKLOG_DB,
        filter={"property": "Status", "status": {"does_not_equal": "Done"}},
        sorts=[
            {"property": "Last Surfaced", "direction": "ascending"},
            {"property": "Priority", "direction": "ascending"},
        ],
        page_size=1,
    )

    if not results["results"]:
        return "No backlog items — enjoy the free time!"

    page = results["results"][0]
    page_id = page["id"]
    desc = _get_title(page["properties"].get("Description", {}))
    category = _get_select(page["properties"].get("Category", {}))

    # Update Last Surfaced to today
    notion.pages.update(
        page_id=page_id,
        properties={"Last Surfaced": {"date": {"start": date.today().isoformat()}}},
    )

    label = f" [{category}]" if category else ""
    return f"{desc}{label}"


# ---------------------------------------------------------------------------
# Routine Templates (T010 — stored in Family Profile page)
# ---------------------------------------------------------------------------

def get_routine_templates() -> str:
    """Read the Routine Templates section from the Family Profile page.

    Returns the raw text of the routine templates section, which contains
    structured time block definitions for different daily scenarios.
    """
    blocks = notion.blocks.children.list(block_id=NOTION_FAMILY_PROFILE_PAGE)
    in_section = False
    lines = []
    for block in blocks["results"]:
        text = _get_block_text(block)
        btype = block["type"]
        if "heading" in btype and text and "routine template" in text.lower():
            in_section = True
            continue
        if in_section:
            if "heading" in btype:
                break  # Next section — stop
            if text:
                lines.append(text)
    if not lines:
        return "No routine templates defined yet. Add them during the weekly meeting."
    return "\n".join(lines)


def save_routine_templates(templates_text: str) -> str:
    """Write updated routine templates to the Family Profile page.

    Finds the Routine Templates section and replaces its content.
    """
    blocks = notion.blocks.children.list(block_id=NOTION_FAMILY_PROFILE_PAGE)
    section_start_id = None
    blocks_to_delete = []
    in_section = False

    for block in blocks["results"]:
        text = _get_block_text(block)
        btype = block["type"]
        if "heading" in btype and text and "routine template" in text.lower():
            section_start_id = block["id"]
            in_section = True
            continue
        if in_section:
            if "heading" in btype:
                break  # Next section — stop
            blocks_to_delete.append(block["id"])

    # Delete old content blocks
    for block_id in blocks_to_delete:
        try:
            notion.blocks.delete(block_id=block_id)
        except Exception as e:
            logger.warning("Failed to delete block %s: %s", block_id, e)

    # Add new content after the heading
    target = section_start_id or NOTION_FAMILY_PROFILE_PAGE
    new_blocks = []
    for line in templates_text.split("\n"):
        line = line.rstrip()
        if not line:
            continue
        new_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]},
        })

    if new_blocks:
        notion.blocks.children.append(block_id=target, children=new_blocks)
    return "Routine templates updated."


# ---------------------------------------------------------------------------
# Grocery History (T011 — reference data for meal planning)
# ---------------------------------------------------------------------------

def get_grocery_history(category: str = "") -> str:
    """Get grocery history items, optionally filtered by category."""
    if not NOTION_GROCERY_HISTORY_DB:
        return "Grocery history not configured."

    kwargs: dict = {"database_id": NOTION_GROCERY_HISTORY_DB}
    if category:
        kwargs["filter"] = {"property": "Category", "select": {"equals": category}}
    kwargs["sorts"] = [{"property": "Frequency", "direction": "descending"}]
    kwargs["page_size"] = 50

    results = notion.databases.query(**kwargs)
    items = []
    for page in results["results"]:
        props = page["properties"]
        name = _get_title(props.get("Item Name", {}))
        cat = _get_select(props.get("Category", {}))
        freq = props.get("Frequency", {}).get("number", 0)
        staple = props.get("Staple", {}).get("checkbox", False)
        items.append(f"- {name} [{cat}] — ordered {freq}x" + (" ⭐ staple" if staple else ""))

    if not items:
        return "No grocery history available."
    return "\n".join(items)


def get_staple_items() -> str:
    """Get frequently purchased items (staples) for auto-suggestions."""
    if not NOTION_GROCERY_HISTORY_DB:
        return "Grocery history not configured."

    results = notion.databases.query(
        database_id=NOTION_GROCERY_HISTORY_DB,
        filter={"property": "Staple", "checkbox": {"equals": True}},
        sorts=[{"property": "Frequency", "direction": "descending"}],
    )
    items = []
    for page in results["results"]:
        props = page["properties"]
        name = _get_title(props.get("Item Name", {}))
        cat = _get_select(props.get("Category", {}))
        items.append(f"- {name} [{cat}]")

    if not items:
        return "No staple items identified yet."
    return "\n".join(items)


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
