# Feature Specification: Feature Discovery & Onboarding

**Feature Branch**: `006-feature-discovery`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Feature discovery and onboarding for Erin — when Erin first texts the bot (or says 'what can you do?' / 'help'), Mom Bot responds with a personalized guided tour of all capabilities using examples from their real data."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Help Menu with Personalized Examples (Priority: P1)

When Erin (or Jason) asks "what can you do?", "help", or similar, Mom Bot responds with a categorized list of all capabilities. Each category includes 1-2 concrete example phrases the user can try, written using real family data (their actual grocery items, budget categories, calendar names, saved recipes) rather than generic placeholders.

**Why this priority**: This is the core value — Erin doesn't know what the bot can do unless she's told. A single help response with relevant examples is the minimum viable onboarding. Every other story builds on this.

**Independent Test**: Send "what can you do?" to the bot and verify the response lists all feature categories with personalized example phrases.

**Acceptance Scenarios**:

1. **Given** Erin has never used the bot before, **When** she sends "what can you do?", **Then** she receives a categorized list of capabilities grouped by topic (recipes, budget, calendar, groceries, chores, reminders, meal planning) with 1-2 example phrases per category she can copy and send.
2. **Given** Jason sends "help", **Then** he receives the same categorized list, and examples reference data relevant to him as well (e.g., his work calendar, budget categories).
3. **Given** the help response is displayed, **When** Erin copies and sends one of the example phrases, **Then** the bot correctly handles that request as if she had typed it herself.

---

### User Story 2 — "Did You Know?" Tips (Priority: P2)

The bot periodically includes a brief tip about an underused or recently-added feature at the end of a normal response, when contextually relevant. For example, after showing a meal plan, it might append: "Did you know? You can say 'find me a keto dinner recipe' to search Downshiftology for new recipe ideas." Tips are non-intrusive (appended after the main response, not sent as separate messages).

**Why this priority**: This surfaces features Erin might not think to ask about, increasing discovery over time. It requires the help content from US1 to exist first.

**Independent Test**: Trigger a meal plan response and verify a contextually relevant tip is appended about a related feature (e.g., recipe search after meal planning, grocery push after recipe details).

**Acceptance Scenarios**:

1. **Given** Erin asks for a meal plan, **When** the bot responds with the plan, **Then** a short tip about a related feature (e.g., recipe search, grocery push) is appended at the end, visually separated from the main content.
2. **Given** a tip was shown in the current conversation, **When** Erin sends another message in the same session, **Then** no additional tip is shown (maximum 1 tip per conversation to avoid annoyance).
3. **Given** Erin has seen a particular tip before, **When** the same context arises again, **Then** a different tip is shown (tips rotate rather than repeating).

---

### User Story 3 — First-Time Welcome Message (Priority: P3)

The very first time a family member messages the bot (no prior conversation history), the bot sends a brief welcome message introducing itself and offering to show what it can do. This is a one-time greeting that sets the tone and invites the user to ask for help.

**Why this priority**: Nice polish for day-one experience, but most users will discover the bot through the family's WhatsApp group where context is already established. Lower priority because the help command (US1) serves the same purpose on demand.

**Independent Test**: Simulate a first-time message from a phone number with no prior history and verify the welcome message appears with an invitation to see capabilities.

**Acceptance Scenarios**:

1. **Given** a family member sends their first-ever message to the bot, **When** the bot processes the message, **Then** it responds to their actual request AND prepends a brief one-time welcome (e.g., "Welcome to Mom Bot! I can help with recipes, budgets, calendars, groceries, chores, and reminders. Say 'help' anytime to see everything I can do.").
2. **Given** the welcome message has already been shown once, **When** the same person sends subsequent messages, **Then** no welcome message is shown again.

---

### User Story 4 — Usage Tracking & Smart Suggestions (Priority: P2)

The bot passively tracks which feature categories each user interacts with (recipes, budget, calendar, groceries, chores, family management) and uses this data to make smarter suggestions. When Erin asks for help, unused categories are highlighted. When contextual tips are shown, the system prioritizes tips about features she hasn't tried yet.

**Why this priority**: Builds on US1 and US2 to close the discovery loop — instead of random tips, the bot actively guides users toward capabilities they haven't explored. Simple counters per category, not a full analytics dashboard.

**Independent Test**: Use several features (recipes, budget, calendar) but not groceries or chores. Ask "help" → verify unused categories are highlighted. Trigger a tip context → verify tip prioritizes an underused category.

**Acceptance Scenarios**:

