# Feature Specification: AI Failover & Resilience Improvements

**Feature Branch**: `034-ai-failover-resilience`
**Created**: 2026-03-13
**Status**: Draft
**Input**: User description: "AI failover and resilience improvements: backup AI provider fallback, fix silent tool failures, detect lost messages, fix premature action item completion, proactive system log diagnostics"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backup AI Provider Failover (Priority: P1)

When the primary AI service is unavailable (overloaded, outage, or timeout), the assistant automatically switches to a backup AI provider so users continue receiving responses without interruption. The user should not notice any degradation other than a brief delay.

**Why this priority**: Without AI failover, the entire assistant becomes unusable during outages. Users like Erin depend on it for daily planning, reminders, and family coordination. A Claude outage means zero functionality.

**Independent Test**: Send a message while the primary AI service is simulated as unavailable. The assistant should respond using the backup provider within a reasonable time.

**Acceptance Scenarios**:

1. **Given** the primary AI service returns a server error or overload response, **When** a user sends a message, **Then** the system retries the request with a backup AI provider and delivers a response to the user.
2. **Given** the primary AI service times out after the configured threshold, **When** a user sends a message, **Then** the system switches to the backup provider without requiring user action.
3. **Given** the backup AI provider is used, **When** the response is delivered, **Then** the user sees a brief note that a backup service was used (e.g., "Note: using backup assistant today").
4. **Given** both the primary and backup AI services are unavailable, **When** a user sends a message, **Then** the system sends a friendly error message explaining the outage and suggesting the user try again later.

---

### User Story 2 - Eliminate Silent Tool Failures (Priority: P2)

When any tool or integration fails during message processing, the assistant MUST inform the user about the failure and what was affected. The assistant must never silently swallow an error and pretend everything succeeded.

**Why this priority**: In real usage, Erin asked for a calendar reminder and the bot responded positively — but the calendar tool had failed silently. She believed the reminder was set when it wasn't. This directly breaks user trust.

**Independent Test**: Trigger a tool failure (e.g., calendar unavailable) and verify the bot explicitly tells the user the action failed, what it tried to do instead, and what the user should know.

**Acceptance Scenarios**:

1. **Given** a tool call returns an error, **When** the assistant composes its response, **Then** it MUST mention the failure to the user and explain what happened.
2. **Given** a tool call returns an error and a fallback succeeds, **When** the assistant responds, **Then** it tells the user the original action failed, what fallback was used, and why (with diagnostic context from system logs).
3. **Given** a tool call returns an "unavailable" or error string (not an exception), **When** the assistant processes the result, **Then** it recognizes this as a failure and does not present it as a success.
4. **Given** multiple tool calls in one response where some succeed and some fail, **When** the assistant responds, **Then** it clearly distinguishes which actions succeeded and which did not.

---

### User Story 3 - Detect and Handle Lost Messages (Priority: P3)

When a user's message appears to reference a previous message that the system never received (e.g., "read the message I just sent"), the assistant acknowledges the gap and asks the user to resend rather than pretending nothing happened.

**Why this priority**: Erin experienced a dropped message and the bot couldn't help. Acknowledging the gap and asking to resend is a better experience than a confused response.

**Independent Test**: Send "read the message I just sent you" as the first message in a conversation (or after a long gap). The assistant should recognize the implied missing message and ask the user to resend.

**Acceptance Scenarios**:

1. **Given** a user sends a message that references a prior message the system has no record of (e.g., "what do you think about what I said?", "read my last message", "did you get that?"), **When** the assistant processes this, **Then** it responds by acknowledging the gap and asking the user to resend.
2. **Given** a user sends a follow-up message that implies context the system doesn't have (e.g., "so can you do that?" with no prior request in the conversation), **When** the assistant processes this, **Then** it politely explains it may have missed the previous message and asks the user to repeat.
3. **Given** a normal conversation flow where the user references something discussed earlier in the same session, **When** the assistant has that context, **Then** it responds normally (no false positive "I missed your message" warnings).

---

### User Story 4 - Fix Premature Action Item Completion (Priority: P3)

When a user states their intention to do something ("I'm going to do X this afternoon"), the assistant should NOT mark the corresponding action item as complete. Items should only be marked done when the user confirms actual completion.

**Why this priority**: Erin said "I'm getting my blood draw this afternoon" and the bot marked the action item as done. She didn't actually complete it for two more days. This undermines the reliability of the action item system.

**Independent Test**: Tell the bot "I'm going to do my blood draw this afternoon" when a "blood draw" action item exists. The item should remain open. Then say "Done with the blood draw" — only then should it be marked complete.

**Acceptance Scenarios**:

1. **Given** a user expresses intent to do a task ("I'll do X later", "I'm planning to X", "going to X this afternoon"), **When** a matching action item exists, **Then** the assistant does NOT mark it as complete.
2. **Given** a user confirms completion of a task ("done", "finished X", "just did X", "X is done"), **When** a matching action item exists, **Then** the assistant marks it as complete.
3. **Given** a user says "I need to do X" or "don't forget about X", **When** a matching action item exists, **Then** the assistant acknowledges the item but does NOT mark it as complete.

---

### User Story 5 - Proactive System Log Diagnostics (Priority: P2)

