# Feature Specification: Smart Nudges & Chore Scheduling

**Feature Branch**: `003-smart-nudges-chores`
**Created**: 2026-02-23
**Status**: Draft
**Input**: Proactive smart nudges and chore scheduling for Erin — departure reminders, laundry workflow, and intelligent chore suggestions based on calendar and routine context.

## Context

Erin is a stay-at-home mom managing two young children (Vienna, 5, in school; Zoey, 3, with grandma some days and starting preschool soon) in Reno, NV. She self-identifies as someone who procrastinates getting out the door, and has specifically requested help timing household tasks like laundry around her daily schedule.

The family assistant bot already has full access to Erin's Google Calendar, daily routine templates (day-specific, stored in Notion), and knowledge of who has the kids on any given day. This feature adds proactive, time-aware nudges that leverage that existing context to help Erin stay on track throughout the day without her having to ask.

## Clarifications

### Session 2026-02-23

- Q: Default departure assumption — should events be assumed to require departure or not? → A: All events assume departure UNLESS they contain virtual indicators (Zoom/Meet link, "call", "virtual" in title). Missing a real event is worse than an occasional unnecessary nudge.
- Q: Should nudges have quiet hours restricting when they can fire? → A: Yes, nudges only fire between 7:00 AM and 8:30 PM. Matches daily briefing start and respects evening wind-down.

## User Scenarios & Testing

### User Story 1 — Departure Nudges (Priority: P1)

Erin has a calendar event that requires leaving the house (park playdate at 10am, Vienna pickup at 3pm, doctor appointment at 2pm). The bot sends a friendly WhatsApp reminder 15–30 minutes before she needs to leave, accounting for the fact that getting two kids out the door takes extra time.

**Why this priority**: Erin specifically identified procrastinating getting out the door as a pain point. This is the highest-impact behavioral nudge — it directly addresses a daily frustration and requires no new data entry from her (it reads her existing calendar).

**Independent Test**: Can be fully tested by creating a calendar event 20 minutes in the future and verifying a WhatsApp reminder arrives at the configured lead time.

**Acceptance Scenarios**:

1. **Given** Erin has a calendar event "Park playdate" at 10:00 AM, **When** the current time reaches 9:30 AM (30 min before), **Then** the bot sends a WhatsApp message like "Hey! Park playdate is at 10 — time to start getting the kids ready!"
2. **Given** Erin has a calendar event marked as a virtual/online meeting, **When** the reminder window arrives, **Then** no departure nudge is sent (virtual events don't require leaving the house).
3. **Given** Erin has two calendar events within 30 minutes of each other, **When** the reminder window arrives, **Then** the bot sends a single consolidated nudge mentioning both events.
4. **Given** Erin has no calendar events requiring departure for the rest of the day, **When** the daily scan runs, **Then** no nudge messages are sent.
5. **Given** Erin replies "stop" or "snooze" to a nudge, **When** the bot receives this reply, **Then** it acknowledges and suppresses further nudges for that event (stop) or delays by 10 minutes (snooze).

---

### User Story 2 — Laundry Workflow Reminders (Priority: P1)

Erin starts a load of laundry in the morning. The bot tracks the laundry cycle and sends timed reminders: one to move clothes to the dryer (after wash cycle completes, ~45 min), and one when the dryer is done (~60 min later). Timing adapts to her schedule — e.g., if she needs to leave for Vienna pickup at 3pm, the bot suggests starting the dryer by 1:30pm so it finishes before she leaves.

**Why this priority**: Erin specifically asked for help with laundry timing. She must be physically home for the washer and dryer, so timing around her calendar is essential. This is a daily task that currently falls through the cracks.

**Independent Test**: Can be fully tested by telling the bot "I started a load of laundry" and verifying timed reminders arrive for the washer-to-dryer transition and dryer completion.

**Acceptance Scenarios**:

1. **Given** Erin tells the bot "I started the laundry," **When** 45 minutes have passed, **Then** the bot sends a reminder: "Washer should be done! Time to move clothes to the dryer."
2. **Given** Erin confirms she moved clothes to the dryer, **When** 60 minutes have passed, **Then** the bot sends a reminder: "Dryer should be done! Clothes are ready to fold."
3. **Given** Erin starts laundry and has a calendar event requiring her to leave at 3pm, **When** the bot calculates timing, **Then** it warns if the dryer cycle will conflict with a departure (e.g., "Heads up — if you move to dryer now, it'll finish around 3:15 but you have Vienna pickup at 3:00. Want to start dryer after you get back?").
4. **Given** Erin tells the bot "I started laundry" but doesn't confirm moving to dryer, **When** 2 hours have passed since the wash reminder, **Then** the bot sends a gentle follow-up: "Did you move the laundry to the dryer? Clothes have been sitting in the washer a while."
5. **Given** Erin says "never mind" or "I didn't do laundry," **When** the bot receives this, **Then** it cancels all pending laundry reminders.

---

### User Story 3 — Intelligent Chore Suggestions (Priority: P2)

During free windows in Erin's day (e.g., Zoey napping, kids at grandma's, gap between events), the bot proactively suggests a chore or task that fits the available time. Suggestions are context-aware: it knows what day it is, who has the kids, how much time is available, and what chores are overdue or recurring.

