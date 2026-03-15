# Feature Specification: Calendar Reliability

**Feature Branch**: `037-calendar-reliability`
**Created**: 2026-03-15
**Status**: Draft
**Input**: User description: "Fix AM/PM time creation bug, enforce recurring event usage, time-aware responses — issues identified from Erin's chat history. Previous prompt-level fixes (016, 024, 6bb0c83) didn't fully resolve these."

## Context: Why Previous Fixes Failed

Three prior attempts addressed calendar issues at the **prompt level** (telling the LLM to format times correctly). All were deployed but the bugs persist:

1. **Feature 016** (Time Awareness): Added rules 11a-11e telling Claude to check current time before generating schedules. Added `[Current time: ...]` prefix to messages.
2. **Commit 6bb0c83** (24-Hour Format): Added rule 11f with explicit conversion examples ("1 PM = 13, 2 PM = 14... NEVER output T01:30 when you mean 1:30 PM").
3. **Feature 024** (Recurring Events): Implemented full RRULE support in `create_quick_event` tool with natural language examples in tool schema.

**Why they failed**: Prompt-level instructions are suggestions, not guarantees. The LLM still occasionally generates `T01:30` instead of `T13:30` for 1:30 PM. The recurring event tool exists but the LLM creates individual events anyway. **The fix must be at the code level** — validate and correct times before they reach the calendar API, and enforce recurring event patterns programmatically.

### Evidence from Erin's Chats

**AM/PM Bug (March 2-9, daily context output):**
```
- 1:00 AM - 1:30 AM: Backlog: Create car emergency kit list
- 2:00 AM - 2:30 AM: Prep for Piper pickup & swim
- 4:00 AM - 5:00 AM: Swim lessons - Erin brings girls
- 5:00 AM - 5:30 AM: Return home & dinner prep
```
These are clearly 1 PM, 2 PM, 4 PM, 5 PM events. The events were **created** with wrong times by the `write_calendar_blocks` tool and stored incorrectly in Google Calendar. The display code (`_format_event`) reads them back correctly — they're just stored wrong.

**Erin's frustration (two separate complaints):**
> Turn 11: "Check the time before sending me info. It's noon"
> Turn 77: "Check the time before sending me reminders."

**Recurring events not used (March 2):**
> "Can you populate our Google calendar? Starting today, every other Tuesday the cleaners come at 10am-1pm."
> "Add the next few dates. As many as you can"

The bot created 7 individual events instead of one recurring event, despite RRULE support being fully implemented.

## Clarifications

### Session 2026-03-15

- Q: Should the system clean up existing corrupted calendar events? → A: One-time cleanup of future-dated corrupted events only, but confirm with the user (Erin) before making changes. Present suspected wrong-time events in small batches with simple A/B/C response options (e.g., "A: Fix all, B: Skip, C: Let me review one by one"). Leave past events untouched. Prevention of future corruption is the primary goal.
- Q: How aggressively should the time validator correct suspected AM/PM errors? → A: Aggressive — shift any event between midnight and 8 AM unless the summary explicitly matches early-morning keywords (e.g., workout, wake up, breakfast, morning routine). For a family calendar, "2 AM swim lessons" is always wrong. Log all corrections.
- Q: Should the user be notified when the system auto-corrects a time? → A: Yes, brief inline note in the response (e.g., "(corrected: 2 AM → 2 PM)") so the user can see what was fixed. Can be turned off later once things stabilize.

## User Scenarios & Testing

### User Story 1 - Calendar Events Created at Correct Times (Priority: P1)

When the assistant creates calendar events from natural language time descriptions (e.g., "swim at 4 PM", "pickup at 2:30"), the events must appear at the correct time in Google Calendar. The system must validate and correct times at the code level, not rely solely on the LLM to format ISO strings correctly.

**Why this priority**: This is a data corruption bug. Every wrong-time event Erin sees erodes trust and requires manual calendar editing. It has persisted through two prior prompt-level fix attempts.

**Independent Test**: Create a calendar block with summary "Test event" at "2:30 PM" and verify the Google Calendar event start time is `T14:30:00`, not `T02:30:00`.

**Acceptance Scenarios**:

