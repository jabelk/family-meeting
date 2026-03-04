# Implementation Plan: Smart Daily Planner

**Branch**: `017-smart-daily-planner` | **Date**: 2026-03-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-smart-daily-planner/spec.md`

## Summary

Make the daily plan smarter by: (1) reading existing calendar events and treating them as immovable blocks, (2) presenting a draft plan for Erin's confirmation before writing to calendar, and (3) storing drive times for common locations and auto-inserting travel buffers. This is primarily a **system prompt + drive time storage** change — the calendar data is already available via `get_daily_context()` and the calendar write tool already exists.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK (Claude Haiku 4.5), existing tool functions
**Storage**: JSON file at `data/drive_times.json` (same atomic write pattern as `preferences.py`, `routines.py`, `conversation.py`)
**Testing**: Manual verification via WhatsApp + NUC logs
**Target Platform**: Linux server (Docker on NUC) + WhatsApp interface
**Project Type**: Web service (existing FastAPI app)
**Performance Goals**: N/A (same single-user latency)
**Constraints**: Must work via WhatsApp conversational interface, no new UI
**Scale/Scope**: Single family, <10 stored drive time locations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | ✅ PASS | Uses existing Google Calendar API (read + write). No new services built. |
| II. Mobile-First Access | ✅ PASS | All interaction via WhatsApp. Confirm/reject is natural conversation ("looks good" / "move gym to 10"). |
| III. Simplicity & Low Friction | ✅ PASS | Zero new steps for Erin. Calendar events auto-read, drive times auto-inserted, plan confirmation is a simple yes/no reply. Adding drive times via conversation ("the gym is 5 minutes away"). |
| IV. Structured Output | ✅ PASS | Daily plan output remains structured time blocks with clear formatting. |
| V. Incremental Value | ✅ PASS | US1 (calendar-aware) works alone. US2 (confirm-before-write) works alone. US3 (drive times) works alone. Each delivers standalone improvement. |

All gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/017-smart-daily-planner/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── assistant.py         # System prompt rules 9-15b (modify rules for US1, US2, US3)
├── drive_times.py       # NEW — drive time storage module (US3)
└── context.py           # Minor tweak: include drive times in daily context output
```

**Structure Decision**: Existing single-project structure. Two files modified (`assistant.py`, `context.py`), one new file (`drive_times.py`) following the same atomic JSON pattern as `preferences.py` and `routines.py`.

## Approach by User Story

### US1: Calendar-Aware Plan Generation
**Files**: `src/assistant.py` (system prompt only)

The data is already there — `get_daily_context()` reads all 3 Google Calendars and returns events grouped by person. The problem is Claude doesn't treat these as immovable. Fix: add system prompt rules explicitly telling Claude to treat existing calendar events as fixed blocks, schedule new activities around them, and never overlap or omit them.

### US2: Confirm Before Writing to Calendar
**Files**: `src/assistant.py` (system prompt only)

Currently rule 14 says: "After generating the plan, write time blocks to Erin's Google Calendar." Change this to: present the plan as a draft, ask for confirmation, only write after explicit approval. This is a pure prompt behavior change — the `write_calendar_blocks` tool already exists and Claude already decides when to call it.

### US3: Drive Time Buffers
**Files**: `src/drive_times.py` (new), `src/assistant.py` (new tool + rules), `src/context.py` (include drive times in context)

New module `drive_times.py` stores location→minutes mappings in `data/drive_times.json`. Two new tools exposed to Claude: `get_drive_times` (read all stored times) and `save_drive_time` (add/update a location). System prompt rules instruct Claude to call `get_drive_times` during plan generation and insert travel buffers.

## Complexity Tracking

No constitution violations. No complexity justifications needed.
