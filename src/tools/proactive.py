"""Proactive automation tools — reorder suggestions, meal planning, conflict detection, reminders."""

import json
import logging
from datetime import date, datetime, timedelta

from src.config import ANTHROPIC_API_KEY
from src.tools import notion, calendar, ynab, outlook

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# US2: Grocery Reorder Suggestions (T026-T028)
# ---------------------------------------------------------------------------

def check_reorder_items() -> dict:
    """Check grocery history for staple/regular items due for reorder.

    Queries items where days since last ordered >= avg reorder interval.
    Groups results by store, sorted by days overdue.
    """
    from src.tools.notion import notion as notion_client, _get_title, NOTION_GROCERY_HISTORY_DB

    if not NOTION_GROCERY_HISTORY_DB:
        return {"items_by_store": {}, "total": 0, "error": "Grocery History DB not configured"}

    today = date.today()
    due_items = []

    try:
        results = notion_client.databases.query(
            database_id=NOTION_GROCERY_HISTORY_DB,
            filter={
                "and": [
                    {"property": "Type", "select": {"is_not_empty": True}},
                    {"property": "Avg Reorder Days", "number": {"is_not_empty": True}},
                ]
            },
            page_size=100,
        )

        for page in results["results"]:
            props = page["properties"]
            item_type = props.get("Type", {}).get("select", {})
            if not item_type:
                continue
            type_name = item_type.get("name", "")
            if type_name not in ("Staple", "Regular"):
                continue

            avg_reorder = props.get("Avg Reorder Days", {}).get("number")
            if not avg_reorder:
                continue

            last_ordered_prop = props.get("Last Ordered", {}).get("date")
            if not last_ordered_prop or not last_ordered_prop.get("start"):
                # Never ordered — definitely due
                days_since = avg_reorder + 1
            else:
                last_ordered = date.fromisoformat(last_ordered_prop["start"])
                days_since = (today - last_ordered).days

            if days_since >= avg_reorder:
                store_options = props.get("Store", {}).get("multi_select", [])
                store = store_options[0]["name"] if store_options else "Whole Foods"
                due_items.append({
                    "id": page["id"],
                    "name": _get_title(props.get("Item Name", {})),
                    "store": store,
                    "days_overdue": days_since - avg_reorder,
                    "days_since": days_since,
                    "avg_reorder_days": avg_reorder,
                    "type": type_name,
                })

    except Exception as e:
        logger.error("Failed to check reorder items: %s", e)
        return {"items_by_store": {}, "total": 0, "error": str(e)}

    # Group by store, sort by days overdue
    items_by_store: dict[str, list] = {}
    for item in sorted(due_items, key=lambda x: -x["days_overdue"]):
        store = item["store"]
        if store not in items_by_store:
            items_by_store[store] = []
        items_by_store[store].append(item)

    return {"items_by_store": items_by_store, "total": len(due_items)}


def handle_order_confirmation() -> dict:
    """Mark all pending-order items as ordered (Last Ordered = today, clear Pending Order).

    Called when Erin says "groceries ordered" or similar.
    """
    pending = notion.get_pending_orders()
    if not pending:
        return {"status": "no_pending", "message": "No pending orders to confirm."}

    item_ids = [item["id"] for item in pending]
    notion.clear_pending_order(item_ids)

    return {
        "status": "confirmed",
        "items_confirmed": len(item_ids),
        "message": f"Marked {len(item_ids)} items as ordered. Last Ordered updated to today.",
    }


def check_grocery_confirmation() -> dict:
    """Check for unconfirmed grocery orders (pending > 2 days).

    Returns reminder text if items are pending too long.
    """
    pending = notion.get_pending_orders()
    if not pending:
        return {"status": "no_pending"}

    today = date.today()
    overdue = []
    for item in pending:
        push_date = item.get("push_date")
        if push_date:
            pushed = date.fromisoformat(push_date)
            days_ago = (today - pushed).days
            if days_ago >= 2:
                overdue.append({**item, "days_ago": days_ago})

    if not overdue:
        return {"status": "pending_but_recent", "pending_count": len(pending)}

    return {
        "status": "needs_reminder",
        "overdue_items": overdue,
        "message": (
            f"You have {len(overdue)} grocery items that were added to AnyList "
            f"{overdue[0]['days_ago']}+ days ago but haven't been confirmed as ordered. "
            "Did you place the order? Just say 'groceries ordered' to confirm!"
        ),
    }


# ---------------------------------------------------------------------------
# US3: Meal Planning (T033-T035)
# ---------------------------------------------------------------------------

