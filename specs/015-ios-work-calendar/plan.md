# Implementation Plan: iOS Work Calendar Sync

**Branch**: `015-ios-work-calendar` | **Date**: 2026-03-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-ios-work-calendar/spec.md`

## Summary

Jason's Cisco Outlook calendar is locked down (no ICS publishing, no calendar subscribe). Both his Google and Cisco calendars show on his iPhone Calendar app. An iOS Shortcut will run weekly (Sunday evening), read the upcoming week's Cisco work calendar events, and POST them to a new authenticated endpoint. The bot stores events in `data/work_calendar.json` using the existing atomic JSON pattern. The existing `get_outlook_events` tool falls back to this data when no ICS URL is configured. Erin's daily plan then shows Jason's meeting windows and free times.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, Pydantic (request model validation), json (stdlib for atomic JSON writes)
**Storage**: Atomic JSON file at `data/work_calendar.json` (same pattern as `preferences.py`, `conversation.py`, `routines.py`)
**Testing**: Manual curl + NUC deployment verification (existing pattern)
**Target Platform**: Linux server (Docker on NUC via Docker Compose)
**Project Type**: Web service (FastAPI endpoint addition + existing tool modification)
**Performance Goals**: Endpoint returns in <1 second; `get_outlook_events` reads file in <100ms
**Constraints**: Storage <1KB per day (~30 meetings max); 7-day expiration with auto-prune
**Scale/Scope**: 1 user (Jason), ~10-30 meetings/week, 1 new endpoint, 1 modified module

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Integration Over Building** | PASS | Leverages iOS Shortcuts (Apple ecosystem feature) to bridge Cisco Exchange → bot. No custom calendar sync engine. |
| **II. Mobile-First Access** | PASS | iOS Shortcut runs natively on Jason's iPhone — zero desktop interaction required. |
| **III. Simplicity & Low Friction** | PASS | One-time 5-minute shortcut setup, then fully automated weekly. Zero ongoing intervention. |
| **IV. Structured Output** | PASS | Daily plan already produces structured meeting windows with time blocks as lists. |
| **V. Incremental Value** | PASS | Standalone feature — enhances daily plan but daily plan works fine without it (shows "work schedule unavailable"). |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/015-ios-work-calendar/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entities and storage schema
├── quickstart.md        # Phase 1: integration test scenarios
├── contracts/           # Phase 1: API endpoint contract
│   └── work-events-endpoint.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── app.py               # ADD: POST /api/v1/calendar/work-events endpoint
├── tools/
│   └── outlook.py       # MODIFY: add file-based fallback in get_outlook_events & get_outlook_busy_windows
└── config.py            # No changes needed (N8N_WEBHOOK_SECRET already exists)

data/
└── work_calendar.json   # NEW: atomic JSON storage for pushed work events

docs/
└── ios-shortcut-setup.md  # NEW: setup guide for Jason (US3)
```

**Structure Decision**: Existing single-project structure. Two source files modified (`app.py`, `outlook.py`), one new data file created at runtime, one new documentation file. No new Python modules needed — this is a ~50-line feature spread across two existing files.
