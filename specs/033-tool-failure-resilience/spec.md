# Feature Specification: Tool Failure Resilience

**Feature Branch**: `033-tool-failure-resilience`
**Created**: 2026-03-12
**Status**: Draft
**Input**: User description: "Investigate Erin's failed reminders and add resilience — automatic retry, clear error reporting, and fallback actions when tools fail"

## Context

On March 4-5, 2026, Erin requested two calendar reminders that silently failed:

1. **Blood draw appointment** (March 5, 2:00 PM) — `create_quick_event` returned an error. The bot ignored the failure and said "You're DONE with today's list!" without mentioning the reminder wasn't created.
2. **Milestones paperwork pickup** (March 6, 11:15 AM) — Same tool error. Bot handled this one better by acknowledging the failure and suggesting an alternative.

**Root cause**: Google Calendar API was temporarily unavailable. The current error handler catches all tool exceptions and returns a generic message that tells the AI to "Skip this section." This gives the AI model permission to silently skip the failed action — leaving the user unaware that their request wasn't fulfilled.

Investigation confirmed this was NOT a Claude AI outage. However, the user's instinct about AI provider resilience is valid as a separate future concern.

## Clarifications

### Session 2026-03-12

- Q: How specific should the error context provided to the AI be? → A: Service-aware — AI receives the integration name and a human-readable failure reason so it can tell the user which specific service is down (e.g., "Google Calendar is having an outage") rather than a vague "something went wrong."
- Q: Which tools should have explicit fallback mappings? → A: Only write/create operations — these are where failure means the user's request was silently lost. Read failures just need clear error reporting.

## User Scenarios & Testing

### User Story 1 - Automatic Retry on Tool Failure (Priority: P1)

When a tool fails (e.g., Calendar API timeout, Notion rate limit), the system should automatically retry before giving up. Most transient failures resolve within seconds.

**Why this priority**: Retrying eliminates the majority of transient failures without any user impact. This is the highest-leverage fix — most of Erin's failed reminders would have succeeded on a second attempt.

**Independent Test**: Can be tested by simulating a tool that fails once then succeeds, verifying the retry happens transparently and the user gets a successful result.

**Acceptance Scenarios**:

1. **Given** a tool call fails with a transient error (timeout, rate limit, connection reset), **When** the system retries after a brief delay, **Then** the tool succeeds and the user receives the expected response with no indication of the initial failure.
2. **Given** a tool call fails on all retry attempts, **When** retries are exhausted, **Then** the system proceeds to error reporting (User Story 2) rather than silently skipping.
3. **Given** a tool call fails with a permanent error (invalid parameters, missing permissions), **When** the error is non-retryable, **Then** the system skips retry and proceeds directly to error reporting.

---

### User Story 2 - Clear Error Reporting to User (Priority: P2)

When a tool permanently fails (after retries), the user must be told clearly what didn't work and what they should do about it. No silent failures.

**Why this priority**: Even with retries, some failures will persist. The current behavior of silently skipping failed actions is the core UX problem — Erin thought her reminder was set when it wasn't.

**Independent Test**: Can be tested by forcing a tool to fail permanently, verifying the bot's response clearly states what failed and offers an alternative.

**Acceptance Scenarios**:

1. **Given** a calendar event creation fails after retries, **When** the bot responds to the user, **Then** the response names the specific service that failed (e.g., "Google Calendar is down right now") and states the action was NOT completed, then suggests a specific alternative (e.g., "Want me to add it as an action item instead?").
2. **Given** a grocery list push fails after retries, **When** the bot responds, **Then** it provides the items in a formatted message so the user can manually add them.
3. **Given** multiple tool calls in a single response where some succeed and some fail, **When** the bot responds, **Then** it clearly distinguishes which actions succeeded and which failed.

---

### User Story 3 - Automatic Fallback Actions (Priority: P3)

For common failure scenarios, the system should automatically take a fallback action instead of just reporting the error. If Calendar fails, create an action item. If AnyList fails, send the grocery list via message.

**Why this priority**: This transforms failures from "broken" to "degraded gracefully." The user still gets value even when an integration is down.

**Independent Test**: Can be tested by disabling the Calendar integration and requesting a reminder, verifying an action item is created automatically with the same details.

**Acceptance Scenarios**:

