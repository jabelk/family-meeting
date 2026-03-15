# Tasks: Calendar Reliability

**Input**: Design documents from `/specs/037-calendar-reliability/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Define shared constants and the core validation utility that all user stories depend on.

- [x] T001 Define `EARLY_MORNING_ALLOWLIST` constant and `_is_early_morning_allowed()` helper in `src/tools/calendar.py`. The allowlist is a module-level `tuple[str, ...]` containing lowercase keyword fragments: workout, gym, exercise, run, jog, walk, wake up, wake, alarm, morning routine, breakfast, coffee, ski, skiing, flight, airport, travel, drive, feed, nursing. The helper takes a summary string and returns True if any allowlist keyword is found (case-insensitive substring match).

- [x] T002 Implement `_validate_event_time(start_time: str, end_time: str, summary: str) -> tuple[str, str, list[str]]` in `src/tools/calendar.py`. Per the contract in `contracts/tool-contracts.md`: parse start/end times via `datetime.fromisoformat()`, check if hour is between 0-7 (inclusive), if so check summary against allowlist via `_is_early_morning_allowed()`. If no allowlist match, add 12 hours to the time and append a human-readable correction message (e.g., `'"Swim lessons" corrected: 4:00 AM → 4:00 PM'`). If allowlist matches, preserve original time. Return `(corrected_start, corrected_end, corrections_list)`. Handle edge cases: times already in PM range (8-23) pass through unchanged; malformed time strings should be returned as-is with a warning logged.

- [x] T003 [P] Create `tests/test_calendar_validation.py` with unit tests for `_validate_event_time()`. Test cases: (1) afternoon event at 2 AM shifted to 2 PM, (2) "workout" at 6 AM preserved, (3) "gym" at 5 AM preserved, (4) "swim lessons" at 4 AM shifted to 4 PM, (5) event at 2 PM (14:00) passes through unchanged, (6) batch with mixed AM/PM events, (7) event at exactly 8 AM (boundary — should NOT be shifted), (8) empty/malformed time string handled gracefully. Also test `_is_early_morning_allowed()` with various summary strings.

**Checkpoint**: Core validation utility ready and tested. All user stories can now proceed.

---

## Phase 2: User Story 1 — Calendar Events Created at Correct Times (Priority: P1) 🎯 MVP

**Goal**: Every calendar event created by the assistant displays at the correct time — zero AM/PM inversions.

**Independent Test**: Create a calendar block with summary "Swim lessons" at `T04:00:00` and verify it's stored as `T16:00:00` in Google Calendar. Create "Breakfast" at `T07:00:00` and verify it stays at `T07:00:00`.

### Implementation for User Story 1

- [x] T004 [US1] Integrate `_validate_event_time()` into `batch_create_events()` in `src/tools/calendar.py` (lines 400-438). Before the `for evt in events_data` loop at line 424, call `_validate_event_time(evt["start_time"], evt["end_time"], evt["summary"])` and replace `evt["start_time"]` and `evt["end_time"]` with the corrected values. Collect all correction messages into a list. Return a tuple `(created_count, corrections_list)` instead of just `created_count` — update the return type and callers accordingly.

- [x] T005 [US1] Integrate `_validate_event_time()` into `create_quick_event()` in `src/tools/calendar.py` (lines 334-397). Before building `event_body` (around line 377), call `_validate_event_time(start_time, end_time or computed_end, summary)`. Replace the time values. If corrections were made, append the correction note to the return message string (e.g., `"\n⚠️ Time corrected: 2:00 AM → 2:00 PM"`).

- [x] T006 [US1] Update `_handle_write_calendar_blocks()` in `src/assistant.py` (lines 1328-1348) to handle the new return type from `batch_create_events()`. Extract the corrections list and append formatted correction notes to the response string per the contract format: `"\n⚠️ Time corrections applied:\n  - ..."`. Log each correction at WARNING level.

- [x] T007 [US1] Run `ruff check src/tools/calendar.py src/assistant.py` and `pytest tests/test_calendar_validation.py tests/ -x` to verify all changes pass lint and existing tests. Fix any regressions.

**Checkpoint**: All new calendar events are validated before Google Calendar API submission. AM/PM errors are auto-corrected with inline notes. This is the MVP — deploy and monitor.

---

## Phase 3: User Story 2 — Recurring Events from Natural Language (Priority: P2)

**Goal**: When a user describes a repeating pattern, the system creates one recurring event with RRULE, not multiple individual events.

**Independent Test**: Ask the bot "add cleaners every other Tuesday at 10am" and verify exactly one Google Calendar event is created with `RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU`.

### Implementation for User Story 2

- [x] T008 [US2] Add a new system prompt rule in `src/prompts/system/07-calendar-reminders.md` for recurring event detection. Add after the existing rules: "Rule XX: When a user mentions ANY repeating pattern (every, weekly, bi-weekly, biweekly, monthly, each Monday, every other, daily, twice a week), you MUST use the `recurrence` parameter on `create_quick_event` with an RRULE. NEVER create multiple individual events for a recurring pattern. If unsure whether the user means recurring, ask — but default to recurring if the language is clear."

- [x] T009 [US2] Strengthen recurring event instructions in `src/prompts/tools/calendar.md`. In the `create_quick_event` section, add a prominent warning: "⚠️ IMPORTANT: If the user describes a repeating event, you MUST use the `recurrence` parameter. Creating 3+ individual events for the same recurring activity is WRONG. One recurring event with RRULE replaces all of them." Add 2 more examples: "every weekday at 9am" → `RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR`, "twice a month on the 1st and 15th" → `RRULE:FREQ=MONTHLY;BYMONTHDAY=1,15`.

- [x] T010 [US2] Update `create_quick_event()` return message in `src/tools/calendar.py` (around line 396) to include the next 3-4 upcoming dates when a recurring event is created. **Depends on T005** (which also modifies `create_quick_event()` for time validation). After the insert, if `recurrence` was provided, query the event instances using `service.events().instances()` with `maxResults=4` and format the dates in the return string (e.g., "Next dates: Mar 17, Mar 31, Apr 14, Apr 28").

- [x] T010a [US2] Add recurring event detection in `src/assistant.py`. In the tool call handler, after `create_quick_event` returns successfully, check the current conversation's recent tool calls (from the messages list). If 3+ `create_quick_event` calls have been made in this conversation with identical or near-identical summaries and regular time intervals, append a warning to the tool response: "⚠️ You've created 3+ individual events with similar names. Consider using the `recurrence` parameter with an RRULE to create a single recurring event instead." This is a soft nudge — the LLM can still proceed, but the warning in the tool response makes it much more likely to self-correct.

**Checkpoint**: Recurring events are created correctly from natural language. The bot uses RRULE, confirms upcoming dates, and is warned if it falls back to creating individual events.

---

## Phase 4: User Story 3 — Time-Aware Schedule Responses (Priority: P3)

**Goal**: When a user asks for their schedule after morning, the response shows completed events separately from upcoming events.

**Independent Test**: At 2 PM Pacific, call `get_daily_context()` and verify output has separate "Completed" and "Upcoming" sections, with morning events under "Completed".

### Implementation for User Story 3

- [x] T011 [US3] Add `_split_events_by_time(events: list[dict], now: datetime) -> tuple[list[dict], list[dict]]` helper in `src/context.py`. Takes a list of event dicts (from Google Calendar API) and the current time. Returns `(completed, upcoming)` where completed events have `end.dateTime` before `now` and upcoming events have `start.dateTime` at or after `now`. Events currently in progress (started but not ended) go in upcoming. All-day events always go in upcoming.

- [x] T012 [US3] Update `get_daily_context()` in `src/context.py` (lines 118-235) to use `_split_events_by_time()`. After events are grouped by calendar source (partner1, partner2, family), split each group. Format the output with `✅ Completed:` and `📋 Upcoming:` sub-sections per the contract in `contracts/tool-contracts.md`. If there are no completed events (e.g., early morning), only show `📋 Upcoming:`. If all events are completed (late evening), show `✅ All done for today!` after the completed list.

- [x] T013 [US3] Run `pytest tests/ -x` to verify all existing tests pass with the new daily context output format. Update any tests that assert on the exact `get_daily_context()` output string to match the new completed/upcoming format.

**Checkpoint**: Daily context output is time-aware. Past events are visually separated from upcoming events.

---

## Phase 5: User Story 4 — One-Time Cleanup of Existing Corrupted Events (Priority: P2)

**Goal**: Scan future-dated calendar events for AM/PM errors, present to user in batches via WhatsApp, and fix only what the user approves.

**Independent Test**: Trigger `POST /api/v1/admin/calendar-cleanup` and verify suspected events are found and sent to Erin via WhatsApp in batches of ≤5 with A/B/C options.

### Implementation for User Story 4

- [x] T014 [US4] Implement `scan_corrupted_events() -> list[dict]` in `src/tools/calendar.py`. Scan all calendars (partner1, partner2, family) for future-dated events created by the assistant (filter by `extendedProperties.private.createdBy == "mombot"`). For each event, check if start time is between midnight and 8 AM and summary does NOT match the early-morning allowlist. Return list of dicts with: `event_id`, `calendar_name`, `summary`, `current_start` (formatted), `proposed_start` (formatted +12h), `current_end`, `proposed_end`, `calendar_id`.

- [x] T015 [US4] Implement `fix_corrupted_event(event_id: str, calendar_id: str) -> bool` in `src/tools/calendar.py`. Takes an event ID and calendar ID, fetches the event, shifts start and end times +12 hours, and updates via `service.events().update()`. Returns True on success, False on failure. Logs the correction.

- [x] T016 [US4] Add `POST /api/v1/admin/calendar-cleanup` endpoint in `src/app.py`. Auth via `N8N_WEBHOOK_SECRET` Bearer token (reuse existing `verify_shortcut_auth` pattern or a simpler header check). On trigger: call `scan_corrupted_events()`, group results into batches of 5, store batches in a module-level dict keyed by phone number. Send first batch to Erin via WhatsApp using the format from `contracts/tool-contracts.md`. Return JSON with `status`, `events_scanned`, `suspects_found`, `batches_queued`.

- [x] T017 [US4] Add cleanup response handler in `src/app.py`. When Erin responds to a cleanup batch message (detect by checking if there's an active cleanup session for her phone number): parse "A", "B", or "C" response. On "A": fix all events in current batch via `fix_corrupted_event()`, send confirmation, advance to next batch. On "B": skip batch, advance to next. On "C": send first event individually with Y/N options, process responses one at a time. When all batches processed, clear the session and send "Cleanup complete!" message.

- [x] T018 [US4] Run `ruff check src/` and `pytest tests/ -x` to verify all changes pass lint and tests.

**Checkpoint**: Cleanup scan can be triggered, finds corrupted events, and interactively fixes them with user confirmation.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup across all user stories.

- [x] T019 Run full test suite `pytest tests/ -v` and verify all 113+ tests pass with the new changes.
- [x] T020 Run `ruff check src/ && ruff format --check src/` and fix any lint/format issues.
- [ ] T021 Run quickstart.md validation: manually test each scenario from `specs/037-calendar-reliability/quickstart.md` against the deployed service.
- [ ] T022 Monitor Railway logs for 24 hours after deployment — verify zero AM/PM corrections are needed for new events (SC-001) and that the inline correction notes appear correctly when they are needed (FR-006).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (US1)**: Depends on Phase 1 (T001-T003) — needs `_validate_event_time()` utility
- **Phase 3 (US2)**: Independent of Phase 2 — prompt-only changes, no code dependencies
- **Phase 4 (US3)**: Independent of Phase 2 and 3 — modifies `context.py`, not `calendar.py` creation paths
- **Phase 5 (US4)**: Depends on Phase 1 (reuses `_is_early_morning_allowed()` from T001 and `scan_corrupted_events()` uses same heuristic)
- **Phase 6 (Polish)**: Depends on all previous phases

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 1 only — no dependencies on other stories
- **US2 (P2)**: No code dependencies — can start after Phase 1 or in parallel with US1
- **US3 (P3)**: No code dependencies — can start after Phase 1 or in parallel with US1/US2
- **US4 (P2)**: Depends on Phase 1 for allowlist — can run in parallel with US1/US2/US3

### Parallel Opportunities

- T001 and T003 can run in parallel (different files)
- T008 and T009 can run in parallel (different prompt files)
- US2 (prompt changes) and US3 (context.py changes) can run in parallel with US1 (calendar.py changes) — different files
- T010 depends on T005 (both modify `create_quick_event` in calendar.py) — run sequentially
- T014 and T015 can run in parallel (different functions, same file but independent)

---

## Parallel Example: After Phase 1 Completes

```bash
# All three user stories can start in parallel (different files):
US1: T004-T007 — modifies src/tools/calendar.py, src/assistant.py
US2: T008-T010 — modifies src/prompts/system/07-calendar-reminders.md, src/prompts/tools/calendar.md, src/tools/calendar.py (different function)
US3: T011-T013 — modifies src/context.py

# US4 can also start in parallel:
US4: T014-T018 — modifies src/tools/calendar.py (new functions), src/app.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: US1 — Time Validation (T004-T007)
3. **STOP and VALIDATE**: Deploy, monitor Erin's calendar for 24h
4. If zero AM/PM errors → MVP proven, continue to US2-US4

### Incremental Delivery

1. Phase 1 → Foundation ready
2. US1 (T004-T007) → Deploy → Monitor (MVP!)
3. US2 (T008-T010) → Deploy → Test with "every Tuesday" request
4. US3 (T011-T013) → Deploy → Test "what's my schedule?" at 2 PM
5. US4 (T014-T018) → Deploy → Trigger cleanup scan
6. Polish (T019-T022) → Final validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 is the MVP — deploy and validate before continuing
- US2 touches one function in calendar.py (`create_quick_event` return message) that US1 also touches — coordinate if working in parallel
- The cleanup (US4) is designed as a one-time operation, not a permanent feature
- All prompt changes (US2) should be tested by asking the bot recurring event questions via WhatsApp after deployment
