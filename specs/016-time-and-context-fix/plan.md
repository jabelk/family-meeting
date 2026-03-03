# Implementation Plan: Time Awareness & Extended Conversation Context

**Branch**: `016-time-and-context-fix` | **Date**: 2026-03-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/016-time-and-context-fix/spec.md`

## Summary

Two fixes for issues Erin reported: (1) Make Claude reliably use the current time when generating schedules and setting reminders — add explicit time-awareness rules to the system prompt and inject timestamp into user messages so it's adjacent to the request. (2) Extend conversation retention from 24 hours / 25 turns to 7 days / 100 turns so the bot remembers discussions from earlier in the week.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: anthropic SDK (system prompt construction), datetime/zoneinfo (time injection)
**Storage**: Existing `data/conversations.json` (atomic JSON file pattern)
**Testing**: Manual verification via WhatsApp + curl
**Target Platform**: Linux server (Docker on NUC via Docker Compose)
**Project Type**: Web service (system prompt + config changes only)
**Performance Goals**: No degradation — conversation file stays small at <100 turns/user
**Constraints**: Claude's context window must accommodate 100 turns of history; at ~500 tokens/turn average, that's ~50K tokens — well within Haiku 4.5's 200K limit
**Scale/Scope**: 2 users (Jason, Erin), <100 turns/week each. ~15 lines of code changed across 2 files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Integration Over Building** | PASS | No new services — fixes behavior of existing assistant and conversation storage. |
| **II. Mobile-First Access** | PASS | WhatsApp remains the interface. Changes are server-side only. |
| **III. Simplicity & Low Friction** | PASS | Zero user-facing changes. Fixes work invisibly — better time awareness, longer memory. |
| **IV. Structured Output** | PASS | Time-aware schedules will still produce checklists. Better time filtering means more relevant lists. |
| **V. Incremental Value** | PASS | Each fix is independently valuable. Time awareness works without extended context and vice versa. |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/016-time-and-context-fix/
├── plan.md              # This file
├── research.md          # Phase 0: time injection strategies
├── data-model.md        # Phase 1: conversation storage schema (unchanged)
├── quickstart.md        # Phase 1: verification scenarios
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── assistant.py         # MODIFY: add time-awareness rules to SYSTEM_PROMPT, inject timestamp into user messages
└── conversation.py      # MODIFY: change CONVERSATION_TIMEOUT to 604800 (7 days), MAX_CONVERSATION_TURNS to 100
```

**Structure Decision**: Existing single-project structure. Two source files modified with ~15 lines of changes total. No new files, no new dependencies.
