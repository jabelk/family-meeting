# Feature Specification: Context-Aware Bot

**Feature Branch**: `014-context-aware-bot`
**Created**: 2026-03-01
**Status**: Draft
**Input**: User description: "Context-aware bot — replace hardcoded weekly schedule and 71-rule system prompt with a dynamic get_daily_context tool that pulls live calendar data per person, infers who has Zoey, checks current time and active preferences, and returns structured context the model uses for planning. Supports personal routine checklists, general quiet hours, and time-appropriate recommendations. Shrinks the system prompt by removing stale hardcoded schedule data."

## Context

The system prompt in `src/assistant.py` has grown to 413 lines containing 71 numbered rules. Lines 46-58 hardcode a weekly family schedule (who drops off Vienna, who has Zoey, what day-specific activities happen). Lines 60-74 hardcode breakfast preferences and chore patterns. When Zoey starts preschool, when ski lessons end, when BSF changes days, or when any recurring schedule shifts — someone must manually edit `src/assistant.py` and redeploy the Docker container.

This hardcoded approach has caused real problems:

- **Issue #7**: The bot suggests tasks at inappropriate times because it passively reads a massive prompt rather than actively checking what time it is and what the family is doing right now.
- **Issue #13**: The bot engages Erin late at night. Only budget topics have quiet hours (Rule 68). There are no general quiet hours — the bot enthusiastically suggests chores at 10:23 PM.
- **Issue #14**: Shared calendar events lack attendee names, so the bot cannot infer who goes to "BSF" or "Gymnastics." This is being fixed separately by renaming calendar events, but the bot still needs to reliably use calendar source labels (`[erin]`, `[jason]`, `[family]`) to attribute events to the right person.
- **Issue #15**: Erin wants personal routine checklists (morning skincare, bedtime routine) that the bot can reference and walk her through, but no storage or retrieval mechanism exists.

The key insight: instead of adding more hardcoded rules to an already bloated system prompt, the fix should be **systemic**. Replace the hardcoded schedule and passive context injection with a dynamic context tool that the model calls at the start of any planning interaction. The tool pulls live calendar data, infers childcare status, checks the current time, reads active preferences, and returns structured context. The system prompt shrinks because static data moves into the tool, and schedule changes never require code deploys again.

## Assumptions

