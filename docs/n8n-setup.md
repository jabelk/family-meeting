# n8n Workflow Setup Guide

This guide walks through creating the 8 scheduled workflows in the dedicated Mom Bot n8n instance.

## Prerequisites

- n8n-mombot container running on port 5679 (part of docker-compose stack)
- FastAPI container running on port 8000
- `N8N_WEBHOOK_SECRET` set in `.env` (shared secret for endpoint auth)

## Access n8n UI

Open `http://<NUC-IP>:5679` in your browser (e.g., `http://192.168.4.152:5679`).

Login with credentials from `.env`:
- Username: `N8N_MOMBOT_USER`
- Password: `N8N_MOMBOT_PASSWORD`

## Workflow Creation Pattern

Every workflow follows the same pattern:

1. **Schedule Trigger** node (cron expression)
2. **HTTP Request** node (POST to FastAPI endpoint)

### HTTP Request Node Settings (Same for All)

| Setting | Value |
|---------|-------|
| Method | POST |
| URL | `http://fastapi:8000/api/v1/<endpoint>` |
| Authentication | None (we use a custom header) |
| Headers | `X-N8N-Auth`: value of `N8N_WEBHOOK_SECRET` from `.env` |
| Headers | `Content-Type`: `application/json` |
| Body Content Type | JSON |
| Timeout | 60000 (60 seconds — some endpoints call Claude which takes time) |
| Retry on Fail | Yes, 1 retry, 300000ms (5 min) wait |

**Important**: The URL uses `fastapi` (Docker service name), not `localhost` or the NUC IP. Both containers are on the same Docker network (`family-net`).

---

## WF-001: Daily Morning Briefing

Generates Erin's daily plan + calendar conflicts. Keeps WhatsApp 24h window open.

| Setting | Value |
|---------|-------|
| **Cron** | `0 7 * * 1-5` |
| **Schedule** | 7:00 AM Monday-Friday |
| **Endpoint** | `/api/v1/briefing/daily` |
| **Body** | `{}` |

---

## WF-002: Weekly Calendar Population

Populates Erin's Google Calendar with routine time blocks for the coming week.

| Setting | Value |
|---------|-------|
| **Cron** | `0 19 * * 0` |
| **Schedule** | 7:00 PM Sunday |
| **Endpoint** | `/api/v1/calendar/populate-week` |
| **Body** | `{}` |

---

## WF-003: Grandma Schedule Prompt

Asks Erin to confirm Sandy's schedule for the week.

| Setting | Value |
|---------|-------|
| **Cron** | `0 9 * * 1` |
| **Schedule** | 9:00 AM Monday |
| **Endpoint** | `/api/v1/prompt/grandma-schedule` |
| **Body** | `{}` |

---

## WF-004: Saturday Meal Plan + Grocery

Combined: 6-night dinner plan + merged grocery list (meal ingredients + reorder staples). Falls back to WhatsApp template message if outside 24h window.

| Setting | Value |
|---------|-------|
| **Cron** | `0 9 * * 6` |
| **Schedule** | 9:00 AM Saturday |
| **Endpoint** | `/api/v1/meals/plan-week` |
| **Body** | `{}` |

---

## WF-005: Weekly Budget Summary

YNAB spending summary before the weekly family meeting.

| Setting | Value |
|---------|-------|
| **Cron** | `0 17 * * 0` |
| **Schedule** | 5:00 PM Sunday |
| **Endpoint** | `/api/v1/budget/weekly-summary` |
| **Body** | `{}` |

---

## WF-006: Mid-Week Action Item Check-In

Progress report on "This Week" action items. No message sent if all complete.

| Setting | Value |
|---------|-------|
| **Cron** | `0 12 * * 3` |
| **Schedule** | 12:00 PM Wednesday |
| **Endpoint** | `/api/v1/reminders/action-items` |
| **Body** | `{}` |

---

## WF-007: Weekly Calendar Conflict Scan