1. **Given** Erin has used recipes and budget features but never groceries, **When** she asks "help", **Then** the help response includes a "Haven't tried yet" section highlighting Groceries & Meal Planning with an example phrase.
2. **Given** Erin triggers a meal plan response, **When** the bot selects a tip, **Then** it prioritizes tips about categories she hasn't used (e.g., recipe search) over categories she uses frequently.
3. **Given** Erin has used all feature categories, **When** she asks "help", **Then** no "Haven't tried yet" section is shown (all categories explored).
4. **Given** the container restarts, **When** Erin sends a message, **Then** her usage history is preserved (counters persist across restarts).

---

### Edge Cases

- What happens when Erin says "help" in the middle of a multi-step flow (e.g., after a recipe search but before saving)? The help response should not clear the current search context.
- What happens when the bot can't fetch live data for personalized examples (e.g., grocery history unavailable)? Fall back to static examples that are still family-relevant.
- What if a new feature is added but the help content isn't updated? The help content should be maintainable in a single location so new features are easy to add.
- What happens if Erin sends "help" multiple times in a row? The bot should respond each time (not suppress repeats) since she may be showing someone else.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST respond to help trigger phrases ("what can you do?", "help", "what are your features?", "show me what you can do") with a categorized capabilities list.
- **FR-002**: The help response MUST group capabilities into categories: Recipes & Cooking, Budget & Spending, Calendar & Reminders, Groceries & Meal Planning, Chores & Home, and Family Management.
- **FR-003**: Each category in the help response MUST include 1-2 example phrases that reference real family data (e.g., actual budget category names, actual grocery items, real recipe names) when available.
- **FR-004**: When live data is unavailable for personalization, the system MUST fall back to static examples that are still contextually relevant to the family (not generic like "search for pizza recipe").
- **FR-005**: The help response MUST be formatted for WhatsApp readability (bold headers, bullet points, concise — scannable in under 30 seconds).
- **FR-006**: The system MUST support "did you know?" tips appended to normal responses, triggered by contextual relevance (e.g., recipe tip after meal planning, budget tip after grocery push).
- **FR-007**: Tips MUST be limited to 1 per conversation session to avoid being annoying.
- **FR-008**: Tips SHOULD vary across sessions. The system MUST track the last tip shown per user and avoid repeating it consecutively.
- **FR-009**: The system MUST support a first-time welcome message for new users that introduces the bot and invites them to say "help".
- **FR-010**: The help response MUST NOT clear or interfere with any in-progress state (e.g., recipe search results, laundry timers).
- **FR-011**: The system MUST passively track which feature categories each user interacts with by counting tool calls per category.
- **FR-012**: Usage data MUST persist across container restarts so tracking is not lost on redeployment.
- **FR-013**: The help response and tip selection MUST prioritize unused or underused feature categories when usage data is available.

### Key Entities

- **Help Category**: A grouping of related capabilities (e.g., "Recipes & Cooking") with a display name, icon, and list of example phrases.
- **Tip**: A short contextual suggestion linking one feature to another, with a trigger context (when to show it) and display text.
- **Tip History**: Tracks which tips a user has seen recently to enable rotation and prevent repetition.
- **Usage Counter**: Tracks how many times each user has interacted with each feature category, enabling smart suggestions for underused features.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can discover all major bot capabilities within 30 seconds of reading the help response.
- **SC-002**: 100% of example phrases in the help response are valid commands that produce correct results when sent to the bot.
- **SC-003**: At least 6 feature categories are represented in the help response, each with at least 1 working example.
- **SC-004**: "Did you know?" tips appear in at most 1 out of every 5 normal responses (non-intrusive frequency).
- **SC-005**: Tips shown are contextually relevant to the preceding interaction at least 80% of the time.
- **SC-006**: First-time users receive a welcome message exactly once — never repeated on subsequent messages.
- **SC-007**: After using 3+ feature categories, the help response highlights remaining unused categories in a dedicated section.

## Assumptions

- The bot already has access to family data (grocery history, budget categories, saved recipes, calendar events) through existing tools, so personalized examples can be generated dynamically.
- WhatsApp formatting supports bold text (*bold*), bullet points (-), and emojis for visual structure.
- "Conversation session" for tip limiting means a single WhatsApp message exchange (one user message → one bot response). A new message is a new session.
- The family has 2 primary users (Jason and Erin) who are already in the WhatsApp group. No onboarding for unknown users is needed.
- Static fallback examples are pre-written for each category using known family context (e.g., "Costco" for budget, "chicken dinner" for recipes) rather than truly generic examples.

## Out of Scope

- Interactive tutorials or step-by-step walkthroughs (too complex for WhatsApp)
- Video or image-based onboarding content
- Full usage analytics dashboards or detailed adoption metrics (simple per-category counters for smart suggestions are in scope)
- In-app onboarding flows (this is WhatsApp text only)
- Localization or multi-language support
