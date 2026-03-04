# Feature Specification: Smart Daily Planner

**Feature Branch**: `017-smart-daily-planner`
**Created**: 2026-03-03
**Status**: Draft
**Input**: User description: "Smarter daily planning — school schedule awareness, drive times, confirm-then-write"
**Related**: GitHub Issue #21

## Context

The daily plan is Erin's #1 interaction with the bot. She asks for a plan almost every morning, and the bot generates a schedule with time blocks written to her Google Calendar. Currently, this process is frustrating because:

1. **The bot forgets recurring obligations** — Vienna's school drop-off (9-9:15 AM) and pickup (3-3:45 PM) are already on the calendar, but the bot doesn't account for them when building the plan. Erin has to correct it every time.
2. **No travel time awareness** — Erin had to manually tell the bot "the gym has a 5 minute drive time." Common locations have predictable drive times that should be stored and automatically included.
3. **Calendar writes happen before confirmation** — The bot generates a plan and immediately writes it to Google Calendar. When Erin requests changes (which she almost always does), the bot rewrites the calendar blocks, sometimes 3+ times in one session. This clutters her calendar with stale entries.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calendar-Aware Plan Generation (Priority: P1)

When Erin asks for a daily plan, the bot automatically reads all of her existing calendar events (including recurring ones like school drop-off/pickup, swim lessons, appointments) and builds the plan around them. She never has to remind the bot about events that are already on her calendar.

**Why this priority**: This is the most frequent pain point — Erin corrects the plan for school times virtually every session. Reading existing calendar events is the foundation that makes the other improvements possible.

**Independent Test**: Ask "plan my day" on a weekday with Vienna's school events on the calendar. The plan should include drop-off and pickup blocks without being told.

**Acceptance Scenarios**:

1. **Given** Vienna's school drop-off (9:00 AM) and pickup (3:00 PM) are on Erin's Google Calendar, **When** Erin asks "plan my day," **Then** the plan includes these events as fixed blocks and schedules other activities around them.
2. **Given** Erin has a doctor appointment at 2:00 PM on her calendar, **When** she asks for a daily plan, **Then** the plan shows the appointment as a fixed block and doesn't schedule anything over it.
3. **Given** there are no calendar events for the day, **When** Erin asks for a plan, **Then** the bot generates a plan with open blocks and notes that the calendar is clear.
4. **Given** a recurring weekly event (e.g., swim Monday 4 PM), **When** Erin asks for Monday's plan, **Then** swim appears automatically without Erin mentioning it.

---

### User Story 2 - Confirm Before Writing to Calendar (Priority: P1)

The bot presents a draft daily plan for Erin to review before writing anything to her calendar. Erin can request changes (add items, remove items, adjust times), and only when she approves does the bot write the final version to the calendar.

**Why this priority**: The current behavior of immediately writing to calendar causes clutter when the plan needs revisions (which is almost every time). This is co-P1 with US1 because together they eliminate the most friction.

**Independent Test**: Ask "plan my day," review the draft, request one change, approve, and verify only the final version appears on the calendar.

**Acceptance Scenarios**:

1. **Given** Erin asks "plan my day," **When** the bot generates the plan, **Then** it presents the plan as a draft and asks "Want me to add this to your calendar?" (or similar confirmation).
2. **Given** Erin reviews the draft and says "move gym to 10 AM," **When** the bot adjusts, **Then** it shows the updated plan and asks for confirmation again — no calendar writes yet.
3. **Given** Erin says "looks good" or "yes" or "add it," **When** the bot writes to calendar, **Then** it confirms with the number of blocks written and they appear in her Apple Calendar.
4. **Given** Erin says "never mind" or "skip the calendar," **When** the bot responds, **Then** no calendar writes happen but she still has the plan in chat.
5. **Given** the morning automated briefing (triggered at 7 AM), **When** the system generates a daily plan, **Then** it does NOT auto-write to calendar — it presents the plan and waits for Erin to confirm via WhatsApp reply.

---

### User Story 3 - Drive Time Buffers (Priority: P2)

