# API Contracts: Smart Budget Maintenance

**Feature**: 012-smart-budget-maintenance
**Date**: 2026-02-25

## Claude Tool Definitions

### Tool: `budget_health_check`

Analyze all budget categories for goal drift, missing goals, stale categories, and merge candidates. Returns a comprehensive health report.

```json
{
  "name": "budget_health_check",
  "description": "Analyze all YNAB budget categories for goal drift, missing goals, stale categories, and merge candidates. Returns a health score and actionable suggestions. Use when user asks 'how are my budget goals?', 'budget health check', or 'any budget issues?'",
  "input_schema": {
    "type": "object",
    "properties": {
      "lookback_months": {
        "type": "integer",
        "description": "Number of months to analyze (default 3, max 12). Use 6+ for spiky categories.",
        "default": 3
      },
      "drift_threshold": {
        "type": "number",
        "description": "Minimum drift percentage to flag (default 30). Lower values catch smaller misalignments.",
        "default": 30
      }
    },
    "required": []
  }
}
```

**Returns**: Formatted WhatsApp message with:
- Health score percentage
- Underfunded categories (spending > goal) ranked by dollar gap
- Overfunded categories (goal > spending) ranked by dollar gap
- Missing goal categories with suggested amounts
- Stale categories (3+ months no spend, excluding sinking funds)
- Merge candidates (if any)
- Actionable prompt: "Reply 'update all' to apply suggestions, or 'yes to [category]' / 'skip [category]' individually."

---

### Tool: `apply_goal_suggestion`

Apply a single goal update suggestion from a budget health check.

```json
{
  "name": "apply_goal_suggestion",
  "description": "Update a YNAB category's goal target based on a budget health check suggestion. Use when user approves a specific suggestion like 'yes to restaurants' or 'update restaurants to $1200'.",
  "input_schema": {
    "type": "object",
    "properties": {
      "category": {
        "type": "string",
        "description": "Category name (fuzzy matched)"
      },
      "amount": {
        "type": "number",
        "description": "New goal amount in dollars. If omitted, uses the recommended amount from the last health check."
      },
      "apply_all": {
        "type": "boolean",
        "description": "If true, apply all pending suggestions at once. Ignores category and amount params.",
        "default": false
      }
    },
    "required": []
  }
}
```

**Returns**: Confirmation message with old goal, new goal, and remaining pending suggestions count.

**Error cases**:
- Category has no existing goal in YNAB → "I can't create a new goal via YNAB's API. Please set a goal type for [category] in the YNAB app, then I can update the target amount."
- No pending suggestions → "No pending goal suggestions. Run a budget health check first."

---

### Tool: `allocate_bonus`

Generate a prioritized allocation plan for distributing bonus/extra income across underfunded categories.

```json
{
  "name": "allocate_bonus",
  "description": "Generate a plan to allocate a bonus, stock vesting, or extra income across underfunded budget categories. Prioritizes essentials, then savings, then discretionary. Use when user asks 'where should this bonus go?' or 'allocate $X'.",
  "input_schema": {
    "type": "object",
    "properties": {
      "amount": {
        "type": "number",
        "description": "Dollar amount to allocate. If omitted, bot looks for recent large deposits in YNAB."
      },
      "description": {
        "type": "string",
        "description": "What the income is from (e.g., 'Q1 bonus', 'stock vesting'). Optional."
      }
    },
    "required": []
  }
}
```

**Returns**: Formatted allocation plan:
```
💰 Bonus Allocation Plan — $5,000

Essential (funded first):
  • Groceries: +$754 (was $754 underfunded)
  • Healthcare: +$1,478 (was $1,478 underfunded)

Savings:
  • Emergency Fund: +$2,000 ($48k remaining to $200k target)

Discretionary:
  • Kids Activities: +$388 (was $388 underfunded)
  • Remaining: +$380 → Fun Money

Reply 'approve' to move money, or adjust: 'put $3000 in emergency fund'
```

---

### Tool: `approve_allocation`

Execute an approved allocation plan by moving money in YNAB.

```json
{
  "name": "approve_allocation",
  "description": "Execute the pending bonus allocation plan, moving money to each category in YNAB. Use when user says 'approve', 'yes', or 'do it' after seeing an allocation plan.",
  "input_schema": {
    "type": "object",
    "properties": {
      "adjustments": {
        "type": "string",
        "description": "Optional free-text adjustments before executing (e.g., 'put $3000 in emergency fund instead'). If provided, regenerates the plan with adjustments before executing."
      }
    },
    "required": []
  }
}
```

**Returns**: Execution confirmation with each category updated, or error details if any move fails.

---

## n8n / Scheduled Endpoints

### POST `/api/v1/budget/health-check`

Monthly scheduled budget health check. Sends comprehensive report directly to WhatsApp.

**Schedule**: 1st of each month, 9:00am Pacific (via n8n)

**Authentication**: `X-N8N-Auth: {N8N_WEBHOOK_SECRET}` header

**Request body**: None required

**Response**:
```json
{
  "status": "sent",
  "health_score": 73.2,
  "drifted_count": 8,
  "stale_count": 2,
  "suggestions_sent": true
}
```

**Behavior**:
- Runs budget_health_check with default 3-month lookback
- If health_score >= 80 and drifted_count == 0: sends brief "budget is healthy" message
- Otherwise: sends detailed report with suggestions
- Includes stale category and merge candidate sections if applicable
- Sends via `send_sync_message_direct()` (same pattern as Amazon/email sync)
- Returns `{"status": "skipped"}` if no significant issues found and score >= 90

---

## Integration with Existing Endpoints

### Weekly Meeting Prep (existing)

The existing meeting prep flow in `assistant.py` will be extended to include a "Budget Goal Health" section when any categories have >30% drift. This is not a new endpoint — it's an enhancement to the existing `create_meeting` tool behavior.

**Format in meeting agenda**:
```
📊 Budget Goal Health
• 8 categories drifted >30% — largest: Restaurants ($400 goal vs $1,200 actual)
• 2 categories have no goals (Amazon $524/mo, Erin Shopping $1,076/mo)
• Health score: 73%
→ Say "budget health check" for full details and suggestions
```

### Daily Briefing (existing)

No changes to the daily briefing. The existing `check_overspend_warnings()` and `check_spending_anomalies()` already cover day-to-day budget monitoring. The monthly health check is the right cadence for goal drift analysis.