When the assistant encounters errors or a user reports issues, it proactively checks its system logs to diagnose the problem and provides specific, actionable information instead of generic error messages.

**Why this priority**: When asked "can you see the railway logs?", the bot previously said "I can't see logs." Now it has a log inspection tool. This story ensures it uses log diagnostics proactively — not just when the user explicitly asks about system health, but whenever errors occur that the user should know about.

**Independent Test**: Trigger a tool failure and verify the bot's response includes specific diagnostic information (e.g., "Google Calendar auth token expired" rather than "calendar is having issues").

**Acceptance Scenarios**:

1. **Given** a tool fails during message processing, **When** the assistant composes its error response, **Then** it includes specific diagnostic context from recent system logs (e.g., "auth token expired", "service is overloaded", "API rate limit hit").
2. **Given** a user asks about system status or reports something isn't working, **When** the assistant processes the message, **Then** it checks system logs and reports specific findings.
3. **Given** system logs show a recurring pattern of errors for a specific integration, **When** the assistant reports the issue, **Then** it provides actionable guidance (e.g., "Jason needs to refresh the calendar token" rather than "calendar is down").

---

### Edge Cases

- What happens when the backup AI provider is also down? System sends a static fallback message via the messaging channel.
- What happens when the primary AI comes back mid-conversation that started on backup? Continue on backup for the current message to avoid confusion; primary resumes on next message.
- What happens when a tool returns a non-exception error string (e.g., "currently unavailable") that looks like success? The system must recognize common error patterns in tool return strings.
- What happens when a user says "I did X" but no matching action item exists? The bot acknowledges without trying to complete a non-existent item.
- What happens when system logs are unavailable (Axiom down)? The bot falls back to generic error messages without crashing.
- What happens when a user sends multiple messages rapidly and some are lost? The bot cannot detect what it never received; it can only detect references to missing context.
- What happens when a user requests an action that requires a tool not available on the backup provider? The assistant informs the user the action is temporarily unavailable and will work again when the primary service recovers.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST attempt the primary AI provider first for every user message.
- **FR-002**: System MUST automatically switch to a backup AI provider when the primary returns server errors, overload responses, or times out.
- **FR-003**: System MUST send a static error message to the user when both primary and backup AI providers are unavailable.
- **FR-004**: System MUST surface all tool failures to the user — no tool error may be silently ignored in the assistant's response.
- **FR-005**: System MUST include diagnostic context from system logs when reporting tool failures to users.
- **FR-006**: System MUST recognize references to missing prior messages and ask the user to resend.
- **FR-007**: System MUST distinguish between user intent ("I'm going to do X") and user confirmation ("I did X") when processing action item completions.
- **FR-008**: System MUST NOT mark action items as complete based on stated intent alone.
- **FR-009**: System MUST include a brief indicator when a backup AI provider generated the response.
- **FR-010**: System MUST audit all existing tool call result handling paths to ensure no error strings are treated as success.

### Non-Functional Requirements

- **NFR-001**: The primary AI provider timeout threshold is 45 seconds. Failover to the backup AI provider MUST complete within 5 seconds of detecting a primary failure (not counting the initial 45-second timeout).
- **NFR-002**: The backup AI provider MUST support a core subset of ~10 most-used tools (daily context, calendar read/write, action items, preferences, system logs, family profile) using OpenAI's tool-calling interface. Tools not in the core subset are unavailable during failover; the assistant MUST inform the user if a requested action requires a tool not available on the backup.
- **NFR-003**: System log queries for diagnostics MUST complete within 5 seconds and MUST NOT block the response if they fail.

### Key Entities

- **AI Provider Configuration**: Which providers are available, their priority order, timeout thresholds, and API credentials.
- **Tool Execution Result**: The outcome of a tool call including success/failure status, error details, fallback actions taken, and diagnostic context.
- **Message Context Window**: Recent conversation history used to detect references to missing messages.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users receive a response to 99% of messages even during primary AI outages (measured over a 30-day period).
- **SC-002**: Zero silent tool failures — 100% of tool errors result in explicit user notification (verified by log audit).
- **SC-003**: Users receive specific diagnostic context (not generic "service is down") for 90% of tool failures.
- **SC-004**: Action items are never marked complete based on stated intent — only explicit confirmation triggers completion (verified by conversation audit).
- **SC-005**: References to missing messages are correctly detected and the user is asked to resend in 80% of cases (with less than 5% false positive rate).

## Clarifications

### Session 2026-03-13

- Q: Which backup AI provider should be used? → A: OpenAI GPT only
- Q: What is the primary AI timeout threshold before failover? → A: 45 seconds
- Q: Should the backup provider support all 30+ tools or a core subset? → A: Core subset (~10 most-used tools)

## Assumptions

- The backup AI provider is OpenAI GPT, chosen for its mature tool-calling interface and straightforward format conversion from Claude's tool definitions.
- API keys for the backup provider will be configured as environment variables.
- The backup provider does not need to perfectly match the primary's personality or family context — functional correctness is the priority during failover. Only a core subset of ~10 most-used tools is available on the backup; advanced integrations (YNAB, recipes, AnyList, etc.) are deferred until the primary recovers.
- The premature completion fix is implemented through improved system prompt instructions rather than code-level intent classification, since the AI interprets user messages.
- System log diagnostics are best-effort and should never cause additional failures.
