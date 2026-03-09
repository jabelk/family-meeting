# Tasks: Recurring Calendar Events

**Input**: Design documents from `/specs/024-recurring-calendar-events/`
**Prerequisites**: spec.md (no plan.md needed — small feature extending existing calendar tools)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new dependencies needed — Google Calendar API already supports recurrence rules (RRULE). No setup tasks.

*(No tasks)*

---

## Phase 2: Foundational

**Purpose**: No foundational/blocking tasks — all changes extend existing calendar module.

*(No tasks)*

---

## Phase 3: User Story 1 — Create Recurring Events from Natural Language (Priority: P1) MVP

**Goal**: User says "add cleaners every other Tuesday at 10am-1pm starting March 3" and a single recurring calendar event is created.

**Independent Test**: Send "add swim class every Monday at 4pm for 8 weeks" via WhatsApp. Bot confirms with pattern and next dates. Google Calendar shows the recurring event with recurrence icon.

### Implementation for User Story 1

- [x] T001 [US1] Add `recurrence` optional parameter to `create_quick_event()` in src/tools/calendar.py. Accept a list of RRULE strings (e.g., `["RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU"]`). When provided, add `"recurrence": recurrence` to the event body dict before the `events().insert()` call. When not provided, behavior is unchanged (no recurrence). Also add optional `calendar_name` parameter (default `"family"`) to allow targeting Jason/Erin calendars.
- [x] T002 [US1] Update the `create_quick_event` tool schema in src/assistant.py. Add `recurrence` property: `{"type": "array", "items": {"type": "string"}, "description": "RRULE strings for recurring events. Examples: ['RRULE:FREQ=WEEKLY;BYDAY=MO'] for weekly Monday, ['RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU'] for biweekly Tuesday, ['RRULE:FREQ=MONTHLY;BYDAY=1FR'] for first Friday of month, ['RRULE:FREQ=WEEKLY;BYDAY=TU,TH'] for Tuesdays and Thursdays. Add COUNT=N for N occurrences or UNTIL=YYYYMMDD for end date."}`. Add `calendar_name` property: `{"type": "string", "enum": ["family", "jason", "erin"], "default": "family"}`. Do NOT add either to `required`.
- [x] T003 [P] [US1] Update the `create_quick_event` tool description in src/prompts/tools/calendar.md. Add guidance that this tool now supports recurring events via RRULE. Include examples: weekly, biweekly, monthly by day, with COUNT or UNTIL. Note that Claude should generate the RRULE from the user's natural language (e.g., "every other Tuesday" → `FREQ=WEEKLY;INTERVAL=2;BYDAY=TU`). Note default calendar is family, but can specify jason or erin.
- [ ] T004 [US1] Verify US1 works end-to-end: start the app locally (or use deployed instance), send a test message like "add a test recurring event every Tuesday at 2pm for 4 weeks". Confirm: (1) bot responds with confirmation showing the recurrence pattern, (2) event appears in Google Calendar with recurrence icon, (3) expanding the event shows "every Tuesday, 4 times". Clean up test event after verification.

**Checkpoint**: Recurring events can be created via natural language. MVP complete.

---

## Phase 4: User Story 2 — Modify or Cancel Recurring Events (Priority: P2)

**Goal**: User can cancel one occurrence ("no swim this Monday") or all future occurrences ("cancel the cleaners") of a recurring event.

**Independent Test**: Create a recurring event, then say "cancel the cleaners." Bot asks "this one or all?" and acts accordingly.

**Depends on**: US1 (need recurring events to exist before managing them)

### Implementation for User Story 2

- [x] T005 [US2] Add `delete_calendar_event(event_id, calendar_name, cancel_mode)` function to src/tools/calendar.py. `cancel_mode` options: `"single"` (delete just this instance — use `instances().list()` to find the specific occurrence then `events().delete()`), `"all_following"` (delete the recurring event itself — `events().delete()` on the parent event ID), `"this_only"` (set the instance status to `"cancelled"` via `events().update()`). The function finds the event by ID, checks if it's recurring, and applies the appropriate action.
- [x] T006 [US2] Register `delete_calendar_event` as a new tool in src/assistant.py. Schema: `event_id` (string, required — the Google Calendar event ID), `calendar_name` (string, enum family/jason/erin, default family), `cancel_mode` (string, enum single/all_following, default single). Add to TOOLS list and TOOL_FUNCTIONS dict.
- [x] T007 [P] [US2] Add `## delete_calendar_event` tool description in src/prompts/tools/calendar.md. Describe: deletes a single occurrence or all future occurrences of an event. Use `cancel_mode: "single"` when user says "no swim this Monday" or "skip cleaners next week". Use `cancel_mode: "all_following"` when user says "cancel the cleaners" or "stop the recurring swim class". To find the event_id, first use `get_calendar_events` or `get_events_for_date` to locate the event.
- [ ] T008 [US2] Verify US2 works: create a test recurring event, then test (1) cancelling a single occurrence — confirm only that date is removed, (2) cancelling all future — confirm the series is deleted. Clean up after.

