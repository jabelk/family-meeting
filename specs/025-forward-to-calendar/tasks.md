# Tasks: Forward-to-Calendar

**Input**: Design documents from `/specs/025-forward-to-calendar/`
**Prerequisites**: spec.md (no plan.md needed — prompt-engineering feature extending existing tools)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new dependencies needed — Claude already has calendar tools, image processing, and drive time data. No setup tasks.

*(No tasks)*

---

## Phase 2: Foundational

**Purpose**: Add `location` support to the calendar event tool — needed by all user stories but missing from `create_quick_event()`.

- [x] T001 Add optional `location` parameter to `create_quick_event()` in src/tools/calendar.py. When provided, add `"location": location` to the event body dict before the `events().insert()` call. When not provided, behavior is unchanged.
- [x] T002 Update the `create_quick_event` tool schema in src/assistant.py. Add `location` property: `{"type": "string", "description": "Physical address or place name for the event. Shown in calendar event details and enables map links."}`. Do NOT add to `required`.
- [x] T003 [P] Update the `create_quick_event` tool description in src/prompts/tools/calendar.md. Add a note that `location` can be included for events with a physical address (doctor offices, schools, restaurants, etc.). The location appears in the calendar event and enables map links on mobile.

**Checkpoint**: `create_quick_event` now supports location. Foundation ready for all user stories.

---

## Phase 3: User Story 1 — Extract Event from Forwarded Text (Priority: P1) MVP

**Goal**: When Erin forwards a text containing an appointment confirmation, the bot detects the appointment, extracts details, and offers to create a calendar event after confirmation.

**Independent Test**: Forward "Your appointment with Dr. Smith is confirmed for March 10 at 2:00 PM at 1234 S Virginia St" to the bot. Bot presents extracted details, asks for confirmation, creates event on confirm.

### Implementation for User Story 1

- [x] T004 [US1] Add a new system prompt section `src/prompts/system/09-forward-to-calendar.md` with instructions for detecting appointment-like content in messages. Rules should cover: (1) When a message contains appointment/confirmation/reservation/scheduled language with a date and time, proactively offer to create a calendar event. (2) Extract: title/description, date, start time, end time (if present), location (if present). (3) Present extracted details to the user and ask for confirmation before creating. (4) Never auto-create without explicit user approval. (5) If date or time is ambiguous, ask for clarification. (6) Recognize cancellation language ("has been cancelled", "appointment cancelled") and offer to find and remove the matching event instead. (7) Ignore messages that are clearly not appointments (jokes, news, casual chat). (8) If multiple dates are mentioned, ask which to create events for. (9) If the date has already passed, flag it and ask if user still wants to create the event. (10) Default to family calendar; ask which calendar if unclear. Include 4-5 examples of appointment patterns: doctor confirmation, service window ("between 1-3 PM"), school event, playdate.
- [ ] T005 [US1] Verify US1 works end-to-end: start the app locally or use deployed instance. Send a test message like "Your appointment with Dr. Smith is confirmed for March 15 at 2:00 PM at 1234 S Virginia St, Reno NV." Confirm: (1) bot detects appointment pattern without being asked, (2) bot presents extracted details (title, date, time, location), (3) bot asks for confirmation, (4) after confirming, event appears in Google Calendar with location field populated. Clean up test event after verification.

**Checkpoint**: Forwarded text appointments auto-detected and converted to calendar events. MVP complete.

---

## Phase 4: User Story 2 — Extract Event from Screenshot/Image (Priority: P2)

**Goal**: When Erin sends a screenshot of an appointment confirmation, the bot reads the image, extracts details, and offers to create a calendar event — same flow as text.

**Depends on**: US1 (same system prompt rules apply; image pipeline already sends images to Claude with the system prompt)

**Independent Test**: Send a screenshot of an appointment confirmation. Bot extracts details from the image and offers to create the event.

### Implementation for User Story 2

- [x] T006 [US2] Update src/prompts/system/09-forward-to-calendar.md to explicitly mention that these appointment detection rules also apply when the user sends a photo/screenshot. Add a note: "When the user sends an image, look for appointment details visible in the screenshot (confirmation screens, calendar entries, text message screenshots). Apply the same extraction and confirmation flow as for text messages. If the image is unclear or details are hard to read, ask the user to clarify rather than guessing."
- [ ] T007 [US2] Verify US2 works: send a screenshot of an appointment confirmation (e.g., a photo of a text message saying "Your dentist appointment is March 20 at 10:30 AM"). Confirm: (1) bot reads the image and detects appointment content, (2) bot presents extracted details, (3) after confirmation, event is created. Clean up test event.