The bot knows how long it takes to drive to common destinations (school, gym, grandma's, church, etc.) and automatically adds travel buffers between activities at different locations. When Erin adds a new location, she can tell the bot the drive time once and it remembers for future plans.

**Why this priority**: Drive times are important for realistic scheduling, but the bot can still generate useful plans without them (just less accurate). This builds on US1's calendar-aware planning.

**Independent Test**: Ask for a plan that includes the gym and school pickup — the plan should include 5-minute drive times between home, gym, and school without being told.

**Acceptance Scenarios**:

1. **Given** the family profile has stored drive times (gym: 5 min, school: 10 min), **When** Erin's plan includes gym at 9:15 AM, **Then** the plan shows a drive-to-gym buffer before it.
2. **Given** Erin says "the park is 15 minutes away," **When** she asks for a plan later that includes the park, **Then** the 15-minute drive time is automatically included.
3. **Given** two consecutive activities are at the same location (e.g., both at home), **When** the plan is generated, **Then** no drive time buffer is added between them.
4. **Given** no drive time is stored for a location, **When** the plan includes that location, **Then** the bot generates the plan without a buffer rather than asking (zero friction).

---

### Edge Cases

- What happens when Erin asks to plan a future day (e.g., "plan my Wednesday")? The bot should read Wednesday's calendar events and generate a plan for that day, still requiring confirmation before writing.
- What happens when existing calendar events overlap with each other? The bot should flag the conflict and ask Erin how to handle it.
- What happens when Erin wants to modify a plan that was already written to calendar? The bot should update/delete the old blocks and write the new ones (after confirmation).
- What happens when the calendar is unreachable? The bot should generate the plan from what it knows (backlog, routines) and skip the calendar read, noting the issue.
- What happens when Erin says a drive time has changed (e.g., "gym is actually 10 minutes now")? The stored drive time should be updated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When generating a daily plan, the system MUST read the user's existing calendar events for that day and treat them as fixed, immovable blocks.
- **FR-002**: The system MUST identify recurring events (school, activities, appointments) from the calendar and include them in every relevant plan without the user specifying them.
- **FR-003**: The system MUST present daily plans as drafts for user review before writing any events to the calendar.
- **FR-004**: The system MUST wait for explicit user confirmation (e.g., "yes," "looks good," "add it") before writing plan blocks to the calendar.
- **FR-005**: The system MUST allow the user to request modifications to the draft plan (add, remove, adjust times) and re-present the updated draft.
- **FR-006**: The system MUST store drive times for commonly visited locations so they persist across sessions.
- **FR-007**: When generating a plan with activities at different locations, the system MUST automatically insert travel buffers using stored drive times.
- **FR-008**: Users MUST be able to add or update drive times for locations through natural conversation (e.g., "the gym is 5 minutes away").
- **FR-009**: If no drive time is stored for a location, the system MUST generate the plan without a buffer rather than asking.
- **FR-010**: The automated morning briefing MUST present the plan as a draft, not auto-write to calendar.

### Key Entities

- **Daily Plan Draft**: A proposed schedule for a specific day, including fixed calendar events, planned activities, and travel buffers. Exists in chat until confirmed.
- **Drive Time Entry**: A stored association between a location name and its one-way drive time from home. Persists in the family profile.
- **Calendar Event (existing)**: Events already on the user's Google Calendar, treated as immovable blocks during plan generation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Erin's daily plan includes school drop-off and pickup times on the first attempt in 100% of weekday plans (zero corrections needed for calendar events).
- **SC-002**: Plan revision cycles drop from 3+ per session to 1 or fewer (Erin confirms or requests one tweak).
- **SC-003**: Calendar blocks are only written once per planning session (no duplicate/stale entries from multiple rewrites).
- **SC-004**: Drive times for stored locations appear automatically in plans without Erin mentioning them.

## Assumptions

- Erin's existing calendar events (school, appointments, activities) are reliably on her Google Calendar before she asks for a plan.
- The family has fewer than 10 commonly visited locations with stored drive times.
- Drive times are one-way from home (the family lives in one location and drives out to activities).
- Erin will naturally say "looks good" or similar when approving a plan — no new UI or special commands needed.
- The n8n morning briefing (7 AM) triggers the same plan generation but skips auto-writing to calendar.

## Out of Scope

- Real-time traffic or route-based drive time estimation — stored static values are sufficient for a small city like Reno.
- Multi-stop trip optimization (e.g., "go to gym then UPS then school") — the plan is sequential, not route-optimized.
- Automatic detection of new locations from calendar events — Erin adds drive times manually when she wants them.
- Plan templates or saved plan patterns — each day is generated fresh from calendar + preferences.
