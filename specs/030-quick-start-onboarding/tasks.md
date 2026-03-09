# Tasks: Quick Start Onboarding

**Input**: Design documents from `/specs/030-quick-start-onboarding/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup

**Purpose**: Branch creation and orientation

- [X] T001 Checkout feature branch `030-quick-start-onboarding` and verify existing spec artifacts

---

## Phase 2: Foundational — Integration Registry

**Purpose**: Centralized integration registry that maps integrations → env vars, tools, prompt tags. Drives all downstream filtering, health checks, and validation.

**⚠️ CRITICAL**: All user stories depend on this registry being complete.

- [X] T002 Create src/integrations.py with INTEGRATION_REGISTRY dict mapping each integration (core, whatsapp, ai_api, notion, google_calendar, outlook, ynab, anylist, recipes) to its display_name, required flag, env_vars list, tools list, and system_prompt_tag. "core" is a pseudo-integration that is always enabled (no env vars required) — it represents base tools (preferences, daily context) and prompt sections (identity, response rules, chores/nudges) available in every deployment. Include get_enabled_integrations(), get_tools_for_integrations(), and is_integration_enabled() functions. Reference data-model.md IntegrationGroup table for env var and tool mappings.
- [X] T003 Update src/config.py to import integration registry: add ENABLED_INTEGRATIONS set computed at startup via get_enabled_integrations(), replace or augment OPTIONAL_GROUPS with registry-based detection, log enabled/disabled integrations at module load time.

**Checkpoint**: Integration registry available — `get_enabled_integrations()` returns correct set based on env vars.

---

## Phase 3: User Story 2 — Bot Adapts to Configured Integrations (Priority: P1) 🎯 MVP

**Goal**: Tools and system prompt sections dynamically reflect only configured integrations. A minimal deployment (WhatsApp + AI) feels intentional, not broken.

**Independent Test**: Deploy with only ANTHROPIC_API_KEY and WHATSAPP_* vars set. Verify TOOLS list contains only core tools. Verify system prompt omits Notion/Calendar/YNAB sections. Send "what's on my calendar?" — bot explains calendar isn't set up (no tool call attempted).

### Implementation for User Story 2

- [X] T004 [P] [US2] Add YAML frontmatter `requires: [core]` to src/prompts/system/01-identity.md and src/prompts/system/02-response-rules.md
- [X] T005 [P] [US2] Add YAML frontmatter `requires_any: [notion, google_calendar, outlook]` to src/prompts/system/03-daily-planner.md
- [X] T006 [P] [US2] Add YAML frontmatter to remaining system prompt files: 04-grocery-recipes.md (requires_any: [anylist, recipes]), 05-chores-nudges.md (requires: [core]), 06-budget.md (requires: [ynab]), 07-calendar-reminders.md (requires: [google_calendar]), 08-meeting-notes.md (requires: [notion]), 09-forward-to-calendar.md (requires: [google_calendar]), 10-receipt-categorization.md (requires: [ynab]). Read each file first to confirm correct integration tag.
- [X] T007 [US2] Update src/prompts/__init__.py: add _parse_frontmatter() helper to extract `requires` and `requires_any` tags from markdown files. Modify load_system_prompt() to accept enabled_integrations parameter, filter out sections whose requirements aren't met, strip frontmatter before concatenation. Handle lru_cache invalidation (make cache key include frozenset of enabled integrations or remove cache).
- [X] T008 [US2] Update src/assistant.py: import ENABLED_INTEGRATIONS from config and get_tools_for_integrations from integrations. Build TOOLS list dynamically — include only tools whose integration is enabled. Build TOOL_FUNCTIONS dict to match filtered TOOLS. Keep _ALL_TOOLS reference for validation script use.
- [X] T009 [US2] Update src/prompts/__init__.py: modify load_tool_descriptions() to accept enabled_integrations parameter. Filter tool description sections to include only tools for enabled integrations. Update render_tool_descriptions() to pass enabled_integrations through.

**Checkpoint**: Minimal deployment loads only core tools and core prompt sections. Full deployment behavior unchanged.

---

## Phase 4: User Story 1 + User Story 3 — Setup & Validation (Priority: P1/P2)

**Goal**: One CLI command validates family.yaml + .env together, reports deployment readiness, catches errors before deploy.

**Independent Test**: Run `python scripts/validate_setup.py` with full config → "READY TO DEPLOY". Remove ANTHROPIC_API_KEY → exit code 1 with error. Set NOTION_TOKEN but remove NOTION_ACTION_ITEMS_DB → partial config warning. See contracts/validate-setup-cli.md for full output spec.

### Implementation for User Stories 1 & 3

- [X] T010 [US1] Create scripts/validate_setup.py with CLI arg parsing (--env-file, --config-file), family.yaml loading and validation (required fields: family name, bot name, timezone, partners), and .env loading via dotenv. Report section-by-section with checkmark/cross output per contracts/validate-setup-cli.md.
- [X] T011 [US3] Add required env var validation to scripts/validate_setup.py: check ANTHROPIC_API_KEY (format: sk-ant-*), WHATSAPP_* vars (4 required), N8N_WEBHOOK_SECRET, PARTNER phone numbers (digits only, 10-15 chars). Provide actionable error messages with fix hints per contracts/validate-setup-cli.md.
- [X] T012 [US1] [US3] Add integration group completeness checking to scripts/validate_setup.py: import INTEGRATION_REGISTRY, check each integration's env vars (all-or-nothing), report enabled/disabled/partial status, calculate tool count from registry, output summary with exit code 0 (ready) or 1 (errors).

**Checkpoint**: `python scripts/validate_setup.py` catches all config errors before deployment.

---

## Phase 5: User Story 4 — Health Endpoint Reflects Configured State (Priority: P2)

**Goal**: Health endpoint returns "healthy" for minimal deployments where optional integrations are intentionally unconfigured.

**Independent Test**: Deploy with WhatsApp + AI only. `curl /health` → `{"status": "healthy", ...}` with unconfigured integrations showing `"configured": false`. See contracts/health-endpoint.md for response examples.

### Implementation for User Story 4

- [X] T013 [US4] Update health status determination logic in src/app.py: import ENABLED_INTEGRATIONS or is_integration_enabled from registry. Change status calculation so unconfigured optional integrations (configured: false) are excluded — "degraded" only when a configured optional integration is failing. ~2-line change per contracts/health-endpoint.md.

**Checkpoint**: Minimal deployment health check returns "healthy" status.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Testing, documentation, and end-to-end validation

- [X] T014 [P] Create tests/test_integrations.py: test INTEGRATION_REGISTRY completeness (all integrations have required fields), test get_enabled_integrations() with mocked env vars (full config, minimal config, partial config), test get_tools_for_integrations() returns correct tool lists.
- [X] T015 [P] Create tests/test_validate_setup.py: test validation script with valid config, missing required vars, partial integration configs, invalid phone number format. Mock file reads and env.
- [X] T016 [P] Update tests/test_prompts.py: test frontmatter parsing (_parse_frontmatter helper), test load_system_prompt() with different enabled_integrations sets, verify core sections always included and integration sections filtered correctly.
- [X] T017 Update ONBOARDING.md: add "Quick Start (30 minutes)" section at top, reference validation script, document minimal vs full deployment paths.
- [X] T018 Update CLAUDE.md: document integration registry pattern (src/integrations.py), prompt frontmatter convention, validation script usage.
- [X] T019 Run quickstart.md validation scenarios end-to-end (validation script, tool filtering, health endpoint, system prompt filtering, full e2e).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US2 (Phase 3)**: Depends on Phase 2 — can run in parallel with Phases 4 and 5
- **US1+US3 (Phase 4)**: Depends on Phase 2 — can run in parallel with Phases 3 and 5
- **US4 (Phase 5)**: Depends on Phase 2 — can run in parallel with Phases 3 and 4
- **Polish (Phase 6)**: Depends on Phases 3, 4, and 5

### User Story Dependencies

- **US2 (P1)**: After Foundational — no dependencies on other stories
- **US1 + US3 (P1/P2)**: After Foundational — no dependencies on other stories
- **US4 (P2)**: After Foundational — no dependencies on other stories

### Within Each User Story

- US2: Frontmatter tagging (T004–T006) before prompt filtering logic (T007). Tool filtering (T008) and tool description filtering (T009) depend on T007 being complete for consistent behavior.
- US1+US3: Family config validation (T010) before env var checks (T011) before integration completeness (T012) — sequential build-up of the validation script.
- US4: Single task (T013), no internal dependencies.

### Parallel Opportunities

- T004, T005, T006 — different prompt files, no conflicts
- T014, T015, T016 — different test files, no conflicts
- After Phase 2 completes: Phases 3, 4, and 5 can all start simultaneously

---

## Parallel Example: User Story 2

```bash
# Launch all frontmatter tasks together (different files):
Task: "Add frontmatter to 01-identity.md, 02-response-rules.md" (T004)
Task: "Add frontmatter to 03-daily-planner.md" (T005)
Task: "Add frontmatter to remaining prompt files" (T006)

# Then sequential prompt/tool filtering:
Task: "Update load_system_prompt() with frontmatter parsing" (T007)
Task: "Build TOOLS list dynamically in assistant.py" (T008)
Task: "Filter tool descriptions by enabled integrations" (T009)
```

---

## Implementation Strategy

### MVP First (US2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Integration Registry (CRITICAL — blocks all stories)
3. Complete Phase 3: US2 — Bot adapts to configured integrations
4. **STOP and VALIDATE**: Deploy with minimal config, verify tools/prompts filtered
5. Deploy — minimal deployment feels intentional, not broken

### Incremental Delivery

1. Setup + Foundational → Integration registry ready
2. Add US2 → Filtered tools and prompts → Deploy (MVP!)
3. Add US1+US3 → Validation script → Operators validate before deploy
4. Add US4 → Health endpoint fix → "healthy" for minimal deployments
5. Polish → Tests, docs, end-to-end validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] labels map tasks to user stories for traceability
- Total: 19 tasks across 6 phases
- The integration registry (Phase 2) is the single foundation that enables everything else
- US2 is the true MVP — a minimal deployment that doesn't reference unavailable features
- The validation script (US1+US3) and health fix (US4) add operator quality-of-life
