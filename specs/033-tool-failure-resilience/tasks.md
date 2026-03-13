# Tasks: Tool Failure Resilience

**Input**: Design documents from `/specs/033-tool-failure-resilience/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create the new resilience module skeleton

- [X] T001 Create src/tool_resilience.py with module docstring, imports (httpx, logging, time, enum, typing), and ExceptionCategory enum (RETRYABLE, NON_RETRYABLE, INPUT_ERROR)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that all user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Add get_integration_for_tool(tool_name) reverse lookup helper to src/integrations.py — build reverse map from INTEGRATION_REGISTRY at module level, return display_name (e.g., "Google Calendar") or "Unknown" for unmapped tools
- [X] T003 Implement classify_exception(exc) function in src/tool_resilience.py — map exception types to ExceptionCategory per data-model.md classification rules (httpx.TimeoutException→RETRYABLE, httpx.HTTPStatusError check status code 5xx→RETRYABLE vs 4xx→NON_RETRYABLE, googleapiclient.errors.HttpError similarly, notion_client.errors.RequestTimeoutError→RETRYABLE, ValueError/json.JSONDecodeError→INPUT_ERROR, catch-all→NON_RETRYABLE)

**Checkpoint**: Foundation ready — exception classification and integration lookup available for all stories

---

## Phase 3: User Story 1 — Automatic Retry on Tool Failure (Priority: P1) MVP

**Goal**: Automatically retry transient tool failures up to 2 times with 1s/2s delays so most failures resolve transparently

**Independent Test**: Mock a tool to fail once with httpx.TimeoutException then succeed — verify user gets successful result with no error visible, and log shows 1 retry

### Implementation for User Story 1

- [X] T004 [US1] Implement execute_with_retry(func, tool_name, tool_input) in src/tool_resilience.py — retry loop that calls func(**tool_input), catches exceptions, classifies them, retries RETRYABLE up to 2 times with time.sleep(1) then time.sleep(2), returns result string on success or raises on non-retryable/input-error
- [X] T005 [US1] Replace the catch-all handler in src/assistant.py (lines 1853-1855) with a call to execute_with_retry() — pass the resolved func, tool_name, and tool_input; handle the return value as the tool result string; preserve the existing tool_results.append() pattern
- [X] T006 [US1] Add structured failure logging in src/tool_resilience.py — log tool_name, error type, exception category, retry attempt number, and final outcome (success after retry / exhausted / non-retryable / input-error) using the existing logger pattern

**Checkpoint**: Transient failures now auto-retry. Non-retryable errors still need proper messages (US2).

---

## Phase 4: User Story 2 — Clear Error Reporting to User (Priority: P2)

**Goal**: When a tool permanently fails (after retries or immediately for non-retryable), provide the AI with a service-aware error message that instructs it to tell the user what failed and suggest alternatives — never allow silent skipping

**Independent Test**: Force create_quick_event to fail with 403 — verify the error message returned to Claude contains "Google Calendar", states action was NOT completed, and includes "DO NOT skip" instruction

### Implementation for User Story 2

- [X] T007 [US2] Implement format_error_message(tool_name, exception, category) in src/tool_resilience.py — use get_integration_for_tool() to get display_name, extract human-readable reason from exception, format per research R6: "TOOL FAILED: {tool_name} ({display_name}) — {reason}. DO NOT skip this — you MUST tell the user that {display_name} is currently having issues and their {action_description} was NOT completed. Suggest an alternative."
- [X] T008 [US2] Add category-specific message variations in src/tool_resilience.py — RETRYABLE (exhausted): mention service outage; NON_RETRYABLE: mention permission/config issue; INPUT_ERROR: mention invalid input from the request, no service blame
- [X] T009 [US2] Wire format_error_message() into execute_with_retry() failure paths in src/tool_resilience.py — return formatted error string instead of raising, so assistant.py receives it as the tool result

**Checkpoint**: All tool failures now produce clear, actionable error messages for Claude. No more "Skip this section."

---

## Phase 5: User Story 3 — Automatic Fallback Actions (Priority: P3)

**Goal**: For write/create tool failures, automatically attempt a fallback action (e.g., Calendar → Notion action item) and WhatsApp message as last resort — user always receives their information

**Independent Test**: Disable Calendar integration and request a reminder — verify a Notion action item is created automatically with same details, and the error message mentions the fallback was taken

### Implementation for User Story 3

- [X] T010 [US3] Define FALLBACK_MAPPINGS dict in src/tool_resilience.py — map each write tool to its fallback per research R5: create_quick_event→add_action_item, write_calendar_blocks→add_action_item, push_grocery_list→None (WhatsApp only), add_action_item→None, save_meal_plan→None, add_topic→None, complete_action_item→None, add_backlog_item→None. Each entry includes fallback_tool (str|None) and last_resort_type (str for WhatsApp formatting)
- [X] T011 [US3] Implement attempt_fallback(tool_name, tool_input, available_tools) in src/tool_resilience.py — look up FALLBACK_MAPPINGS, if fallback_tool exists and is in available_tools dict, execute it with adapted parameters; return (success: bool, result: str, fallback_used: str|None)
- [X] T012 [US3] Add WhatsApp last-resort message formatting in src/tool_resilience.py — when both primary and fallback fail (or no fallback tool exists), format the original tool_input into a human-readable summary string that instructs Claude to relay the information directly in the chat message (e.g., event title + date + time for calendar, item list for grocery)
- [X] T013 [US3] Integrate fallback chain into execute_with_retry() in src/tool_resilience.py — after retries exhausted for a RETRYABLE error, check FALLBACK_MAPPINGS; if mapped, call attempt_fallback(); if fallback succeeds, return success message noting degraded path; if fallback fails, include last-resort WhatsApp instruction in error message

**Checkpoint**: All write tool failures now attempt fallback actions. Users always receive their information.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Testing, validation, and edge case coverage

- [X] T014 [P] Create unit tests for classify_exception(), execute_with_retry(), format_error_message(), and attempt_fallback() in tests/test_tool_resilience.py — cover all 8 quickstart.md scenarios (transient retry, permanent failure, fallback to Notion, WhatsApp last resort, input error, classification correctness, reverse lookup, retry timing)
- [X] T015 [P] Create unit test for get_integration_for_tool() in tests/test_tool_resilience.py — verify create_quick_event→"Google Calendar", add_action_item→"Notion", push_grocery_list→"AnyList", get_budget_summary→"YNAB", unknown_tool→"Unknown"
- [X] T016 Validate all 8 quickstart.md scenarios pass end-to-end with mocked tool functions
- [X] T017 Verify worst-case timing: initial call + 2 retries (1s + 2s) + fallback attempt stays well under 30-second budget

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — core retry mechanism
- **US2 (Phase 4)**: Depends on US1 (T004 execute_with_retry must exist to wire messages into)
- **US3 (Phase 5)**: Depends on US2 (error messages must be in place before adding fallback logic)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US2 (P2)**: Depends on US1 — wires error messages into the retry function created in US1
- **US3 (P3)**: Depends on US2 — adds fallback logic that builds on the error reporting from US2

### Within Each User Story

- Implementation tasks are sequential within each story (same file: src/tool_resilience.py)
- T005 (assistant.py integration) depends on T004 (execute_with_retry must exist first)
- T002 (integrations.py) is parallel with T003 (different files)

### Parallel Opportunities

- T002 and T003 can run in parallel (different files)
- T014 and T015 can run in parallel (different test targets, same file but independent sections)
- Within stories, tasks are sequential due to same-file dependencies

---

## Parallel Example: Phase 2

```bash
# These can run in parallel (different files):
Task T002: "Add get_integration_for_tool() to src/integrations.py"
Task T003: "Implement classify_exception() in src/tool_resilience.py"
```

## Parallel Example: Phase 6

```bash
# These can run in parallel (independent test functions):
Task T014: "Unit tests for resilience functions in tests/test_tool_resilience.py"
Task T015: "Unit tests for reverse lookup in tests/test_tool_resilience.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002, T003)
3. Complete Phase 3: User Story 1 (T004–T006)
4. **STOP and VALIDATE**: Verify transient failures auto-retry and succeed transparently
5. Deploy — most common failure mode (Google Calendar transient errors) is now handled

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Retry) → Test → Deploy (MVP — handles most transient failures)
3. Add US2 (Error Reporting) → Test → Deploy (no more silent failures)
4. Add US3 (Fallback Actions) → Test → Deploy (graceful degradation for write operations)
5. Each story adds resilience without breaking previous stories

---

## Notes

- All resilience logic lives in a single new file: src/tool_resilience.py
- The only change to existing code is src/assistant.py (replace 3-line catch-all) and src/integrations.py (add helper function)
- No new Python dependencies required
- User stories build on each other but each is a meaningful increment
- Tests are included in Phase 6 (not TDD) since the spec didn't explicitly request TDD approach
