# Implementation Plan: AI-Powered Weekly Family Meeting Assistant

**Branch**: `001-ai-meeting-assistant` | **Date**: 2026-02-22 | **Spec**: `specs/001-ai-meeting-assistant/spec.md`
**Input**: Feature specification from `/specs/001-ai-meeting-assistant/spec.md`

## Summary

Build an AI-powered family assistant that lives in a WhatsApp group chat for Jason and Erin. The assistant uses Claude Haiku 4.5 as its brain (agentic tool-use loop), connects to Google Calendar (read + write), Outlook (read via ICS), Notion (data persistence), YNAB (budget read), and AnyList (grocery push). It generates weekly meeting agendas, daily plans for Erin, captures action items, plans meals, checks budget, and bridges grocery lists to delivery. All services run on a NUC at home via Docker Compose + Cloudflare Tunnel, with n8n handling scheduled automations.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, anthropic SDK, notion-client, google-api-python-client, google-auth-oauthlib, icalendar, recurring-ical-events, ynab, uvicorn, httpx
**Storage**: Notion API (free plan) — 5 databases (Action Items, Meal Plans, Meetings, Backlog, Grocery History) + Family Profile page
**Testing**: pytest + httpx (async test client for FastAPI)
**Target Platform**: Linux (NUC, Docker), webhook service exposed via Cloudflare Tunnel
**Project Type**: Web service (webhook-based WhatsApp bot)
**Performance Goals**: <30s response for standard requests, <60s for meal plan generation
**Constraints**: WhatsApp 1600-char message limit (split at section breaks), free-tier Notion (unlimited blocks with 1 member + guests), ~$2/month total operating cost
**Scale/Scope**: 2 users (Jason + Erin), ~20-50 messages/week, 4-6 API integrations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Integration Over Building | PASS | Uses existing services (Google Calendar, YNAB, Notion, AnyList, Outlook) via APIs. Claude AI handles all intelligence. Custom code is orchestration only. |
| II. Mobile-First Access | PASS | WhatsApp is the sole interface for Erin. Calendar blocks appear in Apple Calendar with push notifications. Jason can also use WhatsApp or browse Notion. |
| III. Simplicity & Low Friction | PASS | Erin texts WhatsApp — that's it. No logins, no apps, no config. Daily briefing is automatic (n8n cron). Calendar blocks just appear. |
| IV. Structured Output | PASS | All output is formatted checklists/lists with WhatsApp bold headers, bullet points, and emoji indicators. 1600-char limit enforces conciseness. |
| V. Incremental Value | PASS | 6 user stories prioritized P1-P6, each independently testable. Agenda (P1) works alone. Daily Planner (P2) works alone. No feature requires another. |

**Post-Phase-1 re-check**: All principles still satisfied. The addition of Google Calendar write access, Outlook ICS polling, AnyList sidecar, and n8n automations all serve existing services (Principle I) and keep Erin on WhatsApp/Apple Calendar only (Principles II, III).

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-meeting-assistant/
├── plan.md              # This file
├── research.md          # Phase 0 output (9 decisions, v2)
├── data-model.md        # Phase 1 output (7 entities)
├── quickstart.md        # Phase 1 output (6 scenarios)
├── contracts/           # Phase 1 output (6 contracts)
│   ├── whatsapp-webhook.md
│   ├── notion-schema.md
│   ├── google-calendar-api.md
│   ├── outlook-ics-feed.md
│   ├── anylist-sidecar.md
│   └── n8n-webhooks.md
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── app.py               # FastAPI webhook endpoints + health check
├── assistant.py          # Claude brain — system prompt, tool defs, agentic loop
├── config.py             # Environment variable loading + validation
├── whatsapp.py           # WhatsApp send/receive helpers, message splitting
└── tools/
    ├── __init__.py
    ├── notion.py          # Notion CRUD (action items, meals, meetings, profile, daily plans, backlog)
    ├── calendar.py        # Google Calendar read + write (3 calendars)
    ├── outlook.py         # Outlook ICS feed polling (Jason's work calendar)
    ├── ynab.py            # YNAB budget summary
    └── anylist_bridge.py  # HTTP client for AnyList Node.js sidecar

anylist-sidecar/
├── Dockerfile
├── package.json
├── server.js             # Express REST wrapper around codetheweb/anylist

scripts/
├── setup_calendar.py     # One-time Google Calendar OAuth setup

docker-compose.yml        # FastAPI + AnyList sidecar + Cloudflare Tunnel
.env                      # All secrets (not committed)
.env.example              # Template with all required env vars
requirements.txt          # Python dependencies
Procfile                  # Fallback for cloud deployment (Railway/Render)
```

**Structure Decision**: Single service with a tools/ subpackage for each integration. The AnyList Node.js sidecar is a separate directory since it's a different runtime. Docker Compose orchestrates everything on the NUC. This is the simplest architecture that supports all 6 user stories.

## Architecture Overview

```text
                    WhatsApp
                       │
                       ▼
Internet ──→ Cloudflare Tunnel ──→ NUC Docker Network
                                    │
                              ┌─────┴─────┐
                              │  FastAPI   │ :8000
                              │  (Python)  │
                              └─────┬─────┘
                                    │
                    ┌───────┬───────┼───────┬────────┐
                    ▼       ▼       ▼       ▼        ▼
                 Claude   Notion  Google   YNAB   Outlook
                 (Haiku)  (API)   Calendar (API)  (ICS feed)
                 AI brain  Data   Read+Write Budget  Jason's
                           store  3 calendars       work cal
                                    │
                              ┌─────┴─────┐
                              │  AnyList  │ :3000
                              │ (Node.js) │
                              └───────────┘
                                    │
                              ┌─────┴─────┐
                              │   n8n     │ :5678
                              │  (cron)   │
                              └───────────┘
```

**Data Flow**:
1. WhatsApp message → FastAPI webhook → Claude agentic loop → tool calls → response → WhatsApp
2. n8n cron (7am daily) → `POST /api/v1/briefing/daily` → generates Erin's daily plan → writes calendar blocks → sends WhatsApp
3. n8n cron (Sunday PM) → `POST /api/v1/calendar/populate-week` → writes weekly time blocks to Erin's Google Calendar
4. n8n cron (Monday 9am) → sends WhatsApp asking about grandma's schedule this week

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| AI Model | Claude Haiku 4.5 | 90% of Sonnet's tool-use quality at 3x cheaper, 3-4x faster. Upgrade path: change one string. |
| WhatsApp | Meta Cloud API (direct) | Free for user-initiated conversations. No middleware needed at this volume. |
| Data Store | Notion (free plan) | Code already written. Browsable UI for Jason. Zero cost. Can migrate to SQLite later. |
| Calendar Write | Google Calendar API v3 | Batch API for 25-40 events/week. extendedProperties for tagging. Delete-and-recreate pattern. |
| Outlook Read | ICS feed (published) | Avoids Microsoft Graph (needs Cisco admin). Always-fresh data (no sync delay). |
| Grocery | AnyList via Node.js sidecar | Only viable API option. Battle-tested npm package. $12/year. |
| Hosting | NUC + Docker Compose | Zero hosting cost. Cloudflare Tunnel for public HTTPS. n8n already running. |
| Scheduling | n8n on NUC | Already deployed for another project. Cron → HTTP Request → FastAPI endpoints. |

## Complexity Tracking

No constitution violations to justify. Architecture uses standard patterns (webhook + API calls + cron) with no unnecessary abstractions.
