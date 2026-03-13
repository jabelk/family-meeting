# Tasks: Port AI Failover & Resilience to Downstream Repos

**Input**: Design documents from `/specs/035-port-failover-downstream/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. Two repos are involved:
- **SCC**: `/Users/jabelk/dev/projects/client-scc-tom-construction/`
- **Template**: `/Users/jabelk/dev/projects/claude-speckit-template/`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Add dependencies and configuration for backup AI provider in both repos

- [X] T001 Add `openai` SDK dependency to SCC project in `/Users/jabelk/dev/projects/client-scc-tom-construction/pyproject.toml`
- [X] T002 Add `OPENAI_API_KEY` and `OPENAI_MODEL` config vars to `/Users/jabelk/dev/projects/client-scc-tom-construction/src/config.py`
- [X] T003 [P] Add `OPENAI_API_KEY` and `OPENAI_MODEL` to SCC `.env.example` in `/Users/jabelk/dev/projects/client-scc-tom-construction/.env.example`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the core `ai_provider.py` module with format converters and failover logic — this MUST be complete before any user story integration work

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create `AllProvidersDownError` exception and module constants (PRIMARY_TIMEOUT=45, BACKUP_TIMEOUT=30, model names) in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`
- [X] T005 Implement `_convert_tool_for_openai(tool_def)` converter (Anthropic `input_schema` → OpenAI `parameters` wrapped in function object) in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`
- [X] T006 Implement `_convert_tool_choice_for_openai(tool_choice)` converter (forced tool mapping: `{"type": "tool", "name": "X"}` → `{"type": "function", "function": {"name": "X"}}`) in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`
- [X] T007 Implement `_convert_image_for_openai(image_block)` converter (Anthropic base64 source → OpenAI data URI format) in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`
- [X] T008 Implement `_convert_messages_for_openai(system, messages)` converter (full message format conversion including system-as-first-message, tool_use/tool_result blocks) in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`

**Checkpoint**: Foundation ready — all format converters tested, failover logic available for user story integration

---

## Phase 3: User Story 1 — SCC Backup AI Provider Failover (Priority: P1)

**Goal**: When Claude is unavailable (500/529/timeout), SCC automatically switches to OpenAI GPT-4o-mini for all 5 AI functions

**Independent Test**: Simulate Claude API failure, verify intent classification, receipt parsing, and caption generation all respond via backup provider

### Tests for User Story 1

- [X] T009 [P] [US1] Write unit tests for format converters (`_convert_tool_for_openai`, `_convert_tool_choice_for_openai`, `_convert_image_for_openai`, `_convert_messages_for_openai`) in `/Users/jabelk/dev/projects/client-scc-tom-construction/tests/unit/test_ai_provider.py`
- [X] T010 [P] [US1] Write unit tests for failover behavior (Claude 529 → OpenAI, Claude timeout → OpenAI, both-down → AllProvidersDownError) in `/Users/jabelk/dev/projects/client-scc-tom-construction/tests/unit/test_ai_provider.py`
- [X] T011 [P] [US1] Write unit test for primary path (Claude succeeds, no failover triggered) in `/Users/jabelk/dev/projects/client-scc-tom-construction/tests/unit/test_ai_provider.py`

### Implementation for User Story 1

- [X] T012 [US1] Implement `classify_intent(message, conversation_history, active_jobs)` with try-Claude/catch/try-OpenAI/catch/raise pattern in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`
- [X] T013 [P] [US1] Implement `parse_receipt(image_data, media_type)` with vision failover (image format conversion) in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`
- [X] T014 [P] [US1] Implement `generate_social_caption(photo_data, media_type, context)` with vision failover in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`
- [X] T015 [P] [US1] Implement `generate_paired_caption(before_data, after_data, media_type, context)` with dual-image vision failover in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`
- [X] T016 [P] [US1] Implement `suggest_category(vendor, line_items, available_categories)` with text-only failover in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`
- [X] T017 [US1] Refactor `claude_svc.py` functions to delegate to `ai_provider.py` (thin wrappers preserving existing signatures) in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/claude_svc.py`
- [X] T018 [US1] Update `router_svc.py` to catch `AllProvidersDownError` and return `_build_fallback_message()` in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/router_svc.py`
- [X] T019 [US1] Add backup provider health check to `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/health_svc.py`

**Checkpoint**: SCC failover fully functional — Claude outage triggers automatic OpenAI backup for all 5 AI functions

---

## Phase 4: User Story 2 — Template Repo Resilience Scaffolding (Priority: P2)

**Goal**: New projects scaffolded from the template include ready-to-customize AI failover patterns and resilience prompts

**Independent Test**: Verify template files exist with `{{PLACEHOLDER}}` patterns, customization comments, and clear instructions

### Implementation for User Story 2

- [X] T020 [P] [US2] Create `ai_provider.py` with failover logic, all converters, BACKUP_TOOLS subset, and customization comments in `/Users/jabelk/dev/projects/family-assistant/src/ai_provider.py`
- [X] T021 [P] [US2] Create resilience prompt with `{bot_name}` / `{partner1_name}` placeholders in `/Users/jabelk/dev/projects/family-assistant/src/prompts/system/11-resilience.md`
- [X] T022 [US2] Add resilience architecture section to CLAUDE.md describing the ai_provider pattern and customization steps in `/Users/jabelk/dev/projects/family-assistant/CLAUDE.md`

**Checkpoint**: Template repo includes resilience scaffolding — new projects start with failover patterns built in

---

## Phase 5: User Story 3 — SCC Tool Result Auditing & Error Surfacing (Priority: P2)

**Goal**: When tool calls fail (QuickBooks, Twilio, Ayrshare), the bot detects the error and informs Tom explicitly

**Independent Test**: Simulate a QuickBooks API failure during expense creation, verify the bot tells Tom the expense was not recorded

### Implementation for User Story 3

- [X] T023 [US3] Review existing error handling patterns in SCC services (QuickBooks, Twilio, Ayrshare) to identify where errors are silently swallowed in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/`
- [X] T024 [US3] Add `audit_tool_result()` helper that inspects tool call results for error indicators and prepends warning context in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`
- [X] T025 [US3] Integrate tool result auditing into the ai_provider response pipeline so errors in service results are detected and surfaced in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/services/ai_provider.py`

