# Feature Specification: Holistic Family Intelligence

**Feature Branch**: `008-holistic-family-intelligence`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Smarter daily briefing that thinks holistically — connecting budget, calendar, goals, free time, meal plans, chores, and action items so the bot acts as a family strategist rather than a collection of isolated tools"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cross-Domain Questions (Priority: P1)

When Erin asks a question that spans multiple areas of family life, the bot connects the dots across calendar, budget, meal plans, chores, and action items — giving a unified answer instead of siloed responses.

**Examples**:
- "How's our week looking?" — calendar density + meal plan gaps + budget health + overdue tasks
- "Can we afford to eat out Friday?" — restaurant budget remaining + Friday schedule + whether a meal is already planned
- "I feel like we're behind" — overdue chores, stale action items, pending grocery orders, budget overruns — prioritized by urgency
- "Why are we always over on restaurants?" — check transactions for patterns, identify root causes (e.g., takeout on late meeting nights), suggest structural fixes
- "Are we making progress on our goals?" — compare current data to past weeks, track trends, celebrate wins

**Why this priority**: This is the core behavioral change. Every other story builds on the bot's ability to reason across domains. Without this, the bot remains a tool dispatcher.

**Independent Test**: Ask "how's our week looking?" and verify the response weaves together calendar, budget, meal plan, and action item data into a cohesive narrative — not separate bulleted sections per tool.

**Acceptance Scenarios**:

1. **Given** Erin has a busy week on the calendar and an overdue grocery order, **When** she asks "how's our week looking?", **Then** the bot mentions both the busy schedule AND the pending grocery order in a single coherent response, with specific recommendations (e.g., "Tuesday and Thursday are packed — I'd suggest easy meals those nights")
2. **Given** Erin asks "can we eat out this weekend?", **When** the restaurant budget is nearly spent, **Then** the bot checks remaining restaurant budget, Saturday/Sunday schedule, and existing meal plan before answering with a specific recommendation
3. **Given** Erin asks a single-domain question like "what's on the calendar today?", **When** there are no relevant cross-domain insights, **Then** the bot answers normally without forcing unnecessary connections
4. **Given** Erin asks "why are we always over on restaurants?", **When** there are patterns in the transaction data, **Then** the bot digs into the transactions, identifies the pattern (e.g., "4 DoorDash orders last week, all on days Jason had late meetings"), and suggests a structural fix (e.g., "Maybe we batch-prep easy freezer meals for his long days")
5. **Given** Erin asks "are we making progress on our goals?", **When** there's historical data to compare, **Then** the bot compares current metrics to previous periods and highlights both wins and areas that need attention

---

### User Story 2 - Smarter Daily Briefing (Priority: P2)

The automated morning briefing (sent via scheduled workflow) becomes a strategic overview of the day that connects relevant domains, rather than a flat list of calendar events and to-dos.

**Why this priority**: The daily briefing is Erin's primary touchpoint with the bot. Making it smarter means she starts every day with a strategist's perspective, not just a schedule dump.

**Independent Test**: Trigger the daily briefing and verify it includes cross-domain insights (e.g., "Tonight's a busy evening with Awana's — I planned an easy 30-minute dinner" or "Grocery budget is tight this week, the meal plan uses pantry staples").

**Acceptance Scenarios**:

1. **Given** it's a weekday morning with a packed schedule, **When** the daily briefing triggers, **Then** it highlights schedule conflicts, suggests time management strategies, and connects meal complexity to schedule density
2. **Given** the grocery budget is nearly spent mid-month, **When** the daily briefing triggers, **Then** it mentions the budget status in context of upcoming meal plans or grocery needs
3. **Given** there are overdue action items from the last family meeting, **When** the daily briefing triggers, **Then** it surfaces the 1-2 most urgent items with a suggestion for when to tackle them based on today's free time
4. **Given** Erin receives the briefing, **When** she wants to adjust something, **Then** she can reply conversationally (e.g., "move the chiro to Thursday" or "swap tonight's dinner for something easier") and the bot acts on it using conversation memory

---

### User Story 3 - Weekly Meeting Prep (Priority: P3)

When the family meeting approaches (or when Erin asks), the bot generates a holistic family meeting agenda that synthesizes the past week's data and upcoming week's outlook across all domains.

**Why this priority**: The weekly meeting is where Jason and Erin align on family strategy. A comprehensive prep document saves significant manual gathering time and ensures nothing falls through the cracks.

**Independent Test**: Ask "prep me for our family meeting" and verify the response includes budget trends, calendar review, action item status, meal plan effectiveness, and upcoming priorities — organized as a coherent meeting agenda.

**Acceptance Scenarios**:

