# Feature Specification: Chat Memory & Conversation Persistence

**Feature Branch**: `007-chat-memory`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Erin said she asks follow-up questions to Mom Bot and it doesn't know what she's talking about. Implement conversation persistence so the bot remembers recent context, enabling natural multi-turn conversations."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Conversational Follow-Ups (Priority: P1)

When Erin sends a follow-up message that references something from her recent conversation, Mom Bot understands the context and responds correctly — just like texting a friend who remembers what you were just talking about. Currently, every message is treated as brand new, so "tell me more about number 2" after a recipe search means nothing to the bot.

**Why this priority**: This is the core problem Erin reported. Without conversation memory, multi-step workflows (recipe search → details → save, meal plan → swap → grocery push) all break. This single change makes the bot feel like a real assistant instead of a goldfish.

**Independent Test**: Send "what's on our calendar this week?" → get a response. Then send "what about next week?" → verify the bot understands this is a follow-up about the calendar (not a standalone question).

**Acceptance Scenarios**:

1. **Given** Erin has just asked for a meal plan, **When** she sends "swap Wednesday for tacos", **Then** the bot recalls the meal plan from the previous message and performs the swap without asking her to repeat the plan.
2. **Given** Erin searched Downshiftology for chicken recipes, **When** she says "tell me more about number 2", **Then** the bot retrieves details for the second result from the previous search.
3. **Given** Erin asked "what's on our calendar this week?", **When** she follows up with "what about next week?", **Then** the bot understands she wants the calendar for the following week.
4. **Given** Erin asked for a budget summary, **When** she says "what about groceries specifically?", **Then** the bot narrows to the Groceries category without her needing to say "get budget summary for groceries".

---

### User Story 2 — Multi-Step Workflows (Priority: P2)

The bot supports natural multi-step interactions where each step builds on the previous. For example: Erin asks for recipe ideas → picks one → asks to see ingredients → says "add those to the grocery list" → says "order it". This entire chain should work without Erin needing to repeat context at each step.

**Why this priority**: Multi-step workflows are where conversation memory delivers the most value. Erin currently has to re-explain context at every step, making complex tasks tedious. This story extends US1 by ensuring tool results (not just messages) are preserved for reference.

**Independent Test**: Run a 4-step recipe workflow: "find me a chicken dinner" → "number 3 looks good, tell me more" → "save that one" → "add the ingredients to the grocery list". Verify each step works without re-stating context.

**Acceptance Scenarios**:

1. **Given** Erin searched Downshiftology and got results, **When** she says "save number 2", **Then** the bot imports the second result without her needing to name the recipe.
2. **Given** Erin is viewing recipe details, **When** she says "add those ingredients to the grocery list", **Then** the bot generates a grocery list from the recipe in context.
3. **Given** a grocery list was just generated, **When** Erin says "order it" or "push to AnyList", **Then** the bot pushes the contextual grocery list without asking what items.
4. **Given** Erin completed a budget check, **When** she says "move $50 from that to Groceries", **Then** the bot understands "that" refers to the category she was just viewing.

---

### User Story 3 — Conversation Boundaries (Priority: P3)

Conversations have a natural expiry so that stale context from hours ago doesn't confuse new topics. If Erin was talking about recipes this morning but messages about the calendar in the afternoon, the old recipe context doesn't interfere.

**Why this priority**: Without boundaries, accumulated history could cause confusion or irrelevant context. This story ensures the conversation window is right-sized — long enough for natural multi-turn exchanges but not so long that old topics leak into new ones.

**Independent Test**: Have a conversation about recipes, wait beyond the expiry window, then send "what's my budget look like?" — verify the bot treats this as a fresh conversation with no recipe context bleeding in.

**Acceptance Scenarios**:

1. **Given** Erin had a recipe conversation 2 hours ago, **When** she sends a new message about the budget, **Then** the bot does not reference or confuse context from the earlier recipe conversation.
2. **Given** Erin sends messages 5 minutes apart on the same topic, **When** she continues the conversation, **Then** the full recent history is available as context.
3. **Given** the system restarts (container redeployment), **When** Erin sends a follow-up message that was part of a pre-restart conversation, **Then** her conversation history is still available.
4. **Given** Jason and Erin are both messaging the bot around the same time, **When** each sends a follow-up, **Then** each person's history is independent — Jason's recipes don't appear in Erin's calendar conversation.

