# Implementation Plan: Holistic Family Intelligence

**Branch**: `008-holistic-family-intelligence` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-holistic-family-intelligence/spec.md`

## Summary

Transform the bot from a tool dispatcher into a family strategist by adding cross-domain reasoning instructions to the system prompt, enhancing the daily briefing prompt to synthesize across domains, and adding a meeting prep capability. No new tools or databases — this is a prompt engineering feature that leverages all 47 existing tools.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK (Claude Opus), existing 47 tools
**Storage**: N/A (no new storage — uses existing Notion, YNAB, Google Calendar via tools)
**Testing**: Manual SSH + docker compose exec testing per quickstart.md
**Target Platform**: Linux server (Docker on NUC)
**Project Type**: Web service (existing FastAPI app)
**Performance Goals**: Cross-domain responses within existing response time (~10-30s for multi-tool queries)
**Constraints**: 200K context window must fit system prompt + cross-domain data + conversation history
**Scale/Scope**: 2 users, low volume

## Key Decisions

### D1: System Prompt Enhancement (Not New Tools)

**Decision**: Add cross-domain reasoning guidelines as new rules in the existing system prompt rather than creating new tools or a "family context snapshot" function.

**Rationale**: Claude already has access to all data via 47 tools and an agentic loop with 25-iteration cap. The gap isn't data access — it's reasoning instructions. The daily briefing already triggers 5+ tool calls successfully. Adding a snapshot tool would duplicate data retrieval logic and add maintenance burden.

**Alternative rejected**: A `get_family_snapshot()` tool that pre-fetches key metrics from all domains. Rejected because it adds code complexity, the existing tool loop handles multi-tool queries fine for 2 users, and the constitution mandates "fewer abstractions, fewer moving parts."

### D2: Cross-Domain Reasoning via Prompt Rules

**Decision**: Add a new "Cross-Domain Thinking" section to the system prompt (after the existing 38 rules) with 4-5 rules that guide Claude on when and how to connect dots across domains.

**Approach**: The rules teach Claude to:
1. Recognize broad questions ("how's our week", "are we on track", "I feel behind") as cross-domain triggers
2. Gather data from relevant domains before synthesizing
3. Weave insights into narrative advice, not bulleted sections per tool
4. Include specific recommendations (not just data)
5. Stay focused on single domains when the question is narrow

### D3: Enhanced Daily Briefing Prompt

**Decision**: Modify `generate_daily_plan()` to include explicit cross-domain synthesis instructions. The current prompt asks about calendar/routine/backlog. The enhanced version also asks Claude to check budget health, meal plan status, and overdue action items — and weave them together.

**Approach**: Expand the prompt string in `generate_daily_plan()`. No structural changes to the function or the n8n endpoint.

### D4: Meeting Prep via System Prompt + Endpoint

**Decision**: Add meeting prep capability through both:
1. System prompt rules that handle "prep me for our family meeting" naturally
2. A new n8n endpoint `POST /api/v1/meetings/prep-agenda` for scheduled triggers

**Approach**: The system prompt rules define the 5-section agenda structure (budget, calendar, action items, meals, priorities). The endpoint calls `generate_meeting_prep()` which is a lightweight trigger function like `generate_daily_plan()`.

### D5: No Model Change

**Decision**: Keep Claude Opus as the model for all interactions including cross-domain queries.

**Rationale**: Opus already handles multi-tool orchestration well. Cross-domain reasoning is about prompt quality, not model capability. Switching to a cheaper model for simple queries would add complexity without meaningful savings at 2-user scale.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | No new services — enhances existing tool orchestration via prompt engineering |
| II. Mobile-First Access | PASS | All interactions via WhatsApp (unchanged) |
| III. Simplicity & Low Friction | PASS | Same interface, smarter responses. No new steps for Erin |
| IV. Structured Output | PASS | Meeting prep produces scannable agenda with sections. Briefing remains structured |
| V. Incremental Value | PASS | Cross-domain questions (US1) work independently. Briefing (US2) adds value independently. Meeting prep (US3) adds value independently |

## Project Structure

### Documentation (this feature)

```text
specs/008-holistic-family-intelligence/
├── plan.md              # This file
├── research.md          # Prompt engineering research
├── data-model.md        # Conceptual entities (no new DB)
├── quickstart.md        # Manual test scenarios
├── contracts/
│   ├── system-prompt-additions.md    # New prompt rules
│   └── meeting-prep-endpoint.md      # New n8n endpoint
└── tasks.md             # Task breakdown
```

### Source Code (repository root)

```text
src/
├── assistant.py         # MODIFIED: system prompt additions, enhanced briefing prompt, meeting prep function
└── app.py               # MODIFIED: new meeting prep endpoint
```

**Structure Decision**: Minimal file changes — 2 existing files modified. No new source files. The feature is implemented entirely through prompt engineering (system prompt rules) and lightweight prompt triggers (briefing and meeting prep functions).

## Phases

### Phase 1: Cross-Domain Reasoning (US1)
- Add cross-domain reasoning rules to system prompt in `src/assistant.py`
- Rules cover: when to go cross-domain, how to synthesize, when to stay focused

### Phase 2: Smarter Daily Briefing (US2)
- Enhance `generate_daily_plan()` prompt to include cross-domain synthesis
- Existing n8n endpoint unchanged — just smarter prompts flowing through it

### Phase 3: Weekly Meeting Prep (US3)
- Add meeting prep rules to system prompt
- Add `generate_meeting_prep()` function in `src/assistant.py`
- Add `/api/v1/meetings/prep-agenda` endpoint in `src/app.py`

### Phase 4: Polish
- Syntax check, deploy, validate all 3 user stories on NUC
