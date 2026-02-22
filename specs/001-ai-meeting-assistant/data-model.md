# Data Model: AI-Powered Weekly Family Meeting Assistant

**Branch**: `001-ai-meeting-assistant` | **Date**: 2026-02-21

All data is stored in Notion databases. Entities map to Notion database
properties. Family members can view and edit all data directly in Notion.

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

## Entity: Meal Plan

Stored in a Notion database named "Meal Plans".

| Property    | Type    | Description                            |
|------------|---------|----------------------------------------|
| Week Of    | Title   | Week start date (e.g., "Week of Feb 23") |
| Start Date | Date    | Monday of the week                     |
| Status     | Select  | Draft / Active / Archived              |

Each Meal Plan page contains block content:
- **Daily meals**: Toggle headings for each day (Monday–Sunday) with
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

## Entity: Family Profile

Stored as a single Notion page named "Family Profile" (not a database).

Block content sections:
- **Members**: Jason (partner), Erin (partner), Vienna (age 5), Zoey (age 3)
- **Preferences**: Dietary constraints, meal preferences, recurring chore
  assignments
- **Recurring Topics**: Items that appear on every agenda (e.g., weekly
  calendar review, budget check-in)
- **Service Connections**: Notes on which APIs are connected and any
  configuration (calendar ID, YNAB budget ID)
- **Meeting Schedule**: Day/time of weekly meeting (default: Sunday evening)

## Relationships

```text
Meeting 1──→ many Action Items  (relation property on Action Item)
Meeting 1──→ 1 Meal Plan        (referenced by week date, not formal relation)
Family Profile ──→ read by assistant for context on every interaction
```

## External Data (read-only, not stored in Notion)

| Source          | Data                                    | Access Pattern              |
|----------------|-----------------------------------------|-----------------------------|
| Google Calendar | Upcoming events for next 7 days         | Read on demand per agenda   |
| YNAB           | Budget categories, spending, goals       | Read on demand per request  |

These are fetched live via API — not cached in Notion — so the assistant
always shows current data.
