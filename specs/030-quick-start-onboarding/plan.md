# Implementation Plan: Quick Start Onboarding

**Branch**: `030-quick-start-onboarding` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/030-quick-start-onboarding/spec.md`

## Summary

Enable minimal WhatsApp + AI deployments by dynamically filtering tools and system prompt sections based on configured integrations. Add a validation script that cross-references family.yaml and .env to catch configuration errors before deployment. Fix health endpoint to report "healthy" for minimal deployments.

**Core approach**: Centralized integration registry → drives tool filtering, prompt filtering, health checks, and validation. YAML frontmatter tags on system prompt files. Auto-detect enabled integrations from env vars.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, anthropic SDK, PyYAML (existing)
**Storage**: JSON files in `data/` (unchanged)
**Testing**: pytest
**Target Platform**: Linux server (Railway), Docker
**Project Type**: Web service (existing codebase enhancement)
**Performance Goals**: Startup time < 5s (current baseline), no per-request overhead for integration detection
**Constraints**: Single uvicorn worker (APScheduler), backward compatible with existing full deployments
**Scale/Scope**: 6 integration groups, ~70 tools, 9 system prompt files, 13 tool description files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Feature enhances integration management, doesn't rebuild anything |
| II. Mobile-First Access | PASS | No UI changes — WhatsApp remains the interface |
| III. Simplicity & Low Friction | PASS | Reduces operator setup friction. End users unaffected. |
| IV. Structured Output | N/A | No output format changes |
| V. Incremental Value | PASS | Core design principle of this feature — each integration adds standalone value |

**Post-design re-check**: All gates still pass. The integration registry adds one new file (`src/integrations.py`) but simplifies the overall system by centralizing scattered detection logic.

## Project Structure

### Documentation (this feature)

```text
specs/030-quick-start-onboarding/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── validate-setup-cli.md
│   └── health-endpoint.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── integrations.py          # NEW — centralized integration registry
├── config.py                # MODIFIED — use registry for integration detection
├── assistant.py             # MODIFIED — dynamic tool filtering at startup
├── app.py                   # MODIFIED — health endpoint logic
├── prompts/
│   ├── __init__.py          # MODIFIED — frontmatter parsing, conditional loading
│   ├── system/
│   │   ├── 01-identity.md   # MODIFIED — add frontmatter (requires: [core])
│   │   ├── 02-response-rules.md  # MODIFIED — add frontmatter (requires: [core])
│   │   ├── 03-daily-planner.md   # MODIFIED — split or add frontmatter
│   │   ├── ...              # Each file gets frontmatter tags
│   │   └── 10-receipt-categorization.md
│   └── tools/
│       ├── calendar.md      # Unchanged (filtered by tool name, not file)
│       └── ...

scripts/
└── validate_setup.py        # NEW — pre-deployment validation CLI

tests/
├── test_integrations.py     # NEW — integration registry tests
├── test_validate_setup.py   # NEW — validation script tests
└── test_prompts.py          # MODIFIED — test prompt filtering
```

**Structure Decision**: Single project, existing directory structure. One new module (`src/integrations.py`), one new script (`scripts/validate_setup.py`), two new test files.

## Implementation Phases

### Phase 1: Integration Registry (Foundation)

Create `src/integrations.py` with:
- `INTEGRATION_REGISTRY` dict mapping integration names to env vars, tools, and prompt tags
- `get_enabled_integrations() -> set[str]` — checks env vars, returns enabled integration names
- `get_tools_for_integrations(enabled: set[str]) -> list[str]` — returns tool names for enabled integrations
- `is_integration_enabled(name: str) -> bool` — convenience check

Update `src/config.py`:
- Replace `OPTIONAL_GROUPS` with reference to registry
- Add `ENABLED_INTEGRATIONS: set[str]` computed at startup
- Log enabled/disabled integrations using registry

### Phase 2: Tool Filtering

Update `src/assistant.py`:
- Import `ENABLED_INTEGRATIONS` from config
- Build `TOOLS` list dynamically: include only tools whose integration is enabled
- Build `TOOL_FUNCTIONS` dict to match filtered tools
- Add `_ALL_TOOLS` for reference (full list) and `TOOLS` (filtered)

Update `src/prompts/__init__.py`:
- Modify `load_tool_descriptions()` to accept `enabled_integrations` parameter
- Filter tool descriptions to only include enabled tools
- Modify `render_tool_descriptions()` accordingly

### Phase 3: System Prompt Filtering

Add YAML frontmatter to each system prompt file:
```yaml
---
requires: [core]
---
```
or
```yaml
---
requires: [notion, google_calendar]
---
```

Update `src/prompts/__init__.py`:
- `load_system_prompt()` accepts `enabled_integrations: set[str]`
- Parse YAML frontmatter from each .md file (manual parsing, no new dependency)
- Skip files whose `requires` list contains any integration not in `enabled_integrations`
- Strip frontmatter before concatenation
- Clear `@lru_cache` or make cache key include enabled integrations

Handle multi-integration prompt files (e.g., `03-daily-planner.md` references Notion, Calendar, and Outlook):
- Option A: Split into separate files per integration
- Option B: Tag with all required integrations, include if ANY are enabled
- **Decision**: Option B — tag with `requires_any: [notion, google_calendar, outlook]`. Include if at least one is enabled. The prompt text uses `{placeholder}` for names which are already handled.

### Phase 4: Health Endpoint Fix

Update `src/app.py` health endpoint:
- Change status logic: "degraded" only if a *configured* optional integration is failing
- Unconfigured integrations (`configured: false`) excluded from status calculation
- ~2-line change to existing logic

### Phase 5: Validation Script

Create `scripts/validate_setup.py`:
- Reads family.yaml (validates structure, required fields, timezone)
- Reads .env (via dotenv) — checks required vars, format patterns
- Cross-references integration registry for completeness
- Reports per-integration status
- Exit code 0/1
- See `contracts/validate-setup-cli.md` for full output spec

### Phase 6: Testing & Documentation

- Add `tests/test_integrations.py` — registry correctness, enable/disable logic
- Add `tests/test_validate_setup.py` — validation script coverage
- Update `tests/test_prompts.py` — prompt filtering tests
- Update ONBOARDING.md — add "Quick Start" section at top pointing to validation script
- Update CLAUDE.md — document integration registry

## Key Design Decisions

1. **Auto-detect from env vars, not explicit YAML declaration**: Operator doesn't need to declare `integrations: [notion]` in family.yaml. The registry checks env vars and determines what's enabled. Less configuration, less drift.

2. **Frontmatter parsing without new dependencies**: Simple regex-based YAML frontmatter parsing (~10 lines). No `python-frontmatter` package needed. Pattern: strip everything between first `---` and second `---` at file start.

3. **`requires_any` semantics for multi-integration prompts**: A prompt file tagged `requires_any: [notion, google_calendar]` is included if at least one of those integrations is enabled. This handles `03-daily-planner.md` which covers multiple integrations.

4. **Tools filtered at module load time**: `TOOLS` list built once at import. No per-request overhead. Changes require restart (which is the only way to change env vars anyway).

5. **Backward compatible**: Existing deployments with all integrations configured see zero behavior change. No new required config fields.
