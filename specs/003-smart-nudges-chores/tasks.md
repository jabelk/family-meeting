# Tasks: Smart Nudges & Chore Scheduling

**Input**: Design documents from `/specs/003-smart-nudges-chores/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/nudge-endpoints.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add configuration and Notion database helpers shared by all nudge features

- [x] T001 Add NOTION_NUDGE_QUEUE_DB and NOTION_CHORES_DB environment variables to src/config.py and .env.example
- [x] T002 Document Nudge Queue and Chores Notion database creation steps in docs/notion-setup.md (Steps 10–11 per data-model.md schema)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Notion CRUD helpers and calendar extensions that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement Nudge Queue CRUD in src/tools/notion.py — create_nudge(summary, nudge_type, status, scheduled_time, event_id, message, context), query_pending_nudges(due_before), query_nudges_by_type(nudge_type, statuses), update_nudge_status(page_id, new_status), count_sent_today(), check_quiet_day()
- [x] T004 [P] Implement Chores CRUD in src/tools/notion.py — query_all_chores(), update_chore_completion(page_id, date), update_chore_preference(page_id, preference, preferred_days, frequency), seed_default_chores() per data-model.md seed data table
- [x] T005 [P] Add get_events_for_date_raw(calendar_id, date) to src/tools/calendar.py returning full Google Calendar event dicts (including conferenceData, description, start/end, creator) instead of formatted strings

**Checkpoint**: Foundation ready — Notion CRUD and calendar raw data available for all stories

---

## Phase 3: User Story 1 — Departure Nudges (Priority: P1) MVP

**Goal**: Automatically scan Erin's calendar and send WhatsApp departure reminders 15–30 minutes before events that require leaving the house. Support snooze, dismiss, quiet day, message batching, and daily cap.

**Independent Test**: Create a Google Calendar event 25 minutes from now → wait for n8n scan → verify WhatsApp nudge arrives ~15 min before the event. Reply "snooze" → verify 10-min delayed nudge. Reply "stop" → verify no more nudges for that event.

### Implementation for User Story 1

- [x] T006 [US1] Create src/tools/nudges.py — implement is_virtual_event(event_dict) using conferenceData detection and keyword matching ("call", "virtual", "remote", "online", "zoom", "meet", "teams", "webinar") per plan.md virtual event detection rules; also detect all-day events and assistant-created events
- [x] T007 [US1] Implement scan_upcoming_departures(hours_ahead=2) in src/tools/nudges.py — call get_events_for_date_raw() for Erin's and family calendars, filter out virtual events, skip events already in Nudge Queue (match by Event ID), create departure nudge records with Scheduled Time = event_start - 30 min (or immediate if <15 min away)
- [x] T008 [US1] Implement process_pending_nudges() in src/tools/nudges.py — query Nudge Queue for Status=Pending AND Scheduled Time <= now, check daily cap (count_sent_today() < 8), batch nudges within 5-min window into single messages (FR-011), send via WhatsApp with template fallback, update status to Sent
- [x] T009 [US1] Implement set_quiet_day() in src/tools/nudges.py — create quiet_day nudge record, cancel all Pending non-laundry nudges for today
- [x] T010 [US1] Add POST /api/v1/nudges/scan endpoint in src/app.py — protected by verify_n8n_auth, calls scan_upcoming_departures() then process_pending_nudges(), returns JSON response per contracts/nudge-endpoints.md schema, skips processing if check_quiet_day() is true
- [x] T011 [US1] Register set_quiet_day tool in src/assistant.py — add tool definition with no parameters, wire to nudges.set_quiet_day(), add snooze/dismiss natural language handling in system prompt (snooze → create new Pending nudge +10 min and update original to Snoozed; dismiss → update to Dismissed)
- [ ] T012 [US1] Create n8n workflow WF-009 (Nudge Scanner) — cron `*/15 7-20 * * *`, HTTP POST to /api/v1/nudges/scan with X-N8N-Auth header

**Checkpoint**: Departure nudges fully functional — Erin receives reminders before calendar events, can snooze/dismiss/quiet-day

---

## Phase 4: User Story 2 — Laundry Workflow Reminders (Priority: P1)

**Goal**: Erin tells the bot "started laundry" and receives timed reminders to move to dryer (~45 min) and when dryer is done (~60 min). Timing adapts to calendar conflicts. Follow-up nudge if laundry sits in washer too long.

**Independent Test**: Send "I started a load of laundry" → verify confirmation with times → wait 45 min (or check Nudge Queue) → verify washer-done nudge → reply "moved to dryer" → wait 60 min → verify dryer-done nudge.

### Implementation for User Story 2

- [ ] T013 [P] [US2] Create src/tools/laundry.py — implement start_laundry_session(washer_minutes=45, dryer_minutes=60): cancel any existing active laundry session (query Nudge Queue for laundry_* types with Pending/Sent status), generate session_id, create laundry_washer nudge (now + washer_minutes) and laundry_followup nudge (now + 2h45m), store dryer_minutes in Context JSON, check calendar for departure conflicts during expected dryer window
- [ ] T014 [US2] Implement advance_laundry() in src/tools/laundry.py — find active laundry session, create laundry_dryer nudge (now + dryer_minutes from session context), cancel pending laundry_followup nudge, check calendar for conflicts with dryer completion time
- [ ] T015 [US2] Implement cancel_laundry() in src/tools/laundry.py — find active laundry session, update all Pending laundry nudges for that session to Cancelled
- [ ] T016 [US2] Register start_laundry, advance_laundry, and cancel_laundry tools in src/assistant.py — start_laundry with optional washer_minutes/dryer_minutes params, advance_laundry with no params, cancel_laundry with no params; all wired to laundry.py functions; add natural language triggers in system prompt ("never mind" / "didn't do laundry" → cancel_laundry)

**Checkpoint**: Laundry workflow end-to-end — washer done, dryer done, follow-up, cancel, calendar conflict warnings all working

---

## Phase 5: User Story 3 — Intelligent Chore Suggestions (Priority: P2)

**Goal**: During free windows in Erin's day, proactively suggest chores that fit the available time. Suggestions consider day of week, childcare context, chore overdue score, and duration. Erin can respond "done" or "skip".

**Independent Test**: Ensure a 90-min free window exists in the calendar → wait for nudge scan during that window → verify chore suggestion arrives with duration context → reply "done" → verify chore marked completed in Notion.

### Implementation for User Story 3

- [ ] T017 [P] [US3] Create src/tools/chores.py — implement detect_free_windows(date) by comparing get_events_for_date_raw() results against routine templates from Family Profile page, return list of {start, end, duration_minutes} for gaps >= 15 min
- [ ] T018 [US3] Implement suggest_chore(free_window_minutes) in src/tools/chores.py — query Chores DB, filter by Duration <= free_window_minutes, calculate overdue score (days_since_last / frequency_days), boost if today matches Preferred Day, deprioritize disliked chores (still suggest if overdue > 2x), return top 1-2 suggestions per data-model.md chore selection algorithm
- [ ] T019 [US3] Implement complete_chore(chore_name) and skip_chore(chore_name) in src/tools/chores.py — complete: update Last Completed to today, increment Times Completed, mark associated nudge as Done; skip: mark nudge as Dismissed, track skipped chore for today (don't re-suggest)
- [ ] T020 [US3] Extend POST /api/v1/nudges/scan in src/app.py — after departure scanning, call detect_free_windows() and suggest_chore() for the next upcoming free window, create chore nudge in Nudge Queue with Context JSON containing chore_id and chore details; add chores_suggested to response
- [ ] T021 [US3] Register complete_chore and skip_chore tools in src/assistant.py — complete_chore with chore_name param, skip_chore with chore_name param, both wired to chores.py; seed default chores on first scan if Chores DB is empty

**Checkpoint**: Chore suggestions during free windows — context-aware suggestions, done/skip responses, overdue prioritization all working

---

## Phase 6: User Story 4 — Chore Preferences and History (Priority: P3)

**Goal**: Erin can tell the bot her chore preferences (frequency, preferred days, like/dislike) and ask what chores she's done recently. The bot tracks patterns and adapts suggestions over time.

**Independent Test**: Tell bot "I like to vacuum on Wednesdays" → verify preference saved → on next Wednesday verify vacuum is prioritized. Ask "what chores have I done this week?" → verify formatted summary.

### Implementation for User Story 4

- [ ] T022 [P] [US4] Implement set_chore_preference(chore_name, preference, preferred_days, frequency) in src/tools/chores.py — fuzzy-match chore_name against Chores DB, update matching fields (only non-None params), return confirmation
- [ ] T023 [P] [US4] Implement get_chore_history(days=7) in src/tools/chores.py — query Nudge Queue for nudge_type=chore AND Status=Done within date range, join with Chores DB for names and durations, return formatted summary grouped by date
- [ ] T024 [US4] Register set_chore_preference and get_chore_history tools in src/assistant.py — set_chore_preference with chore_name (required), preference/preferred_days/frequency (optional); get_chore_history with optional days param; update system prompt with natural language examples ("I hate cleaning bathrooms" → preference=dislike)

**Checkpoint**: Chore preferences and history — Erin can set preferences conversationally, view history, and suggestions adapt to preferences

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, deployment, and end-to-end validation

- [ ] T025 Update system prompt in src/assistant.py with comprehensive nudge interaction guidelines — warm encouraging tone (NFR-003), examples of snooze/dismiss/done/skip responses, quiet day activation, laundry natural language triggers
- [ ] T026 Deploy to NUC via ./scripts/nuc.sh deploy and push .env with new Notion database IDs via ./scripts/nuc.sh env
- [ ] T027 Run quickstart.md validation — Test 1 (departure nudge), Test 2 (virtual exclusion), Test 3 (laundry workflow), Test 4 (chore suggestion), Test 5 (quiet day), Test 6 (daily cap)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001 for config vars) — BLOCKS all user stories
- **US1 Departure Nudges (Phase 3)**: Depends on Foundational (T003 for Nudge CRUD, T005 for raw calendar)
- **US2 Laundry Workflow (Phase 4)**: Depends on Foundational (T003 for Nudge CRUD) + US1 (T008 for process_pending_nudges reuse, T010 for scan endpoint)
- **US3 Chore Suggestions (Phase 5)**: Depends on Foundational (T003 + T004 for Chores CRUD) + US1 (T010 for scan endpoint extension)
- **US4 Chore Preferences (Phase 6)**: Depends on US3 (T019 for chore completion tracking, Chores DB seeded)
- **Polish (Phase 7)**: Depends on all stories complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — fully independent MVP
- **US2 (P1)**: Reuses nudge processing pipeline from US1 (T008, T010)
- **US3 (P2)**: Reuses scan endpoint from US1 (T010), needs Chores CRUD from Foundational (T004)
- **US4 (P3)**: Builds on Chores DB and completion tracking from US3

### Within Each User Story

- Notion CRUD before business logic
- Business logic before endpoint/tool registration
- Endpoint before n8n workflow
- Core implementation before system prompt updates

### Parallel Opportunities

**Phase 2 — Foundational**:
```
T003 (Nudge Queue CRUD) || T004 (Chores CRUD) || T005 (calendar raw)
```

**Phase 4 — US2**:
```
T013 (laundry.py core) can start while US1 is being finalized
```

**Phase 5 — US3**:
```
T017 (free window detection) || T018 development can start once T017 interface is defined
```

**Phase 6 — US4**:
```
T022 (set_chore_preference) || T023 (get_chore_history) — different functions, no dependencies
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T005) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T006–T012)
4. **STOP and VALIDATE**: Deploy, create test calendar event, verify departure nudge arrives via WhatsApp
5. If working: proceed to US2

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Departure Nudges) → Deploy → Erin starts getting departure reminders (MVP!)
3. US2 (Laundry Workflow) → Deploy → Erin can trigger laundry timers
4. US3 (Chore Suggestions) → Deploy → Erin gets chore suggestions during free windows
5. US4 (Chore Preferences) → Deploy → Erin can customize and review chore history
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after its phase completes
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Manual prerequisite: Erin must create Nudge Queue and Chores databases in Notion (documented in T002)
