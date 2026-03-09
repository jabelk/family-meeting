# Data Model: Railway Cloud Deployment

**Feature**: 020-railway-cloud-deploy
**Date**: 2026-03-08

## Overview

This feature does not introduce new domain entities. Instead, it adapts the existing data storage and credential management patterns for cloud deployment. The primary changes are:

1. **Storage location**: Local filesystem → Railway Volume (same path, same files)
2. **Credential storage**: `.env` file + filesystem tokens → Railway env vars
3. **Scheduling config**: n8n workflows → in-app scheduler with JSON config
4. **Repo structure**: Single repo → template repo with per-instance customization

---

## Existing Data Files (Unchanged)

These files persist on the Railway Volume at `/app/data/`. No schema changes.

| File | Purpose | Size | Write Frequency |
|------|---------|------|-----------------|
| `conversations.json` | Active conversation context | ~2KB | Every message |
| `conversation_archives/` | Daily conversation backups | ~5KB/day | Daily |
| `user_preferences.json` | User settings | <1KB | Rare |
| `work_calendar.json` | Jason's work meetings | ~1KB | Daily |
| `usage_counters.json` | Feature discovery tracking | <1KB | Per feature use |
| `budget_pending_suggestions.json` | YNAB nudge queue | <1KB | Daily |
| `budget_pending_allocation.json` | Budget allocation state | <1KB | Monthly |
| `amazon_sync_records.json` | Amazon order tracking | ~5KB | Daily |
| `amazon_sync_config.json` | Amazon sync config | <1KB | Rare |
| `category_mappings.json` | YNAB category mappings | ~2KB | On new category |
| `email_pending_suggestions.json` | Email sync tracking | <1KB | Daily |

---

## New Data: Schedule Configuration

**File**: `data/schedules.json`
**Purpose**: Configurable schedule for all automated jobs (replaces n8n workflow definitions)

```json
{
  "timezone": "America/Los_Angeles",
  "jobs": [
    {
      "id": "daily_briefing",
      "endpoint": "briefing/daily",
      "schedule": {"hour": 7, "minute": 0, "day_of_week": "mon-fri"},
      "enabled": true
    },
    {
      "id": "nudge_scan",
      "endpoint": "nudges/scan",
      "schedule": {"minute": "*/15", "hour": "7-20"},
      "enabled": true
    },
    {
      "id": "budget_scan",
      "endpoint": "budget/scan",
      "schedule": {"hour": 9, "minute": 0},
      "enabled": true
    },
    {
      "id": "populate_week",
      "endpoint": "calendar/populate-week",
      "schedule": {"hour": 19, "minute": 0, "day_of_week": "sun"},
      "enabled": true
    },
    {
      "id": "meal_plan",
      "endpoint": "meals/plan-week",
      "schedule": {"hour": 9, "minute": 0, "day_of_week": "sat"},
      "enabled": true
    },
    {
      "id": "amazon_sync",
      "endpoint": "amazon/sync",
      "schedule": {"hour": 22, "minute": 0},
      "enabled": true
    },
    {
      "id": "email_sync",
      "endpoint": "email/sync",
      "schedule": {"hour": 22, "minute": 5},
      "enabled": true
    },
    {
      "id": "budget_health",
      "endpoint": "budget/health-check",
      "schedule": {"hour": 9, "minute": 0, "day": 1},
      "enabled": true
    },
    {
      "id": "grandma_prompt",
      "endpoint": "prompt/grandma-schedule",
      "schedule": {"hour": 9, "minute": 0, "day_of_week": "mon"},
      "enabled": true
    },
    {
      "id": "conflict_check",
      "endpoint": "calendar/conflict-check",
      "schedule": {"hour": 19, "minute": 30, "day_of_week": "sun"},
      "enabled": true
    },
    {
      "id": "action_item_reminder",
      "endpoint": "reminders/action-items",
      "schedule": {"hour": 12, "minute": 0, "day_of_week": "wed"},
      "enabled": true
    },
    {
      "id": "grocery_reorder",
      "endpoint": "grocery/reorder-check",
      "schedule": {"hour": 10, "minute": 0, "day_of_week": "sat"},
      "enabled": true
    },
    {
      "id": "grocery_confirmation",
      "endpoint": "reminders/grocery-confirmation",
      "schedule": {"hour": 10, "minute": 0},
      "enabled": true
    },
    {
      "id": "budget_summary",
      "endpoint": "budget/weekly-summary",
      "schedule": {"hour": 17, "minute": 0, "day_of_week": "sun"},
      "enabled": true
    }
  ]
}
```

**Key design decisions**:
- `enabled` flag lets families disable jobs they don't use (e.g., no YNAB = disable budget jobs)
- `timezone` is instance-level (all jobs share it)
- Schedule format matches APScheduler's `CronTrigger` kwargs for direct passthrough
- File lives on the volume so it survives redeploys and can be customized per instance
- Ships with sensible defaults in the template repo

---

## New Data: Credential Environment Variables

These are additions to `.env.example` for Railway deployment:

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOOGLE_TOKEN_JSON` | If using Calendar | Serialized `token.json` content (from `setup_calendar.py`) |
| `GOOGLE_CREDENTIALS_JSON` | If using Calendar | Serialized `credentials.json` content (OAuth client secret) |
| `ANYLIST_SIDECAR_URL` | If using AnyList | Internal Railway URL (e.g., `http://anylist-sidecar.railway.internal:3000`) |
| `RAILWAY_RUN_UID` | Maybe | Set to `0` if volume permissions fail |
| `SCHEDULER_ENABLED` | No (default: true) | Set to `false` to disable in-app scheduler (e.g., if using external cron) |

---

## Entity Relationships (Unchanged)

No new domain entities are introduced. The existing entity relationships (Conversations, Preferences, Calendar Events, Notion databases, YNAB budgets) remain the same. This feature only changes where and how data is stored and accessed, not what data exists.
