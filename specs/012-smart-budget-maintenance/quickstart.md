# Quickstart: Smart Budget Maintenance

**Feature**: 012-smart-budget-maintenance
**Date**: 2026-02-25

## Integration Scenarios

### Scenario 1: On-Demand Goal Health Check (US1 — MVP)

**Trigger**: User sends "how are my budget goals?" in WhatsApp

**Expected flow**:
1. Claude calls `budget_health_check` tool (default 3-month lookback, 30% threshold)
2. Tool fetches YNAB data for current month + 2 prior months (3 API calls)
3. Tool computes drift for each category, health score, stale detection, merge candidates
4. Returns formatted report to Claude
5. Claude sends report to WhatsApp with actionable suggestions

**Expected WhatsApp output**:
```
📊 Budget Health Check — 73% Aligned

⚠️ Underfunded (spending exceeds goal):
1. Restaurants: $400 goal → $1,200 avg (+200%) — suggest $1,200
2. Groceries: $1,600 goal → $2,354 avg (+47%) — suggest $2,400
3. Healthcare: $400 goal → $1,878 avg (+370%) — suggest $1,900
4. Kids Activities: $348 goal → $736 avg (+112%) — suggest $750

📉 Overfunded (goal exceeds spending):
5. Haircuts: $2,520 goal → $289 avg (-89%) — suggest $300
6. Buenos: $980 goal → $0 avg — suggest removing

🔍 Missing goals:
7. Amazon: $524/mo avg — suggest $525 goal
8. Erin Shopping: $1,076/mo avg — suggest $1,075 goal

Reply "update all", "yes to 1", "skip 3", or "set 2 to $2000"
```

**Verification**:
- Health score reflects dollar-weighted alignment
- Sinking funds (Home Insurance, HOA) are NOT flagged as stale
- Categories with <2 months of data show "insufficient data" note
- Spiky categories (Maintenance) noted separately

---

### Scenario 2: Approving Goal Suggestions (US1)

**Trigger**: User replies "yes to restaurants" after receiving health check

**Expected flow**:
1. Claude calls `apply_goal_suggestion` with category="restaurants"
2. Tool fuzzy-matches "restaurants" to YNAB category
3. Tool checks if category has existing goal (goal_type != null)
4. If yes: PATCH `/categories/{id}` with new `goal_target`
5. Returns confirmation

**Expected WhatsApp output**:
```
✅ Updated Restaurants goal: $400 → $1,200
7 suggestions remaining. Reply "update all" or continue individually.
```

**Error case — missing goal**:
```
⚠️ Amazon doesn't have a goal set in YNAB yet. Please open YNAB and add a "Monthly Savings Builder" or "Plan Your Spending" goal to the Amazon category, then I can set the target to $525.
```

---

### Scenario 3: Bonus Allocation (US2)

**Trigger**: User sends "where should this $5,000 bonus go?"

**Expected flow**:
1. Claude calls `allocate_bonus` with amount=5000
2. Tool fetches current month's budget data
3. Tool classifies categories into tiers using AI (group names → essential/savings/discretionary)
4. Tool calculates shortfalls per category
5. Tool generates allocation plan: essentials first, then savings, then discretionary
6. Returns formatted plan

**Expected WhatsApp output**:
```
💰 Bonus Allocation Plan — $5,000

Essential (funded first):
  • Groceries: +$754 (was $754 short)
  • Healthcare: +$1,478 (was $1,478 short)

Savings:
  • Emergency Fund: +$2,000 ($48k left to $200k target)

Discretionary:
  • Kids Activities: +$388 (was $388 short)
  • Remaining: +$380 → Restaurants

Total: $5,000 | Reply "approve" to move money, or "put $3000 to emergency fund"
```

---

### Scenario 4: Executing Allocation (US2)

**Trigger**: User replies "approve" after seeing allocation plan

**Expected flow**:
1. Claude calls `approve_allocation` (no adjustments)
2. Tool moves money to each category via `update_category_budget()` (existing function)
3. Returns confirmation

