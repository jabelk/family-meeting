"""Claude AI assistant core — system prompt, tool definitions, and message handling."""

import json
import logging
from anthropic import Anthropic
from src.config import ANTHROPIC_API_KEY, PHONE_TO_NAME
from src.tools import notion, calendar, ynab, outlook, recipes, proactive, nudges, laundry, chores, downshiftology

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Module-level storage for images in the current conversation.
# Set by handle_message, consumed by extract_and_save_recipe tool handler.
# This avoids passing the large base64 payload through Claude's tool-call JSON.
# For multi-page recipes, images accumulate until the tool is called.
_current_image_data: dict | None = None  # most recent image (single-page fast path)
_buffered_images: list[dict] = []  # accumulated images for multi-page recipes

SYSTEM_PROMPT = """\
You are Mom Bot — the family assistant for Jason and Erin's family. You live \
in their WhatsApp group chat and help plan, run, and follow up on weekly \
family meetings. You also generate daily plans for Erin and manage their \
household coordination. Erin named you "Mom Bot" — lean into that identity \
when chatting (friendly, organized, slightly playful).

**Family:**
- Jason (partner) — works from home at Cisco, has Google Calendar (personal) \
+ Outlook (work)
- Erin (partner) — stays at home with the kids
- Vienna (daughter, age 5) — kindergarten at Roy Gomm, M-F
- Zoey (daughter, age 3)

**Childcare:**
- Sandy Belk (Jason's mom) takes Zoey: Monday 9am-12pm, Tuesday 10am-1pm
- Zoey starts Milestones preschool late April/early May (replaces Sandy days)

**Weekly Schedule:**
- Mon: Erin drops off Vienna 9:30am, Sandy has Zoey 9-12. Pickup Vienna 3:30.
- Tue: Erin drops off Vienna 9:30am, Sandy has Zoey 10-1. Pickup Vienna 3:15 \
(early — Zoey's gymnastics class).
- Wed: Erin drops off Vienna 9:30am, Zoey with Erin. Pickup Vienna 3:45 (not 3:30).
- Thu: Jason does driving drop-off for Vienna (Jason needs to be at BSF at \
Sparks Christian Fellowship by 10am). Zoey with Erin. Pickup Vienna 3:30.
- Fri: Erin drops off Vienna 9:30am, Zoey with Erin. Nature class at Bartley \
Ranch Park 10:20-11:20 (Mar 4–May 27). Pickup Vienna 3:30.
- Sat: Leave house 8am for Vienna's ski lesson 9-11 (~5 weeks, ending late Mar). \
- Sun: Leave house 8:15 for church 9-10. Next 4 weeks: Erin's parents take \
Zoey & Vienna after church until ~4pm → Jason & Erin attend marriage class.

**Jason's breakfast preference:** 1 scrambled egg, 2 bacon, high fiber \
tortilla, sriracha ketchup + Crystal hot sauce, Coke Zero or Diet Dr Pepper

**Erin's daily needs:** Defined chore blocks, rest/out-of-house time, \
personal development (knitting, projects), exercise, side work for her \
father's real estate business. She tends to procrastinate on getting out \
of the house — the assistant should gently encourage this.

**Erin's chore needs:**
- Laundry: must be home for washer→dryer transfer. Good pattern: start wash \
in morning chore block, move to dryer at ~2:30 before Vienna pickup.
- Vacuum and cooking/meal prep need scheduled blocks.
- Erin likes meal prep but is open to efficient daily cooking instead.
- Best chore windows: Mon morning (Zoey with Sandy), Tue morning (Zoey with \
Sandy), Sun afternoon (kids with grandparents, next 4 weeks).

**Your rules:**
1. ALWAYS format responses as structured checklists with WhatsApp formatting:
   - Use *bold* for section headers
   - Use • or - for bullet lists
   - Use ✅ for completed items, ⬜ for pending items
   - NEVER respond with walls of unformatted prose
2. Keep responses concise and scannable — these are busy parents
3. When generating a *weekly agenda*, use these sections in order:
   📅 This Week (calendar events from all 3 Google Calendars + Jason's \
work calendar)
   ✅ Review Last Week (open action items from prior week)
   🏠 Chores (to be assigned during meeting)
   🍽 Meals (meal plan status)
   💰 Finances (budget summary prompt)
   📋 Backlog Review (items surfaced this week — done or carry over?)
   📌 Custom Topics (user-added items)
   🎯 Goals (long-term items)
4. When parsing action items, identify the assignee (Jason or Erin) and \
create separate items for each task mentioned
5. For meal plans, default to kid-friendly meals. Read family preferences \
from the profile before suggesting. If grocery history is available, use \
actual Whole Foods product names for the grocery list and suggest meals \
based on what the family actually buys. Suggest staple items that might \
be running low.
6. For budget summaries, highlight over-budget categories first
7. If a partner mentions a lasting preference (dietary restriction, recurring \
topic, schedule change), use update_family_profile to save it
8. If an external service (Calendar, YNAB, Outlook) is unavailable, skip \
that section and note it — never fail the whole response

**Daily planner rules** (when asked "what's my day look like?" or triggered \
by the morning briefing):
9. Read routine templates from the family profile to get Erin's daily structure. \
Each day of the week has different commitments — use the day-specific schedule \
above (not just "Zoey with Erin" vs "Zoey with grandma").
10. Check who has Zoey today (Erin, Sandy, or grandparents) and what day-specific \
activities apply (gymnastics Tue, nature class Fri, ski Sat, church Sun, etc.)
11. Fetch Jason's work calendar (Outlook) to show his meeting windows so \
Erin can plan breakfast timing. If he's free 7-7:30am, breakfast window is \
then. If he has early meetings, note when he's free.
12. Pick one backlog item to suggest for today's development/growth block
13. After generating the plan, write time blocks to Erin's Google Calendar \
using write_calendar_blocks so they appear in her Apple Calendar with push \
notifications
14. Recurring activities (chores, gym, rest) are just calendar blocks for \
structure — no check-in needed. One-off backlog items get followed up at \
the weekly meeting.

**Childcare context overrides:**
15. If a partner says "mom isn't taking Zoey today" or "grandma has Zoey \
Wednesday", update the family profile and offer to regenerate today's plan
16. If the backlog is empty, say "No backlog items — enjoy the free time!" \
and suggest adding some during the weekly meeting

**Grocery integration:**
17. After generating a meal plan, offer: "Want me to push this to AnyList \
for delivery?" If the user says yes or "order groceries", push the grocery \
list to AnyList via push_grocery_list. If the AnyList sidecar is unavailable, \
send a well-formatted list organized by store section (Produce, Meat, Dairy, \
Pantry, Frozen, Bakery, Beverages) as a fallback.

**Recipe catalogue:**
18. When you receive a photo, assume it's a cookbook recipe unless told \
otherwise. Call extract_and_save_recipe with the cookbook_name from the caption \
if it mentions a book (e.g., "save this from the keto book" → \
cookbook_name="keto book"). Report what was extracted and flag any unclear \
portions. If the user says "there's another page" or sends another photo \
shortly after, tell them to send the next page — all buffered photos will \
be combined into one recipe when you call extract_and_save_recipe. For \
multi-page recipes, wait until the user indicates all pages are sent \
before calling the tool.
19. For recipe searches ("what was that steak recipe?"), use search_recipes \
with a natural language query. Show the top results with name, cookbook, \
prep/cook time.
20. When asked to cook a saved recipe or add recipe ingredients to the \
grocery list, use recipe_to_grocery_list. Present needed vs already-have \
items, then offer to push needed items to AnyList.
21. To browse saved cookbooks or list what's been catalogued, use \
list_cookbooks.

**Nudge interactions (tone: warm, encouraging, zero guilt):**
22. You send proactive departure reminders before Erin's calendar events. \
If Erin says "snooze" or "remind me in 10", snooze the most recent departure \
nudge (creates a new reminder in 10 minutes). If she says "stop", "dismiss", \
or "I know", dismiss the nudge (no more reminders for that event).
23. If Erin says "quiet day", "no nudges today", or "leave me alone today", \
call set_quiet_day to suppress all proactive nudges for the rest of the day. \
She can still message you and get responses — only proactive nudges stop.
24. When you send a chore suggestion and Erin replies "done", "finished", or \
"did it", call complete_chore with the chore name. If she says "skip", "not \
now", or "pass", call skip_chore. Be encouraging when she completes chores \
and guilt-free when she skips.
25. When Erin mentions chore preferences ("I like to vacuum on Wednesdays", \
"I hate cleaning bathrooms", "can we do laundry every other day?"), call \
set_chore_preference. Map natural language: "hate"/"ugh" → dislike, \
"love"/"enjoy" → like. When she asks "what chores have I done?" or "chore \
history", call get_chore_history.
26. When Erin says "started laundry", "doing a load", "washing clothes", etc., \
call start_laundry. She can optionally specify times ("washer takes 50 min"). \
When she says "moved to dryer" or "put it in the dryer", call advance_laundry. \
If she says "never mind", "didn't do laundry", or "cancel laundry", call \
cancel_laundry.

**Downshiftology recipe search:**
27. For recipe searches from Downshiftology ("find me a chicken dinner", "keto \
breakfast ideas", "what should I make tonight?"), use search_downshiftology. \
Map natural language to parameters: "chicken dinner" → query="chicken", \
course="dinner". "quick keto" → dietary="keto", max_time=30. Show results \
as a numbered list with name, time, and link.
28. For recipe details ("tell me more about number 2", "what's in number 3"), \
use get_downshiftology_details with the result number. The response includes \
ingredients, instructions, nutrition, and which ingredients the family \
typically buys.
29. When Erin says "save number N", "import that recipe", or "add it to our \
recipes" after a Downshiftology search, use import_downshiftology_recipe \
with the result number. It checks for duplicates and saves to the Notion \
catalogue under the "Downshiftology" cookbook.
30. Downshiftology is the only external recipe source. For saved recipe \
searches ("what was that steak recipe?"), still use search_recipes. Only \
use search_downshiftology for new recipe discovery.

**Budget management:**
31. For transaction searches ("what did we spend at Costco?"), use \
search_transactions with the payee name. Show amounts as dollars, sorted \
by most recent. Default search is current month.
32. For recategorization ("categorize the Target charge as Home Supplies"), \
use recategorize_transaction. If multiple matches, show the list and ask \
which one. Always confirm the change.
33. For manual transactions ("add $35 cash for farmers market under Groceries"), \
use create_transaction. Default to checking account and today's date.
34. For budget moves ("move $100 from Dining Out to Groceries"), use move_money. \
Always confirm both categories' new amounts. Warn if source category would go \
negative.
35. For budget adjustments ("budget $200 more for Groceries"), use \
update_category_budget. Confirm old and new budgeted amounts.

**Quick reminders & events:**
36. When someone says "remind me to...", "remind Jason to...", "pick up X at \
Y time", "don't forget to...", or mentions any time-specific task, use \
create_quick_event to add it to the shared family calendar. Format the \
summary as "Sender → Assignee: task" (e.g., "Erin → Jason: pick up dog"). \
If it's a self-reminder, use just "Erin: dentist appointment". Include the \
original message as the event description for context. The event goes on the \
shared family calendar so both partners can see it. Infer today's date and \
Pacific time if not specified. Default to a 15-minute popup reminder.

The current sender's name will be provided with each message.
"""

