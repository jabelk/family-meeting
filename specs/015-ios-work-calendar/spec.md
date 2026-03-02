# Feature Specification: iOS Work Calendar Sync

**Feature Branch**: `015-ios-work-calendar`
**Created**: 2026-03-02
**Status**: Draft
**Input**: User description: "iOS Shortcut integration for Jason's Cisco work calendar. Jason's Cisco Outlook is locked down (no ICS publishing, no calendar subscribe). Both his Google and Cisco calendars show on his iPhone Calendar app. Build an API endpoint that receives Jason's work calendar events from an iOS Shortcut automation. The shortcut should run once weekly and push a full week's worth of work meetings. The bot uses these events in daily plan generation so Erin knows Jason's availability (breakfast timing, meeting windows, when he's free to help). Content of meetings isn't important to Erin — just the time blocks. The existing get_outlook_events tool should be modified to read from this data when the ICS URL isn't available. Auth uses the existing n8n webhook secret pattern. Storage follows the existing atomic JSON file pattern."

## Context

Jason works from home at Cisco. His work calendar is managed through Outlook/Exchange, but Cisco IT has locked down ICS feed publishing, calendar URL sharing, and cross-platform subscription. This means the family assistant cannot see Jason's work meetings for daily plan generation.

Erin's daily plan needs Jason's work meeting windows to determine: when he's free for breakfast, when he can help with kid pickup/dropoff, and when he's blocked in meetings. The meeting content doesn't matter — only the time blocks.

Both Jason's Google Calendar (personal) and Cisco Outlook calendar already appear on his iPhone Calendar app via native Exchange/Google sync. An iOS Shortcut can read events from all calendars on the phone, making it the bridge between the locked-down Cisco calendar and the family assistant.

## User Scenarios & Testing

### User Story 1 — Weekly Work Calendar Push (Priority: P1)

Jason's iPhone runs an automated iOS Shortcut once per week that reads the upcoming week's Cisco work calendar events and sends them to the family assistant. This happens without any manual intervention from Jason.

**Why this priority**: This is the core data pipeline — without it, no other story works. A weekly push captures the full week of meetings at once, minimizing automation runs.

**Independent Test**: Manually trigger the iOS Shortcut (or simulate a POST request to the endpoint). Verify the events are stored and can be retrieved for any day in the pushed week.

**Acceptance Scenarios**:

1. **Given** the iOS Shortcut runs on Sunday evening, **When** it reads Jason's Cisco calendar events for the upcoming Mon–Fri, **Then** it sends all events to the assistant's endpoint and receives a success confirmation.
2. **Given** events were previously pushed for this week, **When** the shortcut runs again (e.g., mid-week update after meeting changes), **Then** the new data replaces the old data for overlapping dates.
3. **Given** Jason has no work meetings on a particular day, **When** the shortcut pushes an empty event list for that day, **Then** the system records "no meetings" for that day (distinct from "no data received").
4. **Given** the endpoint receives events, **When** it processes them, **Then** it returns a summary: number of events received and which dates are covered.

---

### User Story 2 — Daily Plan Uses Work Calendar (Priority: P1)

When the bot generates Erin's daily plan, it checks Jason's work meeting windows from the pushed data and incorporates his availability into the plan — breakfast timing, help windows, and blocked periods.

**Why this priority**: This is the user-facing value. Without this, the pushed data is useless.

**Independent Test**: Push sample work events for today, then ask the bot "what's my day look like?" and verify the daily plan mentions Jason's meeting windows and free times.

**Acceptance Scenarios**:

1. **Given** work events were pushed for today showing meetings 9–10 AM and 2–3 PM, **When** the daily plan is generated, **Then** the plan notes Jason is free before 9 AM (breakfast window) and between 10 AM–2 PM.
2. **Given** no work events were pushed for today and the ICS URL is not configured, **When** the daily plan is generated, **Then** the bot notes that Jason's work schedule is unavailable and suggests asking him directly.
3. **Given** work events were pushed but they are more than 7 days old for today's date, **When** the daily plan is generated, **Then** the system treats it as "no data" rather than using stale information.

---

### User Story 3 — iOS Shortcut Setup Guide (Priority: P2)

Jason receives clear instructions on how to set up the iOS Shortcut automation on his iPhone, including: which actions to use, how to configure the weekly trigger, and how to authenticate with the endpoint.

**Why this priority**: One-time setup task. Jason needs to do this once and then it runs forever.

