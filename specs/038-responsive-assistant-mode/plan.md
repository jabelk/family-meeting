# Implementation Plan: Responsive Assistant Mode

**Branch**: `038-responsive-assistant-mode` | **Date**: 2026-03-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/038-responsive-assistant-mode/spec.md`

## Summary

Flip the assistant's default behavior from proactive (push) to responsive (pull). Remove prompt rules that auto-fill free time with backlog items, quiet the communication modes, and add structured dietary preference enforcement. All changes are prompt edits + preference system extension — no new dependencies, no new endpoints.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, anthropic SDK (existing — no new deps)
**Storage**: JSON files in `data/` (existing `user_preferences.json` extended with dietary category)
**Testing**: pytest
**Target Platform**: Linux server (Railway), WhatsApp Cloud API
**Project Type**: Web service (FastAPI)
**Performance Goals**: N/A — prompt changes have zero runtime cost
**Constraints**: Prompt changes must not break existing tool call patterns or conversation flows
**Scale/Scope**: 2 users, ~6 prompt files modified, 1 preference category added

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | ✅ Pass | No new services — edits existing prompts and preference storage |
| II. Mobile-First Access | ✅ Pass | All interactions remain via WhatsApp; no UX changes |
| III. Simplicity & Low Friction | ✅ Pass | Reduces friction by removing unwanted proactive content |
| IV. Structured Output | ✅ Pass | Daily plans still structured; free time labeled explicitly |
| V. Incremental Value | ✅ Pass | US1 (remove nagging) delivers immediate standalone value |

**Post-Phase 1 Re-check**: All principles still pass. This feature actually improves Principle III compliance by removing friction Erin explicitly complained about.

## Project Structure

### Documentation (this feature)

```text
specs/038-responsive-assistant-mode/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: testing & deployment guide
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── prompts/
│   ├── system/
│   │   ├── 03-daily-planner.md      # MODIFY: remove Rule 12 (auto-fill free time)
│   │   ├── 05-chores-nudges.md      # MODIFY: remove proactive chore suggestion rules
│   │   └── 08-advanced.md           # MODIFY: update communication mode descriptions
│   └── tools/
│       └── meal-planning.md         # MODIFY: add dietary preference check instruction (if exists)
├── preferences.py                   # MODIFY: add "dietary" preference category
├── context.py                       # MODIFY: update communication mode descriptions
└── assistant.py                     # MODIFY: inject dietary preferences into meal planning context
```

**Structure Decision**: Single project, existing layout. All changes are modifications to existing prompt files and the preference module. No new files created.

## Complexity Tracking

No constitution violations — no complexity tracking needed.
