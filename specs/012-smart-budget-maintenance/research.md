# Research: Smart Budget Maintenance

**Feature**: 012-smart-budget-maintenance
**Date**: 2026-02-25

## R1: YNAB API Goal Capabilities

**Decision**: Use existing YNAB API for goal reads + partial writes; accept API limitation that new goals cannot be created programmatically.

**Rationale**: The YNAB API v1 provides full read access to goal metadata (`goal_type`, `goal_target`, `goal_percentage_complete`, `goal_under_funded`, `goal_overall_funded`, `goal_overall_left`) and allows updating `goal_target` on categories that already have a goal. However, `goal_type` is read-only — you cannot create a new goal or change a goal's type via the API. For "missing goal" categories, the bot must instruct the user to set the goal type in the YNAB app, after which the bot can manage the target amount.

**Alternatives considered**:
- Unofficial YNAB web scraping — rejected (fragile, against ToS)
- Only updating budgeted amounts instead of goals — rejected (doesn't solve the goal drift problem, just moves money)
- Creating new categories with goals via POST — rejected (creates duplicates instead of fixing existing categories)

**Key API details**:
- `PATCH /budgets/{id}/categories/{cat_id}` — writable: `goal_target`, `name`, `note`, `category_group_id`
- `goal_type` values: `TB` (Target Balance), `TBD` (Target Balance by Date), `MF` (Monthly Funding), `NEED` (Plan Your Spending), `DEBT` (Debt Payoff), `null` (no goal)
- Rate limit: 200 requests/hour (rolling)

---

## R2: Sinking Fund Detection via Goal Types

**Decision**: Use YNAB `goal_type` as primary sinking fund signal, with spending pattern inference as fallback.

**Rationale**: YNAB's goal type taxonomy cleanly separates savings-oriented goals from spending goals:
- **Sinking funds** (should NOT be flagged as stale): `TB` (Target Balance), `TBD` (Target Balance by Date)
- **Spending goals** (can be flagged as stale): `MF` (Monthly Funding), `NEED` (Plan Your Spending)
- **No goal**: Fall back to spending pattern analysis (large infrequent payments = likely periodic expense)

The `goal_cadence` and `goal_cadence_frequency` fields provide additional signal for recurring expenses (quarterly, annual) but are not writable via API.

**Alternatives considered**:
- Only pattern-based detection — rejected (less accurate, TB/TBD is a definitive signal)
- Hardcoded category list — rejected (brittle, doesn't adapt to user changes)

---

## R3: Multi-Month Data Retrieval Strategy

**Decision**: Use `GET /budgets/{id}/months/{month}` endpoint to fetch per-month category summaries for the lookback window.

**Rationale**: This endpoint returns all categories with their budgeted, activity, balance, and goal fields for a specific month. Fetching 3-6 months of data requires only 3-6 API calls (well within the 200/hour rate limit). This is the same pattern used by `check_spending_anomalies()` in the existing codebase.

**Alternatives considered**:
- Transaction-level queries per category — rejected (much higher API call count, client-side aggregation needed)
- Single-month + delta sync — rejected (need historical comparison, not just current state)

---

## R4: Health Score Formula

**Decision**: Dollar-weighted alignment percentage = 1 - (total absolute drift / total spending) * 100.

**Rationale**: A dollar-weighted score prevents many small categories with minor drift from overshadowing a few large categories with significant drift. Categories with no goal are excluded from the score (reported separately as "missing goal"). A 100% score means every category's actual spending equals its goal; lower scores indicate greater misalignment.

**Formula**:
```
For each category with a goal:
  drift = |actual_3mo_avg - goal_amount|
  weight = max(actual_3mo_avg, goal_amount)

health_score = max(0, (1 - sum(drift) / sum(weight)) * 100)
```

**Alternatives considered**:
- Count-based (% of categories within target) — rejected (treats $10 category same as $2,000 category)
- Letter grades — rejected (loses precision, harder to trend over time)
- Traffic light — rejected (too coarse for a comprehensive report)

---

## R5: Priority Tier Classification for Allocation

**Decision**: AI-inferred tiers from YNAB category group names using Claude classification.

**Rationale**: YNAB category groups already organize categories by purpose (e.g., "Fixed Bills", "Savings", "Fun Money"). Claude can classify these into tiers (essential/savings/discretionary) using natural language understanding of group names, avoiding manual configuration or hardcoded mappings. The classification happens at allocation time, not as a stored attribute, so it adapts to group name changes.

**Tier definitions**:
- **Essential**: Bills, housing, healthcare, food, transportation, childcare — must be funded first
- **Savings**: Emergency fund, sinking funds, debt payoff — funded second
- **Discretionary**: Fun money, dining out, entertainment, shopping — funded last

**Alternatives considered**:
- Manual family tagging — rejected (friction, maintenance burden)
- Hardcoded mapping — rejected (breaks when categories change)
- YNAB UI order — rejected (no semantic meaning)

---

## R6: Existing Reusable Infrastructure

**Decision**: Build on existing ynab.py functions rather than creating a new module.

**Rationale**: The existing YNAB module already provides:
- `get_budget_summary(month)` — fetches all categories for a month with goal fields
- `update_category_budget(category, amount)` — changes budgeted amount
- `move_money(from, to, amount)` — rebalances between categories
- `check_spending_anomalies()` — 3-month rolling average comparison (50% threshold)
- `check_savings_goals()` — goal progress vs expected pace
- `check_overspend_warnings()` — categories >80% spent
- `_get_categories()` — cached category list with group, goal_type, etc.
- `_fuzzy_match_category()` — name matching for user input

New functions should extend ynab.py rather than creating a separate module. The budget maintenance logic (drift detection, health reports, allocation plans) builds directly on these primitives.

**Key gap**: No function to update `goal_target` (only `budgeted` amount). Need to add `PATCH /categories/{id}` support.

**Alternatives considered**:
- New `budget_maintenance.py` module — rejected (would duplicate YNAB API setup, caching, and helper functions)
