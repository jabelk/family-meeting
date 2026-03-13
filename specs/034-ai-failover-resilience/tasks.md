# Tasks: AI Failover & Resilience Improvements

**Input**: Design documents from `/specs/034-ai-failover-resilience/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested. Tests will be added in the Polish phase for the new `ai_provider.py` module.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Add OpenAI dependency and configuration

- [X] T001 Add `openai` package to requirements.txt in requirements.txt
- [X] T002 Add `OPENAI_API_KEY` and `OPENAI_MODEL` configuration to src/config.py — load from env with `OPENAI_MODEL` defaulting to `gpt-4o-mini`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Integration registry update and backup tool subset definition — MUST complete before user stories

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add `openai_backup` integration entry to INTEGRATION_REGISTRY in src/integrations.py — name="openai_backup", display_name="OpenAI Backup", required=False, env_vars=("OPENAI_API_KEY",), tools=(), prompt_tag="openai_backup"
- [X] T004 Define BACKUP_TOOLS constant in src/ai_provider.py — list of ~10 core tool names for backup provider: get_daily_context, get_calendar_events, create_quick_event, get_action_items, add_action_item, complete_action_item, save_preference, list_preferences, check_system_logs, get_family_profile

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Backup AI Provider Failover (Priority: P1) MVP

**Goal**: When Claude is unavailable (500/529/timeout), automatically switch to OpenAI GPT so users still get responses

**Independent Test**: Mock Claude as unavailable, verify OpenAI responds with core tools working

### Implementation for User Story 1

- [X] T005 [US1] Create Anthropic-to-OpenAI tool format converter in src/ai_provider.py — function `_convert_tools_for_openai(anthropic_tools)` that wraps each tool in `{"type": "function", "function": {...}}` and renames `input_schema` to `parameters`. Filter to only BACKUP_TOOLS.
- [X] T006 [US1] Create OpenAI-to-Anthropic response normalizer in src/ai_provider.py — function `_normalize_openai_response(openai_response)` that converts OpenAI `choices[0].message` (with `.tool_calls` and `.content`) into an Anthropic-like object with `.content` list of TextBlock/ToolUseBlock and `.stop_reason`. Must `json.loads()` tool call arguments since OpenAI returns JSON strings.
- [X] T007 [US1] Create message format converter in src/ai_provider.py — function `_convert_messages_for_openai(system, messages)` that converts Anthropic message format (system as separate param, tool_result blocks as user content) to OpenAI format (system as role message, tool results as role="tool" messages with tool_call_id).
- [X] T008 [US1] Implement main `create_message(system, tools, messages, max_tokens)` function in src/ai_provider.py — tries Claude first with 45-second timeout (`anthropic.Anthropic(timeout=httpx.Timeout(45.0))`), catches `anthropic.APIStatusError` (500/529), `anthropic.APITimeoutError`, `anthropic.APIConnectionError`, then retries with OpenAI using converted tools/messages. Returns `(response, provider_used)` tuple where provider_used is "claude" or "openai".
- [X] T009 [US1] Handle both-providers-down case in src/ai_provider.py — if OpenAI also fails, raise a custom `AllProvidersDownError` exception that the caller can catch.
- [X] T010 [US1] Modify `handle_message()` in src/assistant.py to use `ai_provider.create_message()` instead of direct `client.messages.create()` call — replace the API call at ~line 1829 with `response, provider_used = ai_provider.create_message(...)`. Remove or bypass the module-level `client = Anthropic()` (the client is now created inside ai_provider.py). Keep the existing tool loop unchanged (it consumes the normalized response).
- [X] T011 [US1] Append backup provider indicator in src/assistant.py — after the tool loop completes, if `provider_used == "openai"`, append "\n\n_Note: using backup assistant today_" to the response text before returning.
- [X] T012 [US1] Add static fallback message handler in src/app.py — in `_process_and_reply()`, catch `AllProvidersDownError` from `handle_message()` and send a hardcoded WhatsApp message: "I'm having trouble connecting to my AI services right now. Please try again in a few minutes. If this keeps happening, let Jason know."

**Checkpoint**: US1 complete — Claude outage triggers OpenAI backup; both down sends static message

---

## Phase 4: User Story 2 — Eliminate Silent Tool Failures (Priority: P2)

**Goal**: Ensure every tool error is surfaced to the user — no silent failures

**Independent Test**: Trigger a tool failure (e.g., calendar unavailable), verify bot explicitly mentions the failure

### Implementation for User Story 2

- [X] T013 [P] [US2] Add `audit_tool_result(tool_name, result_str)` function in src/tool_resilience.py — scan tool return strings for error patterns: starts with "Error:" or "TOOL FAILED:", contains "unavailable"/"failed"/"unauthorized"/"forbidden"/"not found"/"error occurred", or returns empty string. Return `(is_error, warning_prefix)` tuple. If error detected, prefix is "TOOL WARNING: The result from {tool_name} may indicate a failure — check the details and inform the user if the action did not succeed. Result: "
- [X] T014 [US2] Integrate `audit_tool_result()` into the tool loop in src/assistant.py — after `execute_with_retry()` returns a result string (~line 1878), call `audit_tool_result(tool_name, result)` and prepend the warning prefix if `is_error` is True before passing the result back to Claude.
- [X] T015 [P] [US2] Add explicit tool failure reporting rule to src/prompts/system/02-response-rules.md — add rule 9: "If ANY tool result contains an error, failure, or 'TOOL FAILED' prefix, you MUST mention the failure to the user. NEVER present a failed tool action as successful. If a fallback was used, explain what happened and what alternative was taken."
- [X] T015b [US2] Audit all existing tool handlers in src/assistant.py (TOOL_FUNCTIONS dict ~lines 1475-1635 and handler functions) for error string patterns that could bypass tool_resilience — look for try/except blocks that return user-friendly strings without "Error:" prefix, or tool functions that catch exceptions and return strings that look like success. Document and fix any found. (Covers FR-010)

**Checkpoint**: US2 complete — all tool errors surfaced to user, no silent failures

---

## Phase 5: User Story 5 — Proactive System Log Diagnostics (Priority: P2)

**Goal**: Ensure the bot uses log diagnostics proactively when errors occur, not just when asked

**Independent Test**: Trigger a tool failure, verify response includes specific diagnostic info from system logs

### Implementation for User Story 5

- [X] T016 [P] [US5] Enhance check_system_logs tool description in src/prompts/tools/context.md — update to emphasize proactive use: "Call this when something isn't working, a user reports a problem, a tool just failed, or someone asks about system status. Also call proactively after any error to include specific diagnostic context in your response."
- [X] T017 [P] [US5] Add proactive diagnostics rule to src/prompts/system/02-response-rules.md — add rule 10: "When reporting any tool failure or system issue, always include specific diagnostic context (e.g., 'Google Calendar auth token expired' rather than 'calendar is having issues'). Use information from tool error messages and system logs to give actionable guidance (e.g., 'Jason needs to refresh the calendar token' rather than 'calendar is down')."

**Checkpoint**: US5 complete — bot provides specific diagnoses for all failures

---

## Phase 6: User Story 3 — Detect and Handle Lost Messages (Priority: P3)

**Goal**: When a user references a message the system never received, acknowledge the gap and ask to resend

**Independent Test**: Send "read the message I just sent" with no prior context; bot should ask user to resend

### Implementation for User Story 3

- [X] T018 [US3] Create src/prompts/system/11-resilience.md with lost message detection rules — YAML frontmatter `requires: [core]`. Rules: (1) If a user references a prior message the system has no record of ("read my last message", "did you get that?", "what do you think about what I said?"), acknowledge the gap and ask to resend. (2) If a user sends a context-dependent follow-up ("so can you do that?") with no prior request in the conversation, explain you may have missed it and ask to repeat. (3) Do NOT trigger false positives — if the user references something discussed earlier in the same conversation and you have that context, respond normally.

**Checkpoint**: US3 complete — lost message references detected and handled gracefully

---

## Phase 7: User Story 4 — Fix Premature Action Item Completion (Priority: P3)

**Goal**: Only mark action items complete when user confirms actual completion, not stated intent

**Independent Test**: Say "I'm going to do X" — item stays open. Say "done with X" — item marked complete.

### Implementation for User Story 4

- [X] T019 [US4] Add action item completion rules to src/prompts/system/11-resilience.md — append rules after the lost message section: (1) NEVER mark an action item as complete when the user expresses INTENT ("I'm going to", "I'll do", "planning to", "need to", "going to", "about to"). Acknowledge the item but keep it open. (2) ONLY mark an action item complete when the user confirms ACTUAL COMPLETION ("done", "finished", "just did", "completed", "X is done", "took care of"). (3) When unsure, keep the item open — a false "not done" is less harmful than a false "done".

**Checkpoint**: US4 complete — intent vs completion correctly distinguished

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Tests, validation, and deployment

- [X] T020 [P] Create unit tests for ai_provider.py in tests/test_ai_provider.py — test tool format conversion (Anthropic→OpenAI), response normalization (OpenAI→Anthropic), message format conversion, failover logic (mock Claude failure → OpenAI success), both-down case (AllProvidersDownError raised)
- [X] T021 [P] Add tool result auditing tests to tests/test_tool_resilience.py — test audit_tool_result with error strings ("Error: unavailable"), normal strings ("[{data}]"), empty strings, and TOOL FAILED prefixed strings
- [X] T022 Update prompt section and tool description counts in tests/test_prompts.py — adjust assertion counts for the new 11-resilience.md system prompt section and any updated tool descriptions
- [X] T023 Run full test suite and fix any regressions — `pytest tests/`
- [X] T024 Add OPENAI_API_KEY to Railway environment variables via `railway variables set`
- [X] T025 Deploy to Railway and run quickstart.md E2E validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — core failover implementation
- **US2 (Phase 4)**: Depends on Foundational — can run in PARALLEL with US1
- **US5 (Phase 5)**: Depends on Foundational — can run in PARALLEL with US1/US2
- **US3 (Phase 6)**: Depends on Foundational — can run in PARALLEL with all others
- **US4 (Phase 7)**: Depends on US3 (T018 creates the prompt file that T019 appends to)
- **Polish (Phase 8)**: Depends on US1 completion (for ai_provider tests); other polish tasks can start after their respective stories

### User Story Dependencies

- **US1 (P1)**: Independent — creates ai_provider.py, modifies assistant.py and app.py
- **US2 (P2)**: Independent — modifies tool_resilience.py, assistant.py (different section), 02-response-rules.md
- **US5 (P2)**: Independent — modifies prompt files only (context.md, 02-response-rules.md different rule)
- **US3 (P3)**: Independent — creates new 11-resilience.md prompt file
- **US4 (P3)**: Depends on US3 — appends to the same 11-resilience.md file created by T018

### Parallel Opportunities

Within each user story, tasks marked [P] can run in parallel:
- T013 and T015 (US2) — different files
- T016 and T017 (US5) — different files
- T020 and T021 (Polish) — different test files

Across user stories (after Foundational):
- US2 (T013-T015) can run in parallel with US1 (T005-T012)
- US3 (T018) and US5 (T016-T017) can run in parallel with everything
- US4 (T019) must wait for US3 (T018)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T004)
3. Complete Phase 3: US1 — AI Failover (T005-T012)
4. **STOP and VALIDATE**: Test with simulated Claude outage
5. Deploy if ready — users now have failover protection

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Failover) → Test → Deploy (MVP!)
3. US2 (Silent failures) + US5 (Diagnostics) → Test → Deploy (trust improvement)
4. US3 (Lost messages) + US4 (Completion fix) → Test → Deploy (conversation quality)
5. Polish → Full test suite → Final deploy

---

## Notes

- US2 and US5 are partially implemented from PRs #61-#63 (tool_resilience.py, log_diagnostics.py, check_system_logs tool). Tasks focus on remaining gaps.
- US3 and US4 are prompt-only fixes — no Python code changes, just new system prompt rules.
- The `openai` package is the only new dependency. No other infrastructure changes.
- Static fallback message in US1 bypasses AI entirely — sends via WhatsApp API directly.
