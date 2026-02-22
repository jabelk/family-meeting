# Data Model: AI-Powered Weekly Family Meeting Assistant

**Branch**: `001-ai-meeting-assistant` | **Date**: 2026-02-22 (v2 — expanded scope)

All persistent data is stored in Notion databases. Erin never accesses Notion
directly — the assistant manages all reads/writes. Jason can browse Notion if
he wants but doesn't need to.

## Entity: Action Item

Stored in a Notion database named "Action Items".

| Property     | Type          | Description                                      |
|-------------|---------------|--------------------------------------------------|
| Description | Title         | What needs to be done                            |
| Assignee    | Select        | Which partner (Jason / Erin)                    |
| Status      | Status        | Not Started → In Progress → Done                 |
| Due Context | Select        | "This Week" / "Ongoing" / "Someday"              |
| Created     | Date          | When the item was created                        |
| Meeting     | Relation      | Link to the Meeting where this was captured      |
| Rolled Over | Checkbox      | True if carried forward from a previous week     |

**Lifecycle**: Created during or after a meeting → status updated during the
week → reviewed in next meeting's agenda. Incomplete items auto-rollover
(Rolled Over = true) when the next agenda is generated. Partners can mark
items as Done or drop them at any time.

## Entity: Backlog Item

Stored in a Notion database named "Backlog".

| Property     | Type          | Description                                      |
|-------------|---------------|--------------------------------------------------|
| Description | Title         | What needs to be done (e.g., "Reorganize tupperware") |
| Category    | Select        | "Home Improvement" / "Personal Growth" / "Side Work" / "Exercise" / "Other" |
| Assignee    | Select        | Which partner (Jason / Erin)                    |
| Status      | Status        | Not Started → In Progress → Done                 |
| Priority    | Select        | "High" / "Medium" / "Low"                        |
| Created     | Date          | When the item was added                          |
| Last Surfaced | Date        | Last date this was suggested in a daily plan     |

