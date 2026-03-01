# Tasks: Context-Aware Bot

**Input**: Design documents from `/specs/014-context-aware-bot/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tool-schemas.md, quickstart.md

**Tests**: Not requested in the feature specification. Manual WhatsApp E2E validation in Polish phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Existing codebase — no new project initialization needed

No setup tasks required. All infrastructure is in place:
- Python 3.12 + FastAPI (existing)
- Google Calendar API (existing `src/tools/calendar.py`)
- Preferences system (existing `src/preferences.py`)
- Notion backlog (existing `src/tools/notion.py`)
- Atomic JSON file storage pattern (existing `src/conversation.py`, `src/preferences.py`)

**Checkpoint**: Infrastructure verified — proceed directly to user stories

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational tasks — all dependencies exist in the current codebase

No blocking prerequisites. Existing modules provide all needed APIs:
- `calendar.get_events_for_date()` for calendar queries
- `preferences.get_preferences()` for user preferences
- `notion.get_backlog_items()` for backlog count
- `config.PHONE_TO_NAME`, `config.CALENDAR_IDS` for lookups

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 — Dynamic Context Tool (Priority: P1) 🎯 MVP

**Goal**: Replace hardcoded weekly schedule with a `get_daily_context` tool that returns live calendar data grouped by person, childcare inference, communication mode, and active preferences.

**Independent Test**: Remove the hardcoded weekly schedule from the system prompt. Ask the bot "what's my day look like?" and verify it calls `get_daily_context`, returns today's actual calendar events grouped by person, correctly infers who has Zoey, and generates an accurate daily plan.

### Implementation for User Story 1

- [x] T001 [US1] Create `src/context.py` — implement `get_daily_context(phone)` function that queries `calendar.get_events_for_date(today, ["jason", "erin", "family"])`, groups events by `_calendar_source`, infers childcare status via keyword matching (zoey, sandy, preschool, childcare, babysit, milestones, daycare, nanny), reads `preferences.get_preferences(phone)`, counts pending backlog items via `notion.get_backlog_items()`, and returns a structured text block per the format in `contracts/tool-schemas.md`. Handle Google Calendar API failures gracefully — return `calendar_available: false` with degraded output. Use `PACIFIC = ZoneInfo("America/Los_Angeles")` for all time operations.
- [x] T002 [US1] Implement `get_communication_mode(phone)` helper in `src/context.py` — derive mode from current Pacific time using default boundaries (morning 7-12, afternoon 12-5, evening 5-9, late_night 9-7). Check user's `quiet_hours` preferences for custom overrides by parsing "quiet after Xpm" patterns. Return mode string. This function is called by `get_daily_context()` to populate the `communication_mode` field.
- [x] T003 [US1] Add `get_daily_context` tool definition to the `TOOLS` list in `src/assistant.py` — use the schema from `contracts/tool-schemas.md` (no required params, phone injected). Add the tool handler in the `handle_message()` tool dispatch chain. Add phone injection for `get_daily_context` in the same block as `save_preference` (~line 1678).
- [x] T004 [US1] Update system prompt rules 9-10 in `src/assistant.py` — replace "use the day-specific schedule above" and hardcoded Zoey schedule references with instructions to use `get_daily_context` output. Add a new instruction: "Call `get_daily_context` at the start of any planning, scheduling, daily plan, or recommendation interaction. Do NOT call for simple factual questions."

**Checkpoint**: US1 complete — bot can generate daily plans from live calendar data. Hardcoded schedule references replaced with tool calls. Childcare inferred from events.

---

## Phase 4: User Story 2 — Smart Quiet Hours and Communication Modes (Priority: P1)

**Goal**: Add time-of-day communication modes that control bot tone and proactivity. Late night = minimal responses. Morning = energetic. Users can customize boundaries via preferences.

**Depends on**: US1 (communication_mode is computed in `src/context.py`)

**Independent Test**: Send the bot a message at 10 PM Pacific. Verify the response is direct with zero proactive suggestions. Send a message at 8 AM and verify energetic tone with proactive suggestions.

### Implementation for User Story 2

- [x] T005 [US2] Add communication mode behavioral instructions to the system prompt in `src/assistant.py` — add rules specifying behavior for each mode: morning (proactive suggestions welcome, energetic), afternoon (normal responsive), evening (respond to questions, limit proactive content but still allow nudges), late_night (direct answers only, no proactive suggestions, no follow-up prompts, no discovery tips, no nudges). Reference the `communication_mode` field from `get_daily_context` output. Also remove the budget-specific quiet hours rule (Rule 68) since the general communication mode system now subsumes it — late_night and evening modes handle what Rule 68 previously did.
- [x] T006 [US2] Integrate communication mode into `process_pending_nudges()` in `src/tools/nudges.py` — import `get_communication_mode` from `src/context.py`. Suppress proactive nudges only during "late_night" mode (not "evening" — current nudge window is 7 AM–8:30 PM, and evening mode starts at 5 PM which would be too aggressive a change). Allow departure nudges for imminent events (<15 min away) even during late_night. Keep existing `QUIET_HOURS_START`/`QUIET_HOURS_END` as a fallback if context module import fails.

**Checkpoint**: US2 complete — bot adjusts tone and proactivity based on time of day. No more 10 PM chore suggestions. Nudge system respects communication mode.

---

## Phase 5: User Story 3 — Personal Routine Checklists (Priority: P2)

**Goal**: Let Erin create, view, and modify personal routine checklists via WhatsApp. Routines referenced in daily plans.

**Depends on**: None (independent of US1/US2 — can be implemented in parallel)

**Independent Test**: Send "save my morning routine: wash face, toner, serum, moisturizer, sunscreen" via WhatsApp. Then send "show me my morning routine." Verify the bot returns the ordered checklist. Then send "add SPF after moisturizer" and verify the step is inserted correctly.

### Implementation for User Story 3

- [x] T008 [P] [US3] Create `src/routines.py` — implement routine storage module following the same pattern as `src/preferences.py`: `_DATA_DIR` detection (Docker vs local), in-memory `_routines` dict cache, atomic file writes to `data/routines.json` (write .tmp → rename), auto-load on module import. Public API: `get_routine(phone, name)` returns formatted checklist or not-found message, `save_routine(phone, name, steps)` creates/overwrites routine, `list_routines(phone)` returns all routine names with step counts, `delete_routine(phone, name)` removes a routine. Max 20 routines per user, max 30 steps per routine. Routine names normalized to lowercase for matching. IDs use `rtn_` + 8 hex chars pattern.
- [x] T009 [US3] Add `save_routine`, `get_routine`, and `delete_routine` tool definitions to the `TOOLS` list in `src/assistant.py` — use schemas from `contracts/tool-schemas.md`. Add tool handlers in the `handle_message()` dispatch chain: `save_routine` calls `routines.save_routine(phone, name, steps)`, `get_routine` calls `routines.get_routine(phone, name)` or `routines.list_routines(phone)` when name is "all", `delete_routine` calls `routines.delete_routine(phone, name)`. Add phone injection for all three tools. Add `from src import routines` import at top of file.
- [x] T010 [US3] Add routine-aware instructions to the daily planner rules in the system prompt in `src/assistant.py` — instruct the model: (1) when generating a daily plan, call `get_routine` with name="all" to check for stored routines; if a time block matches a routine name (e.g., "morning routine"), mention it: "Your morning skincare routine (5 steps, ~10 min). Say 'show morning routine' for the full list." (2) For routine modification ("add X after Y in my Z routine"), use the read-modify-save pattern: call `get_routine` to get current steps, modify the list in-context per the user's instruction (insert, remove, or reorder), then call `save_routine` with the updated steps. (3) For routine deletion ("delete my morning routine"), call `delete_routine` directly.

**Checkpoint**: US3 complete — Erin can create, view, and modify routines via WhatsApp. Routines persist across container restarts. Daily plans reference stored routines.

---

## Phase 6: User Story 4 — System Prompt Cleanup (Priority: P2)

**Goal**: Reduce system prompt from ~413 lines to ≤280 lines by removing all hardcoded data that now comes from tools.

**Depends on**: US1 (context tool must exist before removing hardcoded data)

**Independent Test**: Count lines in the system prompt. Verify ≤280. Run a daily plan generation and verify no information is lost — all schedule data available via tool calls.

### Implementation for User Story 4

- [x] T011 [US4] Remove hardcoded schedule and preference data from the system prompt in `src/assistant.py` — delete: childcare schedule (lines ~42-44), weekly schedule Mon-Sun (lines ~46-58), Erin's daily needs (lines ~63-66), Erin's chore needs and best windows (lines ~68-74). Before deleting Jason's breakfast preference (lines ~60-61), migrate it to the Notion family profile page by calling `update_family_profile(section="Preferences", content="Jason's breakfast: 1 scrambled egg, 2 bacon, high fiber tortilla, sriracha ketchup + Crystal hot sauce, Coke Zero or Diet Dr Pepper")` — this ensures it's still retrievable via `read_family_profile`. Replace the entire removed block with a 5-line `**Dynamic context:**` instruction directing the model to call `get_daily_context` per research.md R5.
- [x] T012 [US4] Consolidate verbose system prompt rules in `src/assistant.py` — merge cross-domain thinking rules 40-46 (7 rules) into 3 concise rules. Merge Amazon sync rules 51-56 (6 rules) into 3 rules. Merge email sync rules 57-61 (5 rules) into 3 rules. Merge preference rules 69-71 (3 rules) into 1 rule. Preserve all behavioral intent while reducing line count. Renumber all rules sequentially.
- [x] T013 [US4] Audit and fix all system prompt rule references in `src/assistant.py` — verify no remaining rule references hardcoded data that was removed (e.g., "check who has Zoey today" referencing old schedule). Update any stale cross-references (e.g., "see Rule 3" must still point correctly after renumbering). Count final lines and verify ≤280.

**Checkpoint**: US4 complete — system prompt is ≤280 lines. All dynamic data sourced from tools. No stale hardcoded references.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation and cleanup across all user stories

- [ ] T014 E2E validation: send "what's my day look like?" via WhatsApp and verify the bot calls `get_daily_context`, generates accurate daily plan from live calendar data, correctly attributes events by person, and infers childcare status
- [ ] T015 E2E validation: send a message at late_night hours and verify bot responds with direct answer only, no proactive suggestions, no discovery tips, no follow-up prompts
- [ ] T016 E2E validation: send "save my morning routine: wash face, toner, moisturizer, sunscreen" then "show me my morning routine" and verify round-trip storage and retrieval works correctly
- [x] T017 Verify `data/routines.json` persists across container restart by checking the Docker volume mount covers the `data/` directory (it should — same as `data/conversations.json` and `data/user_preferences.json`) — verified: data/ is Docker volume mounted
- [x] T018 Final line count verification: confirm system prompt in `src/assistant.py` is ≤280 lines (result: 123 lines)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No action needed — existing infrastructure
- **Foundational (Phase 2)**: No action needed — existing modules provide all APIs
- **US1 (Phase 3)**: Can start immediately — creates `src/context.py` and wires into `src/assistant.py`
- **US2 (Phase 4)**: Depends on US1 (uses `get_communication_mode` from `src/context.py`)
- **US3 (Phase 5)**: **Independent** — can run in parallel with US1 and US2 (different files: `src/routines.py`)
- **US4 (Phase 6)**: Depends on US1 (must have context tool before removing hardcoded data)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

```
US1 (Dynamic Context Tool) ─────┬──→ US2 (Smart Quiet Hours)
                                 └──→ US4 (System Prompt Cleanup)

