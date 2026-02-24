# Feature Specification: YNAB Smart Budget Management

**Feature Branch**: `004-ynab-smart-budget`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "YNAB smart budget management — write operations (recategorize transactions, adjust budgets, create manual transactions), spending insights and suggestions based on transaction data, budget grouping help, and model upgrade to Opus for deeper financial reasoning."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Transaction Management (Priority: P1)

Erin or Jason texts the bot to recategorize a transaction, log a cash purchase, or ask "what did we spend at Costco this month?" The bot reads their transaction history, makes the requested change, and confirms. This is the foundation — write access to YNAB unlocks everything else.

**Why this priority**: Without write access, the bot is read-only and users must open the YNAB app to make changes. Write access is the prerequisite for all other stories.

**Independent Test**: Send "Recategorize the last Costco charge to Groceries" via WhatsApp and verify the transaction is updated in YNAB within 10 seconds.

**Acceptance Scenarios**:

1. **Given** a recent uncategorized transaction exists, **When** the user says "categorize the $47 Target charge as Home Supplies", **Then** the bot finds the matching transaction, recategorizes it, and confirms with the transaction details.
2. **Given** the user paid cash at a farmers market, **When** they say "add $35 cash transaction for farmers market under Groceries", **Then** a new manual transaction is created in the correct account and category with today's date.
3. **Given** the user asks "what did we spend at Whole Foods this month?", **When** the bot searches transactions, **Then** it returns a list of matching transactions with dates, amounts, and categories.
4. **Given** the user requests a recategorization but multiple transactions match, **When** the bot finds ambiguity, **Then** it presents the top matches and asks the user to confirm which one.

---

### User Story 2 — Smart Spending Insights (Priority: P2)

The bot proactively analyzes spending patterns and alerts the family when something looks off — like unusually high grocery spending, a category going over budget mid-month, or uncategorized transactions piling up. Jason asked "how did we spend 3K on groceries?" — the bot should catch this pattern before Jason has to ask.

**Why this priority**: The highest-value use of budget data is surfacing insights the family wouldn't notice on their own. This turns the bot from a data-entry tool into a financial advisor.

**Independent Test**: After a month with above-average grocery spending, the bot proactively sends a WhatsApp message like "Heads up — Groceries is at $2,800 this month (budget: $1,500). That's 87% higher than last month."

**Acceptance Scenarios**:

1. **Given** a budget category exceeds 80% of its monthly allocation before the 20th of the month, **When** the daily scan runs, **Then** the bot sends a warning like "Dining Out is at $380/$450 with 10 days left — you might want to slow down."
2. **Given** there are 3 or more uncategorized transactions older than 48 hours, **When** the daily scan runs, **Then** the bot sends a nudge like "You have 5 uncategorized transactions totaling $234. Want me to help sort them?"
3. **Given** spending in a category is 50% higher than the 3-month rolling average, **When** the weekly scan runs, **Then** the bot flags the anomaly with the comparison.
4. **Given** a savings goal is falling behind pace (funded percentage below expected for this point in the month), **When** the weekly scan runs, **Then** the bot mentions the gap and how much extra is needed to get back on track.

---

### User Story 3 — Budget Rebalancing (Priority: P3)

The user asks to move money between budget categories — "move $100 from Dining Out to Groceries" or "we need more in the vacation fund this month." The bot adjusts the budgeted amounts and confirms the change. This is the conversational equivalent of dragging money around in the YNAB app.

**Why this priority**: Budget adjustments are a common YNAB action but less frequent than transaction management. Still important for month-end rebalancing and reacting to overspending.

**Independent Test**: Send "move $200 from Clothing to Groceries" and verify both category budgets are updated in YNAB.

**Acceptance Scenarios**:

1. **Given** the user says "budget $200 more for Groceries this month", **When** the bot processes the request, **Then** the Groceries budgeted amount increases by $200 and the bot confirms the new total.
2. **Given** the user says "move $100 from Jason Fun to Erin Shopping", **When** the bot processes the request, **Then** Jason Fun decreases by $100, Erin Shopping increases by $100, and the bot confirms both changes.
3. **Given** the user requests a move that would make the source category negative, **When** the bot checks the balance, **Then** it warns the user before proceeding ("Jason Fun only has $45 left — move $45 instead?").

---

### User Story 4 — Model Upgrade (Priority: P1)

Upgrade the assistant's language model from Sonnet to Opus for better reasoning about financial data, nuanced conversation, and more helpful budget advice. The family doesn't send many messages per day, so the higher per-message cost of Opus is acceptable.

**Why this priority**: Opus provides significantly better analytical reasoning for financial questions, multi-step budget analysis, and natural conversation. Low message volume makes the cost increase negligible.

**Independent Test**: Ask a complex financial question like "Based on our spending this month, are we on track for our savings goals? What would you change?" and verify the response demonstrates deeper analysis than current behavior.