1. **Given** a calendar event creation fails, **When** fallback is triggered, **Then** the system automatically creates a Notion action item with the same details (title, date, time) and tells the user: "Calendar is down — I added this as an action item instead so you don't forget."
2. **Given** a grocery list push to AnyList fails, **When** fallback is triggered, **Then** the system sends the formatted grocery list via WhatsApp message and tells the user.
3. **Given** the fallback action itself fails (e.g., both Calendar AND Notion are down), **When** the secondary fallback fails, **Then** the system sends the details via WhatsApp message as a last resort — the user always receives the information.

---

### Edge Cases

- What happens when the same tool fails repeatedly across multiple user messages? The system should track recent failures and proactively warn: "Calendar has been having issues today."
- What happens during a multi-tool response where retry delays accumulate? Total response time including retries should not exceed 30 seconds.
- What happens when a retry succeeds but the tool was called with slightly different parameters by the AI on the second attempt? Treat the successful response as authoritative.
- What happens when the user sends a follow-up message repeating the same failed request? The system should handle it normally — the retry mechanism handles each request independently.

## Requirements

### Functional Requirements

- **FR-001**: System MUST retry failed tool calls up to 2 times with a brief delay between attempts before reporting failure
- **FR-002**: System MUST distinguish between retryable errors (timeouts, rate limits, connection resets, 5xx responses) and non-retryable errors (invalid parameters, 4xx responses, missing permissions)
- **FR-003**: System MUST provide the AI model with service-aware error context that includes the integration name (e.g., "Google Calendar") and a human-readable failure reason (e.g., "service unavailable"). The error message must instruct the model to tell the user which specific service failed and suggest alternatives — never allow silent skipping
- **FR-004**: System MUST define fallback mappings for all write/create operations. Read-only tool failures only require clear error reporting (no fallback needed). Write fallback mappings include: Calendar event creation → Notion Action Item, AnyList push → WhatsApp grocery list, Notion action item/meal plan writes → WhatsApp formatted message, and any other tool that creates or modifies user data
- **FR-005**: System MUST ensure the user always receives the information from their request, even if through a degraded channel (WhatsApp text as last resort)
- **FR-006**: System MUST log all tool failures with sufficient detail for debugging (tool name, error type, retry count, whether fallback was attempted, outcome)
- **FR-007**: System MUST complete all retries and fallbacks within a reasonable time — individual retry delays must not cause the overall response to exceed 30 seconds
- **FR-008**: System MUST NOT retry when the error indicates invalid user input (e.g., malformed date, unknown calendar name)

### Key Entities

- **ToolFailure**: A failed tool invocation — includes tool name, integration name (e.g., "Google Calendar"), human-readable failure reason, error classification (transient vs. permanent), retry count, fallback action taken, timestamp
- **FallbackMapping**: Maps a failed tool to its fallback action — primary tool, fallback tool, and last-resort action (WhatsApp message)

## Success Criteria

### Measurable Outcomes

- **SC-001**: 90% of transient tool failures are resolved by automatic retry, with no user-visible impact
- **SC-002**: 100% of permanent tool failures result in a user-visible message explaining what failed and what alternative was taken — zero silent failures
- **SC-003**: When a fallback action is taken, the user receives equivalent information within 5 seconds of the original failure
- **SC-004**: Overall response time including retries does not exceed 30 seconds for any user request
- **SC-005**: Tool failure rate and fallback usage are tracked in logs for operational monitoring

## Assumptions

- Google Calendar API transient failures are the most common failure mode (based on March 4-5 incident)
- Most transient failures resolve within 2-3 seconds, making a short retry delay sufficient
- The AI model (Claude) will follow explicit instructions in the error message about reporting failures to users — the current problem is that the error message says "Skip this section" which gives the model permission to ignore the failure
- Notion and WhatsApp are reliable enough to serve as fallback channels
- AI provider failover (Claude → Gemini/OpenAI) is a separate concern not addressed in this feature — the investigation confirmed the recent failures were tool-level, not AI-level

## Out of Scope

- AI provider failover (Claude → OpenAI/Gemini) — may be a separate feature if needed
- Proactive health monitoring or alerting dashboards for integrations
- User-configurable retry or fallback preferences
- Offline mode or message queuing for extended outages
