# Contract: n8n Scheduled Automations

**Type**: HTTP Request workflows (n8n on NUC → FastAPI endpoints)

**n8n Base URL**: `http://localhost:5678` (NUC, Docker network)
**FastAPI Base URL**: `http://fastapi:8000` (Docker network) or `http://localhost:8000`

## Overview

n8n handles scheduled (cron) automations that trigger FastAPI endpoints.
All intelligence lives in FastAPI/Claude — n8n is just the scheduler.

## Workflow 1: Daily Morning Briefing

**Schedule**: 7:00 AM Pacific, Monday–Friday
**n8n Trigger**: Cron node with `GENERIC_TIMEZONE=America/Los_Angeles`

```
POST http://fastapi:8000/api/v1/briefing/daily
Content-Type: application/json

{
  "target": "erin"
}
```

**What FastAPI does**:
1. Read Erin's routine template from Family Profile
2. Check grandma schedule (from stored context or last known)
3. Fetch Jason's Outlook calendar (ICS) for meeting windows
4. Fetch today's Google Calendar events (all 3 calendars)
5. Pick one backlog item to surface
6. Generate daily plan via Claude
7. Write time blocks to Erin's Google Calendar
8. Send daily plan to WhatsApp group

**Expected response**: `200 OK` with `{"status": "sent", "blocks_created": 8}`

**Error**: `500` with `{"error": "description"}` — n8n logs the error, no retry

## Workflow 2: Weekly Calendar Population

**Schedule**: Sunday 7:00 PM Pacific
**n8n Trigger**: Cron node

```
POST http://fastapi:8000/api/v1/calendar/populate-week
Content-Type: application/json

{
  "week_start": "2026-02-23"
}
```

**What FastAPI does**:
1. Read routine templates from Family Profile
2. For each day Mon-Fri:
   - Check grandma schedule (default or last communicated)
   - Select appropriate template
   - Adapt time blocks based on context
3. Delete all assistant-created events for the week (extendedProperties filter)
4. Batch-create new events via Google Calendar Batch API
5. Send summary to WhatsApp: "Your calendar for the week is set up!"

**Expected response**: `200 OK` with `{"status": "populated", "events_created": 35}`

## Workflow 3: Grandma Schedule Prompt

**Schedule**: Monday 9:00 AM Pacific
**n8n Trigger**: Cron node

```
POST http://fastapi:8000/api/v1/prompt/grandma-schedule
Content-Type: application/json
```

**What FastAPI does**:
1. Send WhatsApp message to group: "What days is grandma taking Zoey this week?"
2. When a reply comes in through the regular webhook, Claude parses the response and updates the stored schedule
3. Daily briefings for the rest of the week use the updated schedule

**Expected response**: `200 OK` with `{"status": "prompted"}`

## n8n Docker Configuration

```yaml
n8n:
  image: n8nio/n8n:latest
  ports:
    - "5678:5678"
  environment:
    - GENERIC_TIMEZONE=America/Los_Angeles
    - N8N_BASIC_AUTH_ACTIVE=true
    - N8N_BASIC_AUTH_USER=${N8N_USER}
    - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
  volumes:
    - n8n_data:/home/node/.n8n
```

## n8n Workflow Setup (manual)

Each workflow is created in the n8n UI:

1. **Daily Briefing**: Cron (7am M-F) → HTTP Request (POST /api/v1/briefing/daily)
2. **Weekly Calendar**: Cron (Sun 7pm) → HTTP Request (POST /api/v1/calendar/populate-week)
3. **Grandma Prompt**: Cron (Mon 9am) → HTTP Request (POST /api/v1/prompt/grandma-schedule)

All use "HTTP Request" node with:
- Method: POST
- URL: `http://fastapi:8000/api/v1/...`
- Body Content Type: JSON
- Authentication: None (internal Docker network)

## Error Handling

- If FastAPI is down, n8n logs the error. No automatic retry (next scheduled run will work).
- n8n has built-in error workflows — can send a notification if a workflow fails.
- All endpoints are idempotent — safe to trigger manually from n8n UI for testing.