**Acceptance Scenarios**:

1. **Given** the bot is running the upgraded model, **When** a user asks a nuanced budget question, **Then** the response shows multi-step reasoning (e.g., comparing categories, identifying trends, suggesting trade-offs).
2. **Given** the monthly message volume is under 500 messages, **When** the model is upgraded, **Then** the incremental cost increase stays under $50/month.

---

### Edge Cases

- What happens when the YNAB service is temporarily unavailable? The bot should gracefully report the issue and suggest trying again later.
- What happens when a transaction search matches zero results? The bot should suggest alternative search terms or date ranges.
- What happens when the user tries to recategorize a transaction that was already categorized? The bot should show the current category and confirm the user wants to change it.
- What happens when the user references a category name that doesn't exist in YNAB? The bot should suggest the closest matching category names.
- What happens when multiple budget accounts exist? The bot should use the configured default budget and not require the user to specify.
- What happens when proactive insights fire but it's a quiet day? Insights should respect the existing quiet day, quiet hours, and daily cap system from Feature 003.
- What happens when the user tries to move more money than a category has budgeted? The bot should warn and offer to move the available amount instead.
- What happens when the YNAB API rate limit (200 requests/hour) is approached? The bot should throttle proactive scans and prioritize user-initiated requests.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to recategorize existing transactions by payee name, amount, or date via natural language.
- **FR-002**: System MUST allow users to create manual transactions with payee, amount, category, and optional date.
- **FR-003**: System MUST allow users to search transactions by payee name, category, amount range, or date range.
- **FR-004**: System MUST allow users to adjust budgeted amounts for any category (increase, decrease, or move between categories).
- **FR-005**: System MUST proactively alert when a category exceeds 80% of its budget before the 20th of the month.
- **FR-006**: System MUST proactively nudge when 3 or more uncategorized transactions are older than 48 hours.
- **FR-007**: System MUST flag spending anomalies when a category is 50% or more above its 3-month rolling average.
- **FR-008**: System MUST report savings goal progress and gaps during weekly scans.
- **FR-009**: System MUST confirm all write operations before executing when the request is ambiguous (multiple transaction matches) and proceed directly when the request is unambiguous.
- **FR-010**: System MUST use a more capable language model for improved financial reasoning and conversational quality.
- **FR-011**: Proactive budget insights MUST respect quiet day, quiet hours, and daily message cap from Feature 003.
- **FR-012**: System MUST fuzzy-match category names so users don't need to remember exact YNAB category names.

### Non-Functional Requirements

- **NFR-001**: Transaction search and recategorization responses MUST complete within 15 seconds.
- **NFR-002**: Proactive budget insights MUST NOT exceed 2 budget-related messages per day (within the existing daily cap of 8).
- **NFR-003**: The model upgrade MUST NOT increase monthly costs by more than $50 at current usage levels (under 500 messages/month).

### Key Entities

- **Transaction**: A YNAB transaction with payee, amount, date, category, account, cleared status, and memo. Users interact with transactions by searching, recategorizing, and creating new ones.
- **Budget Category**: A YNAB budget category with name, budgeted amount, activity (spent), balance (remaining), and optional savings goal. Users adjust budgeted amounts and monitor spending.
- **Budget Insight**: A proactive observation about spending patterns — overspend warnings, anomaly flags, uncategorized transaction reminders, or savings goal gaps. Generated by periodic scans and delivered as WhatsApp nudges.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can recategorize a transaction via WhatsApp in under 30 seconds (one message plus one confirmation).
- **SC-002**: Users can create a manual transaction via WhatsApp in a single message.
- **SC-003**: Proactive budget alerts catch overspending categories at least 5 days before month-end.
- **SC-004**: 90% of uncategorized transactions are flagged within 48 hours of appearing.
- **SC-005**: Users report the bot feels noticeably smarter and more helpful after the model upgrade.
- **SC-006**: Monthly assistant costs stay under $75 total (model upgrade plus existing usage).

## Assumptions

- The family uses a single YNAB budget (configured via the existing budget ID setting).
- The default account for manual transactions will be inferred from the most recently used account, or the user can specify.
- The budget service rate limits (200 requests/hour) are sufficient for the expected usage pattern.
- Transaction search will cover the current month by default; users can specify other date ranges.
- Category fuzzy matching uses case-insensitive substring matching, consistent with the chore matching pattern from Feature 003.
- Proactive insights will run on the existing scheduled scan infrastructure or a dedicated daily/weekly schedule.
- The 3-month rolling average for anomaly detection uses the current month plus the previous 2 full months.

## Out of Scope

- Budget account creation, deletion, or management (only budget categories and transactions).
- Multi-budget support (the family uses one budget).
- Recurring transaction management (scheduled transactions are handled by the budget service itself).
- Savings goal creation or modification (only monitoring existing goals).
- Bank connection or import management.