**Expected WhatsApp output**:
```
✅ Bonus allocated!
  • Groceries: +$754 (now fully funded)
  • Healthcare: +$1,478 (now fully funded)
  • Emergency Fund: +$2,000 (now $152,000 of $200,000)
  • Kids Activities: +$388 (now fully funded)
  • Restaurants: +$380

All money assigned. Your budget is now 89% aligned!
```

---

### Scenario 5: Monthly Scheduled Health Check (US3)

**Trigger**: n8n fires `POST /api/v1/budget/health-check` on the 1st at 9am

**Expected flow**:
1. Endpoint calls `run_budget_health_check()` as background task
2. Function computes full health report
3. If health_score >= 90 and no critical issues: sends brief message
4. Otherwise: sends detailed report (same format as Scenario 1)
5. Includes stale category and merge candidate sections

**Healthy budget message**:
```
📊 Monthly Budget Check — 92% Aligned ✅

All categories within target. Keep it up!
Tip: Your Restaurants spending dropped 15% this month — the meal-prep strategy is working.
```

**Unhealthy budget message**: Same as Scenario 1 format, plus:
```
🗂️ Stale categories (no spend in 3+ months):
  • Buenos ($980 goal) — consider removing

🔀 Merge candidates:
  • Dog food Chewy + Dog services → "Pet" ($158/mo combined)
  • CVS → merge into Healthcare/Pharmacy
```

---

### Scenario 6: Stale Category Cleanup (US4)

**Trigger**: User asks "are there any budget categories I should clean up?"

**Expected flow**:
1. Claude calls `budget_health_check` (focuses on stale + merge sections)
2. Tool identifies stale categories (3+ months, $0 spend, not sinking fund)
3. Tool identifies merge candidates (small amounts, similar names)
4. Returns focused cleanup report

**Expected WhatsApp output**:
```
🧹 Budget Cleanup Suggestions

Stale (no spending in 3+ months):
1. Buenos — $980 goal, $0 spent × 3 months. Remove goal?
2. Kids Health — $300 goal, $0 spent × 4 months. Remove goal?

⚠️ NOT stale (sinking funds — saving for periodic expense):
  • Home Insurance — $167/mo saving toward annual payment ✓
  • HOA — $91/mo saving toward quarterly payment ✓

Merge candidates:
3. Dog food Chewy ($136/mo) + Dog services ($22/mo) → "Pet" ($158/mo)
4. CVS ($32/mo) → merge into Healthcare/Pharmacy

Reply "remove 1", "merge 3", or "skip all"
```

---

### Scenario 7: Weekly Meeting Integration (US1)

**Trigger**: Existing meeting prep flow

**Expected enhancement**: When `create_meeting` runs, it now includes a budget health section if any categories have >30% drift.

**Expected addition to meeting agenda**:
```
📊 Budget Goal Health
• 8 categories drifted >30% — largest: Restaurants ($400 goal vs $1,200 actual)
• 2 categories need goals (Amazon $524/mo, Erin Shopping $1,076/mo)
• Health score: 73%
→ Say "budget health check" for full report
```

---

## Verification Checklist

- [ ] `budget_health_check` returns correct drift calculations for known category data
- [ ] Sinking fund categories (TB, TBD goal types) excluded from stale detection
- [ ] Categories with <2 months data marked as "insufficient data"
- [ ] Spiky categories (CV > 1.0) use 6-month lookback or "spiky" flag
- [ ] `apply_goal_suggestion` updates goal_target via PATCH /categories/{id}
- [ ] `apply_goal_suggestion` gracefully handles categories without existing goals
- [ ] `allocate_bonus` distributes amount across tiers in priority order
- [ ] `allocate_bonus` sums to exactly the specified amount
- [ ] `approve_allocation` moves money via existing `update_category_budget()`
- [ ] Monthly health check endpoint sends WhatsApp message via `send_sync_message_direct()`
- [ ] Meeting prep includes budget health section when drift detected
- [ ] Merge candidates only suggest categories with <$200/mo average
- [ ] Health score formula produces sensible values (73% for the known budget state)
