# Tasks: Feature Discovery & Onboarding

**Input**: Design documents from `/specs/006-feature-discovery/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/help-tool.md

**Tests**: No automated tests requested. Validation via manual WhatsApp + curl testing per quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. US4 (Usage Tracking & Smart Suggestions) is a new addition incorporating the user's request to track feature usage with counters and suggest underused features.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new module and define shared constants used by all user stories

- [x] T001 Create `src/tools/discovery.py` with module docstring, imports (json, os, random, logging, pathlib), and empty section placeholders for categories, tips, counters
- [x] T002 Define HELP_CATEGORIES constant in `src/tools/discovery.py` — list of 6 category dicts (icon, name, capabilities list, static_examples list, personalize_from tool name) per data-model.md
- [x] T003 [P] Define TOOL_TO_CATEGORY mapping in `src/tools/discovery.py` — dict mapping all ~40 tool names to one of 6 category keys (recipes, budget, calendar, groceries, chores, family_management)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infrastructure that must be complete before user story work begins

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `data/` directory with `.gitkeep` and add `data/*.json` to `.gitignore`
- [x] T005 Add Docker volume mount `- ./data:/app/data` to fastapi service in `docker-compose.yml`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Help Menu with Personalized Examples (Priority: P1) 🎯 MVP

**Goal**: When Erin says "help" or "what can you do?", the bot responds with a categorized list of all capabilities using personalized examples from real family data.

**Independent Test**: Send "what can you do?" to the bot → verify response has 6 categories with icons, bold headers, and example phrases. Copy one example phrase and send it → verify it works.

### Implementation for User Story 1

- [x] T006 [US1] Implement `get_help()` function in `src/tools/discovery.py` — iterate HELP_CATEGORIES, try to call personalize_from tools (list_cookbooks, get_staple_items, get_budget_summary) for live examples, fall back to static_examples on failure, return formatted WhatsApp-ready text per contracts/help-tool.md
- [x] T007 [US1] Register `get_help` tool definition in TOOLS array in `src/assistant.py` — no parameters, description: "Generate a personalized help menu showing all bot capabilities"
- [x] T008 [US1] Add `get_help` entry to TOOL_FUNCTIONS dict in `src/assistant.py` — lambda calling discovery.get_help()
- [x] T009 [US1] Add import for `discovery` module in `src/assistant.py` imports section
- [x] T010 [US1] Add system prompt rules for help trigger detection in `src/assistant.py` — rule instructing Claude to call get_help when user says "help", "what can you do?", "what are your features?", "show me what you can do", or similar; rule that help response must not clear any in-progress state (e.g., _last_search_results)

**Checkpoint**: Help menu is fully functional and testable independently. Validate with quickstart.md Tests 1-3.

---

## Phase 4: User Story 2 — "Did You Know?" Tips (Priority: P2)

**Goal**: The bot appends contextual tips about related features after normal responses (e.g., recipe search tip after meal plan).

**Independent Test**: Ask "what's for dinner this week?" → verify a contextual tip is appended about a related feature (e.g., grocery push). Send another message → verify no additional tip.

### Implementation for User Story 2

- [x] T011 [P] [US2] Define TIP_DEFINITIONS list in `src/tools/discovery.py` — 10 tip dicts (id, trigger_tools list, text, related_category) per data-model.md tip definitions table
- [x] T012 [US2] Implement `get_contextual_tip(tools_used: list[str]) -> str | None` in `src/tools/discovery.py` — match tools_used against trigger_tools in TIP_DEFINITIONS, return random matching tip text or None if no match
- [x] T013 [US2] Add system prompt rules for tip appending in `src/assistant.py` — instruct Claude to call get_contextual_tip after tool-using responses, append result as "💡 *Did you know?* {tip}" if non-None, max 1 tip per response, only for tool-using contexts (meal plan, recipe search, budget, chores, calendar)

**Checkpoint**: Tips appear after relevant responses. Validate with quickstart.md Test 4.

---

## Phase 5: User Story 3 — First-Time Welcome Message (Priority: P3)

**Goal**: First-time users receive a brief welcome message introducing Mom Bot and inviting them to say "help".

**Independent Test**: Restart the container, send a message from Erin's phone → verify welcome is prepended. Send another message → verify no welcome.

### Implementation for User Story 3

- [x] T014 [US3] Add module-level `_welcomed_phones: set[str] = set()` in `src/assistant.py`
- [x] T015 [US3] Add welcome check in `handle_message()` in `src/assistant.py` — before calling Claude, check if phone is in _welcomed_phones; if not, add phone to set and prepend a brief welcome instruction to the system message ("This is the user's first message. Prepend a brief welcome: ..."); keep welcome under 2 lines

**Checkpoint**: First-time welcome works. Validate with quickstart.md Test 5.

---

## Phase 6: User Story 4 — Usage Tracking & Smart Suggestions (Priority: P2)

**Goal**: Track which feature categories each user interacts with via tool call counters, and use this data to prioritize suggestions for underused/unused features in tips and help responses.

**Independent Test**: Use several features (recipes, budget, calendar) but not groceries or chores. Ask "help" → verify underused categories are highlighted. Trigger a tip context → verify tip prioritizes an underused category.

### Implementation for User Story 4

- [x] T016 [P] [US4] Implement usage counter persistence in `src/tools/discovery.py` — module-level `_usage_counters: dict[str, dict[str, int]]` (phone → category → count), `_load_counters()` reads from `/app/data/usage_counters.json` (or `data/usage_counters.json` locally), `_save_counters()` writes atomically, auto-load on module import
- [x] T017 [US4] Implement `record_usage(phone: str, tool_name: str)` in `src/tools/discovery.py` — look up TOOL_TO_CATEGORY for the tool, increment counter, call _save_counters()
- [x] T018 [US4] Implement `get_underused_categories(phone: str) -> list[str]` in `src/tools/discovery.py` — return category names with 0 usage count, sorted by help menu order
- [x] T019 [US4] Integrate usage recording into tool loop in `src/assistant.py` `handle_message()` — after each successful tool call, call `discovery.record_usage(phone, tool_name)`
- [x] T020 [US4] Enhance `get_contextual_tip()` in `src/tools/discovery.py` — accept optional `phone` parameter, when provided use get_underused_categories to prefer tips whose related_category the user hasn't tried yet; fall back to random if all categories used
- [x] T021 [US4] Enhance `get_help()` in `src/tools/discovery.py` — accept optional `phone` parameter, when provided append a "✨ *Haven't tried yet:*" section at the bottom listing unused categories with one example each; skip section if all categories have been used
- [x] T022 [US4] Update `get_help` tool definition in `src/assistant.py` to pass phone number to discovery.get_help(phone=phone) and get_contextual_tip(tools_used, phone=phone)

**Checkpoint**: Usage counters persist across restarts. Tips and help responses prioritize underused features. Validate manually.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Refinements affecting multiple user stories, deploy, and full validation

- [x] T023 Review and refine system prompt tip/help phrasing for natural tone in `src/assistant.py`
- [x] T024 Deploy to NUC via `./scripts/nuc.sh deploy` and run quickstart.md validation (all 6 test scenarios)
- [x] T025 Verify usage counters persist across container restart on NUC

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Can run in parallel with Phase 1 (different files)
- **US1 (Phase 3)**: Depends on Phase 1 (T001-T003) — needs HELP_CATEGORIES and TOOL_TO_CATEGORY
- **US2 (Phase 4)**: Depends on Phase 1 (T001-T003) — needs TOOL_TO_CATEGORY for tip matching
- **US3 (Phase 5)**: No dependency on other stories — only touches assistant.py
- **US4 (Phase 6)**: Depends on Phases 1-4 (needs categories, tool mapping, tip system, and help function to enhance)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 1 — no dependencies on other stories
- **US2 (P2)**: Can start after Phase 1 — independent of US1 (uses same constants)
- **US3 (P3)**: Can start after Phase 1 — fully independent (only touches assistant.py)
- **US4 (P2)**: Depends on US1 and US2 — enhances existing get_help() and get_contextual_tip() functions

### Within Each User Story

- Constants/definitions before functions
- Functions before registration in assistant.py
- Registration before system prompt rules
- assistant.py changes are sequential (same file)

### Parallel Opportunities

- T003 can run in parallel with T001-T002 (T003 is a constant definition, no function deps)
- T004 and T005 can run in parallel with Phase 1 (different files: .gitignore, docker-compose.yml)
- T011 can run in parallel with US1 tasks (different section of discovery.py, but same file — serialize if needed)
- T014-T015 (US3) can run in parallel with US1 or US2 (different file: assistant.py welcome logic vs discovery.py)
- T016 can run in parallel with US2 implementation (different section of discovery.py)

---

## Parallel Example: Phase 1 + Phase 2

```bash
# These can all run in parallel (different files):
Task: "T001 Create src/tools/discovery.py with structure"
Task: "T004 Add data/ directory and .gitignore entry"
Task: "T005 Add Docker volume mount in docker-compose.yml"

# Then after T001, these can run in parallel:
Task: "T002 Define HELP_CATEGORIES in src/tools/discovery.py"
Task: "T003 Define TOOL_TO_CATEGORY in src/tools/discovery.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 3: User Story 1 (T006-T010)
3. **STOP and VALIDATE**: Send "help" to bot, verify categorized response with examples
4. Deploy if ready — Erin can start discovering features immediately

### Incremental Delivery

1. Setup + US1 → Help menu works → Deploy (MVP!)
2. Add US2 → Tips appear after relevant responses → Deploy
3. Add US3 → Welcome message for first contact → Deploy
4. Add US4 → Usage tracking surfaces underused features → Deploy
5. Each story adds value without breaking previous stories

### Full Build Order (Sequential)

1. T001 → T002 + T003 (parallel) → T004 + T005 (parallel with T002/T003)
2. T006 → T007 → T008 → T009 → T010
3. T011 → T012 → T013
4. T014 → T015
5. T016 → T017 → T018 → T019 → T020 → T021 → T022
6. T023 → T024 → T025

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable (except US4 which enhances US1+US2)
- Usage counter file path: `data/usage_counters.json` (local) or `/app/data/usage_counters.json` (Docker)
- The spec lists "Usage analytics or feature adoption tracking" as out of scope — US4 is intentionally scoped to simple counters for smart suggestions, not analytics dashboards
- Commit after each phase or logical group
- Stop at any checkpoint to validate story independently
