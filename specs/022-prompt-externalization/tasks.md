# Tasks: Prompt Externalization

**Input**: Design documents from `/specs/022-prompt-externalization/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Test task included (T014) — validates prompt file loading at CI level.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create directory structure and prompt loader module

- [x] T001 Create directory structure: src/prompts/system/, src/prompts/tools/, src/prompts/templates/ and add empty __init__.py in src/prompts/
- [x] T002 Create src/prompts.py — prompt loader module with three functions: load_system_prompt() reads and concatenates all .md files from src/prompts/system/ in sorted filename order; load_tool_descriptions() parses ## headers from src/prompts/tools/*.md into dict[str, str]; render_template(name, **kwargs) loads src/prompts/templates/{name}.md and calls .format(**kwargs). Use @lru_cache for startup caching. Add startup validation: fail fast if system/ dir is empty, warn on missing tool descriptions.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No additional foundational work — the loader module (T002) is the only prerequisite for all user stories.

**Checkpoint**: src/prompts.py importable and functions callable (even if prompt files don't exist yet)

---

## Phase 3: User Story 1 — System Prompt Externalization (Priority: P1) MVP

**Goal**: Move the ~376-line SYSTEM_PROMPT from src/assistant.py into 8 composable Markdown section files

**Independent Test**: Restart the app, send a WhatsApp message, verify identical assistant behavior. Git diff shows no SYSTEM_PROMPT string literal in assistant.py.

### Implementation for User Story 1

- [x] T003 [US1] Extract SYSTEM_PROMPT (lines ~43-418) from src/assistant.py into 8 section files in src/prompts/system/: 01-identity.md (persona, family members, core directive), 02-response-rules.md (WhatsApp formatting, conciseness rules 1-8), 03-daily-planner.md (rules 9-17 including calendar safety, confirm-before-writing, childcare, backlog), 04-grocery-recipes.md (rules 18-31: grocery, recipe catalogue, Downshiftology), 05-chores-nudges.md (rules 23-27: nudge interactions, laundry state machine, quiet days), 06-budget.md (rules 32-36: YNAB transactions, recategorization, budget moves), 07-calendar-reminders.md (rules 37-46: quick reminders, event ownership, feature discovery, cross-domain), 08-advanced.md (rules 47-68: daily briefing, meeting prep, sync patterns, budget goals, communication modes, preferences)
- [x] T004 [US1] Modify src/assistant.py — remove the SYSTEM_PROMPT string literal constant; import load_system_prompt from src.prompts; replace usage in handle_message() (line ~2233) with: system = date_line + "\n\n" + load_system_prompt() + "\n\n" + date_line. Preserve the existing date sandwich and preferences injection logic unchanged.
- [x] T005 [US1] Verify system prompt assembly — run `python -c "from src.prompts import load_system_prompt; p = load_system_prompt(); print(f'Loaded {len(p)} chars, {p.count(chr(10))} lines')"` and confirm the line count is close to the original ~376 lines. Run `pytest tests/` to confirm smoke test still passes.

**Checkpoint**: SYSTEM_PROMPT constant removed from assistant.py. System prompt loaded from 8 Markdown files. App behavior unchanged.

---

## Phase 4: User Story 2 — Tool Description Externalization (Priority: P2)

**Goal**: Move 71 tool description strings from the TOOLS array in src/assistant.py into 12 module-grouped Markdown files

**Independent Test**: Restart the app, verify all tools are available to Claude and descriptions match the external files.

### Implementation for User Story 2

- [x] T006 [US2] Extract all 71 tool descriptions from the TOOLS array (lines ~424-1798) in src/assistant.py into 12 files in src/prompts/tools/ using `## tool_name` Markdown headers: calendar.md (4 tools: get_calendar_events, get_outlook_events, write_calendar_blocks, create_quick_event), notion.md (14 tools), ynab.md (10 tools), anylist.md (3 tools), recipes.md (8 tools), chores.md (10 tools), proactive.md (3 tools), amazon.md (5 tools), email.md (4 tools), preferences.md (3 tools), context.md (1 tool: get_daily_context), routines.md (6 tools)
- [x] T007 [US2] Modify src/assistant.py — restructure TOOLS array: keep input_schema dicts inline in Python; replace description string literals with lookups from load_tool_descriptions(). Create a TOOL_SCHEMAS dict or list mapping tool names to their input_schema, then build TOOLS by merging descriptions from load_tool_descriptions() with schemas. The resulting TOOLS array must be identical in structure to the original (list of dicts with name, description, input_schema keys).
- [x] T008 [US2] Verify tool loading — run `python -c "from src.prompts import load_tool_descriptions; d = load_tool_descriptions(); print(f'Loaded {len(d)} tool descriptions'); missing = [t for t in ['get_calendar_events','get_action_items','push_grocery_list','get_daily_context'] if t not in d]; print(f'Missing: {missing}')"` and confirm 71 tools loaded with 0 missing. Run `pytest tests/` to confirm smoke test passes.

**Checkpoint**: TOOLS array built from external descriptions + inline schemas. All 71 tools present. App behavior unchanged.

---

## Phase 5: User Story 3 — Classification Prompt Externalization (Priority: P3)

**Goal**: Move 11 inline LLM prompt templates from 4 Python files into external Markdown template files with {placeholder} syntax

**Independent Test**: Trigger an Amazon sync or email sync and verify classification/parsing prompts are loaded from external files and work correctly.

### Implementation for User Story 3