**Why this priority**: This builds on the existing daily briefing and routine templates but adds mid-day intelligence. Slightly lower priority than US1/US2 because it requires a chore tracking data model and is more of a "nice to have" optimization versus the direct pain-point solutions above.

**Independent Test**: Can be fully tested by creating a 2-hour free window in the calendar and verifying the bot sends a contextual chore suggestion at the start of that window.

**Acceptance Scenarios**:

1. **Given** Erin has a 90-minute free window starting at 1pm (Zoey is napping), **When** 1:00 PM arrives, **Then** the bot sends a suggestion like "You have about 90 min while Zoey naps — good time to vacuum the downstairs? Or would you rather do meal prep for tonight?"
2. **Given** it's Monday and grandma has Zoey from 9–12, **When** 9:00 AM arrives (after the daily briefing), **Then** the bot suggests a bigger chore that requires uninterrupted time, like deep cleaning or organizing.
3. **Given** the bot suggested vacuuming and Erin replies "done" or "did it," **When** the bot processes this, **Then** it marks the chore as completed and updates the last-done date.
4. **Given** Erin replies "not now" or "skip" to a chore suggestion, **When** the bot processes this, **Then** it acknowledges and doesn't re-suggest the same chore that day.
5. **Given** the free window is only 20 minutes, **When** the bot evaluates chore options, **Then** it suggests only quick tasks (wipe counters, start dishwasher, quick tidy) rather than time-intensive chores.

---

### User Story 4 — Chore Preferences and History (Priority: P3)

Erin can tell the bot her chore preferences (frequency, which chores she dislikes, which rooms matter most) and the bot tracks what's been done recently to avoid suggesting the same thing repeatedly. Over time, the bot learns her patterns.

**Why this priority**: This enhances US3 but isn't required for it to work. US3 can launch with a sensible default chore list. Preference tracking makes the system smarter over time.

**Independent Test**: Can be fully tested by telling the bot "I vacuum every Wednesday" and verifying it suggests vacuuming on subsequent Wednesdays.

**Acceptance Scenarios**:

1. **Given** Erin tells the bot "I like to vacuum on Wednesdays and do laundry Monday and Thursday," **When** Wednesday arrives, **Then** the bot prioritizes vacuum in its chore suggestions.
2. **Given** Erin completed "vacuum downstairs" 2 days ago, **When** the bot generates chore suggestions, **Then** vacuuming is deprioritized in favor of chores not done recently.
3. **Given** Erin says "I hate cleaning bathrooms," **When** the bot generates suggestions, **Then** bathroom cleaning is suggested less frequently but still appears when significantly overdue (with an empathetic tone: "I know this isn't your favorite, but the bathroom could use some love").
4. **Given** Erin asks "what chores have I done this week?", **When** the bot processes this, **Then** it returns a summary of completed chores with dates.

---

### Edge Cases

- What happens if Erin's calendar is empty for the day? The bot should not send departure nudges but may still suggest chores during default free windows from routine templates.
- What happens if the daily briefing already mentioned a departure event? The nudge is still sent closer to the event time — the briefing is a plan, the nudge is an action prompt.
- What happens if Erin starts laundry but the bot is restarted mid-cycle? Pending laundry reminders should survive across bot restarts (persisted, not just in-memory).
- What happens if Erin gets multiple nudges in rapid succession (departure + laundry + chore)? The bot should batch messages sent within a 5-minute window into a single consolidated message.
- What happens if Erin is already out of the house (no location data)? The bot has no location awareness — it sends nudges based on calendar time regardless. Erin can dismiss or snooze.
- What happens if the calendar event is created less than 15 minutes before start time? The bot sends an immediate nudge rather than skipping it.

## Requirements

### Functional Requirements

