# Feature Specification: Smart Budget Maintenance

**Feature Branch**: `012-smart-budget-maintenance`
**Created**: 2026-02-25
**Status**: Draft
**Input**: User description: "Smart budget maintenance — bot proactively detects when YNAB budget goals have drifted from actual spending patterns, suggests reality-based goal updates, helps allocate bonus/stock income to underfunded priorities, runs monthly budget health checks, and flags stale/mergeable categories."

## Context

The family budget was set up in January 2025 during a Mint migration and hasn't been tuned since. A budget analysis (spec 009) found that goals are wildly disconnected from reality — Restaurants budgeted at $400/month but averaging $1,200, Groceries at $1,600 vs $2,354 actual, 9 categories with no goals at all, and several categories that should be merged or deleted. The bot already has full YNAB read/write access (Feature 004) and produces weekly meeting agendas and daily briefings (Feature 001). This feature adds ongoing budget intelligence so goals never go stale again.

## Clarifications

### Session 2026-02-25

- Q: How should categories be classified into priority tiers for bonus allocation? → A: Bot infers tier from YNAB category group names using AI classification (e.g., "Fixed Bills" = essential, "Fun Money" = discretionary)
- Q: How should the bot identify sinking fund categories to avoid false stale alerts? → A: Use YNAB goal type metadata as primary signal (savings-oriented goal types = sinking fund), with spending pattern inference as fallback for categories without goals
- Q: What format should the budget health score use? → A: Percentage score (e.g., "73% aligned") measuring dollar-weighted goal alignment across all categories

## Assumptions

