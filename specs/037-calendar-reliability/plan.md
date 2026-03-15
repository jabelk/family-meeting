# Implementation Plan: Calendar Reliability

**Branch**: `037-calendar-reliability` | **Date**: 2026-03-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/037-calendar-reliability/spec.md`

## Summary

Fix three persistent calendar bugs by moving from prompt-level fixes (tried 3 times, failed) to code-level validation. Add a `_validate_event_time()` utility that catches AM/PM errors before Google Calendar API submission, split `get_daily_context()` output into completed/upcoming sections, strengthen recurring event detection in system prompts, and provide a one-time cleanup scan for existing corrupted events.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, anthropic SDK, google-api-python-client (existing — no new deps)
**Storage**: Google Calendar API (external), JSON files in `data/` (existing, unchanged)
**Testing**: pytest
**Target Platform**: Linux server (Railway), WhatsApp Cloud API
**Project Type**: Web service (FastAPI)
**Performance Goals**: Time validation adds <10ms per event; batch of 30 events validated in <300ms
**Constraints**: Single uvicorn worker (APScheduler requirement); WhatsApp 4096 char message limit
**Scale/Scope**: 2 users, ~20-30 calendar events created per week, ~5-10 daily context queries per day

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | ✅ Pass | Leverages existing Google Calendar API; no new services introduced |
| II. Mobile-First Access | ✅ Pass | All interactions via WhatsApp (existing); cleanup uses WhatsApp messages with A/B/C options |
| III. Simplicity & Low Friction | ✅ Pass | Corrections are automatic and silent (with brief inline note); no new user-facing complexity |
| IV. Structured Output | ✅ Pass | Daily context output gains structured completed/upcoming sections |
| V. Incremental Value | ✅ Pass | P1 (time validation) delivers standalone value; P2 (recurring + cleanup) and P3 (time-aware responses) are independent |

**Post-Phase 1 Re-check**: All principles still pass. No new abstractions, no new services, no new dependencies. Changes are surgical modifications to existing functions.

## Project Structure

### Documentation (this feature)

```text
specs/037-calendar-reliability/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: testing & deployment guide
├── contracts/
│   └── tool-contracts.md # Phase 1: tool response format changes
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── tools/
│   └── calendar.py      # MODIFY: add _validate_event_time(), update batch_create_events() and create_quick_event()
├── context.py           # MODIFY: split get_daily_context() output into completed/upcoming
├── assistant.py         # MODIFY: _handle_write_calendar_blocks() passes correction notes through
├── app.py               # MODIFY: add /api/v1/admin/calendar-cleanup endpoint
└── prompts/
    ├── system/
    │   └── 07-calendar-reminders.md  # MODIFY: add recurring event detection rule
    └── tools/
        └── calendar.md              # MODIFY: strengthen RRULE usage instructions

tests/
└── test_calendar_validation.py      # NEW: unit tests for _validate_event_time()
```

**Structure Decision**: Single project, existing layout. All changes are modifications to existing files in `src/`. One new test file.

## Complexity Tracking

No constitution violations — no complexity tracking needed.