**Checkpoint**: Both text and image appointment forwarding work.

---

## Phase 5: User Story 3 — Drive Time Buffer (Priority: P3)

**Goal**: When a forwarded appointment includes a location with known drive time data, the bot offers to add a travel buffer event before the appointment.

**Depends on**: US1 (need appointment detection working first)

**Independent Test**: Forward a message with a location that exists in drive_times.json. Bot offers to add a travel buffer before the appointment.

### Implementation for User Story 3

- [x] T008 [US3] Update src/prompts/system/09-forward-to-calendar.md to add drive time buffer instructions. Add a rule: "After the user confirms an appointment event that includes a location, check if drive time data is available for that location using the `get_drive_times` tool. If a matching location is found, offer to create an additional 'Travel to [location]' calendar block before the appointment, starting [drive_minutes] minutes before the event. If no drive time data exists for the location, skip the offer — do not ask the user to add drive time data during this flow." Include an example: "I see Dr. Smith's office is about 15 minutes away. Want me to add a travel block from 1:30-1:45 PM before your 2:00 PM appointment?"
- [ ] T009 [US3] Verify US3 works: ensure a test location exists in drive_times.json (e.g., "doctor" → 15 minutes). Forward a message mentioning that location. Confirm: (1) bot detects appointment, (2) after confirmation, bot offers drive time buffer, (3) if accepted, travel block event is created before the appointment.

**Checkpoint**: Full forward-to-calendar flow — detect, extract, confirm, create, optional drive time buffer.

---

## Phase 6: Polish & Validation

**Purpose**: Final checks and deployment.

- [x] T010 Run `ruff check src/` and `ruff format --check src/` — fix any issues in modified files.
- [x] T011 Run `pytest tests/` — verify all existing tests still pass.
- [x] T012 Update the tool count in tests/test_prompts.py if the total changed (currently asserts 73). Check by counting `## ` headers in all src/prompts/tools/*.md files.
- [ ] T013 Commit all changes, push to branch, create PR for merge to main.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A
- **Foundational (Phase 2)**: T001-T003 — Add location support to create_quick_event. Blocks US1.
- **US1 (Phase 3)**: T004-T005 — Depends on Phase 2. Core prompt engineering.
- **US2 (Phase 4)**: T006-T007 — Depends on US1 (extends same prompt file).
- **US3 (Phase 5)**: T008-T009 — Depends on US1 (extends same prompt file).
- **Polish (Phase 6)**: T010-T013 — After all user stories.

### User Story Dependencies

- **US1 (P1)**: Independent — MVP. New system prompt section + existing tools.
- **US2 (P2)**: Depends on US1 (same prompt file, adds image-specific guidance).
- **US3 (P3)**: Depends on US1 (same prompt file, adds drive time buffer logic).

### Parallel Opportunities

- T003 (tool description) can run in parallel with T001-T002 (different file)
- T001 and T002 are sequential (same logical change across two files)

---

## Implementation Strategy

### MVP First (US1 Only)

1. T001-T003 — Add location param to create_quick_event
2. T004 — Write the forward-to-calendar system prompt section
3. T005 — Verify end-to-end
4. **STOP and VALIDATE**: Can detect and create events from forwarded text
5. Deploy — Erin can immediately forward appointment confirmations

### Incremental Delivery

1. T001-T005 → US1 complete → Text appointment forwarding works
2. T006-T007 → US2 complete → Screenshot appointment forwarding works
3. T008-T009 → US3 complete → Drive time buffers offered
4. T010-T013 → Polish → CI passes, PR created

---

## Notes

- Total: 13 tasks
- Files modified: src/tools/calendar.py (1 param), src/assistant.py (1 schema property), src/prompts/tools/calendar.md (1 description update), src/prompts/system/09-forward-to-calendar.md (new file), tests/test_prompts.py (count check)
- No new Python dependencies — this is primarily a prompt engineering feature
- Claude already understands appointment language — the system prompt just needs to instruct it to proactively detect and act on it
- The key insight: forwarded messages arrive as regular text/images through the existing pipeline. Claude just needs instructions to recognize appointment patterns and offer to create calendar events.
- Image handling (US2) requires no code changes — images already go through the vision pipeline with the system prompt. Adding image guidance to the prompt section is sufficient.