---

### Edge Cases

- What happens when the conversation history gets very long (e.g., 20+ messages in a session)? The system should manage size by prioritizing recent messages and summarizing or dropping the oldest ones.
- What happens when Erin sends a message that could be either a follow-up or a new topic (ambiguous)? The bot should include history as context and let the AI determine relevance — do not force-clear history on topic change.
- What happens when automated system messages (daily briefing, nudge reminders) are sent between Erin's manual messages? Automated messages should not appear in or disrupt the user's conversation history.
- What happens when Erin sends a photo (recipe page) followed by a text command? The image context should be preserved in history alongside the text, but stored image data should be referenced (not duplicated in full) to manage storage.
- What happens if two messages arrive nearly simultaneously? The system should process messages sequentially per phone number to prevent race conditions in history storage.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain a conversation history for each user, identified by phone number.
- **FR-002**: When processing a new message, the system MUST include recent conversation history as context so the AI can understand follow-up questions and references.
- **FR-003**: Conversation history MUST include both user messages and bot responses (the full exchange).
- **FR-004**: Conversation history MUST include tool call information (what tools were used and their results) so that follow-up references like "number 2" or "save that one" can be resolved.
- **FR-005**: Conversations MUST expire after a configurable period of inactivity (time since last message in the conversation). Default: 30 minutes.
- **FR-006**: Each user's conversation history MUST be independent — one user's context is never visible to another user.
- **FR-007**: Automated system messages (daily briefings, nudge reminders) MUST NOT be stored in or retrieved from user conversation histories.
- **FR-008**: The system MUST limit the amount of history included as context to prevent excessive processing time or cost — either by message count, token count, or a combination.
- **FR-009**: Conversation history MUST persist across container restarts so that a mid-conversation restart does not break the flow.
- **FR-010**: The system MUST handle image messages in history by storing a reference or placeholder rather than the full image data, to manage storage size.

### Key Entities

- **Conversation**: A time-bounded sequence of exchanges between one user and the bot. Identified by phone number. Expires after a period of inactivity. Contains an ordered list of messages.
- **Message Entry**: A single exchange within a conversation — includes the user's input (text and/or image reference), the bot's response, and any tool calls/results that occurred during processing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Follow-up questions that reference the previous message are correctly understood at least 90% of the time when sent within the conversation window.
- **SC-002**: Multi-step workflows (3+ steps) complete successfully without the user needing to repeat context at any step.
- **SC-003**: Bot response time increases by no more than 2 seconds compared to the current baseline (no-history) for a typical conversation with 5 prior messages.
- **SC-004**: Conversations expire cleanly — messages sent after the inactivity window start a fresh context with no stale references.
- **SC-005**: Conversation history survives at least one container restart without data loss.

## Assumptions

- The family has 2 primary users (Jason and Erin), so storage requirements for conversation history are minimal.
- A 30-minute inactivity timeout is appropriate for family WhatsApp conversations — most follow-ups happen within minutes, and a new topic hours later should start fresh.
- The existing AI model's context window is large enough to accommodate a reasonable conversation history (10-20 message exchanges) alongside the system prompt and tool definitions.
- WhatsApp delivers messages in order per sender, so conversation history can be appended chronologically without reordering concerns.
- Image data (recipe photos) is already handled separately via module-level variables; conversation history only needs to store that an image was sent, not the full base64 data.
- MCP (Model Context Protocol) server refactoring was mentioned as a possible approach but is not required to solve the conversation memory problem — the existing tool architecture works and the fix is in how conversation context is passed to the AI.

## Out of Scope

- Cross-user conversation sharing (Jason seeing Erin's conversation context or vice versa)
- Long-term memory or knowledge base that persists across conversation sessions (e.g., "Erin always asks for keto recipes" — this is handled by the family profile)
- MCP server refactoring of the tool architecture (may be a future feature, not needed for conversation persistence)
- Conversation search, export, or viewing history
- Group chat threading or multi-party conversation context
- Semantic memory or learning from past conversations (beyond the current session window)
