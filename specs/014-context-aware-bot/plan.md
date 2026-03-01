# Implementation Plan: Context-Aware Bot

**Branch**: `014-context-aware-bot` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-context-aware-bot/spec.md`

## Summary

Replace the 413-line hardcoded system prompt (weekly schedule, childcare, food prefs, 71 rules) with a dynamic `get_daily_context` tool that pulls live calendar data, infers childcare status, checks time-of-day communication mode, and reads user preferences. Add personal routine checklists (`save_routine`/`get_routine`). Shrink system prompt to ≤280 lines.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK, google-api-python-client, google-auth-oauthlib
**Storage**: JSON files — `data/routines.json` (new, same atomic-write pattern as `preferences.py` and `conversation.py`)
**Testing**: Manual WhatsApp E2E testing (no unit test framework in project)
**Target Platform**: Linux (Docker on NUC, Ubuntu 24.04) + macOS local dev
**Project Type**: web-service (existing FastAPI + WhatsApp webhook)
**Performance Goals**: `get_daily_context` completes in <3 seconds (2-4 API calls to Google Calendar + in-memory lookups)
**Constraints**: WhatsApp ~1600 char limit per message, Claude Haiku context window, existing agentic tool loop pattern
**Scale/Scope**: 2 users (Jason, Erin), 3 Google Calendars, ~50 tools total after this feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | ✅ PASS | Uses existing Google Calendar API, Notion, preferences. No new external services. Routines stored in local JSON (same pattern as existing modules). |
| II. Mobile-First Access | ✅ PASS | All interaction via WhatsApp. No new UI. Routines managed through natural language chat. |
| III. Simplicity & Low Friction | ✅ PASS | `get_daily_context` is invisible to users — model calls it automatically. Routines: "save my morning routine: step1, step2". Zero setup. |
| IV. Structured Output | ✅ PASS | Context tool returns structured text (events grouped by person, communication mode label). Routines displayed as numbered checklists. |
| V. Incremental Value | ✅ PASS | US1 (context tool) delivers standalone value. US3 (routines) works independently. US2 (quiet hours) enhances US1. US4 (cleanup) is polish. |

**No violations. No complexity tracking needed.**

## Project Structure

### Documentation (this feature)

```text
specs/014-context-aware-bot/
├── plan.md              # This file
├── research.md          # Phase 0: technical decisions
├── data-model.md        # Phase 1: entities and storage
├── quickstart.md        # Phase 1: integration scenarios
├── contracts/
│   └── tool-schemas.md  # Phase 1: tool input/output contracts
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── assistant.py          # MODIFY: system prompt cleanup, add 4 new tool defs + handlers
├── context.py            # NEW: get_daily_context implementation
├── routines.py           # NEW: routine storage (save/get/modify/delete)
├── preferences.py        # READ ONLY: existing preference store (used by context tool)
├── conversation.py       # READ ONLY: reference for storage pattern
├── config.py             # READ ONLY: CALENDAR_IDS, PHONE_TO_NAME, ERIN_PHONE
├── tools/
│   ├── calendar.py       # READ ONLY: get_events_for_date, get_events_for_date_raw
│   ├── nudges.py         # MODIFY: integrate communication_mode check in process_pending_nudges
│   └── notion.py         # READ ONLY: get_backlog_items (for pending count)
└── whatsapp.py           # READ ONLY: send functions

data/
└── routines.json         # NEW: routine storage file (auto-created on first write)
```

**Structure Decision**: Follows existing flat `src/` layout. Two new modules (`context.py`, `routines.py`) at the same level as `preferences.py` and `conversation.py`. No new directories needed. Tools module (`src/tools/`) gets a minor nudge integration update.
