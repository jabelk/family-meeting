# Feature Specification: Recurring Calendar Events

**Feature Branch**: `024-recurring-calendar-events`
**Created**: 2026-03-09
**Status**: Draft
**Input**: GitHub Issue #20 — "Erin asked to add cleaners every other Tuesday. The bot had to add them one at a time."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Recurring Event from Natural Language (Priority: P1)

As Erin, I want to say "add cleaners every other Tuesday at 10am-1pm starting March 3" and have the bot create a single recurring calendar event instead of manually adding each occurrence one by one.

**Why this priority**: This is the core pain point from Issue #20. Erin already tried to do this and the bot had to create individual events — she said "add the next few dates, as many as you can." A single recurring event is the standard solution.

**Independent Test**: Send "add swim class every Monday at 4pm for 8 weeks" in WhatsApp. Bot responds with confirmation. Google Calendar shows a recurring event with the correct pattern visible in event details.

**Acceptance Scenarios**:

1. **Given** the bot is running, **When** Erin says "add cleaners every other Tuesday at 10am to 1pm starting March 3", **Then** a single recurring event is created on the family calendar with biweekly Tuesday recurrence, and the bot confirms with the pattern and next few dates.
2. **Given** the bot is running, **When** Erin says "Vienna has swim every Monday at 4pm for 8 weeks starting March 10", **Then** a recurring event is created with weekly Monday recurrence ending after 8 occurrences, and the bot confirms.
3. **Given** the bot is running, **When** Erin says "add family dinner every Sunday at 6pm", **Then** a weekly recurring event is created with no end date (repeats indefinitely), and the bot confirms.
4. **Given** the bot is running, **When** Erin says "date night first Friday of every month at 7pm", **Then** a monthly recurring event is created on the first Friday, and the bot confirms.

---

### User Story 2 - Modify or Cancel Recurring Events (Priority: P2)

As Erin, I want to cancel or modify a recurring event series through the bot, such as "cancel the cleaners" or "move swim class to 4:30pm."

**Why this priority**: Once recurring events exist, users will need to manage them. Without this, they'd have to open Google Calendar directly.

**Independent Test**: Create a recurring event via the bot, then say "cancel the cleaners starting next week." Google Calendar shows the series is modified/cancelled correctly.

**Acceptance Scenarios**:

1. **Given** a recurring "cleaners" event exists, **When** Erin says "cancel the cleaners", **Then** the bot asks whether to cancel all future occurrences or just one, and acts accordingly.
2. **Given** a recurring "swim class" event exists, **When** Erin says "no swim class this Monday", **Then** only that single occurrence is cancelled, leaving the rest intact.
3. **Given** a recurring event exists, **When** Erin says "move swim class to 4:30pm starting next week", **Then** future occurrences are updated to the new time.

---

### User Story 3 - View Recurring Events (Priority: P3)

As Erin, I want to ask "what recurring events do we have" and see a list of all active recurring series so I know what's on the regular schedule.

**Why this priority**: Nice-to-have for awareness. The daily plan already shows individual occurrences, but a summary of all recurring patterns is useful for schedule reviews.

**Independent Test**: Create 3 recurring events, then ask "list our recurring events." Bot responds with all 3 patterns.

**Acceptance Scenarios**:

1. **Given** recurring events exist on the family calendar, **When** Erin asks "what recurring events do we have", **Then** the bot lists each recurring series with its pattern (e.g., "Cleaners — every other Tue 10am-1pm", "Swim — every Mon 4-5pm").

---

### Edge Cases

- What if the user provides an ambiguous recurrence pattern like "every few weeks"? Bot should ask for clarification (e.g., "Every 2 weeks or every 3 weeks?").
- What if a recurring event conflicts with an existing event? Bot should warn about the conflict but still create the event (same behavior as non-recurring events).
- What if the user wants to create a recurring event on a specific person's calendar instead of the family calendar? Bot should support specifying the target calendar (default: family).
- What if the user says "add tutoring Tuesdays and Thursdays at 3pm"? Bot should handle multi-day recurrence patterns.
- What if the user provides no end date? Default to indefinite recurrence (standard calendar behavior).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST create recurring calendar events from natural language descriptions containing a recurrence pattern (daily, weekly, biweekly, monthly, etc.).
- **FR-002**: The system MUST support these recurrence patterns: daily, weekly, biweekly (every other week), monthly (by day of month or by day of week, e.g., "first Friday"), and custom intervals (every N days/weeks/months).
- **FR-003**: The system MUST support optional end conditions: number of occurrences ("for 8 weeks"), end date ("until June 1"), or no end (indefinite).
- **FR-004**: The system MUST default to the family calendar for recurring events, with the option to specify a different calendar (Jason, Erin).
- **FR-005**: The bot MUST confirm recurring event creation by showing the recurrence pattern and the next 3-4 upcoming dates.
- **FR-006**: The system MUST support cancelling a single occurrence of a recurring event without affecting the series.
- **FR-007**: The system MUST support cancelling all future occurrences of a recurring event.
- **FR-008**: The system MUST support modifying future occurrences of a recurring event (e.g., changing time).
- **FR-009**: The system MUST support listing all active recurring event series on a given calendar.
- **FR-010**: The system MUST handle multi-day patterns (e.g., "Tuesdays and Thursdays at 3pm") by creating the appropriate recurrence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can create a recurring event in a single message instead of creating multiple individual events (reduction from N messages to 1).
- **SC-002**: The system correctly interprets at least 90% of natural language recurrence patterns on the first attempt (daily, weekly, biweekly, monthly, specific day-of-week, "first Friday of month").
- **SC-003**: Created recurring events display correctly in Google Calendar with the proper recurrence icon and pattern description.
- **SC-004**: Single-occurrence cancellation does not affect other occurrences in the series.
- **SC-005**: Users can view all active recurring patterns in a single response within 10 seconds.

## Assumptions

- Google Calendar's existing recurrence rule support is sufficient for all patterns described (daily, weekly, biweekly, monthly, yearly).
- Claude can reliably generate recurrence rules from natural language — this is a pattern-matching task well within its capabilities.
- The existing `create_quick_event` tool is the right place to add recurrence support (add an optional parameter rather than creating a new tool).
- Multi-day patterns like "Tuesdays and Thursdays" may need to be created as two separate recurring events (one for Tuesday, one for Thursday) since most calendar systems model recurrence per-event.
- The existing event deletion tool can be extended for recurring event management (single occurrence vs. all future).