def generate_meal_plan() -> dict:
    """Generate a 6-night dinner plan using saved recipes and family preferences.

    Uses Claude to build the plan considering schedule density, dietary preferences,
    saved recipes, and recent meal history.
    """
    from anthropic import Anthropic

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Gather context
    all_recipes = notion.get_all_recipes()
    recent_plans = []
    try:
        recent_plan = notion.get_meal_plan("")
        if recent_plan and "No meal plan" not in str(recent_plan):
            recent_plans.append(str(recent_plan))
    except Exception:
        pass

    profile = notion.get_family_profile()
    recipes_summary = json.dumps(all_recipes[:20], default=str) if all_recipes else "No saved recipes yet."

    prompt = (
        "Generate a 6-night dinner plan (Monday through Saturday) for this family.\n\n"
        f"Family profile:\n{profile}\n\n"
        f"Saved recipes ({len(all_recipes)} total):\n{recipes_summary}\n\n"
        f"Recent meal plans (avoid repeats):\n{recent_plans[:2] if recent_plans else 'None'}\n\n"
        "Rules:\n"
        "- Mon-Sat dinners only (Sunday is leftovers/eating out)\n"
        "- Simpler meals on busy days (Tue has gymnastics, Fri has nature class)\n"
        "- Use saved recipes when they're a good fit\n"
        "- Kid-friendly focus (Vienna 5, Zoey 3)\n"
        "- No repeats from last 2 weeks\n"
        "- Mix of complexities\n\n"
        "Return ONLY valid JSON array:\n"
        '[{"day": "Monday", "meal_name": "...", "source": "recipe_id or general", '
        '"ingredients": [{"name": "...", "quantity": "...", "unit": "..."}], '
        '"complexity": "easy|medium|involved"}]'
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse meal plan", "raw": raw[:500]}

    return {"success": True, "plan": plan, "nights": len(plan)}


def merge_grocery_list(meal_plan: list[dict], include_reorder: bool = True) -> dict:
    """Merge meal plan ingredients with reorder-due staples into a single grocery list.

    Deduplicates by normalized name, deducts recently ordered items,
    and groups by store.
    """
    from src.tools.recipes import recipe_to_grocery_list

    items_map: dict[str, dict] = {}  # normalized_name -> item info

    # Collect ingredients from meal plan
    for day in meal_plan:
        source = day.get("source", "general")
        if source and source != "general":
            # Use recipe_to_grocery_list for saved recipes
            try:
                grocery = recipe_to_grocery_list(source)
                for item in grocery.get("needed_items", []):
                    key = item["name"].lower().strip()
                    if key not in items_map:
                        items_map[key] = {
                            "name": item["name"],
                            "quantity": item.get("quantity", ""),
                            "store": item.get("store", "Whole Foods"),
                            "source": day["meal_name"],
                        }
            except Exception as e:
                logger.warning("Failed to get grocery list for recipe %s: %s", source, e)

        # Add general ingredients
        for ing in day.get("ingredients", []):
            name = ing.get("name", "")
            if not name:
                continue
            key = name.lower().strip()
            qty = f"{ing.get('quantity', '')} {ing.get('unit', '')}".strip()
            if key not in items_map:
                items_map[key] = {
                    "name": name,
                    "quantity": qty,
                    "store": "Whole Foods",
                    "source": day["meal_name"],
                }

    # Add reorder-due staples
    if include_reorder:
        reorder = check_reorder_items()
        for store, store_items in reorder.get("items_by_store", {}).items():
            for item in store_items:
                key = item["name"].lower().strip()
                if key not in items_map:
                    items_map[key] = {
                        "name": item["name"],
                        "quantity": "",
                        "store": store,
                        "source": "staple reorder",
                    }

    # Group by store
    by_store: dict[str, list] = {}
    for item in items_map.values():
        store = item["store"]
        if store not in by_store:
            by_store[store] = []
        by_store[store].append(item)

    return {"items_by_store": by_store, "total": len(items_map)}


def handle_meal_swap(plan: list[dict], day: str, new_meal: str) -> dict:
    """Swap a meal in the plan and recalculate the grocery list.

    Args:
        plan: Current meal plan (list of day dicts).
        day: Day to swap (e.g., "Wednesday").
        new_meal: New meal name.
    """
    from anthropic import Anthropic

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Update the plan
    for entry in plan:
        if entry["day"].lower() == day.lower():
            entry["meal_name"] = new_meal
            entry["source"] = "general"
            # Get ingredients from Claude
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": (
                        f"List the ingredients for '{new_meal}' (family of 4, kid-friendly). "
                        "Return ONLY a JSON array: "
                        '[{"name": "...", "quantity": "...", "unit": "..."}]'
                    ),
                }],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
            try:
                entry["ingredients"] = json.loads(raw)
            except json.JSONDecodeError:
                entry["ingredients"] = []
            break

    grocery = merge_grocery_list(plan)
    return {"plan": plan, "grocery_list": grocery}


# ---------------------------------------------------------------------------
# US5: Calendar Conflict Detection (T043)
# ---------------------------------------------------------------------------