Full week conflict scan across all 4 calendars. Daily conflicts are handled within WF-001.

| Setting | Value |
|---------|-------|
| **Cron** | `30 19 * * 0` |
| **Schedule** | 7:30 PM Sunday |
| **Endpoint** | `/api/v1/calendar/conflict-check` |
| **Body** | `{"days_ahead": 7}` |

---

## WF-008: Grocery Order Confirmation Check

Sends reminder if AnyList was pushed 2+ days ago with no order confirmation. No action if nothing pending.

| Setting | Value |
|---------|-------|
| **Cron** | `0 10 * * *` |
| **Schedule** | 10:00 AM Daily |
| **Endpoint** | `/api/v1/reminders/grocery-confirmation` |
| **Body** | `{}` |

---

## Step-by-Step: Creating a Workflow

1. Click **"Add workflow"** in the n8n UI
2. Name it (e.g., "WF-001 Daily Morning Briefing")
3. Click the **"+"** button → search for **"Schedule Trigger"** → add it
4. Configure the Schedule Trigger:
   - Mode: **Cron**
   - Cron Expression: paste from table above
   - Timezone should already be `America/Los_Angeles` (set via Docker env)
5. Click **"+"** after the Schedule Trigger → search for **"HTTP Request"** → add it
6. Configure the HTTP Request:
   - Method: **POST**
   - URL: `http://fastapi:8000/api/v1/<endpoint>` (from table above)
   - Under **Options** → **Headers**: Add `X-N8N-Auth` with the secret value
   - Under **Options** → **Headers**: Add `Content-Type` with `application/json`
   - Body Content Type: **JSON**
   - Body: paste from table above (usually `{}`)
   - Under **Settings** → **Retry On Fail**: Yes, Max Tries: 2, Wait Between: 300000
   - Under **Settings** → **Timeout**: 60000
7. Click **"Save"**
8. Toggle the workflow **Active** (top-right switch)
9. Repeat for all 8 workflows

## Weekly Schedule Overview

```
Monday
  07:00  WF-001  Daily Briefing
  09:00  WF-003  Grandma Schedule Prompt
  10:00  WF-008  Grocery Confirmation Check

Tuesday
  07:00  WF-001  Daily Briefing
  10:00  WF-008  Grocery Confirmation Check

Wednesday
  07:00  WF-001  Daily Briefing
  10:00  WF-008  Grocery Confirmation Check
  12:00  WF-006  Mid-Week Check-In

Thursday
  07:00  WF-001  Daily Briefing
  10:00  WF-008  Grocery Confirmation Check

Friday
  07:00  WF-001  Daily Briefing
  10:00  WF-008  Grocery Confirmation Check

Saturday
  09:00  WF-004  Meal Plan + Grocery
  10:00  WF-008  Grocery Confirmation Check

Sunday
  10:00  WF-008  Grocery Confirmation Check
  17:00  WF-005  Budget Summary
  19:00  WF-002  Calendar Population
  19:30  WF-007  Conflict Scan
```

## Troubleshooting

**Workflow fires but no WhatsApp message arrives**:
- Check FastAPI logs: `./scripts/nuc.sh logs fastapi 50`
- Common cause: WhatsApp 24-hour window expired. The endpoint should fall back to template messages, but templates need Meta approval first.

**HTTP Request fails with 401**:
- Verify `X-N8N-Auth` header value matches `N8N_WEBHOOK_SECRET` in `.env`
- The header is case-sensitive

**HTTP Request fails with connection refused**:
- Both containers must be on the `family-net` Docker network
- Check: `docker network inspect family-meeting_family-net`

**Workflow shows "Error" in execution history**:
- Click the failed execution to see the error details
- The retry should fire automatically after 5 minutes
- If the retry also fails, the error is logged but no notification is sent to WhatsApp

**Testing a workflow manually**:
- Open the workflow in the editor
- Click **"Test workflow"** (or "Execute workflow") at the top
- This runs it immediately regardless of the cron schedule
