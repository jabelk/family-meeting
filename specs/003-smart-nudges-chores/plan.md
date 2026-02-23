# Implementation Plan: Smart Nudges & Chore Scheduling

**Branch**: `003-smart-nudges-chores` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-smart-nudges-chores/spec.md`

## Summary

Add proactive, time-aware nudges to the family assistant: departure reminders before calendar events, laundry workflow timers, and intelligent chore suggestions during free windows. All nudges are delivered via WhatsApp and persist across bot restarts. The implementation extends the existing FastAPI + n8n + Notion stack with a new polling endpoint, a Notion nudge queue database, and 3 new tools for the Claude agent.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK (Claude Sonnet 4), notion-client >=2.2.0,<2.3.0, httpx, google-api-python-client
**Storage**: Notion API (2 new databases: Nudge Queue, Chores) + existing Google Calendar read
**Testing**: Manual E2E validation via WhatsApp + n8n test execution
**Target Platform**: Docker Compose on NUC (Ubuntu 24.04)
**Project Type**: Web service (existing FastAPI app)
**Performance Goals**: Nudge delivery within 2 minutes of scheduled time (NFR-001)
**Constraints**: Max 8 proactive messages/day (NFR-002), quiet hours 7:00 AM – 8:30 PM Pacific (NFR-005)
**Scale/Scope**: Single user (Erin), ~5-10 nudges/day, 1 concurrent laundry session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Integration Over Building | PASS | Uses existing Google Calendar, Notion, WhatsApp — no new services introduced |
| II. Mobile-First Access | PASS | All interactions via WhatsApp on iPhone — no web UI needed |
| III. Simplicity & Low Friction | PASS | Nudges are automatic (zero effort from Erin); responses are natural language ("done", "snooze", "skip") |
| IV. Structured Output | PASS | Nudges are short, scannable messages; chore suggestions include duration and options |
| V. Incremental Value | PASS | Each user story is independently deployable: departure nudges work without laundry or chores |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/003-smart-nudges-chores/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── nudge-endpoints.md
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── app.py               # ADD: 2 new endpoints (/api/v1/nudges/scan, /api/v1/nudges/process-laundry)
├── assistant.py          # ADD: 3 new tools (start_laundry, complete_chore, set_quiet_day)
├── config.py             # ADD: NOTION_NUDGE_QUEUE_DB, NOTION_CHORES_DB
├── tools/
│   ├── nudges.py         # NEW: nudge scanning, scheduling, virtual event detection, batching
│   ├── laundry.py        # NEW: laundry session lifecycle, calendar conflict detection
│   ├── chores.py         # NEW: chore suggestions, free window calculation, preference tracking
│   ├── calendar.py       # EXTEND: add get_events_for_date_raw() returning full event dicts
│   ├── notion.py         # EXTEND: CRUD for Nudge Queue and Chores databases
│   └── proactive.py      # UNCHANGED
└── whatsapp.py           # UNCHANGED (send_message already handles splitting)

docs/
└── notion-setup.md       # UPDATE: Steps 10-11 for Nudge Queue and Chores databases
```

**Structure Decision**: Extends the existing flat `src/tools/` module pattern. Three new modules (`nudges.py`, `laundry.py`, `chores.py`) keep concerns separated while following the same patterns as `proactive.py` and `recipes.py`.

## Architecture

### Nudge Delivery Pipeline

```
n8n (every 15 min, 7am-8:30pm)
  → POST /api/v1/nudges/scan
    → scan_upcoming_departures() → creates Nudge records in Notion (status: pending)
    → check_free_windows() → creates chore suggestion Nudges
    → process_pending_nudges() → sends due nudges via WhatsApp, respects daily cap
```

### Laundry Flow (Event-Driven)

```
Erin: "started laundry"
  → Claude calls start_laundry tool
    → creates Laundry Session in Notion (phase: washing)
    → creates 2 Nudge records: washer_done (now + 45min), follow_up (now + 2h45m)
    → checks calendar for conflicts with dryer timing

Erin: "moved to dryer"
  → Claude calls advance_laundry tool
    → updates session phase to "drying"
    → creates Nudge: dryer_done (now + 60min)
    → cancels follow_up nudge

n8n scan picks up pending laundry nudges → sends via WhatsApp
```

### Chore Suggestion Flow

```
n8n scan (every 15 min)
  → check_free_windows()
    → compares calendar events vs. routine templates
    → finds gaps >= 15 min
    → queries Chores DB for best match (duration fits, not done recently, day preference)
    → creates Nudge with chore context

Erin: "done" / "skip"
  → Claude calls complete_chore / skip_chore
    → updates Chore.last_completed / marks nudge dismissed
```

### Virtual Event Detection (FR-003)

Events are assumed to require departure unless:
- `conferenceData` field is present (contains Zoom/Meet/Teams link)
- Title or description contains keywords: "call", "virtual", "remote", "online", "zoom", "meet", "teams", "webinar"
- Event is an all-day event (no specific departure time)
- Event was created by the assistant (`createdBy=family-meeting-assistant` tag)

### Message Batching (FR-011)

When `process_pending_nudges()` finds multiple nudges due within a 5-minute window:
1. Group them by type
2. Format as a single consolidated message
3. Mark all as sent
4. Count as 1 toward the daily 8-message cap

### Quiet Day Override (NFR-004)

When Erin says "quiet day" or "no nudges today":
- Claude calls `set_quiet_day` tool
- Sets a flag in Notion (Family Profile or a simple key-value in Nudge Queue)
- `process_pending_nudges()` checks flag and skips all pending nudges
- Flag auto-resets at midnight

## n8n Workflows (New)

| # | Workflow | Cron | Endpoint |
|---|----------|------|----------|
| WF-009 | Nudge Scanner | `*/15 7-20 * * *` | `/api/v1/nudges/scan` |

Single workflow handles everything: departure nudge creation, chore suggestion creation, and pending nudge delivery. Runs every 15 minutes from 7am to 8:30pm (last run at 8:15pm, `*/15 7-20` covers 7:00-20:45).

## Phases

### Phase 1: Departure Nudges (US1) — MVP

- New Notion database: Nudge Queue
- `src/tools/nudges.py`: scan calendar, detect virtual events, create/process nudges
- New endpoint: `POST /api/v1/nudges/scan`
- n8n WF-009
- Snooze/dismiss handling in Claude system prompt

### Phase 2: Laundry Workflow (US2)

- `src/tools/laundry.py`: session lifecycle, calendar conflict checks
- New tools in assistant.py: `start_laundry`, `advance_laundry`
- Laundry nudges flow through existing Nudge Queue

### Phase 3: Chore Suggestions (US3)

- New Notion database: Chores (with default seed data)
- `src/tools/chores.py`: free window detection, chore matching, suggestion generation
- New tools: `complete_chore`, `skip_chore`

### Phase 4: Chore Preferences (US4)

- Extend Chores DB with preference fields
- Update Claude system prompt for conversational preference setting
- Chore history query tool
