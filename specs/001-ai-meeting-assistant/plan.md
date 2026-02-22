# Implementation Plan: AI-Powered Weekly Family Meeting Assistant

**Branch**: `001-ai-meeting-assistant` | **Date**: 2026-02-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-ai-meeting-assistant/spec.md`

## Summary

Build a WhatsApp-based family meeting assistant powered by Claude AI. The
assistant lives in a shared WhatsApp group chat and helps the family plan,
run, and follow up on weekly meetings. Claude Haiku 4.5 handles all
intelligence (intent parsing, agenda generation, meal planning, budget
summarization) via tool use. Notion serves as the persistent data layer and
family-viewable dashboard. Custom code is limited to a thin Python webhook
that shuttles messages between WhatsApp and Claude, plus tool function
wrappers for Google Calendar, YNAB, and Notion APIs.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: anthropic SDK, fastapi, notion-client, google-api-python-client, ynab, uvicorn
**Storage**: Notion (databases for action items, meal plans, meetings, family profile)
**Testing**: pytest
**Target Platform**: Linux cloud server (Railway, Render, or Fly.io)
**Project Type**: Web service (webhook-based)
**Performance Goals**: <30s response time for standard requests
**Constraints**: ~$0-6/month operating cost; <200 lines custom business logic
**Scale/Scope**: 2 users, ~20-50 messages/week, ~100 records/month in Notion

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Integration Over Building | PASS | Uses existing services (WhatsApp, Claude, Notion, Google Calendar, YNAB) via APIs. Custom code is orchestration only. |
| II. Mobile-First Access | PASS | WhatsApp is the interface — fully native on iPhone. Notion has a mobile app for browsing data. |
| III. Simplicity & Low Friction | PASS | Partners message in WhatsApp (already installed). Notion for viewing data (one new app). No terminal, no config for end users. |
| IV. Structured Output | PASS | Claude system prompt mandates checklist/list formatting. WhatsApp supports bold, lists, numbered items. |
| V. Incremental Value | PASS | Each user story (agenda, tasks, meals, budget) is an independent Claude tool — can ship and use one at a time. |

**Post-Phase 1 re-check**: All principles remain satisfied. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-meeting-assistant/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── whatsapp-webhook.md
│   └── notion-schema.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── app.py               # FastAPI app — WhatsApp webhook endpoint
├── assistant.py          # Claude tool runner — system prompt + tool definitions
├── tools/
│   ├── calendar.py       # Google Calendar API wrapper (read events)
│   ├── ynab.py           # YNAB API wrapper (read budget)
│   └── notion.py         # Notion API wrapper (CRUD action items, meals, meetings)
├── config.py             # Environment variables and secrets
└── whatsapp.py           # WhatsApp message send/receive helpers

tests/
├── test_assistant.py     # Tool routing and response formatting tests
├── test_tools/
│   ├── test_calendar.py
│   ├── test_ynab.py
│   └── test_notion.py
└── test_webhook.py       # Webhook endpoint tests

requirements.txt          # Python dependencies
.env.example              # Template for required environment variables
```

**Structure Decision**: Single project layout. No frontend — WhatsApp IS the
frontend. No separate backend/frontend split needed. Notion IS the dashboard.
The entire codebase is a thin Python service (~150-200 lines of meaningful
code) that connects WhatsApp → Claude → external APIs.

## Architecture Flow

```text
Partner sends WhatsApp message
    ↓
Meta servers POST webhook to our FastAPI endpoint (app.py)
    ↓
app.py extracts message text + sender phone number
    ↓
assistant.py passes message to Claude Haiku 4.5 with tool definitions
    ↓
Claude decides which tools to call (or just responds conversationally)
    ↓
SDK tool runner executes tool functions automatically:
    ├── calendar.py → Google Calendar API (fetch upcoming events)
    ├── ynab.py → YNAB API (fetch budget summary)
    └── notion.py → Notion API (read/write action items, meal plans, etc.)
    ↓
Claude receives tool results, formats a structured response
    ↓
whatsapp.py sends response back via Meta Graph API
    ↓
Partner sees formatted checklist/agenda in WhatsApp group chat
```

## Key Technical Decisions

### WhatsApp Setup Path

1. **Dev**: Use Meta Cloud API sandbox (5 test recipients, temporary token)
2. **Production**: Complete Meta Business verification, register dedicated
   phone number, generate permanent System User token
3. Webhook hosted on cloud service with HTTPS

### Claude Tool Design

Each tool maps to one external API operation:
- `get_calendar_events(days_ahead)` → Google Calendar
- `get_budget_summary(month, category?)` → YNAB
- `get_action_items(assignee?, status?)` → Notion
- `add_action_item(assignee, description)` → Notion
- `complete_action_item(description)` → Notion
- `add_topic(description)` → Notion
- `get_meal_plan(week_start?)` → Notion
- `save_meal_plan(plan)` → Notion
- `get_family_profile()` → Notion

The system prompt includes family context and formatting instructions. Claude
handles all intelligence: intent parsing, multi-tool orchestration, natural
language generation, and conflict detection.

### Conversation State

Conversation history is maintained in memory per webhook session. For cross-
session memory, Claude reads persistent state from Notion (action items,
family profile, previous meeting notes). No need for a separate conversation
database — each message is stateless from the backend's perspective, with
Notion providing the "memory."

### Notion Database Architecture

Four Notion databases (see data-model.md for full schema):
1. **Action Items** — kanban-style task board
2. **Meal Plans** — weekly pages with daily breakdown
3. **Meetings** — timeline of meeting agendas and notes
4. **Family Profile** — static configuration page

## Complexity Tracking

No constitution violations. No complexity justifications needed.