- [x] T009 [US3] Create 11 template files in src/prompts/templates/ by extracting inline prompt strings: amazon_order_parsing.md (from src/tools/amazon_sync.py _parse_order_email, placeholder: {clean_text}), amazon_classification.md (from classify_item, placeholders: {category_list}, {examples_text}, {item_title}, {item_price}), paypal_parsing.md (from src/tools/email_sync.py _parse_paypal_email, placeholder: {stripped_text}), venmo_parsing.md (from _parse_venmo_email, placeholder: {stripped_text}), apple_parsing.md (from _parse_apple_email, placeholder: {stripped_text}), meal_plan_generation.md (from src/tools/proactive.py generate_meal_plan, placeholders: {profile}, {recipe_count}, {recipes_summary}, {recent_plans}), meal_swap.md (from handle_meal_swap, placeholder: {new_meal}), conflict_detection.md (from detect_conflicts, placeholders: {days_ahead}, {today}, {cal_events}, {outlook_events}, {templates}), budget_formatting.md (from format_budget_summary, placeholder: {raw}), recipe_extraction.md (from src/tools/recipes.py extract_and_save_recipe, placeholders: {page_suffix}, {multi_page_rule}), daily_briefing.md (from generate_daily_briefing if present, placeholder: {context_data})
- [x] T010 [P] [US3] Modify src/tools/amazon_sync.py — replace 2 inline prompt strings in _parse_order_email() and classify_item() with render_template("amazon_order_parsing", clean_text=...) and render_template("amazon_classification", category_list=..., examples_text=..., item_title=..., item_price=...) calls. Add `from src.prompts import render_template` import.
- [x] T011 [P] [US3] Modify src/tools/email_sync.py — replace 3 inline prompt strings in _parse_paypal_email(), _parse_venmo_email(), _parse_apple_email() with render_template() calls using paypal_parsing, venmo_parsing, apple_parsing templates. Add `from src.prompts import render_template` import.
- [x] T012 [P] [US3] Modify src/tools/proactive.py — replace 4 inline prompt strings in generate_meal_plan(), handle_meal_swap(), detect_conflicts(), format_budget_summary() with render_template() calls. Add `from src.prompts import render_template` import.
- [x] T013 [P] [US3] Modify src/tools/recipes.py — replace 1 inline prompt string in extract_and_save_recipe() with render_template("recipe_extraction", page_suffix=..., multi_page_rule=...) call. Add `from src.prompts import render_template` import.

**Checkpoint**: All 11 inline prompts replaced with render_template() calls. Template files contain the prompt text with {placeholder} syntax. App behavior unchanged.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Testing, documentation, and validation

- [x] T014 [P] Create tests/test_prompts.py — test that: load_system_prompt() returns non-empty string with expected section markers; load_tool_descriptions() returns dict with 71 entries; all template files in src/prompts/templates/ are loadable and non-empty; render_template() raises KeyError on missing placeholders
- [x] T015 [P] Update CLAUDE.md — add Prompt Architecture section documenting: src/prompts/ directory structure, how to add/edit prompts, file naming conventions, loader module usage
- [x] T016 Run ruff check/format on all modified files, run pytest tests/, push branch, open PR, verify CI passes. Run quickstart.md scenarios 1-4 and 7-8 as validation.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: No additional work needed
- **US1 System Prompt (Phase 3)**: Depends on T002 (loader module)
- **US2 Tool Descriptions (Phase 4)**: Depends on T002 (loader module). Independent of US1.
- **US3 Classification Prompts (Phase 5)**: Depends on T002 (loader module). Independent of US1/US2.
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (System Prompt)**: Independent after T002 — only touches SYSTEM_PROMPT in assistant.py
- **US2 (Tool Descriptions)**: Independent after T002 — only touches TOOLS in assistant.py (different section from US1)
- **US3 (Classification Prompts)**: Independent after T002 — touches 4 different files (amazon_sync, email_sync, proactive, recipes)

### Within Each User Story

- Extract content to files before modifying Python code
- Modify Python code to use loader
- Verify behavior unchanged

### Parallel Opportunities

- T010, T011, T012, T013 can run in parallel (US3 — different Python files)
- T014, T015 can run in parallel (Polish — different files)
- US1, US2, US3 could theoretically run in parallel (independent file sections) but US1+US2 both modify assistant.py so they should be sequential

---

## Implementation Strategy

### MVP First (US1 Only — Phase 1 + 3)

1. Complete T001-T002: Create directories and loader module
2. Complete T003-T005: Extract and wire up system prompt
3. **STOP and VALIDATE**: Verify app works with external system prompt
4. This alone delivers the highest-value change (375 lines of prompt text externalized)

### Incremental Delivery

1. Setup (T001-T002) → Loader module ready
2. US1 (T003-T005) → System prompt externalized (MVP!)
3. US2 (T006-T008) → Tool descriptions externalized
4. US3 (T009-T013) → All remaining prompts externalized (SC-001 achieved: 100% external)
5. Polish (T014-T016) → Tests, docs, CI validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 and US2 both modify assistant.py — execute sequentially to avoid merge conflicts
- US3 tasks T010-T013 modify 4 different Python files — safe to parallelize
- The recipe_extraction template (T009/T013) has conditional logic (multi_page flag) — convert to two placeholders ({page_suffix}, {multi_page_rule}) rather than inline conditional
- Total prompt files created: 31 (8 system + 12 tools + 11 templates)
- No new Python dependencies required
