# Tasks: Smart Daily Planner

**Input**: Design documents from `/specs/017-smart-daily-planner/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new dependencies needed. Only US3 requires a new file — setup is minimal.

*(No setup tasks — existing Python 3.12 + FastAPI project. US3's new file is created within its story phase.)*

---

## Phase 2: User Story 1 — Calendar-Aware Plan Generation (Priority: P1) MVP

**Goal**: Claude treats existing calendar events (including recurring ones) as fixed, immovable blocks when generating daily plans. Erin never has to remind the bot about events already on her calendar.

**Independent Test**: Ask "plan my day" on a weekday with Vienna's school events on the calendar. The plan should include drop-off and pickup blocks without being told.

### Implementation for User Story 1

- [x] T001 [US1] Add calendar-aware planning rules to SYSTEM_PROMPT in src/assistant.py. After rule 9 (which calls get_daily_context), add new rules: "**Calendar-aware planning (CRITICAL):** 9a. When generating a daily plan, the calendar events returned by get_daily_context are **FIXED, IMMOVABLE blocks**. NEVER omit them, move them, or schedule activities that overlap with them. These include recurring events (school drop-off, swim lessons, appointments) — they appear automatically from the calendar. 9b. Build the plan AROUND existing calendar events. First lay out all fixed blocks from the calendar, then fill remaining open time slots with planned activities, backlog items, and routines. 9c. If existing calendar events overlap with each other, flag the conflict to Erin and ask how she wants to handle it. 9d. If the calendar is unreachable, generate the plan from backlog and routines, noting that calendar events could not be loaded."
- [x] T002 [US1] Verify calendar-aware rules: read src/assistant.py and confirm the new rules 9a-9d are present after rule 9. Check that get_daily_context already returns calendar events from all 3 calendars (Jason, Erin, Family) by reading src/context.py get_daily_context function.

**Checkpoint**: Claude now treats existing calendar events as immovable blocks. School drop-off/pickup appear automatically in plans.

---

## Phase 3: User Story 2 — Confirm Before Writing to Calendar (Priority: P1)

**Goal**: The bot presents a draft plan and waits for explicit confirmation before writing to Google Calendar. No more 3+ calendar rewrites per session.

**Independent Test**: Ask "plan my day," review the draft, request one change, approve, and verify only the final version appears on the calendar.

**Depends on**: No hard dependency on US1 (different rules), but best implemented after US1 since they modify the same section of the system prompt.

### Implementation for User Story 2

- [x] T003 [US2] Replace rule 14 in SYSTEM_PROMPT in src/assistant.py. Change the current rule 14 ("After generating the plan, write time blocks to Erin's Google Calendar using write_calendar_blocks so they appear in her Apple Calendar with push notifications") to: "**Confirm before writing (CRITICAL):** 14. After generating the daily plan, present it as a **DRAFT** for review. Say something like 'Here's your plan — want me to add it to your calendar?' or 'Ready to write this to your calendar?' 14a. Do NOT call write_calendar_blocks until Erin explicitly confirms (e.g., 'yes,' 'looks good,' 'add it,' 'write it'). 14b. If Erin requests changes ('move gym to 10 AM,' 'add a walk at 2,' 'remove the laundry block'), adjust the plan and re-present the updated draft. Ask for confirmation again. 14c. If Erin declines ('never mind,' 'skip the calendar,' 'no'), do NOT write to calendar. She still has the plan in chat. 14d. When triggered by the automated morning briefing (7 AM n8n), ALWAYS present the plan as a draft — never auto-write. Wait for Erin's WhatsApp reply to confirm. 14e. When writing to calendar after confirmation, report the number of blocks written (e.g., 'Done! Wrote 6 blocks to your calendar.')."
- [x] T004 [US2] Verify confirm-before-write rules: read src/assistant.py and confirm rule 14 has been replaced with the draft-then-confirm pattern (rules 14, 14a-14e). Confirm the old auto-write language is gone.

**Checkpoint**: Plans are presented as drafts. Calendar writes only happen after Erin says "yes." Morning briefing also waits for confirmation.

---

## Phase 4: User Story 3 — Drive Time Buffers (Priority: P2)

**Goal**: The bot knows drive times to common destinations and automatically adds travel buffers between activities at different locations.

**Independent Test**: Ask for a plan that includes the gym and school pickup — the plan should include 5-minute and 10-minute drive times without being told.

**Depends on**: Independent of US1 and US2 (different files + separate rules). Can run in parallel.

### Implementation for User Story 3

- [x] T005 [P] [US3] Create src/drive_times.py — drive time storage module. Follow the same pattern as src/routines.py (in-memory dict + atomic JSON writes to data/drive_times.json). Implement: (1) `_load_drive_times()` — load from JSON on module init, (2) `_save_drive_times()` — atomic write (write .tmp then rename), (3) `get_drive_times() -> str` — return all stored drive times as formatted string for Claude, (4) `save_drive_time(location: str, minutes: int) -> str` — add or update a drive time entry (normalize location to lowercase, validate minutes 1-120, cap at 20 entries), (5) `delete_drive_time(location: str) -> str` — remove a stored drive time. Storage format: `{"gym": {"minutes": 5, "updated": "ISO"}, ...}`.
- [x] T006 [US3] Register drive time tools in src/assistant.py. Add 3 new tools to the tools list: (1) `get_drive_times` — no parameters, returns all stored drive times, (2) `save_drive_time` — parameters: location (string), minutes (integer), (3) `delete_drive_time` — parameter: location (string). Add handler functions `_handle_get_drive_times`, `_handle_save_drive_time`, `_handle_delete_drive_time` that call the corresponding functions from src/drive_times.py. Add entries to the TOOL_HANDLERS dict.
- [x] T007 [US3] Add drive time rules to SYSTEM_PROMPT in src/assistant.py. After rule 15b (routines), add: "**Drive time buffers:** 15c. When generating a daily plan, call get_drive_times to check for stored travel times. If the plan includes activities at different locations, automatically insert travel buffer blocks (e.g., '🚗 Drive to gym — 5 min') between activities at different locations. 15d. If two consecutive activities are at the same location (e.g., both at home), do NOT add a drive buffer between them. 15e. If no drive time is stored for a location, generate the plan without a buffer for that location — do not ask. 15f. When a user mentions a drive time in conversation (e.g., 'the park is 15 minutes away,' 'gym is actually 10 minutes now'), call save_drive_time to store or update it. Confirm what was saved."
- [x] T008 [US3] Add drive times to daily context output in src/context.py. In the `get_daily_context()` function, after the calendar events section and before the return, import and call `get_drive_times()` from `src.drive_times` and append the result to the context string under a "Drive times" header. This way Claude sees drive times automatically during plan generation without needing a separate tool call.
- [x] T009 [US3] Verify drive time module: read src/drive_times.py and confirm it follows the atomic JSON pattern. Read src/assistant.py and confirm the 3 new tools are registered with handlers. Read src/context.py and confirm drive times are included in daily context output.

**Checkpoint**: Drive times stored persistently. Travel buffers auto-inserted in plans. Erin can add/update drive times via conversation.

---

## Phase 5: Polish & Deployment

**Purpose**: Deploy, validate end-to-end, and close GitHub issue.

- [x] T010 Commit all changes, push to branch `017-smart-daily-planner`, create PR, and deploy to NUC via `./scripts/nuc.sh deploy`.
- [x] T011 Run quickstart.md Scenarios 1-2 (calendar-aware planning) against production: send "plan my day" on a weekday with school events on the calendar, verify drop-off and pickup appear as fixed blocks.
- [x] T012 Run quickstart.md Scenarios 3-5 (confirm-before-write) against production: send "plan my day," verify draft is presented, request a change, approve, verify calendar blocks written only once.
- [x] T013 Run quickstart.md Scenarios 7-10 (drive times) against production: store a drive time via conversation, request a plan with that location, verify buffer appears.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A — no setup needed
- **US1 (Phase 2)**: T001-T002 — system prompt rules in src/assistant.py
- **US2 (Phase 3)**: T003-T004 — system prompt rules in src/assistant.py (same file as US1, different rules)
- **US3 (Phase 4)**: T005-T009 — new file src/drive_times.py + rules in src/assistant.py + context.py update
- **Polish (Phase 5)**: T010-T013 — depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Independent. Adds rules 9a-9d to src/assistant.py.
- **US2 (P1)**: Independent of US1 functionally, but modifies same file (src/assistant.py). Best done sequentially after US1 to avoid merge conflicts.
- **US3 (P2)**: Independent. Creates new file src/drive_times.py. T006-T007 modify src/assistant.py (same file as US1/US2), so best done after US1/US2.

### Parallel Opportunities

- T005 (new file) can run in parallel with T001-T004 (different file)
- T001 and T003 are sequential (same file, same area)
- T006, T007, T008 are sequential with each other and with US1/US2 tasks (shared files)

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete T001-T002 (calendar-aware rules)
2. Complete T003-T004 (confirm-before-write rules)
3. **STOP and VALIDATE**: Deploy and test with Erin — these two changes eliminate 90% of the friction
4. Deploy if ready — Erin immediately gets better planning

### Incremental Delivery

1. T001-T002 → US1 complete → Calendar events are fixed blocks
2. T003-T004 → US2 complete → Draft-then-confirm pattern works
3. T005-T009 → US3 complete → Drive time buffers auto-inserted
4. T010-T013 → Deployed and validated on NUC

---

## Notes

- Total: 13 tasks
- US1: 2 tasks (system prompt only)
- US2: 2 tasks (system prompt only)
- US3: 5 tasks (new module + tools + rules + context integration)
- Polish: 4 tasks (deploy + validation)
- Primary change is system prompt rules in src/assistant.py (~30 lines of prompt text)
- One new file: src/drive_times.py (~80 lines, following routines.py pattern)
- One small edit to src/context.py (append drive times to context output)
- Closes GitHub Issue #21 (Smarter daily planning)