def detect_conflicts(days_ahead: int = 1) -> list[dict]:
    """Detect calendar conflicts across all calendars and routine templates.

    Returns list of conflicts: hard (overlapping events) and soft (event vs routine).
    """
    today = date.today()
    conflicts = []

    # Get events from all calendars
    cal_events_raw = calendar.get_calendar_events(days_ahead, ["jason", "erin", "family"])
    outlook_events_raw = ""
    for d in range(days_ahead):
        check_date = today + timedelta(days=d)
        try:
            day_events = outlook.get_outlook_events(check_date.isoformat())
            outlook_events_raw += f"\n{day_events}" if day_events else ""
        except Exception:
            pass

    # Get routine templates
    try:
        templates = notion.get_routine_templates()
    except Exception:
        templates = ""

    # Use Claude to analyze conflicts (simpler than hand-parsing multiple calendar formats)
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = (
        f"Analyze these calendars for the next {days_ahead} day(s) starting {today.isoformat()}.\n\n"
        f"Google Calendar events:\n{cal_events_raw}\n\n"
        f"Outlook (Jason work) events:\n{outlook_events_raw}\n\n"
        f"Family routine templates:\n{templates}\n\n"
        "Find:\n"
        "1. Hard conflicts: two events with overlapping times across any calendars\n"
        "2. Soft conflicts: events that overlap with routine commitments "
        "(pickup times, dropoff times, Sandy/grandma schedule)\n\n"
        "Return ONLY a JSON array (empty if no conflicts):\n"
        '[{"day": "YYYY-MM-DD", "type": "hard|soft", "event": "event name + time", '
        '"conflict_with": "other event or routine", "suggestion": "how to resolve"}]'
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    try:
        conflicts = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse conflict detection results")
        conflicts = []

    return conflicts


# ---------------------------------------------------------------------------
# US6: Action Item Progress Check (T047)
# ---------------------------------------------------------------------------

def check_action_item_progress() -> dict:
    """Check action item completion for the current week.

    Returns summary with counts and items grouped by assignee.
    """
    items_raw = notion.get_action_items("", "")
    if isinstance(items_raw, str):
        # Parse the string response from notion
        return {"status": "error", "raw": items_raw}

    # get_action_items returns a formatted string, so we need to query directly
    from src.tools.notion import notion as notion_client, _get_title, NOTION_ACTION_ITEMS_DB

    if not NOTION_ACTION_ITEMS_DB:
        return {"status": "error", "message": "Action Items DB not configured"}

    results = notion_client.databases.query(
        database_id=NOTION_ACTION_ITEMS_DB,
        filter={"property": "Due Context", "select": {"equals": "This Week"}},
    )

    total = len(results["results"])
    done = 0
    not_started = 0
    in_progress = 0
    by_assignee: dict[str, list] = {}
    rolled_over = []

    for page in results["results"]:
        props = page["properties"]
        status = props.get("Status", {}).get("status", {}).get("name", "Not Started")
        assignee_people = props.get("Assignee", {}).get("people", [])
        assignee = assignee_people[0].get("name", "Unassigned") if assignee_people else "Unassigned"
        # Try rich_text fallback for assignee
        if assignee == "Unassigned":
            assignee_rt = props.get("Assignee", {}).get("rich_text", [])
            if assignee_rt:
                assignee = assignee_rt[0].get("plain_text", "Unassigned")
        # Some databases use select for assignee
        if assignee == "Unassigned":
            assignee_select = props.get("Assignee", {}).get("select")
            if assignee_select:
                assignee = assignee_select.get("name", "Unassigned")

        title = _get_title(props.get("Description", props.get("Name", {})))
        is_rolled = props.get("Rolled Over", {}).get("checkbox", False)

        if status == "Done":
            done += 1
        elif status == "In Progress":
            in_progress += 1
        else:
            not_started += 1

        if status != "Done":
            item = {"title": title, "status": status, "rolled_over": is_rolled}
            if assignee not in by_assignee:
                by_assignee[assignee] = []
            by_assignee[assignee].append(item)
            if is_rolled:
                rolled_over.append(title)

    if total == done:
        return {
            "status": "all_complete",
            "total": total,
            "done": done,
            "message": "All caught up! Every action item for this week is done.",
        }

    return {
        "status": "incomplete",
        "total": total,
        "done": done,
        "in_progress": in_progress,
        "not_started": not_started,
        "remaining_by_assignee": by_assignee,
        "rolled_over_items": rolled_over,
    }


# ---------------------------------------------------------------------------
# US7: Budget Summary Formatter (T050)
# ---------------------------------------------------------------------------

def format_budget_summary() -> dict:
    """Format YNAB budget data into a structured WhatsApp message.

    Highlights over-budget categories and shows spending trends.
    """
    raw = ynab.get_budget_summary("", "")
    if isinstance(raw, str) and "error" in raw.lower():
        return {"status": "error", "message": raw}

    # Use Claude to format the budget data nicely
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": (
                f"Format this YNAB budget data for a WhatsApp message:\n\n{raw}\n\n"
                "Rules:\n"
                "- Start with *💰 Weekly Budget Summary*\n"
                "- List over-budget categories first with ⚠️ and amount over\n"
                "- Then list top on-track categories briefly\n"
                "- End with total spent vs total budget\n"
                "- Use WhatsApp formatting (*bold*, bullets)\n"
                "- Keep it scannable (< 500 chars if possible)"
            ),
        }],
    )

    formatted = response.content[0].text.strip()
    return {"status": "ok", "message": formatted, "raw_data": str(raw)}
