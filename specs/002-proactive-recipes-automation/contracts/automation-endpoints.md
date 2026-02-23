# Contract: Automation Endpoints

**Feature**: 002-proactive-recipes-automation | **Date**: 2026-02-22

## Overview

FastAPI endpoints triggered by n8n scheduled workflows. These extend the existing 3 stubs (`/api/v1/briefing/daily`, `/api/v1/calendar/populate-week`, `/api/v1/prompt/grandma-schedule`) with new proactive automation endpoints.

## Existing Endpoints (enhanced)

### POST /api/v1/briefing/daily

**Enhancement**: Add calendar conflict detection to the daily briefing output.

**Current behavior**: Generates daily plan for Erin (routine blocks, calendar events, backlog suggestion).

**New behavior**: Same as above + scan all 4 calendars for conflicts with family routines. Include conflict alerts at the top of the briefing if any found.

**Request**: `{}` (no body — triggered by n8n cron)

**Response**:
```json
{
  "status": "sent",
  "conflicts": [
    {
      "type": "soft",
      "description": "Jason's 2:30-3:30 meeting conflicts with Vienna's 3:15 pickup",
      "suggestion": "Erin, can you cover pickup?"
    }
  ],
  "briefing_length": 450
}
```

## New Endpoints

### POST /api/v1/grocery/reorder-check

**Purpose**: Check grocery history for items due for reorder and generate suggestions grouped by store.

**Triggered by**: n8n cron (Saturday 9:00 AM) — but only as part of the combined meal+grocery flow. Can also be called independently for testing.

**Request**: `{}` (no body)

**Logic**:
1. Query Grocery History for Staple and Regular items
2. For each: calculate `days_since_last_ordered = today - last_ordered`
3. Filter: `days_since_last_ordered >= avg_reorder_days`
4. Group by Store (Whole Foods, Costco, Raley's)
5. Sort within each group by how overdue (most overdue first)

**Response**:
```json
{
  "status": "suggestions_ready",
  "stores": {
    "Whole Foods": [
      {"name": "Organic Spinach", "days_overdue": 5, "avg_interval": 30, "last_ordered": "2026-02-17"},
      {"name": "Almond Milk", "days_overdue": 2, "avg_interval": 14, "last_ordered": "2026-02-06"}
    ],
    "Costco": [
      {"name": "Organic Eggs (24pk)", "days_overdue": 8, "avg_interval": 21, "last_ordered": "2026-01-24"}
    ]
  },
  "total_items": 3
}
```

### POST /api/v1/meals/plan-week

**Purpose**: Generate a weekly dinner plan (6 nights) with merged grocery list.

**Triggered by**: n8n cron (Saturday 9:00 AM) — combined with reorder check.

**Request**: `{}` (no body)

**Logic**:
1. Fetch: saved recipes, last 2 meal plans, weekly schedule, family profile
2. Call Claude with context to generate 6-night dinner plan
3. For each meal: extract ingredients (from saved recipe or Claude-generated)
4. Merge meal ingredients + reorder-due staples
5. Deduct recently ordered items
6. Group final list by store
7. Format and send via WhatsApp (single combined message)

**Response**:
```json
{
  "status": "sent",
  "plan": {
    "meals": [
      {"day": "Monday", "name": "Chicken Parmesan", "source": "recipe:abc123", "complexity": "medium"},
      {"day": "Tuesday", "name": "Simple Tacos", "source": "general", "complexity": "easy"}
    ],
    "grocery_items": 18,
    "stores": ["Whole Foods", "Costco"]
  }
}
```

### POST /api/v1/reminders/action-items

**Purpose**: Mid-week check-in on action item progress.

**Triggered by**: n8n cron (Wednesday 12:00 PM)

**Request**: `{}` (no body)

**Logic**:
1. Query Action Items where Due Context = "This Week"
2. Count: total, done, in_progress, not_started
3. Identify rolled-over items (Rolled Over = true)
4. If all done: either skip message or send brief "all caught up!"
5. If incomplete items exist: format progress report + flagged items

**Response**:
```json
{
  "status": "sent",
  "summary": {
    "total": 6,
    "done": 3,
    "in_progress": 1,
    "not_started": 2,
    "rolled_over_count": 1
  }
}
```

### POST /api/v1/budget/weekly-summary

**Purpose**: Weekly budget summary for the family meeting.

**Triggered by**: n8n cron (Sunday 5:00 PM)

**Request**: `{}` (no body)

**Logic**:
1. Call existing `get_budget_summary()` from YNAB tools
2. Format as structured WhatsApp message: over-budget categories, on-track summary, total spent vs budget
3. Send via WhatsApp

**Response**:
```json
{
  "status": "sent",
  "over_budget_categories": 2,
  "total_spent": 3450.00,
  "total_budget": 4000.00
}
```

### POST /api/v1/calendar/conflict-check

**Purpose**: Scan upcoming week for calendar conflicts. Used by both daily briefing (today only) and weekly scan (full week).

**Triggered by**: n8n cron (Sunday 7:30 PM) for weekly scan. Also called internally by daily briefing.

**Request**:
```json
{
  "days_ahead": 7  // optional, default 1 for daily, 7 for weekly
}
```

**Logic**:
1. Fetch events from all 4 calendars for the time range
2. Parse family routine templates for each day
3. Detect hard conflicts (overlapping events)
4. Detect soft conflicts (event overlaps routine — pickup times, dropoffs, etc.)
5. Generate resolution suggestions using Claude
6. If weekly scan: send full conflict report via WhatsApp
7. If daily: return conflicts for embedding in briefing

**Response**:
```json
{
  "status": "sent",
  "conflicts": [
    {
      "day": "Tuesday",
      "type": "soft",
      "event": "Jason: Sprint Planning (2:00-3:30)",
      "routine": "Vienna pickup (3:15)",
      "suggestion": "Erin covers Tuesday pickup"
    }
  ],
  "total_conflicts": 1
}
```

### POST /api/v1/reminders/grocery-confirmation

**Purpose**: Check if Erin confirmed a grocery order after AnyList push. Send reminder if 2+ days with no confirmation.

**Triggered by**: n8n cron (daily 10:00 AM)

**Request**: `{}` (no body)

**Logic**:
1. Check Grocery History for items with `Pending Order = true`
2. If `Last Push Date` was 2+ days ago: send reminder
3. If no pending items: no action

**Response**:
```json
{
  "status": "reminder_sent",  // or "no_pending"
  "pending_since": "2026-02-20",
  "item_count": 12
}
```

## Authentication

All `/api/v1/*` endpoints are protected by a shared secret header:

```
X-N8N-Auth: {N8N_WEBHOOK_SECRET}
```

This prevents unauthorized triggers. The n8n workflows include this header in their HTTP request nodes.
