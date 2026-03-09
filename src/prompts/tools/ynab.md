## get_budget_summary

Get budget summary from YNAB for a given month, optionally filtered to one category.

## search_transactions

Search recent YNAB transactions by payee name, category, or uncategorized status.

## recategorize_transaction

Change the category of an existing transaction. Finds by payee/amount/date, then updates.

## create_transaction

Create a manual YNAB transaction (e.g., cash purchase, reimbursement).

## update_category_budget

Adjust the budgeted amount for a YNAB category this month (add or subtract dollars).

## move_money

Move budgeted money from one YNAB category to another.

## budget_health_check

Analyze all YNAB budget categories for goal drift, missing goals, stale categories, and merge candidates. Returns a health score and actionable suggestions. Use when user asks 'how are my budget goals?', 'budget health check', or 'any budget issues?'.

## apply_goal_suggestion

Update a YNAB category's goal target based on a budget health check suggestion. Use when user approves a specific suggestion like 'yes to restaurants' or 'update restaurants to $1200'.

## allocate_bonus

Generate a plan to allocate a bonus, stock vesting, or extra income across underfunded budget categories. Prioritizes essentials, then savings, then discretionary. Use when user asks 'where should this bonus go?' or 'allocate $X'.

## approve_allocation

Execute the pending bonus allocation plan, moving money to each category in YNAB. Use when user says 'approve', 'yes', or 'do it' after seeing an allocation plan.