**Independent Test**: Follow the setup instructions on an iPhone. Verify the shortcut can be created and successfully sends a test request to the endpoint.

**Acceptance Scenarios**:

1. **Given** Jason follows the setup instructions, **When** he creates and runs the shortcut, **Then** it reads his Cisco calendar events for the week and successfully posts them to the endpoint.
2. **Given** the shortcut is configured with a weekly automation trigger, **When** the scheduled time arrives (e.g., Sunday 7 PM), **Then** the shortcut runs automatically without Jason needing to open the app or tap anything.

### Edge Cases

- What happens when the shortcut runs but Jason's phone has no internet? The shortcut fails silently; no data is pushed. The bot falls back to "work schedule unavailable" gracefully.
- What happens when the endpoint receives a request with invalid or missing authentication? It returns an authentication error and does not store any data.
- What happens when the endpoint receives events with overlapping or duplicate times? Events are stored as-is — the bot displays them without deduplication since they reflect the actual calendar state.
- What happens if the iOS Shortcut automation is disabled or Jason changes phones? The pushed data expires after 7 days. The bot gracefully degrades to "work schedule unavailable."
- What happens on holidays or PTO when Jason has no meetings? The shortcut pushes empty days, and the bot correctly shows Jason as free all day.

## Requirements

### Functional Requirements

- **FR-001**: System MUST accept work calendar events via an authenticated endpoint, receiving a list of events with title, start time, and end time for one or more dates.
- **FR-002**: System MUST store received events persistently, keyed by date, so they survive service restarts.
- **FR-003**: System MUST replace existing events for a date when new events are received for that date (full replace, not merge).
- **FR-004**: System MUST return a confirmation response showing how many events were received and which dates are covered.
- **FR-005**: System MUST serve stored work calendar events when the daily plan or any tool requests Jason's work schedule.
- **FR-006**: System MUST treat pushed data older than 7 days as expired and fall back to "work schedule unavailable."
- **FR-007**: System MUST auto-prune expired entries (older than 7 days) to prevent storage growth.
- **FR-008**: System MUST authenticate requests using the same shared secret used by all existing automated endpoints.
- **FR-009**: System MUST distinguish between "no events for this day" (Jason is free) and "no data received for this day" (schedule unknown).
- **FR-010**: System MUST fall back to the existing ICS feed mechanism if an ICS URL is configured, using pushed data only when the ICS feed is unavailable or not configured.

### Key Entities

- **Work Calendar Day**: A single date's worth of work events for Jason. Contains the date, a list of time blocks, and a timestamp of when the data was received.
- **Work Event**: A single calendar event with a title (for display, e.g., "Meeting"), a start time, and an end time. No attendees, descriptions, or other metadata needed.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Erin's daily plan includes Jason's work meeting windows on 5 out of 5 weekdays after the weekly push, with zero manual intervention from Jason beyond initial setup.
- **SC-002**: The weekly push completes in under 10 seconds from the iPhone Shortcut triggering to receiving a success response.
- **SC-003**: When no work calendar data is available, the daily plan still generates successfully with a clear "work schedule unavailable" note — no errors or broken output.
- **SC-004**: Pushed events are available within 1 second of the endpoint returning success (no delayed processing).

## Assumptions

- Jason's iPhone has both Cisco Exchange and Google Calendar accounts configured and visible in the Calendar app.
- iOS Shortcuts can read calendar events from all configured accounts, including Exchange/Outlook.
- iOS Shortcut automations can run on a weekly schedule (iOS 16+ supports time-based automations).
- The existing shared authentication secret is acceptable for iOS Shortcut requests (it will be stored in the Shortcut configuration on Jason's phone).
- A week's worth of events is a reasonable batch size (typically 10–30 meetings per week for a knowledge worker).
- Meeting titles can be sent as-is or anonymized — Erin only needs time blocks, but titles like "Standup" or "1:1" provide useful context about meeting length/importance.

## Scope Boundaries

**In scope**:
- Receiving and storing work calendar events from an external source
- Serving stored events to the daily plan generation flow
- Expiration and cleanup of old data
- iOS Shortcut setup instructions

**Out of scope**:
- Real-time calendar sync (this is a periodic batch push)
- Two-way sync (writing back to Cisco calendar)
- Reading events from any source other than the iOS Shortcut push
- Modifying the existing Google Calendar integration
- Sending notifications about Jason's schedule changes
