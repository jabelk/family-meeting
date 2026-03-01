# Implementation Plan: User Preference Persistence

**Branch**: `013-user-preference-persistence` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-user-preference-persistence/spec.md`

## Summary

Add persistent per-user preference storage so the bot remembers Erin and Jason's explicit opt-outs and communication preferences across conversations. Preferences are stored in a JSON file (`data/user_preferences.json`), injected into the system prompt on each message, and checked before nudge delivery. Three new Claude tools (`save_preference`, `list_preferences`, `remove_preference`) enable natural language CRUD via WhatsApp. A new module `src/preferences.py` follows the exact pattern of `src/conversation.py` for atomic file I/O.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK (Claude Opus for tool loop), existing WhatsApp/n8n infrastructure
**Storage**: JSON file in `data/` directory (`data/user_preferences.json`), same Docker volume mount as conversations.json
**Testing**: Manual E2E via WhatsApp + python3 -c import verification (same pattern as Features 007/010/011)
**Target Platform**: Docker on NUC (existing deployment)
**Project Type**: Extension of existing web service
**Performance Goals**: Preference lookup under 1ms (in-memory cache). No additional API calls.
**Constraints**: WhatsApp message limit ~4096 chars; max 50 preferences per user
**Scale/Scope**: 2 users, ~5-15 preferences each

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Uses existing WhatsApp interface and Claude tool loop. No new external services. Preferences enhance existing integrations (nudges, calendar, briefings). |
| II. Mobile-First Access | PASS | All interactions via WhatsApp. "Don't remind me about X" and "what are my preferences?" work naturally on mobile. |
| III. Simplicity & Low Friction | PASS | Setting a preference = saying it in natural language. Listing = "what are my preferences?". Removing = "start X again". Zero setup required. |
| IV. Structured Output | PASS | Preference lists use numbered format with category, description, and date. Confirmation messages are concise. |
| V. Incremental Value | PASS | US1 (capture) + US2 (honor) deliver standalone value. US3 (list/manage) adds control. US4 (categories) refines. No dependencies on other features to function. |

**Gate result**: PASS -- no violations.

## Project Structure

### Documentation (this feature)

```text
specs/013-user-preference-persistence/
├── spec.md
├── plan.md              # This file
├── research.md          # Storage format, detection approach, injection strategy decisions
├── data-model.md        # UserPreference entity, PreferenceStore JSON structure
├── quickstart.md        # 7 integration scenarios with expected WhatsApp interactions
├── contracts/
│   └── api-endpoints.md # 3 Claude tools + internal Python API
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Implementation tasks organized by user story
```

### Source Code (repository root)

```text
src/
├── preferences.py       # NEW: Preference store (load/save/get/add/remove/clear)
├── assistant.py         # MODIFIED: 3 new tools, system prompt injection, new rules 68-70
├── tools/
│   └── nudges.py        # MODIFIED: Preference check before nudge delivery
data/
└── user_preferences.json  # Created at runtime (already in .gitignore via data/*.json)
```

**Structure Decision**: Single new module (`src/preferences.py`) plus modifications to two existing files. Follows the pattern of Features 007 (conversation memory) and 010 (Amazon sync) — a data module paired with tool/prompt changes in assistant.py.

## Architecture

### Data Flow

1. **Inbound message** -> `handle_message()` -> load preferences for sender phone -> append to system prompt -> Claude sees preferences and honors them
2. **Tool call** -> `save_preference` / `list_preferences` / `remove_preference` -> `src/preferences.py` -> atomic JSON write -> confirmation
3. **Nudge scan** -> `process_pending_nudges()` -> load preferences for target phone -> filter nudges matching opt-outs -> send remaining

### Implementation Phases

| Phase | Scope | Files |
|-------|-------|-------|
| 1: Setup | Create data structure, .gitignore verification | `data/` |
| 2: Foundational | Preference store module with CRUD + atomic I/O | `src/preferences.py` |
| 3: US1 (P1) | Capture preferences via Claude tool + system prompt instructions | `src/assistant.py` |
| 4: US2 (P1) | Honor preferences in system prompt + nudge filtering | `src/assistant.py`, `src/tools/nudges.py` |
| 5: US3 (P2) | List and manage preferences via tools | `src/assistant.py` |
| 6: US4 (P3) | Category typing and quiet hours support | `src/preferences.py`, `src/assistant.py` |
| 7: Polish | Edge cases, validation, overflow cap | `src/preferences.py` |

## Complexity Tracking

No constitution violations -- no entries needed.
