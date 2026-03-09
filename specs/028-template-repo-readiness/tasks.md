# Tasks: Template Repo Readiness & Service Packaging

**Input**: Design documents from `/specs/028-template-repo-readiness/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/health-endpoint.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Add PyYAML dependency and create config directory structure

- [X] T001 Add `pyyaml>=6.0` to requirements.txt (or pyproject.toml if used)
- [X] T002 Create config/ directory and config/family.yaml populated with current Jason/Erin family values per data-model.md example in specs/028-template-repo-readiness/data-model.md
- [X] T003 Add config/family.yaml.example as a blank template with comments explaining each field (copy structure from data-model.md, replace values with placeholders and inline comments)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core config loader that MUST be complete before any user story can modify files to use it

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create src/family_config.py — YAML loader with validation (required fields: bot.name, family.name, family.timezone, family.partners with at least 1 entry). Must validate timezone via zoneinfo.ZoneInfo. Must compute derived placeholder dict (bot_name, partner1_name, partner2_name, children_summary, grocery_store, etc.) per data-model.md "Derived Values" table. Export load_family_config() returning the placeholder dict. Cache with @lru_cache.
- [X] T005 Modify src/config.py — import and call load_family_config() during startup validation. If config/family.yaml is missing, log a warning and use a default config (backward-compatible with current hardcoded values). Add FAMILY_CONFIG module-level variable accessible to other modules.

**Checkpoint**: Family config loads at startup, validated, accessible from src/config.py

---

## Phase 3: User Story 1 — Externalize Family Identity & Configuration (Priority: P1)

**Goal**: Replace all hardcoded family references with config-driven placeholders so the repo works for any family without code changes.

**Independent Test**: Fill config/family.yaml with a different family's details, start the app, and verify system prompt + tool outputs reflect the new family with zero hardcoded names.

### System Prompt Externalization

- [X] T006 [US1] Modify src/prompts/__init__.py — add render_system_prompt(family_config: dict) function that calls load_system_prompt() then applies .format_map() with family_config dict (use collections.defaultdict to pass through unknown keys). Add render_tool_descriptions(family_config: dict) that does the same for tool descriptions. Clear lru_cache considerations: since prompts are cached as templates, rendering happens each call with the config dict.
- [X] T007 [US1] Convert src/prompts/system/01-identity.md — replace "Mom Bot" with {bot_name}, "Jason" with {partner1_name}, "Erin" with {partner2_name}, "Vienna (daughter, age 5)" with {children_summary}, "works from home at Cisco" with {partner1_work}, "stays at home with the kids" with {partner2_work}. Escape any literal curly braces as {{ }}.
- [X] T008 [P] [US1] Convert src/prompts/system/02-response-rules.md — replace hardcoded "Jason", "Erin" references with {partner1_name}, {partner2_name}. Escape literal curly braces.
- [X] T009 [P] [US1] Convert src/prompts/system/03-daily-planner.md — replace "Zoey" with {child2_name} or appropriate child reference, replace "Jason" with {partner1_name}. Escape literal curly braces.
- [X] T010 [P] [US1] Convert src/prompts/system/04-grocery-recipes.md — replace "Downshiftology" with {recipe_source}. Escape literal curly braces.
- [X] T011 [P] [US1] Convert src/prompts/system/05-chores-nudges.md — replace "Erin" with {partner2_name}. Escape literal curly braces.
- [X] T012 [P] [US1] Convert src/prompts/system/07-calendar-reminders.md — replace hardcoded event mappings ("BSF" = Erin, "Gymnastics" = Vienna, etc.) with {calendar_event_mappings} placeholder or parameterized text using partner/child names. Escape literal curly braces.
- [X] T013 [P] [US1] Convert src/prompts/system/08-advanced.md — replace any hardcoded name references with family config placeholders. Escape literal curly braces.

### Tool Description Externalization

- [X] T014 [P] [US1] Convert src/prompts/tools/anylist.md — replace "Whole Foods" with {grocery_store}, "Erin" with {partner2_name}. Escape literal curly braces.
- [X] T015 [P] [US1] Convert src/prompts/tools/calendar.md — replace "Jason's personal, Erin's personal" with {partner1_name}/{partner2_name}, replace "Outlook/Cisco" with generic work calendar reference. Escape literal curly braces.
- [X] T016 [P] [US1] Convert src/prompts/tools/chores.md — replace "Erin" with {partner2_name}. Escape literal curly braces.
- [X] T017 [P] [US1] Convert src/prompts/tools/context.md — replace "Zoey" with {child2_name} or {youngest_child_name}. Escape literal curly braces.
- [X] T018 [P] [US1] Convert src/prompts/tools/email.md — replace "Erin" with {partner2_name}. Escape literal curly braces.
- [X] T019 [P] [US1] Convert src/prompts/tools/notion.md — replace "Erin's personal backlog" with {partner2_name}-based reference. Escape literal curly braces.
- [X] T020 [P] [US1] Convert src/prompts/tools/preferences.md — replace "Erin" with {partner2_name}. Escape literal curly braces.

### Template Externalization

- [X] T021 [P] [US1] Convert src/prompts/templates/meal_plan_generation.md — replace "Vienna 5, Zoey 3" with {children_summary}, replace activity references with generic or config-driven text. Escape literal curly braces (CRITICAL: this file likely uses {placeholder} syntax already for render_template — must not break existing placeholders).
- [X] T022 [P] [US1] Convert src/prompts/templates/conflict_detection.md — replace "Sandy/grandma" with {caregiver_names} or config-driven reference. Escape literal curly braces (same caution as T021 about existing placeholders).

### Python Source Externalization

- [X] T023 [US1] Modify src/assistant.py — import family config from src/config.py. Replace hardcoded welcome message (line ~1740 "Welcome to Mom Bot!") with config-driven message using bot_name. Use render_system_prompt(family_config) and render_tool_descriptions(family_config) instead of load_system_prompt() and load_tool_descriptions(). Replace hardcoded "Jason"/"Erin" in tool parameter descriptions (line ~95) with config values.
- [X] T024 [US1] Modify src/context.py — import family config. Replace hardcoded CHILDCARE_KEYWORDS set (lines ~27-37) with config-driven keywords from family_config. Replace hardcoded person labels "Jason's events", "Erin's events", "Zoey:" (lines ~189-218) with partner/child names from config. Replace Sandy/caregiver mapping logic (lines ~290-334) with config-driven caregiver_mappings.
- [X] T025 [US1] Modify src/config.py — replace hardcoded PHONE_TO_NAME mapping (lines ~98-100 "Jason"/"Erin") with config-driven names from family_config partners list.
- [X] T026 [P] [US1] Modify src/scheduler.py — replace hardcoded "Erin's Google Calendar" (line ~324-325) and "Zoey" (line ~392) references with config-driven values.
- [X] T027 [P] [US1] Modify src/mcp_server.py — replace hardcoded "Jason personal, Erin personal, Family shared" (lines ~39-78), "Zoey" (line ~209), "Whole Foods" (line ~266) with config-driven values.
- [X] T028 [P] [US1] Modify src/tools/anylist_bridge.py — replace hardcoded "Whole Foods" (line ~66) with grocery_store from family config.
- [X] T029 [P] [US1] Modify src/tools/recipes.py — replace hardcoded "Whole Foods" default (line ~391) with grocery_store from family config.
- [X] T030 [P] [US1] Modify src/tools/proactive.py — replace hardcoded "Whole Foods" defaults (lines ~81, 240, 257) with grocery_store from family config.

**Checkpoint**: System prompt, tool descriptions, and Python source all use config-driven values. Changing config/family.yaml changes all outputs.

---

## Phase 4: User Story 2 — Streamlined WhatsApp Number Setup (Priority: P2)

**Goal**: Document the WhatsApp number provisioning process so new clients can be onboarded within one business day.

**Independent Test**: Follow the guide to provision a test WhatsApp number and verify webhook connectivity.

- [X] T031 [P] [US2] Create docs/WHATSAPP_SETUP.md — step-by-step guide covering: prerequisites (Facebook Business Manager, business verification), creating WhatsApp Business Account, adding/buying phone number, generating permanent access token, configuring webhook URL + verify token, setting webhook subscriptions (messages, message_templates), testing with a test message, troubleshooting section (verification rejected, webhook not receiving, rate limits). Reference Meta's Direct Cloud API documentation.
- [X] T032 [P] [US2] Create docs/ONBOARDING.md — end-to-end client onboarding guide covering: initial client intake (what info to collect), config/family.yaml setup with client's details, .env setup with client credentials, Railway deployment steps, WhatsApp number provisioning (link to WHATSAPP_SETUP.md), integration setup (Notion/Calendar/YNAB — each optional), health check verification, sending first test message, handoff to client. Include estimated time per step.

**Checkpoint**: An operator can follow the guides to provision a new client from scratch.

---

## Phase 5: User Story 3 — Service Pricing & Packaging (Priority: P3)

**Goal**: Define pricing tiers and create service agreement template for client engagements.

**Independent Test**: Present pricing doc to prospective clients and validate they can identify the right tier.

- [X] T033 [P] [US3] Create docs/PRICING.md — define two tiers: Family tier ($99/mo + $499 setup fee, includes WhatsApp assistant, calendar management, grocery lists, budget tracking, white-glove onboarding) and Corporate tier (custom pricing starting $149/mo per family, volume discounts, dedicated support, custom integrations). Include per-client cost breakdown ($12-28/mo infrastructure), competitive positioning vs human VAs ($380-3K/mo) and DIY tools ($19-25/mo), what's included in each tier, add-on integrations pricing.
- [X] T034 [P] [US3] Create docs/SERVICE_AGREEMENT.md — template service agreement covering: service description ("family management assistant"), data privacy (single-tenant isolation, per-incident consent for operator access per FR-016), data ownership (client owns all data), service availability expectations, payment terms, cancellation and data export/deletion, Meta WhatsApp policy compliance (positioned as family management service per FR-012), operator responsibilities, client responsibilities.

**Checkpoint**: Pricing and legal framework ready for client conversations.

---

## Phase 6: User Story 4 — One-Click Deployment & Health Validation (Priority: P4)

**Goal**: Enhanced health check that reports per-integration status, and startup validation that fails fast on missing required config.

**Independent Test**: Deploy with partial config and verify health endpoint reports correct integration statuses.

- [X] T035 [US4] Modify src/app.py — replace the simple health check endpoint (lines ~291-294) with enhanced version per contracts/health-endpoint.md. Check each integration: whatsapp (env vars exist), ai_api (ANTHROPIC_API_KEY exists), notion (attempt notion.users.me() with 5s timeout), google_calendar (attempt calendarList.list with 5s timeout), ynab (check env var exists), anylist (HTTP GET to sidecar /health with 5s timeout), outlook (check ICS URL env var exists). Return status: "healthy" (all required pass + all configured optional pass), "degraded" (required pass but optional fail), "unhealthy" (required fail → HTTP 503). Include family name, bot name, uptime_seconds in response.
- [X] T036 [US4] Modify src/config.py — update startup validation to distinguish between required vars (ANTHROPIC_API_KEY, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET, N8N_WEBHOOK_SECRET) and optional groups. Ensure clear error messages list exactly which required vars are missing. Log which optional integrations are enabled vs disabled.

**Checkpoint**: Health endpoint reports per-integration status. Missing required config prevents startup with clear error.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Linting, testing, documentation cleanup

- [X] T037 Run ruff check and ruff format on all modified Python files (src/family_config.py, src/config.py, src/app.py, src/assistant.py, src/context.py, src/scheduler.py, src/mcp_server.py, src/tools/anylist_bridge.py, src/tools/recipes.py, src/tools/proactive.py, src/prompts/__init__.py)
- [X] T038 Update tests/test_prompts.py — adjust test_load_system_prompt_returns_nonempty to account for placeholder syntax in prompts (may need to test rendered prompt instead of raw). Verify tool description count still matches after prompt changes. Add test for render_system_prompt producing valid output with a test family config.
- [X] T039 Create tests/test_family_config.py — test load_family_config() with valid config, test validation errors for missing required fields (bot.name, family.name, timezone, partners), test derived values computation (children_summary, placeholder dict), test default config fallback when family.yaml is missing.
- [X] T040 Run pytest tests/ to verify all tests pass
- [X] T041 Update .gitignore — ensure config/family.yaml is NOT gitignored (it's per-instance config), but add a comment noting it contains family-specific data
- [X] T042 Run quickstart.md validation scenarios (config loading, system prompt rendering, health check, no-kids config, backward compatibility)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T003) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (T004-T005). Largest phase — 25 tasks.
- **US2 (Phase 4)**: No code dependencies — documentation only. Can start after Foundational or in parallel with US1.
- **US3 (Phase 5)**: No code dependencies — documentation only. Can run in parallel with US1/US2.
- **US4 (Phase 6)**: Depends on Foundational (T004-T005) for family config access in health check. Can run in parallel with US1.
- **Polish (Phase 7)**: Depends on all user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 only. Core feature — most tasks.
- **US2 (P2)**: Independent — documentation only, no code dependencies.
- **US3 (P3)**: Independent — documentation only, no code dependencies.
- **US4 (P4)**: Depends on Phase 2 (family_config.py). Can run in parallel with US1.

### Within US1 (Phase 3)

- T006 (render functions) MUST complete before T007-T022 (prompt conversion) and T023 (assistant.py)
- T007 (01-identity.md) should complete first — it's the most complex prompt conversion
- T008-T022 are all [P] — can run in parallel after T006
- T023-T030 (Python source) depend on T006 but are [P] with each other

### Parallel Opportunities

```text
# After T006 completes, ALL of these can run in parallel:
T008, T009, T010, T011, T012, T013  (system prompts)
T014, T015, T016, T017, T018, T019, T020  (tool descriptions)
T021, T022  (templates)
T026, T027, T028, T029, T030  (Python tools)

# US2 + US3 tasks are all [P] with each other:
T031, T032, T033, T034  (all documentation, no code deps)

# US4 can run in parallel with US1 after Phase 2:
T035, T036
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T005)
3. Complete Phase 3: US1 — config externalization (T006-T030)
4. **STOP and VALIDATE**: Change family.yaml to a different family, verify system prompt renders correctly
5. This alone makes the repo reusable for other families

### Incremental Delivery

1. Setup + Foundational → Config loader ready
2. US1 → Repo is a template (MVP!)
3. US2 + US3 → Docs for onboarding and pricing (can be done in parallel)
4. US4 → Enhanced health check for operator visibility
5. Polish → Tests, lint, quickstart validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- US2 and US3 are documentation-only — no Python code changes
- The largest risk is in T007-T022: converting prompt files to use placeholders without breaking existing {placeholder} syntax in template files (T021, T022 need extra care)
- Backward compatibility: config/family.yaml populated with current Jason/Erin values ensures existing instance works unchanged
