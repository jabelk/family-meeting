# Quickstart: YNAB Smart Budget Management

## Prerequisites

- Existing family meeting assistant deployed (FastAPI + Docker Compose on NUC)
- YNAB API access configured (existing `YNAB_ACCESS_TOKEN` and `YNAB_BUDGET_ID`)
- WhatsApp bot working with existing tool loop
- n8n running with nudge scanner workflow

## Setup Steps

### Step 1: Model Upgrade

Update the model constant in assistant.py from Sonnet to Opus. No config changes needed — the Anthropic API key already has access.

### Step 2: Add YNAB Write Tools

Add 5 new tool functions to `src/tools/ynab.py`:
- `search_transactions()` — search by payee, category, date, or uncategorized
- `recategorize_transaction()` — change a transaction's category
- `create_transaction()` — add a manual transaction
- `update_category_budget()` — adjust a category's budgeted amount
- `move_money()` — transfer budget between two categories

Add helper functions:
- `_get_categories()` — cached category name → id map
- `_get_payees()` — cached payee name → id map
- `_get_accounts()` — cached account list
- `_fuzzy_match_category()` — case-insensitive category matching
- `_fuzzy_match_payee()` — case-insensitive payee matching

### Step 3: Register Tools in Assistant

Add 5 new tool definitions to `src/assistant.py` TOOLS array and TOOL_FUNCTIONS dict. Update system prompt with budget management guidelines.

### Step 4: Create Budget Scan Endpoint

Add `POST /api/v1/budget/scan` to `src/app.py` for proactive budget insights. Protected by `verify_n8n_auth`.

### Step 5: Create n8n Workflow

Create workflow **WF-010: Budget Scanner**:
- **Trigger**: Cron — `0 9 * * *` (daily at 9am Pacific)
- **Action**: HTTP Request POST to `http://fastapi:8000/api/v1/budget/scan`
- **Header**: `X-N8N-Auth: <N8N_WEBHOOK_SECRET>`

### Step 6: Deploy

```bash
git add . && git commit -m "feat: YNAB smart budget management" && git push
./scripts/nuc.sh deploy
```

## Validation

### Test 1: Transaction Search (US1)

1. Send "what did we spend at Costco this month?" to the bot
2. Verify the bot returns a list of Costco transactions with dates and amounts
3. Send "show me uncategorized transactions"
4. Verify uncategorized transactions are listed

### Test 2: Recategorize Transaction (US1)

1. Find an uncategorized or miscategorized transaction in YNAB
2. Send "categorize the $47 Target charge as Home Supplies"
3. Verify the transaction category is updated in YNAB
4. If multiple matches, verify the bot asks which one

### Test 3: Create Manual Transaction (US1)

1. Send "add $35 cash transaction for farmers market under Groceries"
2. Verify a new transaction appears in YNAB with correct payee, amount, and category
3. Verify the default checking account was used

### Test 4: Budget Rebalancing (US3)

1. Send "move $100 from Dining Out to Groceries"
2. Verify both categories' budgeted amounts changed in YNAB
3. Send "budget $200 more for Groceries"
4. Verify the budgeted amount increased

### Test 5: Overspend Alert (US2)

1. Check if any category is >80% spent before the 20th
2. Trigger the budget scan endpoint manually
3. Verify a WhatsApp nudge is sent with the overspend warning
4. Verify the nudge appears in Notion Nudge Queue as type "budget"

### Test 6: Uncategorized Nudge (US2)

1. Verify there are 3+ uncategorized transactions in YNAB
2. Trigger the budget scan
3. Verify the bot sends a nudge about uncategorized transactions
4. Reply "help me categorize them" and verify the bot walks through them

### Test 7: Model Upgrade (US4)

1. Ask "Based on our spending this month, are we on track for savings goals? What would you change?"
2. Verify the response shows multi-step reasoning with specific numbers
3. Compare response quality to previous Sonnet behavior

## Troubleshooting

- **"Category not found"**: Check category name spelling. The bot fuzzy-matches but very short names may not match. Try the full category name.
- **Transaction not found**: Default search is current month only. Try "search transactions since January" for older transactions.
- **Rate limit errors**: YNAB allows 200 requests/hour. If the budget scan runs alongside heavy user queries, reduce scan frequency.
- **Budget move warning**: If the source category has less than the requested amount, the bot will suggest the available amount instead.
- **No insights generated**: Budget insights only fire when thresholds are met (80% overspend, 3+ uncategorized, 50%+ anomaly). Check if conditions are actually met.