- The existing YNAB integration (Feature 004) provides budget summaries, transaction search, category updates, and money moves — all reusable here
- "Large deposit" means an income transaction significantly above the regular paycheck pattern (bonuses, stock vesting, tax refunds)
- Goal drift analysis uses 3-month rolling averages to smooth out spiky categories (e.g., home maintenance)
- The bot already has access to all YNAB category groups, goals, and transaction history via the existing API integration
- Stale means no transactions in a category for 3+ consecutive months
- Merge suggestions are advisory only — the bot does not rename or delete YNAB categories (YNAB API doesn't support category deletion)
- The monthly health check runs via the existing n8n scheduling infrastructure
- All interactions happen through the existing WhatsApp interface

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Goal Drift Detection & Suggestions (Priority: P1)

Erin or Jason asks "how are my budget goals?" or the bot includes goal health in weekly meeting prep. The bot compares each category's monthly goal to the 3-month actual spending average, identifies categories where the goal is significantly off (over 30% drift in either direction), and presents a ranked list of suggested goal updates with the current goal, actual average, and recommended new goal. The user can approve individual suggestions ("yes to restaurants"), approve all ("update all"), or skip ("leave groceries as-is").

**Why this priority**: This is the core problem from the budget analysis — aspirational goals that don't match reality cause the family to ignore the budget entirely. Fixing goal drift is the single highest-value action.

**Independent Test**: Ask "how are my budget goals?" in WhatsApp. The bot analyzes all categories, identifies drifted goals, and presents actionable suggestions. Approving a suggestion updates the YNAB goal.

**Acceptance Scenarios**:

1. **Given** a category where the goal is $400 but the 3-month average spend is $1,200, **When** the user triggers a goal health check, **Then** the bot flags this category as "significantly underfunded" and suggests updating the goal to approximately $1,200
2. **Given** a category where the goal is $2,520 but the 3-month average spend is $289, **When** the goal health check runs, **Then** the bot flags this category as "significantly overfunded" and suggests lowering the goal
3. **Given** a category with no goal set but consistent spending (e.g., $500/month average), **When** the goal health check runs, **Then** the bot identifies it as "missing goal" and suggests setting one based on the spending pattern
4. **Given** the user responds "yes to restaurants" after seeing a suggestion, **When** the bot processes the approval, **Then** the YNAB category goal is updated and the bot confirms the change
5. **Given** the user responds "skip groceries", **When** the bot processes the response, **Then** that category is left unchanged and the bot moves to the next suggestion or finishes
6. **Given** it's weekly meeting prep time, **When** the bot generates the meeting agenda, **Then** a "Budget Goal Health" section is included if any categories have drifted more than 30%

---

### User Story 2 - Bonus & Large Deposit Allocation (Priority: P2)

When Erin asks "where should this bonus go?" or "we got Jason's stock vesting, where should it go?", the bot checks which categories are currently underfunded relative to their goals, ranks them by priority (essential categories first, then savings gaps, then discretionary), and suggests a concrete dollar-by-dollar allocation plan. The user can approve the plan, adjust individual allocations, or ask the bot to re-prioritize.

**Why this priority**: Variable income (bonuses, stock vesting) is a recurring event for this family. Without guidance, bonus money sits unallocated or gets spent without intention. This directly addresses the "bonus allocation strategy" recommendation from the budget analysis.

**Independent Test**: Send "where should this $5,000 bonus go?" in WhatsApp. The bot analyzes underfunded categories and presents a prioritized allocation plan. Approving the plan moves money in YNAB.

**Acceptance Scenarios**:

1. **Given** several categories are underfunded for the current month and the user mentions a bonus amount, **When** the user asks where to allocate it, **Then** the bot presents a prioritized allocation plan showing dollar amounts per category, ordered by priority (essentials first, then savings, then discretionary)
2. **Given** the user approves the allocation plan, **When** the bot processes the approval, **Then** money is moved to each suggested category in YNAB and the bot confirms with a summary
3. **Given** the user says "put more toward emergency fund and less toward fun money", **When** the bot processes the adjustment, **Then** it re-generates the allocation plan with the requested changes
4. **Given** all categories are fully funded for the month, **When** the user asks where to put a bonus, **Then** the bot suggests funding future months, savings goals, or a holding category for next month's budget
5. **Given** the user doesn't specify a dollar amount, **When** they say "where should this bonus go?", **Then** the bot checks for recent large deposits in YNAB to infer the amount, or asks the user to confirm the amount

---

### User Story 3 - Monthly Budget Health Check (Priority: P3)

On the 1st of each month (or on-demand), the bot runs a comprehensive budget review comparing all categories' goals to their actual spending over the past 1-3 months. It produces a health report with: an overall budget health score, categories with the largest goal-vs-actual gaps, spending trend direction (increasing/decreasing/stable) for key categories, and any categories that have been consistently over or under budget. The report is sent via WhatsApp and can also be included in the next weekly meeting prep.

**Why this priority**: While US1 handles on-demand and meeting-integrated checks, a scheduled monthly review ensures the budget stays healthy even if the family forgets to ask. This is the "ongoing maintenance" that prevents the budget from going stale again.

**Independent Test**: Trigger the monthly health check endpoint (or wait for the 1st of the month). The bot sends a comprehensive WhatsApp report covering all categories with a health score and trend analysis.

**Acceptance Scenarios**:

1. **Given** it's the 1st of the month, **When** the scheduled health check runs, **Then** a comprehensive budget report is sent via WhatsApp covering all categories
2. **Given** a category has been overspent for 3 consecutive months, **When** the monthly report runs, **Then** it's highlighted with a "persistent overspend" flag and a stronger recommendation to update the goal
3. **Given** all categories are within 20% of their goals, **When** the monthly report runs, **Then** the bot sends a brief "budget is healthy" message rather than a full detailed report
4. **Given** the user says "run a budget health check", **When** the bot processes the request on-demand, **Then** the same comprehensive report is generated as the scheduled version

---

### User Story 4 - Stale Category & Merge Detection (Priority: P4)

The bot identifies categories with no spending in 3+ consecutive months (stale) and categories that appear to overlap or could be consolidated (merge candidates). Stale categories are flagged during the monthly health check or on-demand. Merge suggestions are based on spending patterns — e.g., two categories that always have small amounts and serve similar purposes. The bot presents findings as suggestions; it does not automatically modify categories.

**Why this priority**: The budget analysis found several stale categories (Buenos at $980 goal with $0 spent) and merge candidates (Dog food + Dog services, CVS into Healthcare). Cleaning these up reduces decision fatigue. Lower priority because it's a one-time cleanup benefit rather than ongoing value.

**Independent Test**: Ask "are there any budget categories I should clean up?" in WhatsApp. The bot identifies stale and mergeable categories and presents recommendations.

**Acceptance Scenarios**:

1. **Given** a category has had $0 in transactions for the past 3 months and has a non-zero goal, **When** the stale check runs, **Then** the bot flags it as stale and suggests deleting or pausing the goal
2. **Given** two categories have small average spending and similar names or transaction patterns, **When** the merge check runs, **Then** the bot suggests combining them and explains the rationale
3. **Given** a category has $0 spending but is a known annual/quarterly expense (e.g., home insurance), **When** the stale check runs, **Then** the bot recognizes the saving/sinking fund pattern and does NOT flag it as stale
4. **Given** the user acknowledges a stale category suggestion, **When** they confirm ("yes, remove Buenos"), **Then** the bot zeroes out the goal in YNAB and confirms (actual category deletion must be done manually in YNAB)

---

### Edge Cases

- What happens when a category has highly variable spending (e.g., maintenance: $186 one month, $11,068 the next)? The bot should use a longer lookback window (6+ months) or flag it as "spiky" rather than suggesting a goal based on a misleading average.
- What happens when YNAB has annual or quarterly sinking fund goals? The bot must distinguish between "monthly spending goal" and "savings target for periodic expense" to avoid false stale/drift alerts.
- What happens when the user gets multiple bonuses in quick succession? Allocation suggestions should account for money already allocated from previous bonuses (not double-count underfunded categories).
- What happens when YNAB categories have been recently reorganized or renamed? The bot should use current category names and not compare against historical data from deleted/renamed categories.
- What happens when spending data is insufficient (e.g., new category with only 1 month of data)? The bot should note "insufficient data" and skip drift analysis for that category rather than suggesting a goal from a single month.
- What happens when a goal drift suggestion is approved but YNAB rate limits the API? The bot should queue the update and retry, informing the user of the delay.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compare each YNAB category's monthly goal to the 3-month rolling average of actual spending and calculate the drift percentage
- **FR-002**: System MUST flag categories as "drifted" when actual spending deviates from the goal by more than 30% (configurable threshold)
- **FR-003**: System MUST categorize drift findings into: underfunded (spending exceeds goal), overfunded (goal exceeds spending), missing goal (has spending but no goal set)
- **FR-004**: System MUST present goal update suggestions with current goal, actual average, recommended new goal, and drift percentage
- **FR-005**: Users MUST be able to approve, adjust, or skip individual goal suggestions via WhatsApp replies
- **FR-006**: System MUST update YNAB category goals when the user approves a suggestion
- **FR-007**: System MUST identify underfunded categories when the user asks about bonus/income allocation, ranked by priority tier (essential > savings > discretionary), where tiers are inferred from YNAB category group names using AI classification (e.g., "Fixed Bills" group = essential, "Savings" group = savings, "Fun Money" group = discretionary)
- **FR-008**: System MUST generate a concrete allocation plan showing dollar amounts per category that sums to the specified bonus amount
- **FR-009**: Users MUST be able to approve, adjust priorities, or modify the allocation plan before it's executed
- **FR-010**: System MUST move money to the suggested categories in YNAB when an allocation plan is approved
- **FR-011**: System MUST run a comprehensive monthly budget health check comparing all category goals to actual spending
- **FR-012**: System MUST calculate a budget health score as a dollar-weighted percentage (e.g., "73% aligned") measuring how closely actual spending across all categories matches their goals, where 100% means every category's spending equals its goal
- **FR-013**: System MUST identify spending trends (increasing, decreasing, stable) for each category based on the past 3 months
- **FR-014**: System MUST send the monthly health report via WhatsApp, with a brief summary when the budget is healthy and a detailed report when issues are found
- **FR-015**: System MUST detect stale categories (no transactions for 3+ consecutive months with a non-zero goal)
- **FR-016**: System MUST distinguish sinking fund categories from stale categories by using YNAB goal type metadata as the primary signal (savings-oriented goal types such as "Target Savings Balance" and "Needed for Spending by Date" indicate sinking funds), with spending pattern inference as fallback for categories without explicit goal types (e.g., large infrequent payments suggest periodic expenses)
- **FR-017**: System MUST identify potential merge candidates based on similar names, small spending amounts, or overlapping transaction patterns
- **FR-018**: System MUST integrate goal drift findings into the existing weekly meeting prep output when budget issues are detected
- **FR-019**: System MUST handle spiky categories (high variance in spending) by using longer lookback windows or flagging them separately rather than suggesting misleading averages
- **FR-020**: System MUST infer the bonus amount from recent YNAB deposits when the user doesn't specify one, or ask for confirmation if ambiguous

### Key Entities

- **Budget Health Report**: A point-in-time snapshot of all categories' goal-vs-actual alignment, including drift percentages, trend directions, stale flags, and an overall health score. Generated monthly or on-demand.
- **Goal Suggestion**: A recommended change to a single category's goal, including current goal, actual average, recommended goal, drift percentage, and user response (approved/adjusted/skipped).
- **Allocation Plan**: A prioritized list of categories and dollar amounts for distributing a bonus or large deposit, totaling to the specified amount, with priority tiers (essential, savings, discretionary).
- **Category Health Profile**: Per-category metadata including spending trend, variance level, sinking fund flag, last transaction date, and consecutive months of zero spending.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users receive actionable goal update suggestions within 30 seconds of requesting a budget health check
- **SC-002**: At least 80% of goal suggestions are within 15% of what the user would set manually (measured by acceptance rate without adjustment)
- **SC-003**: Bonus allocation plans are generated within 30 seconds and cover all underfunded categories in priority order
- **SC-004**: Monthly health check correctly identifies all categories with >30% goal drift (zero false negatives for significant drift)
- **SC-005**: Sinking fund categories are correctly excluded from stale category alerts at least 95% of the time
- **SC-006**: After 3 months of use, no YNAB category goal drifts more than 50% from actual spending without the family being notified
- **SC-007**: Users can complete a full goal update cycle (review suggestions, approve/skip all) in under 5 minutes via WhatsApp
- **SC-008**: The monthly health report fits within 2 WhatsApp messages when the budget is generally healthy, expanding to at most 4 messages for a detailed report