**Checkpoint**: Tool failures are detected and surfaced to Tom with specific error descriptions

---

## Phase 6: User Story 4 — SCC Resilience Prompt Rules (Priority: P3)

**Goal**: SCC system prompts include rules for error transparency — Claude mentions failures and provides actionable guidance

**Independent Test**: Verify system prompts include error reporting rules, test that Claude references specific error details on tool failure

### Implementation for User Story 4

- [X] T026 [US4] Create resilience prompt rules (error transparency, diagnostic specificity, never present failures as successful) in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/prompts/system/05-resilience.md`
- [X] T027 [US4] Verify prompt loading includes the new resilience section (check prompt concatenation order and loading in SCC prompt system) in `/Users/jabelk/dev/projects/client-scc-tom-construction/src/prompts/`

**Checkpoint**: SCC bot follows prompt-level rules for error reporting and diagnostic transparency

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Regression testing, lint, and deployment validation across both repos

- [X] T028 Run full SCC test suite (`uv run pytest tests/ -v`) and verify zero regressions in `/Users/jabelk/dev/projects/client-scc-tom-construction/`
- [X] T029 [P] Run linter and formatter (`uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/`) in `/Users/jabelk/dev/projects/client-scc-tom-construction/`
- [X] T030 Run quickstart.md validation scenarios (Scenarios 1-9) for SCC repo
- [X] T031 Verify template repo files are well-structured with proper placeholder patterns in `/Users/jabelk/dev/projects/family-assistant/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T002 for openai SDK and config)
- **User Story 1 (Phase 3)**: Depends on Foundational (T004-T008 for converters and base module)
- **User Story 2 (Phase 4)**: Depends on Setup only — can run in parallel with US1 (different repo)
- **User Story 3 (Phase 5)**: Depends on US1 completion (ai_provider.py must exist for audit integration)
- **User Story 4 (Phase 6)**: No dependency on other stories — can run in parallel with US1/US3
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational phase — core SCC failover
- **US2 (P2)**: Independent of US1 — different repo (template), can start after Setup
- **US3 (P2)**: Depends on US1 — tool auditing integrates into ai_provider.py
- **US4 (P3)**: Independent — prompt file only, can run in parallel with US1

### Within Each User Story

- Tests written before implementation (US1)
- Format converters before public functions (Foundational → US1)
- ai_provider.py before claude_svc.py refactor (T012-T016 before T017)
- claude_svc.py refactor before router_svc.py integration (T017 before T018)

### Parallel Opportunities

**Cross-repo parallelism**: US2 (template repo) can run entirely in parallel with US1/US3/US4 (SCC repo)

**Within US1**: T013, T014, T015, T016 can run in parallel (independent function implementations in same file)

**Within US2**: T020, T021 can run in parallel (different files in template repo)

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "Unit tests for format converters in tests/unit/test_ai_provider.py"
Task: "Unit tests for failover behavior in tests/unit/test_ai_provider.py"
Task: "Unit test for primary path in tests/unit/test_ai_provider.py"

# Launch vision functions together (after classify_intent baseline):
Task: "parse_receipt with vision failover in src/services/ai_provider.py"
Task: "generate_social_caption with vision failover in src/services/ai_provider.py"
Task: "generate_paired_caption with dual-image vision in src/services/ai_provider.py"
Task: "suggest_category with text-only failover in src/services/ai_provider.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (add openai SDK + config)
2. Complete Phase 2: Foundational (format converters + AllProvidersDownError)
3. Complete Phase 3: User Story 1 (5 failover functions + integration)
4. **STOP and VALIDATE**: Run test suite, test failover manually
5. Deploy if ready — SCC has full failover capability

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (SCC Failover) → Test independently → Deploy (MVP!)
3. US2 (Template Scaffolding) → Verify file structure (can run in parallel with US1)
4. US3 (Tool Auditing) → Test with simulated failures → Deploy
5. US4 (Prompt Rules) → Verify prompt loading → Deploy
6. Polish → Full regression + lint → Final deploy

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- SCC repo uses `uv` for package management and `pytest` for testing
- Template repo has no test suite — validation is file structure inspection
- Family-meeting `src/ai_provider.py` is the reference implementation for porting
- SCC has 5 distinct AI functions (vs family-meeting's single `create_message()` agentic loop)
- All SCC format converters must handle forced tool_choice and vision image blocks