**Checkpoint**: Users can manage recurring events through the bot.

---

## Phase 5: User Story 3 — View Recurring Events (Priority: P3)

**Goal**: User asks "what recurring events do we have" and sees a list of all active recurring series.

**Independent Test**: Create 2-3 recurring events, ask "list recurring events." Bot responds with patterns.

### Implementation for User Story 3

- [x] T009 [US3] Add `list_recurring_events(calendar_name)` function to src/tools/calendar.py. Query events from today forward (next 90 days, `singleEvents=False` to get parent recurring events). Filter to events that have a `recurrence` field. Return a list of dicts with: `id`, `summary`, `recurrence` (the RRULE string), `start` (first occurrence time), `calendar`. Deduplicate by recurring event ID.
- [x] T010 [US3] Register `list_recurring_events` as a new tool in src/assistant.py. Schema: `calendar_name` (string, enum family/jason/erin, default family). Add to TOOLS list and TOOL_FUNCTIONS dict.
- [x] T011 [P] [US3] Add `## list_recurring_events` tool description in src/prompts/tools/calendar.md. Describe: lists all active recurring event series on a calendar. Returns the event title, recurrence pattern, and start time. Use when user asks "what recurring events do we have" or "show me our regular schedule."
- [ ] T012 [US3] Verify US3 works: ensure test recurring events exist, ask "what recurring events are on the family calendar." Confirm bot lists them with human-readable patterns.

**Checkpoint**: Full recurring event lifecycle — create, view, cancel.

---

## Phase 6: Polish & Validation

**Purpose**: Final checks and deployment.

- [x] T013 Run `ruff check src/` and `ruff format --check src/` — fix any issues in src/tools/calendar.py and src/assistant.py.
- [x] T014 Run `pytest tests/` — verify all existing tests still pass.
- [x] T015 Update the tool count in tests/test_prompts.py if new tool descriptions were added (currently asserts 71). Update to new count.
- [ ] T016 Commit all changes, push to branch, create PR for merge to main.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A
- **Foundational (Phase 2)**: N/A
- **US1 (Phase 3)**: T001-T004 — No dependencies, can start immediately. Core feature.
- **US2 (Phase 4)**: T005-T008 — Depends on US1 (need recurring events to test against).
- **US3 (Phase 5)**: T009-T012 — Independent of US2 but practical to do after US1.
- **Polish (Phase 6)**: T013-T016 — After all user stories.

### User Story Dependencies

- **US1 (P1)**: Independent — MVP. Extends existing `create_quick_event`.
- **US2 (P2)**: Depends on US1 (need recurring events to manage). Adds new tool `delete_calendar_event`.
- **US3 (P3)**: Independent of US2 but requires US1 for test data. Adds new tool `list_recurring_events`.

### Parallel Opportunities

- T003 (tool description) can run in parallel with T001-T002 (different file)
- T007 (tool description) can run in parallel with T005-T006 (different file)
- T011 (tool description) can run in parallel with T009-T010 (different file)

---

## Implementation Strategy

### MVP First (US1 Only)

1. T001 — Add `recurrence` param to `create_quick_event()`
2. T002 — Update tool schema in assistant.py
3. T003 — Update tool description in prompts
4. T004 — Verify end-to-end
5. **STOP and VALIDATE**: Can create recurring events via WhatsApp
6. Deploy — Erin can immediately use "add cleaners every other Tuesday"

### Incremental Delivery

1. T001-T004 → US1 complete → Recurring event creation works
2. T005-T008 → US2 complete → Can cancel/modify recurring events
3. T009-T012 → US3 complete → Can list all recurring patterns
4. T013-T016 → Polish → CI passes, PR created

---

## Notes

- Total: 16 tasks
- Files modified: src/tools/calendar.py (3 functions), src/assistant.py (3 tool schemas), src/prompts/tools/calendar.md (3 descriptions), tests/test_prompts.py (count update)
- No new Python dependencies — Google Calendar API already supports RRULE natively
- Claude generates RRULE strings from natural language — no custom parsing needed
- The key insight: Google Calendar API accepts `"recurrence": ["RRULE:..."]` in the event body — this is the only code change needed for US1