US3 (Routine Checklists) ────────── Independent (parallel with US1/US2)
```

### Within Each User Story

- T001 → T002 → T003 → T004 (US1: context module → mode helper → tool wiring → prompt update)
- T005 → T006 (US2: prompt rules + remove Rule 68 → nudge integration)
- T008 → T009 → T010 (US3: routines module → tool wiring → prompt instructions)
- T011 → T012 → T013 (US4: remove data → consolidate rules → audit)

### Parallel Opportunities

- **T008 [P]** can run in parallel with T001-T004 (US3's routines.py is independent of US1's context.py)
- Within US4, T011 and T012 both modify the same file (`assistant.py`), so they must be sequential
- E2E validation tasks T014-T016 can run in parallel after deployment

---

## Parallel Example: US1 + US3

```bash
# These can run simultaneously since they touch different files:
# Agent A: US1 — create src/context.py
Task T001: "Create get_daily_context in src/context.py"
Task T002: "Create get_communication_mode in src/context.py"

# Agent B: US3 — create src/routines.py (independent)
Task T008: "Create routine storage module in src/routines.py"

# After both complete, wire both into assistant.py sequentially:
Task T003: "Add get_daily_context tool to src/assistant.py"
Task T009: "Add save_routine and get_routine tools to src/assistant.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001-T004 (US1: Dynamic Context Tool)
2. **STOP and VALIDATE**: Verify `get_daily_context` returns accurate live calendar data
3. Deploy to NUC and test via WhatsApp

### Incremental Delivery

1. US1 (context tool) → Deploy → Validate live calendar data ✅
2. US2 (quiet hours) → Deploy → Validate communication modes ✅
3. US3 (routines) → Deploy → Validate routine CRUD ✅
4. US4 (prompt cleanup) → Deploy → Validate ≤280 lines, no broken references ✅
5. Each story adds value without breaking previous stories

### Recommended Execution Order (Single Agent)

```
T001 → T002 → T003 → T004    (US1: context tool — MVP)
T008                           (US3: routines module — parallel with US1 assistant.py work)
T005 → T006                    (US2: quiet hours)
T009 → T010                    (US3: wire routines into assistant.py)
T011 → T012 → T013            (US4: system prompt cleanup)
T014 → T015 → T016 → T017 → T018  (Polish: E2E validation)
```

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- US3 (routines) is fully independent and can be built in parallel with US1/US2
- US4 (cleanup) MUST come last since it modifies the same system prompt lines as US1/US2
- All `src/assistant.py` modifications should be done sequentially to avoid merge conflicts
- Commit after each user story phase for clean rollback points
