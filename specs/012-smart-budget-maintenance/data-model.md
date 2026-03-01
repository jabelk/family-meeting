# Data Model: Smart Budget Maintenance

**Feature**: 012-smart-budget-maintenance
**Date**: 2026-02-25

## Entities

### 1. CategoryHealthProfile

Per-category analysis result computed from YNAB data. Not persisted — computed on each health check run.

| Field | Type | Description |
|-------|------|-------------|
| category_id | string (UUID) | YNAB category ID |
| category_name | string | Display name |
| group_name | string | YNAB category group name |
| goal_type | string or null | YNAB goal type: TB, TBD, MF, NEED, DEBT, null |
| goal_target | float | Goal target amount in dollars (0 if no goal) |
| budgeted_avg | float | 3-month average of budgeted amounts |
| spending_avg | float | 3-month rolling average of actual spending |
| spending_months | list[float] | Per-month spending for lookback window (newest first) |
| drift_pct | float | (spending_avg - goal_target) / goal_target * 100 |
| drift_type | enum | "underfunded", "overfunded", "missing_goal", "aligned" |
| trend | enum | "increasing", "decreasing", "stable" |
| is_sinking_fund | bool | True if goal_type in (TB, TBD) or inferred from patterns |
| is_spiky | bool | True if coefficient of variation > 1.0 |
| months_since_last_txn | int | Consecutive months with $0 activity |
| is_stale | bool | True if months_since_last_txn >= 3 and not is_sinking_fund |
| priority_tier | enum | "essential", "savings", "discretionary" (AI-inferred from group name) |

**Validation rules**:
- drift_pct is null/skipped when goal_target == 0 and drift_type == "missing_goal"
- is_spiky requires at least 3 months of data; default false with fewer months
- Trend requires at least 2 months of data; default "stable" with 1 month
- Hidden and deleted categories are excluded

---

### 2. GoalSuggestion

A single recommended change to a category's goal. Part of a BudgetHealthReport.

| Field | Type | Description |
|-------|------|-------------|
| category_id | string (UUID) | YNAB category ID |
| category_name | string | Display name |
| current_goal | float | Current goal_target in dollars (0 if missing) |
| recommended_goal | float | Suggested new goal amount |
| drift_pct | float | Current drift percentage |
| drift_type | string | "underfunded", "overfunded", "missing_goal" |
| has_existing_goal | bool | Whether category has a goal_type set in YNAB |
| status | enum | "pending", "approved", "adjusted", "skipped" |
| adjusted_value | float or null | User-provided override (if status == "adjusted") |

**State transitions**:
```
pending → approved (user says "yes to X" or "update all")
pending → adjusted (user says "set X to $Y")
pending → skipped (user says "skip X" or "leave X")
```

**Constraints**:
- recommended_goal is rounded to nearest $25 for clean numbers
- If has_existing_goal is false, bot cannot update via API — must instruct user to create goal in YNAB app first

---

### 3. BudgetHealthReport

Point-in-time snapshot of overall budget health. Not persisted — generated on each run.

| Field | Type | Description |
|-------|------|-------------|
| generated_at | datetime | When the report was generated |
| lookback_months | int | Number of months analyzed (default 3) |
| health_score | float | Dollar-weighted alignment percentage (0-100) |
| total_categories | int | Number of active categories analyzed |
| drifted_count | int | Categories with >30% drift |
| missing_goal_count | int | Categories with spending but no goal |
| stale_count | int | Categories with 3+ months of $0 spending |
| profiles | list[CategoryHealthProfile] | All category profiles |
| suggestions | list[GoalSuggestion] | Recommended goal changes (only drifted + missing) |
| merge_candidates | list[MergeCandidate] | Suggested category merges |

---

### 4. AllocationPlan

A prioritized plan for distributing a bonus or large deposit.

| Field | Type | Description |
|-------|------|-------------|
| total_amount | float | Total dollars to allocate |
| source_description | string | e.g., "Jason's bonus" or "$5,000 deposit on Feb 25" |
| allocations | list[Allocation] | Ordered list of category allocations |
| status | enum | "draft", "approved", "adjusted", "executed" |

**State transitions**:
```
draft → approved (user says "yes" or "approve")
draft → adjusted (user modifies allocations)
approved → executed (bot moves money in YNAB)
draft → adjusted → approved → executed
```

---

### 5. Allocation (sub-entity of AllocationPlan)

| Field | Type | Description |
|-------|------|-------------|
| category_id | string (UUID) | YNAB category ID |
| category_name | string | Display name |
| priority_tier | string | "essential", "savings", "discretionary" |
| current_shortfall | float | How much the category is underfunded |
| allocated_amount | float | Dollars assigned from the bonus |
| rationale | string | Brief explanation (e.g., "Groceries is $754 underfunded this month") |

**Constraints**:
- sum(allocated_amount) == AllocationPlan.total_amount
- Allocations ordered by priority_tier (essential first), then by shortfall size within tier

---

### 6. MergeCandidate

A suggested category consolidation.

| Field | Type | Description |
|-------|------|-------------|
| categories | list[str] | Category names to merge (2+) |
| combined_avg_spending | float | Sum of all categories' average spending |
| rationale | string | Why these should be merged (similar names, small amounts, etc.) |
| suggested_name | string | Recommended merged category name |

**Constraints**:
- Only categories with avg spending < $200/month each are merge candidates
- At least one similarity signal required: name overlap, same group, or correlated transactions

---

## Relationships

```
BudgetHealthReport
  ├── 1:N → CategoryHealthProfile (one per active YNAB category)
  ├── 1:N → GoalSuggestion (subset of profiles with drift)
  └── 1:N → MergeCandidate (detected overlaps)

AllocationPlan
  └── 1:N → Allocation (one per underfunded category)
```

## Storage

No persistent storage required. All entities are computed on-demand from YNAB API data and held in memory for the duration of the WhatsApp conversation. Pending suggestions and allocation plans are tracked via the existing conversation memory (Feature 007 — 24-hour window) and the existing pending suggestions pattern (`data/budget_pending_suggestions.json`) used by Amazon/email sync.
