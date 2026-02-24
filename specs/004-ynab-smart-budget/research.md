# Research: YNAB Smart Budget Management

## R1: YNAB API Write Capabilities

**Decision**: Use YNAB API v1 direct HTTP calls (httpx) for all write operations — no SDK needed.

**Rationale**: The existing codebase already uses httpx for YNAB reads. The API is simple REST with Bearer token auth. Adding an SDK would introduce a dependency for ~5 endpoints.

**Alternatives considered**: ynab-sdk-python (unofficial, unmaintained), ynab-sdk-js (wrong language). Direct HTTP is consistent with existing pattern.

### Key Endpoints

| Operation | Method | Endpoint | Notes |
|-----------|--------|----------|-------|
| List transactions | GET | `/budgets/{id}/transactions` | `since_date` filter, `type=uncategorized` |
| Create transaction | POST | `/budgets/{id}/transactions` | Requires account_id, date, amount |
| Update transaction | PUT | `/budgets/{id}/transactions/{txn_id}` | Can change category_id (recategorize) |
| List categories | GET | `/budgets/{id}/categories` | Grouped by category group |
| Update budget amount | PATCH | `/budgets/{id}/months/{month}/categories/{cat_id}` | Only `budgeted` field is writable |
| List payees | GET | `/budgets/{id}/payees` | For payee name → ID resolution |
| Get month detail | GET | `/budgets/{id}/months/{month}` | Full category breakdown per month |
| Transactions by payee | GET | `/budgets/{id}/payees/{payee_id}/transactions` | For payee-specific search |

### Amount Format

All amounts in **milliunits**: $45.50 = 45500, -$100.00 = -100000. Outflows are negative.

### Search Limitations

- No free-text search — payee search requires payee_id lookup first
- `since_date` provides date floor only — no `before_date`, must filter client-side
- `type=uncategorized` returns null-category transactions directly
- Amount/memo search is client-side only

### Rate Limits

- 200 requests/hour per token (rolling window)
- HTTP 429 when exceeded, no remaining-quota header
- Sufficient for conversational use; cache category/payee lists to minimize calls

## R2: Transaction Recategorization Flow

**Decision**: Two-step flow — search → update. For unambiguous matches, proceed directly. For multiple matches, present options.

**Rationale**: Natural language requests like "categorize the Target charge to Home" may match multiple transactions. The bot should handle both unambiguous and ambiguous cases.

**Flow**:
1. Fetch recent transactions (current month by default)
2. Match by payee name (fuzzy, case-insensitive)
3. If 1 match → recategorize directly, confirm
4. If 2-5 matches → present list, ask user to pick
5. If 0 matches → suggest alternatives
6. If >5 matches → ask user to narrow (add date or amount)

## R3: Category Fuzzy Matching

**Decision**: Cache category list on first use, match case-insensitive with substring. Same pattern as chore matching in Feature 003.

**Rationale**: Users say "groceries" not "Groceries", "dining" not "Dining Out". The chore fuzzy match pattern already works well.

**Implementation**: Fetch categories once per session (they rarely change), store as name→id map, match with case-insensitive contains.

## R4: Budget Rebalancing

**Decision**: Two PATCH calls — read current amounts, decrease source, increase destination.

**Rationale**: YNAB API has no "move money" endpoint. Must read both categories, compute new amounts, and update each separately.

**Validation**: Check source category has sufficient budgeted amount before proceeding. Warn user if move would make source negative.

## R5: Proactive Insights Architecture

**Decision**: Add budget insights to the existing nudge scan pipeline (n8n cron). Run budget checks once daily (not every 15 min) to conserve API rate limit.

**Rationale**: The nudge scanner already runs every 15 min. Budget data changes slowly (transactions imported once/day by banks). A daily budget check is sufficient and uses ~5-10 API calls vs. the 200/hour limit.

**Insight types and triggers**:

| Insight | Trigger | Frequency | Priority |
|---------|---------|-----------|----------|
| Overspend warning | Category > 80% budget before 20th | Daily | High |
| Uncategorized pile-up | 3+ uncategorized transactions > 48h old | Daily | Medium |
| Spending anomaly | Category 50%+ above 3-month average | Weekly | Medium |
| Savings goal gap | Goal funded% below expected pace | Weekly | Low |

**API calls per daily scan**: ~5 (1 month detail + 1 uncategorized transactions + 3 historical months for anomaly on weekly run)

## R6: Model Upgrade

**Decision**: Change model from `claude-sonnet-4-20250514` to `claude-opus-4-20250514` in assistant.py.

**Rationale**: Family sends <500 messages/month. Opus input is ~$15/MTok vs Sonnet ~$3/MTok (5x). At ~2K tokens/message average, 500 messages = ~1M tokens/month. Cost goes from ~$3/month to ~$15/month — well within the $75/month budget.

**Alternatives considered**: Keep Sonnet for simple queries, use Opus only for budget analysis. Rejected — adds complexity for minimal savings. Single model is simpler.

## R7: Account Selection for Manual Transactions

**Decision**: Use the checking account (most common) as default. Allow user to specify "from savings" or "from credit card" to override.

**Rationale**: Manual transactions are typically cash/check payments from checking. The bot should fetch the account list and pick the primary checking account. Users rarely need to specify.

**Implementation**: Fetch accounts once, find the first non-closed checking/cash account, use as default. Store account_id in memory for the session.