**Lifecycle**: Added conversationally ("add to my backlog: reorganize
tupperware") or during weekly meetings. One item is surfaced in each daily
plan based on priority and staleness (least recently surfaced first).
Reviewed at the weekly meeting — done items cleared, remaining items
reprioritized. Unlike action items, backlog items do NOT auto-rollover weekly
— they persist until explicitly completed or dropped.

**Key difference from Action Items**: Action items are weekly commitments
tracked with deadlines. Backlog items are a "someday" queue worked through
gradually at Erin's pace.

## Entity: Routine Template

Stored as structured content in the Family Profile page (not a separate database).

| Field            | Type    | Description                                      |
|-----------------|---------|--------------------------------------------------|
| Name            | Text    | Template name (e.g., "Weekday with Zoey")        |
| Day Pattern     | Text    | When this applies (e.g., "M-F when Zoey is home") |
| Time Blocks     | List    | Ordered list of activity blocks with times        |

**Example templates**:

```
Weekday — Zoey with Erin:
  7:00-7:30  Make Jason breakfast
  7:30-8:00  Get kids ready
  9:00-9:30  Drop off Vienna (Roy Gomm)
  9:30-11:00 Chore block (with Zoey)
  11:00-12:00 Out-of-house / errand time
  12:00-12:30 Lunch
  12:30-1:30  Zoey nap / Rest time
  1:30-2:30   Personal development
  2:30-3:00   Side work (dad's real estate)
  3:00-3:30   Pick up Vienna

Weekday — Zoey with Grandma:
  7:00-7:30  Make Jason breakfast
  7:30-8:00  Get kids ready
  9:00-9:30  Drop off Vienna (Roy Gomm)
  9:30-10:00 Drop off Zoey at Grandma's
  10:00-11:30 Exercise / Gym
  11:30-12:30 Personal development (knitting, projects)
  12:30-1:00  Lunch
  1:00-2:30   Side work / Backlog item
  2:30-3:00   Pick up Vienna
  3:00-3:30   Pick up Zoey
```

These templates are defined/refined during the weekly meeting. The assistant
uses them to generate daily calendar blocks, adapting based on that day's
context (grandma schedule, Jason's meetings, calendar events).

## Entity: Meal Plan

Stored in a Notion database named "Meal Plans".

| Property    | Type    | Description                            |
|------------|---------|----------------------------------------|
| Week Of    | Title   | Week start date (e.g., "Week of Feb 23") |
| Start Date | Date    | Monday of the week                     |
| Status     | Select  | Draft / Active / Archived              |

Each Meal Plan page contains block content:
- **Daily meals**: Toggle headings for each day (Monday-Sunday) with
  breakfast, lunch, dinner as bullet items
- **Grocery list**: Checklist block at the bottom, consolidated from all meals
- **Notes**: Any dietary notes or substitutions

## Entity: Meeting

Stored in a Notion database named "Meetings".

| Property | Type   | Description                              |
|----------|--------|------------------------------------------|
| Date     | Title  | Meeting date (e.g., "Feb 23, 2026")      |
| When     | Date   | Actual date for sorting/filtering        |
| Status   | Select | Planned / In Progress / Complete         |

Each Meeting page contains block content:
- **Agenda**: Generated checklist with sections (Calendar, Action Review,
  Chores, Meals, Finances, Goals, Custom Topics)
- **Notes**: Free-form notes captured during the meeting
- **Action Items**: Linked from the Action Items database via relation
- **Backlog Review**: Summary of backlog items discussed (done/carry over)

## Entity: Family Profile

Stored as a single Notion page named "Family Profile" (not a database).

Block content sections:
- **Members**: Jason (partner), Erin (partner), Vienna (age 5), Zoey (age 3)
- **Preferences**: Dietary constraints, meal preferences, Jason's breakfast
  (1 scrambled egg, 2 bacon, high fiber tortilla, sriracha ketchup + Crystal
  hot sauce, Coke Zero or Diet Dr Pepper)
- **Routine Templates**: Structured daily templates for different scenarios
  (see Routine Template entity above)
- **Childcare Schedule**: Default grandma days, Vienna school schedule
- **Recurring Agenda Topics**: Items that appear on every weekly agenda
- **Service Connections**: Notes on which APIs are connected
- **Meeting Schedule**: Day/time of weekly meeting (default: Sunday evening)

## Entity: Grocery History (reference data)

**Stored as a Notion database named "Grocery History"** — populated once from
a Whole Foods / Amazon order export, then updated occasionally.

| Property     | Type          | Description                                      |
|-------------|---------------|--------------------------------------------------|
| Item Name   | Title         | Product name as it appears on Whole Foods (e.g., "365 Organic Chicken Breast") |
| Category    | Select        | "Produce" / "Meat" / "Dairy" / "Pantry" / "Frozen" / "Bakery" / "Beverages" / "Other" |
| Frequency   | Number        | How many past orders included this item           |
| Last Ordered | Date         | Most recent order date containing this item       |
| Staple      | Checkbox      | True if ordered in 50%+ of orders (auto-calculated on import) |

**Purpose**: Gives Claude context for smarter meal planning and grocery lists:
- **Item name matching**: Use actual Whole Foods product names instead of
  generic terms so AnyList/Instacart matches correctly
- **Staple detection**: Items flagged as staples can be auto-suggested weekly
  ("You usually buy milk, eggs, and bread — add to list?")
- **Meal suggestions**: Knowing what the family actually buys helps Claude
  suggest meals they'll actually make

**Lifecycle**: One-time bulk import from Amazon/Whole Foods order history
(CSV or copy-paste from order pages). Jason exports, runs a script to parse
and populate the Notion database. Refreshed occasionally (quarterly or
when preferences change significantly).

**Import approach**: Jason exports order history from amazon.com/your-orders
(filter to Whole Foods), saves as CSV or text. A Python script parses item
names, deduplicates, counts frequency, and writes to Notion via API.

## Entity: Daily Plan (transient)

**Not stored in Notion** — generated on demand and delivered via WhatsApp +
Google Calendar events. No persistence needed because:
- The calendar events ARE the persistent record
- The WhatsApp message is the delivery
- Tomorrow's plan may be completely different

| Field            | Source                  | Description                        |
|-----------------|-------------------------|------------------------------------|
| Date            | System                  | The day being planned              |
| Childcare       | Family Profile / user input | Who has Zoey today             |
| Jason Meetings  | Outlook ICS + Google Cal | Jason's schedule for breakfast timing |
| Time Blocks     | Routine Template        | Adapted template for today's context |
| Backlog Suggestion | Backlog database     | One item to surface today          |
| Calendar Events | Google Calendar         | Any personal/family events today   |

## Relationships

```text
Meeting 1──→ many Action Items  (relation property on Action Item)
Meeting 1──→ 1 Meal Plan        (referenced by week date, not formal relation)
Family Profile ──→ read by assistant for context on every interaction
Family Profile ──→ contains Routine Templates (block content)
Backlog Item ──→ surfaced in Daily Plan (one per day)
Daily Plan ──→ written to Google Calendar (events are the output)
Meal Plan ──→ grocery list pushed to AnyList (via sidecar)
Grocery History ──→ read by Claude for item name matching + staple suggestions
```

## External Data (read-only from APIs, not stored in Notion)

| Source               | Data                                    | Access Pattern                |
|---------------------|-----------------------------------------|-------------------------------|
| Google Calendar (3x) | Events from Jason personal, Erin personal, shared family | Read on demand per agenda/daily plan |
| Outlook ICS          | Jason's work meetings                   | Polled on demand via HTTP GET  |
| YNAB                 | Budget categories, spending, goals       | Read on demand per request    |

## External Data (write via APIs)

| Target               | Data Written                            | Access Pattern                |
|---------------------|-----------------------------------------|-------------------------------|
| Google Calendar (Erin) | Daily time blocks from routine template | Batch write weekly + on-demand adjustments |
| AnyList              | Grocery list items from meal plan       | Push after meal plan creation  |