1. **Given** the assistant creates a batch of daily schedule blocks via `write_calendar_blocks`, **When** any event's start time falls between midnight and 8 AM but its summary contains afternoon/evening context (e.g., "pickup", "dinner", "swim"), **Then** the system detects the likely AM/PM error, corrects the hour by adding 12, and logs a warning.
2. **Given** a batch of daily schedule blocks where all events fall between midnight and 8 AM (a pattern indicating systematic 12-hour shift), **When** the batch is validated, **Then** the system applies 12-hour correction to events whose summaries don't match early-morning activities.
3. **Given** a valid early-morning event (e.g., "7 AM workout"), **When** the event is validated, **Then** the system correctly preserves the AM time without false correction.
4. **Given** a single event created via `create_quick_event` with an explicit ISO time like `T14:30:00`, **When** the event is submitted, **Then** no correction is applied (it's already correct).

---

### User Story 2 - Recurring Events Created from Natural Language (Priority: P2)

When a user describes a repeating pattern ("every other Tuesday", "weekly on Mondays", "every Friday at 3"), the system creates a single recurring calendar event, not multiple individual events.

**Why this priority**: The RRULE tool already exists and works. Individual events can't be edited/deleted as a series, waste API calls, and clutter the calendar. This is a prompt reinforcement issue backed by code-level detection.

**Independent Test**: Send "cleaners come every other Tuesday at 10am" and verify exactly one Google Calendar event is created with an RRULE pattern, not 7+ individual events.

**Acceptance Scenarios**:

1. **Given** a user says "every other Tuesday the cleaners come at 10am-1pm", **When** the assistant processes the request, **Then** it creates one recurring event with a bi-weekly RRULE, not multiple individual events.
2. **Given** a user says "add my Monday gym class at 9am, I go every week", **When** the assistant processes the request, **Then** it creates a weekly recurring event.
3. **Given** a user says "remind me about my appointment next Thursday at 2pm", **When** the assistant processes the request, **Then** it creates a single one-time event (not recurring), because no repeating pattern was expressed.
4. **Given** the assistant is about to call `create_quick_event` multiple times in sequence for the same recurring pattern, **When** the system detects 3+ events with identical summaries and regular intervals, **Then** it intervenes to consolidate into a single recurring event.

---

### User Story 3 - Time-Aware Schedule Responses (Priority: P3)

When a user asks about their schedule or "what should I do now", the response should be anchored to the current time — showing only remaining events, not replaying the full day's completed schedule.

**Why this priority**: Erin had to tell the bot twice to "check the time." The timestamp injection (Feature 016) is working, but the daily context output returns all events regardless of time, so the LLM sometimes presents morning events at 2 PM.

**Independent Test**: At 2 PM, request daily context and verify that morning events are clearly marked as past or omitted from the "what's next" output.

**Acceptance Scenarios**:

1. **Given** it is 2 PM and the user asks "what should I do?", **When** the daily context is generated, **Then** morning events are marked as completed or omitted, and the response focuses on remaining afternoon/evening events.
2. **Given** it is 8 AM and the user asks "schedule my day", **When** the daily context is generated, **Then** the full day is shown since nothing has passed yet.
3. **Given** it is 9 PM and the user asks "what's left today?", **When** the daily context is generated, **Then** the response indicates the day's events are effectively complete.

---

### User Story 4 - One-Time Cleanup of Existing Corrupted Events (Priority: P2)

After deployment, the system runs a one-time scan of future-dated calendar events to detect likely AM/PM corruptions. Before making changes, it messages the user (Erin) via WhatsApp with a summary of suspected wrong-time events, grouped in small batches, with simple response options to approve or skip fixes.

**Why this priority**: Erin has corrupted future events on her calendar right now. Prevention alone won't fix what's already there. But modifying calendar events without confirmation risks breaking events she's already manually corrected.

**Independent Test**: Trigger the cleanup scan and verify it finds known corrupted events, presents them to Erin with clear options, and only modifies events she approves.

**Acceptance Scenarios**:

1. **Given** the cleanup scan finds 12 future-dated events with suspected AM/PM errors, **When** it messages Erin, **Then** it groups them into batches of 5 or fewer with simple options like "A: Fix all 5, B: Skip these, C: Show me each one."
2. **Given** Erin replies "A" to a batch, **When** the system processes the approval, **Then** it corrects all events in that batch (adds 12 hours to the start/end times) and confirms the changes.
3. **Given** Erin replies "C" to review individually, **When** the system shows each event, **Then** it presents: event name, current time (wrong), proposed time (corrected), and options "Y: Fix / N: Skip."
4. **Given** the cleanup scan finds zero corrupted future events, **When** the scan completes, **Then** it silently logs "no cleanup needed" without messaging the user.

---

### Edge Cases

- What happens when the LLM generates a valid ISO string that is genuinely at 2 AM (e.g., a late-night event, baby feeding, red-eye flight)? The validation must not false-positive on legitimately early times.
- What happens when daylight saving time changes? Events near the DST boundary must be handled correctly, especially for recurring events that span a DST transition.
- What happens when a user creates a recurring event, then later asks to modify "just this week's" occurrence? Single-occurrence exceptions should be supported (Feature 024 already handles this).
- What happens when `write_calendar_blocks` creates 20-30 blocks for a full week? The batch validation must handle the full set efficiently.
- What happens if the LLM provides a non-ISO time string (e.g., "1:30 PM")? The system logs a warning and passes it through — Google Calendar API will reject it, triggering a tool error the LLM can respond to. This is safer than guessing the format. Informal format parsing is deferred.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST validate all event start and end times at the code level before submitting to the calendar API. Any event with a start time between midnight and 8 AM MUST be shifted +12 hours unless its summary matches an explicit early-morning allowlist (e.g., "workout", "wake up", "breakfast", "morning routine", "gym").
- **FR-002**: The system MUST parse and normalize ISO 8601 time strings with Pacific timezone offset before calendar API submission. If the LLM provides a malformed or non-ISO time string, the system MUST log a warning and pass it through unchanged (Google Calendar API will reject invalid formats, which is a safer failure mode than guessing). Informal format parsing (e.g., "2:30 PM") is deferred to a future enhancement.
- **FR-003**: The system MUST detect when the assistant is about to create 3 or more individual events with identical or similar summaries at regular intervals, and prompt the assistant to use a recurring event with RRULE instead.
- **FR-004**: The daily context output MUST separate events into "completed" (past) and "upcoming" (future) groups based on the current time, so the assistant can present time-relevant information.
- **FR-005**: The system MUST preserve times for events whose summaries match the early-morning allowlist. All other events between midnight and 8 AM are assumed to be AM/PM errors and corrected. The allowlist must be configurable.
- **FR-006**: The system MUST log a warning whenever it auto-corrects a time, including the original value, corrected value, and the reason for correction. Additionally, the tool response MUST include a brief inline note (e.g., "(corrected: 2 AM → 2 PM)") so the assistant can relay the correction to the user. This inline notification is designed to be removable once corrections stabilize.
- **FR-007**: The system MUST handle daylight saving time transitions correctly when validating and creating events, particularly for recurring events that span DST boundaries.
- **FR-008**: The system MUST provide a one-time cleanup scan of future-dated calendar events, presenting suspected corruptions to the user in batches of 5 or fewer via WhatsApp with simple response options (fix all, skip, review individually), and only modifying events the user explicitly approves.

### Key Entities

- **Calendar Event**: Summary, start time (ISO 8601 with TZ), end time (ISO 8601 with TZ), optional recurrence rule (RRULE), color category, target calendar.
- **Daily Context**: Current time, completed events (past), upcoming events (future), action items, backlog summary.
- **Time Validation Result**: Original time, corrected time (if changed), correction reason, allowlist match status.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of calendar events created by the assistant display at the correct time — zero AM/PM inversions in a 2-week observation window after deployment.
- **SC-002**: When a user describes a repeating event pattern, the system creates a single recurring event at least 90% of the time (vs. multiple individual events).
- **SC-003**: When a user asks for their schedule after noon, the response focuses on remaining events — past events are either omitted or clearly marked as completed.
- **SC-004**: Zero "check the time" complaints from the user in the 2 weeks following deployment.
- **SC-005**: No false-positive time corrections — legitimate early-morning events (before 8 AM) are preserved unchanged when they are contextually appropriate.

## Assumptions

- The AM/PM bug originates from the LLM generating incorrect ISO hour values (T01 instead of T13) when creating events via `write_calendar_blocks`, not from a display/read bug. Evidence: `_format_event()` correctly formats whatever's stored; the stored times are wrong.
- The recurring event tool (`create_quick_event` with `recurrence` parameter) is functioning correctly at the API level — the issue is purely that the LLM doesn't use it.
- Google Calendar API correctly stores and returns timezone-aware ISO 8601 strings — the corruption happens before API submission.
- The `[Current time: ...]` injection from Feature 016 is working and available in the message context — the issue is that `get_daily_context` returns all events unfiltered, and the LLM doesn't always separate past from future.

## Dependencies

- Feature 016 (time awareness rules) — already deployed, provides timestamp injection
- Feature 024 (recurring event RRULE support) — already deployed, provides tool infrastructure
- Commit 6bb0c83 (24-hour format prompt rules) — already deployed, provides prompt guidance
