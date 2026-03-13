# Implementation Plan: Tool Failure Resilience

**Branch**: `033-tool-failure-resilience` | **Date**: 2026-03-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/033-tool-failure-resilience/spec.md`

## Summary

Add automatic retry, classified error reporting, and fallback actions to the tool execution loop in `src/assistant.py`. The current catch-all handler silently drops failures with a "Skip this section" message. This refactor classifies exceptions (retryable vs permanent vs input-error), retries transient failures up to 2 times, provides service-aware error messages that instruct Claude to inform the user, and triggers fallback actions for failed write operations (e.g., Calendar → Notion action item, AnyList → WhatsApp message).

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK, httpx, notion-client, google-api-python-client — no new dependencies
**Storage**: N/A (no new storage; existing JSON files in `data/` unchanged)
**Testing**: pytest (existing test suite)
**Target Platform**: Linux server (Railway) / Docker
**Project Type**: Web service (existing FastAPI application)
**Performance Goals**: Total response time including retries must not exceed 30 seconds per user request
**Constraints**: Retry delays max 3 seconds total (1s + 2s); single uvicorn worker (APScheduler constraint)
**Scale/Scope**: ~77 tools across 9 integrations; ~10 write tools need fallback mappings

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Leverages existing integrations; adds resilience to existing tool calls, not new custom functionality |
| II. Mobile-First Access | PASS | No UI changes; improves reliability of the WhatsApp-based interface by ensuring failures are reported |
| III. Simplicity & Low Friction | PASS | Zero user-facing setup; retry/fallback is fully automatic and transparent |
| IV. Structured Output | PASS | Error messages instruct Claude to provide clear, actionable failure reports |
| V. Incremental Value | PASS | Retry (US1) delivers standalone value; error reporting (US2) and fallbacks (US3) layer independently |

**Post-design re-check**: All principles still pass. The new `src/tool_resilience.py` module is a single file with clear responsibilities. No new abstractions or frameworks introduced.

## Project Structure

### Documentation (this feature)

```text
specs/033-tool-failure-resilience/
├── plan.md              # This file
├── research.md          # Phase 0 output (completed)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── tool_resilience.py   # NEW — exception classification, retry logic, fallback mappings, error message formatting
├── integrations.py      # MODIFIED — add get_integration_for_tool() reverse lookup helper
└── assistant.py         # MODIFIED — replace catch-all handler (lines 1853-1855) with resilience wrapper call

tests/
└── test_tool_resilience.py  # NEW — unit tests for classification, retry, fallback, error messages
```

**Structure Decision**: Existing flat `src/` layout. One new module (`src/tool_resilience.py`) keeps all resilience logic in a single file — exception classification, retry loop, fallback mappings, and error message formatting. The assistant.py change is minimal: replace the 3-line catch-all with a call to the resilience module. A reverse-lookup helper is added to `src/integrations.py` since it's a natural extension of the registry.

## Complexity Tracking

No constitution violations — no complexity justifications needed.
