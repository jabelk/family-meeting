# Contract: n8n Scheduled Workflows

**Feature**: 002-proactive-recipes-automation | **Date**: 2026-02-22

## Overview

7 scheduled workflows in the dedicated `n8n-mombot` container (port 5679). Each workflow is a simple cron trigger → HTTP request to the FastAPI service at `http://fastapi:8000` (Docker internal network).

## Workflow Definitions

### WF-001: Daily Morning Briefing

| Field | Value |
|-------|-------|
| **Name** | Daily Morning Briefing |
| **Cron** | `0 7 * * 1-5` (7:00 AM Mon-Fri, America/Los_Angeles) |
| **Endpoint** | `POST http://fastapi:8000/api/v1/briefing/daily` |
| **Headers** | `X-N8N-Auth: {secret}`, `Content-Type: application/json` |
| **Body** | `{}` |
| **Retry** | 1 retry after 5 minutes on failure |
| **Notes** | Generates Erin's daily plan + calendar conflicts. Keeps WhatsApp 24h window open. |

### WF-002: Weekly Calendar Population

| Field | Value |
|-------|-------|
| **Name** | Weekly Calendar Population |
| **Cron** | `0 19 * * 0` (7:00 PM Sunday, America/Los_Angeles) |
| **Endpoint** | `POST http://fastapi:8000/api/v1/calendar/populate-week` |
| **Headers** | `X-N8N-Auth: {secret}`, `Content-Type: application/json` |
| **Body** | `{}` |
| **Retry** | 1 retry after 5 minutes on failure |
| **Notes** | Populates Erin's Google Calendar with routine time blocks for the coming week. |

### WF-003: Grandma Schedule Prompt

| Field | Value |
|-------|-------|
| **Name** | Grandma Schedule Prompt |
| **Cron** | `0 9 * * 1` (9:00 AM Monday, America/Los_Angeles) |
| **Endpoint** | `POST http://fastapi:8000/api/v1/prompt/grandma-schedule` |
| **Headers** | `X-N8N-Auth: {secret}`, `Content-Type: application/json` |
| **Body** | `{}` |
| **Retry** | 1 retry after 5 minutes on failure |
| **Notes** | Asks Erin to confirm Sandy's schedule for the week. |

### WF-004: Saturday Meal Plan + Grocery

| Field | Value |
|-------|-------|
| **Name** | Saturday Meal & Grocery Planner |
| **Cron** | `0 9 * * 6` (9:00 AM Saturday, America/Los_Angeles) |
| **Endpoint** | `POST http://fastapi:8000/api/v1/meals/plan-week` |
| **Headers** | `X-N8N-Auth: {secret}`, `Content-Type: application/json` |
| **Body** | `{}` |
| **Retry** | 1 retry after 5 minutes on failure |
| **Notes** | Combined: generates dinner plan (6 nights) + merged grocery list (meal ingredients + reorder staples). Falls back to WhatsApp template message if outside 24h window. |

### WF-005: Weekly Budget Summary

| Field | Value |
|-------|-------|
| **Name** | Weekly Budget Summary |
| **Cron** | `0 17 * * 0` (5:00 PM Sunday, America/Los_Angeles) |
| **Endpoint** | `POST http://fastapi:8000/api/v1/budget/weekly-summary` |
| **Headers** | `X-N8N-Auth: {secret}`, `Content-Type: application/json` |
| **Body** | `{}` |
| **Retry** | 1 retry after 5 minutes on failure |
| **Notes** | YNAB spending summary before the weekly family meeting. Falls back to template if outside 24h window. |

### WF-006: Mid-Week Action Item Check-In

| Field | Value |
|-------|-------|
| **Name** | Mid-Week Check-In |
| **Cron** | `0 12 * * 3` (12:00 PM Wednesday, America/Los_Angeles) |
| **Endpoint** | `POST http://fastapi:8000/api/v1/reminders/action-items` |
| **Headers** | `X-N8N-Auth: {secret}`, `Content-Type: application/json` |
| **Body** | `{}` |
| **Retry** | 1 retry after 5 minutes on failure |
| **Notes** | Progress report on "This Week" action items. No message if all complete. |

### WF-007: Weekly Conflict Scan

| Field | Value |
|-------|-------|
| **Name** | Weekly Calendar Conflict Scan |
| **Cron** | `30 19 * * 0` (7:30 PM Sunday, America/Los_Angeles) |
| **Endpoint** | `POST http://fastapi:8000/api/v1/calendar/conflict-check` |
| **Headers** | `X-N8N-Auth: {secret}`, `Content-Type: application/json` |
| **Body** | `{"days_ahead": 7}` |
| **Retry** | 1 retry after 5 minutes on failure |
| **Notes** | Full week conflict scan. Daily conflicts are handled within WF-001 (daily briefing). |

### WF-008: Grocery Order Confirmation Check

| Field | Value |
|-------|-------|
| **Name** | Grocery Order Confirmation |
| **Cron** | `0 10 * * *` (10:00 AM daily, America/Los_Angeles) |
| **Endpoint** | `POST http://fastapi:8000/api/v1/reminders/grocery-confirmation` |
| **Headers** | `X-N8N-Auth: {secret}`, `Content-Type: application/json` |
| **Body** | `{}` |
| **Retry** | 1 retry after 5 minutes on failure |
| **Notes** | Sends reminder if AnyList was pushed 2+ days ago with no order confirmation. No action if nothing pending. |

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

## Docker Compose Addition

```yaml
n8n-mombot:
  image: n8nio/n8n:latest
  container_name: n8n-mombot
  ports:
    - "5679:5678"
  environment:
    - N8N_BASIC_AUTH_ACTIVE=true
    - N8N_BASIC_AUTH_USER=${N8N_MOMBOT_USER}
    - N8N_BASIC_AUTH_PASSWORD=${N8N_MOMBOT_PASSWORD}
    - GENERIC_TIMEZONE=America/Los_Angeles
    - TZ=America/Los_Angeles
    - N8N_ENCRYPTION_KEY=${N8N_MOMBOT_ENCRYPTION_KEY}
  volumes:
    - n8n_mombot_data:/home/node/.n8n
  networks:
    - family-net
  restart: unless-stopped
```

## Error Handling

All workflows use the same error handling pattern:

1. **Retry**: On HTTP error (non-2xx) or timeout (30s), wait 5 minutes and retry once
2. **Log**: If retry also fails, n8n logs the error in execution history (visible in n8n UI at port 5679)
3. **No spam**: Failed workflows do NOT send error messages to the family WhatsApp chat
4. **Monitoring**: Jason checks n8n UI periodically for failed executions (no automated alerting for v1)

## Template Message Fallback

For workflows that fire outside the WhatsApp 24-hour window (likely: Saturday WF-004, Sunday WF-005/WF-007):

1. Endpoint attempts to send free-form WhatsApp message
2. If Meta returns error 131026 ("outside service window"), endpoint sends pre-approved template message instead
3. Template includes brief summary + "Reply to see full details"
4. When Erin replies (opening the window), endpoint sends the full content as a follow-up