- **FR-001**: System MUST scan Erin's calendar periodically and identify events that require leaving the house.
- **FR-002**: System MUST send departure nudge messages 15–30 minutes before qualifying calendar events via the existing messaging channel.
- **FR-003**: System MUST assume all calendar events require departure by default. Events are excluded from departure nudges ONLY if they contain virtual indicators: a video conferencing link (Zoom, Google Meet, Teams), or keywords like "call", "virtual", "remote", "online" in the title or description.
- **FR-004**: System MUST allow Erin to trigger a laundry workflow by sending a natural language message (e.g., "started laundry," "doing a load of wash").
- **FR-005**: System MUST send timed reminders at configurable intervals for washer completion (~45 min) and dryer completion (~60 min).
- **FR-006**: System MUST cross-reference laundry timing with calendar events and warn if the dryer cycle will conflict with a departure.
- **FR-007**: System MUST identify free windows in the daily schedule by comparing calendar events against routine templates.
- **FR-008**: System MUST suggest contextually appropriate chores during free windows, considering available time, day of week, and childcare situation.
- **FR-009**: System MUST track when chores were last completed to avoid repetitive suggestions.
- **FR-010**: System MUST allow Erin to respond to nudges with snooze, dismiss, done, or skip actions via natural conversation.
- **FR-011**: System MUST batch multiple nudges occurring within a 5-minute window into a single consolidated message.
- **FR-012**: System MUST persist pending reminders (laundry timers, scheduled nudges) so they survive system restarts.
- **FR-013**: System MUST support Erin setting chore preferences (frequency, day assignments, disliked chores) via conversational commands.
- **FR-014**: System MUST adapt chore suggestion duration to the available free window (quick tasks for short windows, bigger chores for long windows).

### Non-Functional Requirements

- **NFR-001**: Nudge messages MUST arrive within 2 minutes of the scheduled nudge time.
- **NFR-002**: The system MUST NOT send more than 8 proactive messages per day (excluding direct replies to Erin's messages) to avoid notification fatigue.
- **NFR-003**: All nudge messages MUST use a warm, encouraging tone — never nagging or guilt-inducing.
- **NFR-004**: Erin MUST be able to silence all nudges for the day with a single command ("quiet day" or "no nudges today").
- **NFR-005**: Proactive nudges MUST only be sent between 7:00 AM and 8:30 PM Pacific time. Events outside this window do not trigger nudges.

### Key Entities

- **Nudge**: A scheduled proactive message with a target delivery time, trigger source (calendar event, laundry timer, chore suggestion), status (pending, sent, snoozed, dismissed), and associated context.
- **Laundry Session**: Tracks an active laundry cycle — start time, current phase (washing, drying, done), expected completion times, and any calendar conflicts.
- **Chore**: A recurring household task with name, estimated duration (minutes), preferred frequency (daily, weekly, biweekly), preferred day(s), last completed date, and Erin's preference level (like, neutral, dislike).
- **Free Window**: A calculated time block derived from comparing calendar events against routine templates — has start time, end time, duration, and childcare context (who has the kids).

## Success Criteria

### Measurable Outcomes

- **SC-001**: Erin receives departure reminders for 90%+ of qualifying calendar events (measured over a 2-week period).
- **SC-002**: Laundry reminder workflow completes end-to-end (start to washer done to dryer done) with all reminders arriving within 2 minutes of scheduled time.
- **SC-003**: Erin reports reduced instances of "running late" or "forgot to move laundry" within the first 2 weeks of use.
- **SC-004**: Chore suggestions are contextually appropriate (correct duration for available window) at least 80% of the time.
- **SC-005**: Erin interacts with (accepts, defers, or completes) at least 50% of chore suggestions, indicating relevance.
- **SC-006**: Daily proactive message count stays at or below 8 messages per day (no notification fatigue).
- **SC-007**: Erin uses the "quiet day" command fewer than twice per week (indicating nudges are generally welcome, not annoying).

## Assumptions

- Erin's Google Calendar is kept reasonably up to date with events that require leaving the house (playdates, appointments, pickups).
- The existing daily briefing (7am) continues to run separately — nudges complement but don't replace it.
- Erin interacts with the bot primarily via WhatsApp text messages (no voice, no app UI).
- Default washer cycle is ~45 minutes and default dryer cycle is ~60 minutes; these are configurable.
- The bot does not have location awareness — nudges are time-based only.
- Chore suggestions start with a sensible default list (vacuum, laundry, meal prep, dishes, tidy living room, wipe counters, bathroom clean, organize closet) and Erin refines over time.
- Free windows shorter than 15 minutes are not worth a chore suggestion.
- The existing n8n scheduling infrastructure handles periodic calendar scanning (e.g., every 15 minutes during daytime hours).

## Scope Boundaries

**In scope**:
- Departure nudges based on calendar events
- Laundry workflow with timed reminders
- Chore suggestions during free windows
- Snooze/dismiss/done/skip responses
- Chore preference tracking
- Message batching to reduce notification noise
- "Quiet day" override

**Out of scope**:
- Location-based reminders (geofencing)
- Smart home integration (washer/dryer sensors)
- Chore assignment between family members (this is Erin-only for now)
- Gamification or rewards for completing chores
- Integration with cleaning service scheduling
- Morning routine checklists for getting kids ready (potential future feature)