# ---------------------------------------------------------------------------
# Tool definitions for Claude
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_calendar_events",
        "description": "Fetch upcoming events from Google Calendars for the next N days. Reads from Jason's personal, Erin's personal, and the shared family calendar. Events are labeled by source.",
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
                    "description": "Which calendars to read: 'jason', 'erin', 'family'. Default all three.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_outlook_events",
        "description": "Fetch Jason's work calendar events (Outlook/Cisco) for a specific date. Shows meeting times so Erin can plan around his schedule. Use for daily plan generation and breakfast timing.",
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
        "description": "Read the family profile including member info, dietary preferences, routine templates, childcare schedule, recurring agenda topics, and configuration.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "update_family_profile",
        "description": "Update the family profile with new persistent information. Use when a partner mentions a lasting preference, dietary restriction, schedule change, childcare update, or recurring topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "Which section to update: 'Preferences', 'Recurring Agenda Topics', 'Members', 'Childcare Schedule', 'Routine Templates', or 'Configuration'."},
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
    # --- YNAB transaction tools (US1) ---
    {
        "name": "search_transactions",
        "description": "Search recent YNAB transactions by payee name, category, or uncategorized status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "payee": {"type": "string", "description": "Payee name to search for (fuzzy match)."},
                "category": {"type": "string", "description": "Category name to filter by."},
                "since_date": {"type": "string", "description": "ISO date floor (default: first of current month)."},
                "uncategorized_only": {"type": "boolean", "description": "If true, return only uncategorized transactions."},
            },
            "required": [],
        },
    },
    {
        "name": "recategorize_transaction",
        "description": "Change the category of an existing transaction. Finds by payee/amount/date, then updates.",
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
        "description": "Create a manual YNAB transaction (e.g., cash purchase, reimbursement).",
        "input_schema": {
            "type": "object",
            "properties": {
                "payee": {"type": "string", "description": "Payee/merchant name."},
                "amount": {"type": "number", "description": "Dollar amount (positive number — system makes it negative for outflow)."},
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
        "description": "Adjust the budgeted amount for a YNAB category this month (add or subtract dollars).",
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
        "description": "Move budgeted money from one YNAB category to another.",
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
        "description": "Query Erin's personal backlog of one-off tasks (home improvement, personal growth, side work). These are not weekly action items — they persist until done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignee": {"type": "string", "description": "Filter by assignee. Default empty (all)."},
                "status": {"type": "string", "description": "Filter by status: 'Not Started', 'In Progress', 'Done', or 'open'."},
            },
            "required": [],
        },
    },
    {
        "name": "add_backlog_item",
        "description": "Add a one-off task to the backlog (e.g., 'reorganize tupperware', 'clean garage', 'knitting project'). These are personal growth / home improvement tasks worked through at Erin's pace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "What needs to be done."},
                "category": {
                    "type": "string",
                    "description": "Category: 'Home Improvement', 'Personal Growth', 'Side Work', 'Exercise', or 'Other'.",
                    "default": "Other",
                },
                "assignee": {"type": "string", "description": "Who this is for. Default 'Erin'.", "default": "Erin"},
                "priority": {"type": "string", "description": "'High', 'Medium', or 'Low'. Default 'Medium'.", "default": "Medium"},
            },
            "required": ["description"],
        },
    },
    {
        "name": "complete_backlog_item",
        "description": "Mark a backlog item as done by its Notion page ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "The Notion page ID of the backlog item to mark done."},
            },
            "required": ["page_id"],
        },
    },
    # --- Routine templates (US5) ---
    {
        "name": "get_routine_templates",
        "description": "Read Erin's daily routine templates from the family profile. Templates define time blocks for different scenarios (e.g., 'Weekday with Zoey', 'Weekday with Grandma'). Used for daily plan generation.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # --- Calendar write (US5) ---
    {
        "name": "write_calendar_blocks",
        "description": "Write time blocks to Erin's Google Calendar. Use after generating a daily plan to create events that appear in her Apple Calendar with push notifications. Each block needs: summary, start_time (ISO), end_time (ISO), and color_category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "blocks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string", "description": "Event title (e.g., 'Chore block', 'Rest time')"},
                            "start_time": {"type": "string", "description": "ISO datetime (e.g., '2026-02-23T09:30:00-08:00')"},
                            "end_time": {"type": "string", "description": "ISO datetime"},
                            "color_category": {
                                "type": "string",
                                "description": "Category for color coding: 'chores', 'rest', 'development', 'exercise', 'side_work', or 'backlog'.",
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
        "description": "Create a reminder or event on the shared family calendar. Both Jason and Erin will see it. Use when someone says 'remind me to...', 'pick up X at Y time', 'don't forget to...', or any time-specific task. Includes a 15-minute popup reminder by default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title. Format as 'Sender → Assignee: task' (e.g., 'Erin → Jason: pick up dog'). If self-reminder, use 'Erin: dentist appointment'."},
                "start_time": {"type": "string", "description": "ISO datetime (e.g., '2026-02-24T12:30:00-08:00'). Infer today's date if not specified."},
                "end_time": {"type": "string", "description": "ISO datetime. Defaults to start + 30 min if omitted."},
                "description": {"type": "string", "description": "Original message text for context (e.g., 'Erin said: remind Jason to pick up the dog at 12:30')."},
                "reminder_minutes": {"type": "number", "description": "Minutes before event to send popup reminder. Default 15.", "default": 15},
            },
            "required": ["summary", "start_time"],
        },
    },
    # --- Grocery tools (US3 + US6) ---
    {
        "name": "get_grocery_history",
        "description": "Get grocery purchase history from past Whole Foods orders. Use when planning meals to reference what the family actually buys. Can filter by category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Filter by category: 'Produce', 'Meat', 'Dairy', 'Pantry', 'Frozen', 'Bakery', 'Beverages'. Empty for all."},
            },
            "required": [],
        },
    },
    {
        "name": "get_staple_items",
        "description": "Get frequently purchased grocery items (staples). Suggest these when generating grocery lists — the family probably needs them every week.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "push_grocery_list",
        "description": "Push grocery list items to AnyList for Whole Foods delivery. Clears old items first, then adds the new list. Erin opens AnyList → 'Order Pickup or Delivery' → Whole Foods. If the service is unavailable, returns an error and you should send a formatted list via WhatsApp instead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of grocery items to add (e.g., ['Chicken breast', 'Rice', 'Stir-fry veggies']).",
                },
            },
            "required": ["items"],
        },
    },
    # --- Recipe tools (US1) ---
    {
        "name": "extract_and_save_recipe",
        "description": "Extract a recipe from a cookbook photo using AI vision and save it to the recipe catalogue. The photo from the current conversation is used automatically — just provide the cookbook name if mentioned.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cookbook_name": {"type": "string", "description": "Name of the cookbook (e.g., 'The Keto Book'). Defaults to 'Uncategorized'."},
            },
            "required": [],
        },
    },
    {
        "name": "search_recipes",
        "description": "Search the recipe catalogue by name, cookbook, or tags. Returns matching recipes with name, cookbook, tags, prep/cook time, and usage count.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (recipe name, ingredient, or description)."},
                "cookbook_name": {"type": "string", "description": "Filter by cookbook name. Empty for all."},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tags: Keto, Kid-Friendly, Quick, Vegetarian, Comfort Food, Soup, Salad, Pasta, Meat, Seafood.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_recipe_details",
        "description": "Get full recipe details including ingredients list, step-by-step instructions, photo URL, and all metadata.",
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
        "description": "Generate a grocery list from a saved recipe. Cross-references ingredients against grocery purchase history to show what's needed vs what you likely already have. Supports servings scaling.",
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
        "description": "List all saved cookbooks with their recipe counts. Use to show what's been catalogued.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # --- Downshiftology recipe tools (Feature 005) ---
    {
        "name": "search_downshiftology",
        "description": "Search Downshiftology.com for healthy recipes by course, cuisine, ingredient, dietary preference, or time constraint. Returns a numbered list of matching recipes with names, times, tags, and links.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text search term (e.g., 'chicken', 'sweet potato')."},
                "course": {"type": "string", "description": "Course type: dinner, breakfast, appetizer, side-dish, salad, soup, snack, dessert, drinks."},
                "cuisine": {"type": "string", "description": "Cuisine: american, mexican, italian, mediterranean, asian, french, indian, greek, middle-eastern."},
                "dietary": {"type": "string", "description": "Dietary preference: keto, paleo, whole30, gluten-free, dairy-free, vegan, vegetarian."},
                "max_time": {"type": "number", "description": "Maximum total time in minutes (e.g., 30 for quick meals)."},
            },
            "required": [],
        },
    },
    {
        "name": "get_downshiftology_details",
        "description": "Get full details of a Downshiftology recipe from search results, including ingredients, instructions, nutrition, and grocery history match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "result_number": {"type": "number", "description": "Number from the most recent Downshiftology search results (1-based)."},
            },
            "required": ["result_number"],
        },
    },
    {
        "name": "import_downshiftology_recipe",
        "description": "Import a Downshiftology recipe into the family's recipe catalogue for meal planning. Checks for duplicates by source URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "result_number": {"type": "number", "description": "Number from most recent search results (e.g., 2)."},
                "recipe_name": {"type": "string", "description": "Recipe name to search and import (alternative to number)."},
            },
            "required": [],
        },
    },
    # --- Nudge tools (Feature 003) ---
    {
        "name": "set_quiet_day",
        "description": "Suppress all proactive nudges (departure reminders, chore suggestions) for the rest of today. Use when Erin says 'quiet day', 'no nudges today', or 'leave me alone today'. She can still message the bot and get responses — only proactive nudges are paused.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "complete_chore",
        "description": "Mark a chore as completed. Updates the Chores database and marks the nudge as done. Use when Erin says 'done', 'finished', 'did it' after a chore suggestion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chore_name": {"type": "string", "description": "Name of the completed chore (matched against Chores DB)."},
            },
            "required": ["chore_name"],
        },
    },
    {
        "name": "skip_chore",
        "description": "Skip a suggested chore (won't be re-suggested today). Use when Erin says 'skip', 'not now', 'pass' to a chore suggestion.",
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
        "description": "Start a laundry session with timed reminders. Creates washer-done nudge and follow-up nudge. Checks calendar for conflicts with dryer timing. Use when Erin says 'started laundry', 'doing a load', etc.",
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
        "description": "Move laundry to dryer phase. Creates dryer-done nudge and cancels follow-up. Use when Erin says 'moved to dryer', 'put it in the dryer', etc.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "cancel_laundry",
        "description": "Cancel the active laundry session and all pending laundry reminders. Use when Erin says 'never mind', 'didn't do laundry', or 'cancel laundry'.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "set_chore_preference",
        "description": "Update Erin's preferences for a chore: how often, preferred days, and like/dislike. Use when Erin says things like 'I like to vacuum on Wednesdays', 'I hate cleaning bathrooms', 'vacuum weekly instead of daily'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chore_name": {"type": "string", "description": "Chore to update preferences for."},
                "preference": {
                    "type": "string",
                    "description": "'like', 'neutral', or 'dislike'. Use 'like' for 'I enjoy...', 'dislike' for 'I hate...', etc.",
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
        "description": "Show what chores Erin has completed recently. Use when she asks 'what have I done this week?', 'chore history', etc.",
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
        "description": "Check grocery history for staple/regular items due for reorder. Returns items grouped by store with days overdue. Use when asked about grocery needs or to proactively suggest reorders.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "confirm_groceries_ordered",
        "description": "Mark all pending grocery orders as confirmed (updates Last Ordered date). Call when user says 'groceries ordered', 'placed the order', etc.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "generate_meal_plan",
        "description": "Generate a 6-night dinner plan (Mon-Sat) considering saved recipes, family preferences, schedule density, and recent meal history. Returns structured plan with ingredients.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "handle_meal_swap",
        "description": "Swap a meal in the current plan and recalculate the grocery list. Use when user says 'swap Wednesday for tacos' or similar.",
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
]

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
        events_data.append({
            "summary": block["summary"],
            "start_time": block["start_time"],
            "end_time": block["end_time"],
            "color_id": color_id,
        })

    created = calendar.batch_create_events(events_data, calendar_name="erin")
    return f"Created {created} calendar blocks on Erin's calendar."


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
        return f"AnyList is unavailable ({e}). Please send the grocery list as a formatted WhatsApp message organized by store section instead."


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


# Map tool names to functions
TOOL_FUNCTIONS = {
    "get_calendar_events": lambda **kw: calendar.get_calendar_events(
        kw.get("days_ahead", 7), kw.get("calendar_names")
    ),
    "get_outlook_events": lambda **kw: outlook.get_outlook_events(kw.get("date", "")),
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
    "search_transactions": lambda **kw: ynab.search_transactions(
        kw.get("payee", ""), kw.get("category", ""), kw.get("since_date", ""), kw.get("uncategorized_only", False)
    ),
    "recategorize_transaction": lambda **kw: ynab.recategorize_transaction(
        kw.get("payee", ""), kw.get("amount", 0), kw.get("date", ""), kw.get("new_category", "")
    ),
    "create_transaction": lambda **kw: ynab.create_transaction(
        kw.get("payee", ""), kw.get("amount", 0), kw.get("category", ""),
        kw.get("date", ""), kw.get("memo", ""), kw.get("account", "")
    ),
    "update_category_budget": lambda **kw: ynab.update_category_budget(kw.get("category", ""), kw.get("amount", 0)),
    "move_money": lambda **kw: ynab.move_money(
        kw.get("from_category", ""), kw.get("to_category", ""), kw.get("amount", 0)
    ),
    # Backlog
    "get_backlog_items": lambda **kw: notion.get_backlog_items(kw.get("assignee", ""), kw.get("status", "")),
    "add_backlog_item": lambda **kw: notion.add_backlog_item(
        kw["description"], kw.get("category", "Other"), kw.get("assignee", "Erin"), kw.get("priority", "Medium")
    ),
    "complete_backlog_item": lambda **kw: notion.complete_backlog_item(kw["page_id"]),
    # Routine templates
    "get_routine_templates": lambda **kw: notion.get_routine_templates(),
    # Calendar write
    "write_calendar_blocks": _handle_write_calendar_blocks,
    "create_quick_event": lambda **kw: calendar.create_quick_event(
        kw["summary"], kw["start_time"], kw.get("end_time", ""),
        kw.get("description", ""), int(kw.get("reminder_minutes", 15))
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
        kw.get("query", ""), kw.get("course", ""), kw.get("cuisine", ""),
        kw.get("dietary", ""), int(kw.get("max_time", 0))
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
    "handle_meal_swap": lambda **kw: proactive.handle_meal_swap(
        kw["plan"], kw["day"], kw["new_meal"]
    ),
}


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
            {"type": "text", "text": f"[From {sender_name}]: {message_text}{buffer_note}"},
        ]
    else:
        user_content = f"[From {sender_name}]: {message_text}"

    messages = [{"role": "user", "content": user_content}]

    # Agentic tool-use loop (capped to prevent runaway API costs)
    MAX_TOOL_ITERATIONS = 25
    iteration = 0

    while True:
        iteration += 1
        if iteration > MAX_TOOL_ITERATIONS:
            logger.warning("Tool loop hit max iterations (%d) — stopping", MAX_TOOL_ITERATIONS)
            return "I hit my processing limit for this request. Please try a simpler question or break it into parts."

        response = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=2048,
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
                    logger.info("Tool call [%d/%d]: %s(%s)", iteration, MAX_TOOL_ITERATIONS, tool_name, json.dumps(tool_input))

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


def generate_daily_plan(target: str = "erin") -> str:
    """Generate a daily plan programmatically (called by n8n cron endpoint).

    Constructs a prompt that triggers the full daily plan flow through Claude.
    """
    prompt = (
        f"Generate today's daily plan for {target.title()}. "
        "Check the routine templates, see who has Zoey today, look at Jason's "
        "work calendar for meeting windows, check today's Google Calendar events, "
        "pick a backlog item to suggest, and write the time blocks to Erin's "
        "Google Calendar. Format the plan for WhatsApp."
    )
    return handle_message("system", prompt)
