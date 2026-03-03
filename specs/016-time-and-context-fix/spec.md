# Feature Specification: Time Awareness & Extended Conversation Context

**Feature Branch**: `016-time-and-context-fix`
**Created**: 2026-03-03
**Status**: Draft
**Input**: User description: "Fix two issues Erin reported: (1) Time awareness - bot doesn't reliably use the current time when responding. (2) Conversation context too short - extend to 7 days."
**Related**: GitHub Issue #7 (Time-context-aware recommendations)

## Context

Erin has reported two recurring frustrations:

1. **Time blindness**: The bot generates full-day schedules starting from morning when it's already afternoon. It also scheduled a reminder for the wrong date ("today" was interpreted as yesterday). The current time is already injected into the system prompt at the top and bottom, but the assistant doesn't reliably attend to it when generating schedules, setting reminders, or making time-based recommendations.

2. **Short memory**: The conversation resets too quickly. Erin wants the bot to remember what was discussed earlier in the week — e.g., a meal plan decision on Monday should still be known on Wednesday. The family doesn't send many messages, so a week of history is manageable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Time-Aware Responses (Priority: P1)

When Erin asks the bot for help with scheduling, planning, or reminders, the bot must always consider the current time. It should never suggest activities for times that have already passed, and it should correctly interpret relative time references like "today," "this afternoon," and "later."

**Why this priority**: This is the most impactful issue — Erin has complained about it multiple times (GitHub Issue #7). Getting irrelevant morning schedules at noon makes the bot feel broken.

**Independent Test**: Send a message at 2:00 PM asking "plan my day" — the response should only include afternoon/evening items, with no morning activities.

**Acceptance Scenarios**:

1. **Given** it is 12:30 PM, **When** Erin asks "plan my Monday," **Then** the bot responds with only afternoon/evening tasks, acknowledging that the morning has passed.
2. **Given** it is 3:00 PM on March 3, **When** Erin says "remind me today at 1:45 to call Banfield," **Then** the bot recognizes 1:45 PM has already passed and asks if she means tomorrow.
3. **Given** it is 10:00 PM, **When** Erin asks for scheduling help, **Then** the bot focuses on the next day rather than suggesting late-night tasks.
4. **Given** it is 8:00 AM on Tuesday, **When** Erin says "what do I have today," **Then** the bot shows today's (Tuesday's) schedule, not yesterday's.

---

### User Story 2 - Extended Conversation Memory (Priority: P1)

The bot remembers conversations from the past week. If Erin discussed meal plans on Monday, the bot should still know about that conversation on Thursday without her repeating it.

**Why this priority**: Without sufficient context, the bot asks Erin to repeat information she already provided, which is frustrating and wastes time.

**Independent Test**: Send a message on Monday about a dinner plan. On Wednesday, ask "what did we decide about dinner this week?" — the bot should recall the Monday conversation.

**Acceptance Scenarios**:

1. **Given** Erin discussed a chicken recipe on Monday, **When** she asks "what was that recipe we talked about?" on Wednesday, **Then** the bot recalls the Monday conversation and provides the answer.
2. **Given** no messages for 3 days within the same week, **When** Erin sends a new message, **Then** the bot still has access to conversations from before the gap.
3. **Given** conversations from 8+ days ago, **When** a new message arrives, **Then** those old conversations are no longer in the active context (to keep responses focused).
4. **Given** both Jason and Erin send messages during the week, **When** either asks about a prior conversation, **Then** the bot recalls the relevant history for that specific person (not mixing up who said what).

---

### Edge Cases

- What happens when the time is near midnight (e.g., 11:55 PM)? The bot should treat "today" as the current calendar day, not get confused by the day boundary.
- What happens when Erin says "this morning" at 2 PM? The bot should understand that morning has passed and respond accordingly (e.g., "This morning has already passed — did you mean tomorrow morning?").
- What happens when conversation history exceeds 7 days? Oldest conversations are dropped automatically without affecting recent ones.
- What happens when a user sends many messages in one day? The system should handle high-volume days without losing earlier-in-the-week context.
- What happens when the user references a time without AM/PM (e.g., "at 3")? The bot should infer from context (3 PM if daytime, clarify if ambiguous).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST include the current date, day of week, and time in every interaction with the assistant, positioned so the assistant reliably attends to it.
- **FR-002**: When generating schedules or daily plans, the system MUST filter out time blocks that have already passed, showing only future activities.
- **FR-003**: When a user requests a reminder or event for a time that has already passed today, the system MUST either ask for clarification or suggest the next occurrence.
- **FR-004**: The system MUST correctly resolve relative time references ("today," "tomorrow," "this afternoon," "tonight") based on the current date and time.
- **FR-005**: The system MUST include explicit instructions to the assistant about checking the current time before generating any schedule, plan, or time-based recommendation.
- **FR-006**: The system MUST retain conversation history for at least 7 days per user.
- **FR-007**: The system MUST automatically discard conversation history older than 7 days.
- **FR-008**: The system MUST maintain separate conversation histories per user (phone number), not mixing context between family members.
- **FR-009**: The system MUST support at least 100 conversation turns within the 7-day retention window.

### Key Entities

- **Conversation History**: Per-user message log with timestamps, retained for 7 days. Each entry includes the user message, assistant response, and any tool interactions.
- **Time Context**: Current date, day of week, and time injected into every assistant interaction. Must be prominent enough that the assistant reliably uses it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When asked to "plan my day" after noon, the bot produces a schedule that starts from the current time or later in 100% of cases (zero morning items after noon).
- **SC-002**: Relative time references ("today," "tomorrow," "tonight") resolve to the correct calendar date in 100% of cases.
- **SC-003**: The bot can recall conversations from up to 7 days ago when asked about prior discussions.
- **SC-004**: Erin no longer needs to repeat information she shared earlier in the same week (reduces "what did I say about X?" re-asks to zero).

## Assumptions

- The family sends fewer than 100 turns per person per week, so a 7-day / 100-turn window is sufficient.
- The Docker container's system clock is accurate (NTP-synced), even though it runs in UTC — the application handles timezone conversion.
- The assistant model (Claude) will reliably attend to time information if it is presented prominently and with explicit instructions about how to use it.
- Conversation storage size at ~100 turns per user for 7 days is small enough to fit in a single JSON file without performance concerns.

## Out of Scope

- Proactive time-based suggestions (e.g., "it's almost pickup time!") — that's a separate feature.
- Time zone configuration per user — Reno, NV (Pacific) is hardcoded for this family.
- Message-level timestamps in the conversation display — this is about the assistant's internal awareness, not showing timestamps to users.
- Compression or summarization of old conversation history — simply discard after 7 days.