1. **Given** Erin asks "prep me for our family meeting", **When** there's a week of data available, **Then** the bot produces a structured agenda covering: budget snapshot (what's over/under), calendar review (what happened, what's coming), action items (completed vs overdue), meal plan review (what worked, what didn't), and priorities for next week
2. **Given** the bot generates meeting prep, **When** budget spending is significantly over in a category, **Then** it flags this prominently with the specific amount and suggests a discussion point
3. **Given** the bot generates meeting prep, **When** several action items are overdue, **Then** it groups them by owner and suggests which to carry forward vs drop

---

### Edge Cases

- What happens when one data source is unavailable (e.g., budget service is down)? The bot should still provide insights from the available domains and note which source was unavailable.
- What happens when there's genuinely nothing noteworthy across domains? The bot should give a brief "all clear" response rather than forcing connections.
- What happens when the calendar is empty (e.g., weekend with no events)? The bot should frame free time as an opportunity tied to backlog items or goals.
- How does the bot handle conflicting priorities (e.g., budget says cut spending, but meal plan needs groceries)? It should present the tradeoff honestly and let Erin decide.
- What happens when cross-domain gathering takes longer than usual? The bot should respond within a reasonable time even if some data sources are slow, providing partial insights and noting pending lookups.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The bot MUST be able to gather data from multiple domains (calendar, budget, meal plans, action items, chores, grocery status) within a single response when the user's question warrants it
- **FR-002**: The bot MUST synthesize cross-domain data into coherent narrative advice, not separate bulleted sections per data source
- **FR-003**: The daily briefing MUST include cross-domain insights that connect schedule density to meal complexity, budget status to upcoming spending needs, and free time to actionable tasks
- **FR-004**: The bot MUST support a "meeting prep" interaction that generates a structured family meeting agenda from the past week's data
- **FR-005**: The meeting prep MUST include: budget snapshot, calendar review (past and upcoming), action item status, meal plan review, and suggested priorities
- **FR-006**: The bot MUST gracefully degrade when a data source is unavailable, providing insights from remaining sources and noting the gap
- **FR-007**: The bot MUST NOT force cross-domain connections when the user asks a simple single-domain question — it should add cross-domain context only when genuinely relevant
- **FR-008**: The daily briefing MUST be conversational — Erin can reply to adjust plans, and the bot acts on her requests using existing tools and conversation memory
- **FR-009**: Cross-domain responses MUST include specific, actionable recommendations rather than just reporting data (e.g., "I'd suggest easy meals Tuesday and Thursday since those evenings are packed" not just "Tuesday and Thursday are busy")
- **FR-010**: The meeting prep MUST organize information as discussion points, not raw data dumps — each section should have a headline insight and supporting details
- **FR-011**: For deeper "why" questions, the bot MUST go beyond surface-level data to identify patterns and root causes — checking transaction details, comparing time periods, and connecting causes to effects rather than just reporting current numbers
- **FR-012**: When reporting on goals or progress, the bot MUST compare current data to historical baselines (previous week, previous month) and highlight trends — celebrating improvements and flagging regressions with specific numbers

### Key Entities

- **Family Context Snapshot**: A point-in-time summary of family status across all domains — schedule density, budget health, active meal plans, pending tasks, overdue items. Used to inform cross-domain reasoning.
- **Meeting Agenda**: A structured document with sections for budget review, calendar review, action items, meal planning, and priorities. Generated on demand for weekly family meetings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When asked a cross-domain question, the bot's response references data from 2+ relevant domains at least 80% of the time
- **SC-002**: The daily briefing includes at least one cross-domain insight connecting schedule to meals, budget, or tasks
- **SC-003**: Meeting prep covers all 5 agenda sections (budget, calendar, action items, meals, priorities) in a single response
- **SC-004**: Erin can reply to the daily briefing with an adjustment request and the bot executes it within the same conversation
- **SC-005**: When a data source is unavailable, the bot still responds using available sources within the normal response time
- **SC-006**: Single-domain questions (e.g., "what's on the calendar today?") are answered without unnecessary cross-domain padding — response length stays comparable to current behavior

## Assumptions

- The existing 22 tools already provide access to all required data domains (calendar, budget, meal plans, action items, chores, grocery history)
- No new external integrations or databases are needed — this feature is about how the bot reasons, not what data it can access
- Conversation memory (feature 007) is deployed and working, enabling multi-turn briefing interactions
- The scheduled daily briefing workflow endpoint already exists and can be modified
- The bot's context window is sufficient to hold cross-domain data alongside conversation history and system instructions
- The bot should use its existing tools to gather data at query time rather than pre-caching summaries

## Out of Scope

- New data sources or external service integrations
- Dashboard or web UI for family status
- Automated decision-making (the bot advises, Erin decides)
- Changes to the messaging interface or message formatting beyond what's currently supported
- Persistent goal tracking beyond what already exists in action items and backlog
