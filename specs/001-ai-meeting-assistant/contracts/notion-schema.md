# Contract: Notion Database Schema

**Type**: REST API (our server → Notion API v1)

**Base URL**: `https://api.notion.com/v1`
**Auth**: `Authorization: Bearer {NOTION_INTEGRATION_TOKEN}`
**Version Header**: `Notion-Version: 2022-06-28`

## Database: Action Items

**Purpose**: Track all family action items/tasks from meetings

| Property    | Notion Type | Values / Format                     |
|------------|-------------|-------------------------------------|
| Description | title       | Free text                           |
| Assignee   | select      | "Jason", "Erin"                    |
| Status     | status      | Not Started / In Progress / Done    |
| Due Context | select     | "This Week", "Ongoing", "Someday"   |
| Created    | date        | ISO 8601 date                       |
| Meeting    | relation    | → Meetings database                 |
| Rolled Over | checkbox   | true/false                          |

**Common queries**:
- Open items for a person: filter `Assignee = X AND Status != Done`
- Items to roll over: filter `Status != Done AND Due Context = This Week`

## Database: Meal Plans

**Purpose**: Store weekly meal plans with grocery lists

| Property   | Notion Type | Values / Format               |
|-----------|-------------|-------------------------------|
| Week Of   | title       | "Week of Feb 23"             |
| Start Date | date       | Monday of the week            |
| Status    | select      | "Draft", "Active", "Archived" |

**Page content** (blocks inside each page):
- Toggle headings per day (Monday–Sunday)
- Bullet items per meal under each day
- Divider
- "Grocery List" heading with to-do blocks (checkable)

## Database: Meetings

**Purpose**: Archive meeting agendas and notes

| Property | Notion Type | Values / Format                    |
|----------|-------------|------------------------------------|
| Date     | title       | "Feb 23, 2026"                    |
| When     | date        | Actual date for sorting            |
| Status   | select      | "Planned", "In Progress", "Complete" |

**Page content** (blocks inside each page):
- Heading: "Agenda"
- Categorized checklist sections (Calendar, Action Review, Chores, etc.)
- Heading: "Notes"
- Free-form paragraph blocks
- Heading: "Decisions"
- Bullet list of key decisions made

## Page: Family Profile

**Purpose**: Persistent family context read by the assistant

**Not a database** — a single page with structured block content:

```
# Family Profile

## Members
- Jason (partner) — phone: +1XXXXXXXXXX
- Erin (partner) — phone: +1XXXXXXXXXX
- Vienna (daughter, age 5) — kindergarten at Roy Gomm
- Zoey (daughter, age 3)

## Preferences
- Kid-friendly meals preferred
- [dietary constraints added here over time]

## Recurring Agenda Topics
- Calendar review (upcoming week)
- Action item review (from last week)
- Chore assignments
- Meal planning
- Budget check-in
- Goals and long-term items

## Configuration
- Meeting day: Sunday
- Google Calendar ID: [calendar-id]
- YNAB Budget ID: last-used
```

## API Operations Used

| Operation             | Notion API Endpoint                                  |
|----------------------|------------------------------------------------------|
| Query database       | `POST /databases/{id}/query` with filter/sort        |
| Create page (record) | `POST /pages` with parent database + properties      |
| Update page          | `PATCH /pages/{id}` with changed properties          |
| Append blocks        | `PATCH /blocks/{id}/children` with block content     |
| Read page content    | `GET /blocks/{id}/children`                          |
| Read page            | `GET /pages/{id}`                                    |

**Rate limit**: 3 requests/second average (sufficient for all operations)