- Calendar source labels (`[erin]`, `[jason]`, `[family]`) from `get_calendar_events` and `get_events_for_date` already work correctly. The `_calendar_source` field is set on every event dict. The model just needs to be instructed to use them.
- Routine storage follows the established JSON file pattern: `data/routines.json`, using the same `_DATA_DIR` detection, in-memory cache, and atomic file writes as `preferences.py` and `conversation.py`.
- The `get_daily_context` tool is lightweight — it makes 2-3 API calls (Google Calendar for today's events across 3 calendars, user preferences lookup) and returns a structured text block that the model consumes as context.
- **Out of scope**: Notion fallback for calendar outages (graceful degradation with `calendar_available: false` is sufficient). Jason's Outlook work calendar is not included in `get_daily_context` — the existing `get_outlook_events` tool can be called separately when needed for daily plan generation.
- The preference system (Feature 013, `src/preferences.py`) is already implemented and can be read by the context tool.
- Quiet hours configuration uses the existing preference system categories (`quiet_hours`, `communication_style`) — no new storage mechanism needed.
- Issue #14 (calendar event naming) is being addressed separately. This feature works regardless of whether event names include attendee prefixes, because it uses the `_calendar_source` field to attribute events to people.
- No new Notion databases are needed. Routines are stored in a local JSON file. The context tool reads from existing calendars and preferences.
- No new external APIs. Everything uses existing Google Calendar, Notion, and YNAB integrations.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dynamic Context Tool (Priority: P1)

When the bot needs to generate a daily plan, make a recommendation, or answer a scheduling question, it calls `get_daily_context` to get a structured snapshot of right now: the current time in Pacific, today's events grouped by person (Jason, Erin, Family), who currently has Zoey (inferred from calendar events and time of day), active user preferences for the requesting user, and a count of pending backlog items. The hardcoded weekly schedule (lines 46-58 of the system prompt) is removed entirely. The system prompt instructs the model to call `get_daily_context` instead of referencing a static schedule.

**Why this priority**: This is the foundational fix. Every other issue (#7 time-awareness, #13 quiet hours, #15 routines) depends on the bot having accurate, live context. Without this, the bot continues guessing from stale hardcoded data. This single tool replaces the most fragile part of the system and makes schedule changes zero-deploy.

**Independent Test**: Remove the hardcoded weekly schedule from the system prompt. Ask the bot "what's my day look like?" on a Wednesday. Verify that the bot calls `get_daily_context`, receives today's actual calendar events grouped by person, correctly reports who has Zoey based on live calendar data, and generates an accurate daily plan — all without any hardcoded schedule rules.

**Acceptance Scenarios**:

1. **Given** the hardcoded weekly schedule has been removed from the system prompt, **When** Erin asks "what's my day look like?" on a Tuesday, **Then** the bot calls `get_daily_context` and receives a structured response showing: current Pacific time, Erin's calendar events for today, Jason's calendar events for today, family calendar events for today, who has Zoey right now (Sandy, per the calendar event), and Erin's active preferences.
2. **Given** the bot receives context showing Zoey is with Sandy from 10am-1pm on Tuesday, **When** it generates the daily plan, **Then** it correctly identifies the 10am-1pm window as Erin's free time for chores or personal tasks, without any hardcoded "Tuesday: Sandy has Zoey 10-1" rule in the system prompt.
3. **Given** Zoey has started preschool (new recurring calendar events replacing Sandy's days), **When** the bot calls `get_daily_context` on a Monday, **Then** it sees the preschool calendar event instead of Sandy's babysitting, and generates the plan accordingly — zero code changes needed.
4. **Given** the Google Calendar API is unreachable, **When** the bot calls `get_daily_context`, **Then** the tool returns a degraded response noting that calendar data is unavailable, and the bot tells the user it cannot generate a full plan right now instead of silently using stale data.
5. **Given** the bot is handling a simple factual question ("what's the capital of France?"), **When** it processes the message, **Then** it does NOT call `get_daily_context` — the tool is only invoked for planning, scheduling, and recommendation interactions.

---

### User Story 2 - Smart Quiet Hours and Communication Modes (Priority: P1)

The `get_daily_context` tool includes a `communication_mode` field derived from the current Pacific time and the user's quiet hours preferences. The modes are: "morning" (7am-12pm: energetic, proactive suggestions welcome), "afternoon" (12pm-5pm: normal tone, responsive), "evening" (5pm-9pm: winding down, respond to questions but limit proactive suggestions), and "late_night" (9pm-7am: minimal, direct answers only, zero proactive content). The model adjusts its tone and proactivity based on this field. Users can customize the time boundaries via the existing preference system.

**Why this priority**: This directly fixes Issue #13 (bot engaging Erin at 10:23 PM) and partially fixes Issue #7 (inappropriate time-of-day suggestions). The communication mode is a field in the context tool output, so it requires US1 to exist, but it is equally critical to the user experience. Erin has explicitly complained about late-night engagement twice.

**Independent Test**: Send the bot a message at 10 PM Pacific. Verify the bot responds with a direct answer only, does not suggest any chores or tasks, and does not append discovery tips or follow-up questions. Then send a message at 8 AM and verify the bot is energetic and offers proactive suggestions.

**Acceptance Scenarios**:

1. **Given** the current time is 10:30 PM Pacific and Erin sends a message, **When** the bot calls `get_daily_context`, **Then** the `communication_mode` field returns "late_night" and the bot provides a direct, minimal answer without proactive suggestions, task recommendations, or follow-up prompts.
2. **Given** the current time is 8:00 AM Pacific and Erin asks "what should I work on?", **When** the bot processes the request, **Then** the `communication_mode` is "morning", and the bot responds with energetic, proactive suggestions including backlog items and chore recommendations.
3. **Given** Erin has stored a preference "quiet after 8pm" (custom quiet hours), **When** `get_daily_context` is called at 8:15 PM, **Then** the `communication_mode` returns "late_night" (respecting her custom boundary) instead of "evening."
4. **Given** the `communication_mode` is "late_night" and Erin explicitly asks "what's the meal plan for tomorrow?", **When** the bot processes the request, **Then** it answers the question fully — quiet hours suppress proactive content, not responses to direct questions.
5. **Given** the `communication_mode` is "evening" and the n8n daily briefing job fires, **When** the nudge system checks the communication mode, **Then** proactive nudges are suppressed. Only user-initiated messages get responses.

---

### User Story 3 - Personal Routine Checklists (Priority: P2)

Erin can create, view, and modify personal routine checklists via WhatsApp. A routine is a named, ordered list of steps (e.g., "Morning Skincare: 1. Wash face, 2. Toner, 3. Vitamin C serum, 4. Moisturizer, 5. Sunscreen"). New tools `save_routine` and `get_routine` store and retrieve routines from `data/routines.json`. When the daily plan references a time block that matches a stored routine (e.g., "morning routine" block from 7-7:20am), the bot mentions it: "Your morning skincare routine (5 steps, ~10 min)." Erin can say "show me my morning routine" to get the full checklist, or "add vitamin C serum after toner in my morning routine" to modify it.

**Why this priority**: This addresses Issue #15 directly. Erin specifically requested this feature on Feb 25. It is lower priority than US1 and US2 because the bot must first have accurate context and appropriate communication modes before adding new data types. However, it delivers clear standalone value — Erin can use routines independently of whether the context tool is perfect.

**Independent Test**: Send "save my morning routine: wash face, toner, serum, moisturizer, sunscreen" via WhatsApp. Then send "show me my morning routine." Verify the bot returns the ordered checklist. Then send "add SPF after moisturizer" and verify the step is inserted at the correct position.

**Acceptance Scenarios**:

1. **Given** Erin has no stored routines, **When** she sends "save my morning routine: wash face, toner, serum, moisturizer, sunscreen", **Then** the bot calls `save_routine` with the name "morning" and the ordered steps, stores it in `data/routines.json`, and confirms: "Saved your morning routine (5 steps). Say 'show me my morning routine' anytime to see it."
2. **Given** Erin has a stored "morning" routine, **When** she sends "show me my morning routine", **Then** the bot calls `get_routine` and returns a formatted numbered checklist with all steps.
3. **Given** Erin has a stored "morning" routine with steps [wash face, toner, moisturizer, sunscreen], **When** she sends "add vitamin C serum after toner", **Then** the bot inserts "Vitamin C serum" at position 3 (after toner, before moisturizer), saves the updated routine, and confirms the change showing the new order.
4. **Given** Erin has a stored "morning" routine, **When** the daily plan is generated and includes a morning block, **Then** the plan references the routine: "Your morning skincare routine (5 steps, ~10 min)" with a note that she can say "show morning routine" for the full list.
5. **Given** Erin sends "show me my evening routine" but no evening routine exists, **When** the bot processes the request, **Then** it responds: "You don't have an evening routine saved yet. Want to create one? Just tell me the steps."
6. **Given** Erin sends "delete my morning routine", **When** the bot processes the request, **Then** the routine is removed from storage and the bot confirms deletion.

---

### User Story 4 - System Prompt Cleanup (Priority: P2)

The system prompt is reduced from ~413 lines to ~280 lines or fewer by removing all hardcoded data that now comes from tools. Specifically removed: the hardcoded weekly schedule (lines 46-58), the hardcoded childcare schedule (lines 43-44), Jason's breakfast preference (line 60-61), Erin's chore windows (lines 73-74), and day-specific activity references throughout rules 9-15. What remains: the bot's identity and personality, family member names and roles (static facts), behavioral rules for formatting, tool usage instructions, and cross-domain reasoning guidelines. Dynamic data is sourced exclusively from tools: `get_daily_context` for schedule and time, `get_preferences` / `list_preferences` for user preferences, `get_routine` for routines, and `read_family_profile` for family-specific preferences like breakfast orders.

**Why this priority**: This is a cleanup story that depends on US1 being complete (the context tool must exist before the hardcoded data can be safely removed). It reduces system prompt maintenance burden and prevents future drift, but does not add new user-facing functionality. Marking it P2 because the system prompt cleanup could be done incrementally alongside US1 implementation.

**Independent Test**: Count the lines in the system prompt before and after the cleanup. Verify a reduction of at least 30%. Then run the full daily plan flow and verify that no information is lost — everything that was previously hardcoded is now available via tool calls.

**Acceptance Scenarios**:

1. **Given** the system prompt contains the hardcoded weekly schedule, **When** US4 is complete, **Then** lines 46-58 (weekly schedule) are removed and replaced with an instruction: "Call `get_daily_context` for today's schedule, childcare status, and active preferences."
2. **Given** the system prompt contains Jason's breakfast preference, **When** US4 is complete, **Then** the breakfast preference is moved to the Notion family profile page and retrieved via `read_family_profile`, not hardcoded in the prompt.
3. **Given** the system prompt contains Erin's chore windows referencing specific days, **When** US4 is complete, **Then** day-specific chore windows are removed. The bot infers optimal chore windows from the `get_daily_context` output (free time blocks between calendar events).
4. **Given** the cleaned-up system prompt, **When** the bot generates a daily plan, **Then** the output quality is equivalent to or better than before — all schedule data, childcare status, and preferences are available via tool calls.
5. **Given** the system prompt after cleanup, **When** counted, **Then** it contains 280 lines or fewer (a reduction of at least 30% from the original ~413 lines).

---

### Edge Cases

- **Google Calendar API is down**: The `get_daily_context` tool catches the API error, returns a response with `calendar_available: false` and a message explaining that calendar data is temporarily unavailable. The bot tells the user and offers to retry later. It does not fall back to stale hardcoded data — that data no longer exists in the prompt.
- **Zoey transitions to preschool mid-week**: Because childcare is inferred from calendar events (not hardcoded rules), the transition is handled naturally. On Monday Zoey still has Sandy (Sandy's calendar event exists); on Wednesday her preschool event appears instead. No code change required.
- **Both parents at the same event**: If both Jason's and Erin's calendars show "BSF" at the same time, the context tool reports it under both people. The model sees that both are occupied and infers Zoey needs alternative care. Combined with Issue #14's calendar naming fix, this becomes unambiguous.
- **Routine referenced but does not exist**: When the daily plan references a time block like "morning routine" but no routine is stored, the bot notes: "No morning routine saved — want to create one?" This is a soft suggestion, not an error.
- **User asks about a routine at late night**: The communication mode "late_night" still allows Erin to view her routine if she explicitly asks. Quiet hours suppress proactive references to routines (in daily plans), not direct requests.
- **Preference and context tool conflict**: If Erin has a preference "don't tell me about Jason's appointments" but explicitly asks "what's Jason doing today?", the context tool still returns Jason's events. The preference system (Feature 013) already handles this — opt-outs only suppress unsolicited content.
- **Timezone edge case**: The context tool always uses Pacific time (America/Los_Angeles). If a family member travels, the tool still reports Pacific time. Timezone-awareness for travel is out of scope.
- **System prompt references removed data**: After US4 cleanup, if any remaining rule references hardcoded data that was removed (e.g., "check who has Zoey today" referencing the old schedule), it must be updated to reference the tool instead. A full audit of all 71 rules is required.
- **Routine with zero steps**: If Erin says "save my morning routine" without listing any steps, the bot asks for the steps rather than saving an empty routine.
- **Communication mode boundary**: At exactly 9:00 PM, the mode transitions from "evening" to "late_night." The transition is instant — there is no gradual fade. If a user sends a message at 8:59 PM they get "evening" mode; at 9:00 PM they get "late_night."

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `get_daily_context` tool that returns a structured snapshot of the current family context: Pacific time, today's calendar events grouped by person, childcare inference (who has Zoey), active user preferences, pending backlog count, and communication mode.
- **FR-002**: System MUST remove the hardcoded weekly schedule (current lines 46-58 of the system prompt) and replace all schedule-dependent logic with calls to `get_daily_context`.
- **FR-003**: System MUST infer who has Zoey based on calendar events: if a calendar event on Erin's, Jason's, or family calendar mentions Zoey, Sandy, preschool, or childcare-related keywords during the current time window, the context tool reports the childcare status.
- **FR-004**: System MUST include a `communication_mode` field in the context tool output, derived from the current Pacific time and the user's quiet hours preferences: "morning" (7am-12pm), "afternoon" (12pm-5pm), "evening" (5pm-9pm), "late_night" (9pm-7am).
- **FR-005**: System MUST suppress all proactive suggestions, task recommendations, and follow-up prompts when the communication mode is "late_night." Direct answers to explicit questions are still provided.
- **FR-006**: System MUST allow users to customize communication mode boundaries via the existing preference system (Feature 013). A preference like "quiet after 8pm" adjusts the "late_night" start time.
- **FR-007**: System MUST provide a `save_routine` tool that stores a named, ordered list of steps in `data/routines.json`, following the same atomic-write and in-memory-cache pattern as `preferences.py`.
- **FR-008**: System MUST provide a `get_routine` tool that retrieves a stored routine by name and returns the ordered steps in a formatted list.
- **FR-009**: System MUST support routine modification: inserting a step at a specific position ("add X after Y"), removing a step ("remove X from my morning routine"), and reordering steps.
- **FR-010**: System MUST reference stored routines in daily plan generation when a time block matches a routine name (e.g., "morning routine" block references the stored morning routine with step count and estimated duration).
- **FR-011**: System MUST reduce the system prompt to 280 lines or fewer by removing all hardcoded schedule data, food preferences, and day-specific activity references.
- **FR-012**: System MUST retain all behavioral rules (formatting, tool usage instructions, cross-domain reasoning, nudge interactions) in the system prompt after cleanup.
- **FR-013**: System MUST attribute calendar events to the correct person using the `_calendar_source` field from the calendar API, and group events by person in the context tool output.
- **FR-014**: System MUST handle Google Calendar API failures gracefully — return a degraded context response with `calendar_available: false` rather than crashing or returning stale data.
- **FR-015**: System MUST store routines per phone number (same as preferences) so Jason and Erin can have separate routines.
- **FR-016**: System MUST load routines from disk on startup and keep the in-memory cache synchronized with the on-disk file after every write, using atomic file writes (write-to-tmp-then-rename).

### Key Entities

- **Daily Context**: A structured snapshot returned by the `get_daily_context` tool. Key attributes: current Pacific timestamp, communication mode, calendar events grouped by person (jason_events, erin_events, family_events), childcare status (who has Zoey and until when), active user preferences summary, pending backlog item count, and calendar availability flag.
- **Communication Mode**: One of four time-of-day modes (morning, afternoon, evening, late_night) that controls the bot's tone and proactivity level. Boundaries are configurable per user via preferences.
- **Routine**: A named, ordered list of steps belonging to a specific user. Key attributes: name (e.g., "morning skincare"), owner phone number, ordered list of step descriptions, creation timestamp, last-modified timestamp. Stored in `data/routines.json`.
- **Routine Step**: A single action within a routine. Key attributes: position (ordinal), description (e.g., "Apply vitamin C serum"), optional estimated duration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System prompt shrinks by at least 30% — from ~413 lines to 280 lines or fewer.
- **SC-002**: No more "Today is Saturday!" corrections — the bot always knows the correct day, time, and what events are happening, because it reads live calendar data instead of a hardcoded schedule.
- **SC-003**: The bot correctly identifies event attendees from calendar source labels — events from Erin's calendar are attributed to Erin, events from Jason's calendar to Jason, events from the family calendar to both.
- **SC-004**: Zero proactive suggestions between 9pm and 7am Pacific (default quiet hours) unless the user initiates the conversation with an explicit question.
- **SC-005**: Erin can create, view, and modify personal routines via WhatsApp — verified by creating a routine, viewing it, adding a step, and confirming the updated order.
- **SC-006**: Schedule changes (new preschool, ended ski lessons, changed BSF day) require zero code deploys — the bot adapts immediately because it reads live calendar data.
