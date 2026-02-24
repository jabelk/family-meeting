# Tasks: YNAB Smart Budget Management

**Input**: Design documents from `/specs/004-ynab-smart-budget/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/budget-endpoints.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Model upgrade — immediate value, zero risk

- [x] T001 [P] [US4] Upgrade model from `claude-sonnet-4-20250514` to `claude-opus-4-20250514` in src/assistant.py (single constant change per R6 research)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: YNAB API helpers and caching that ALL write operations depend on

**CRITICAL**: No user story work (US1/US2/US3) can begin until this phase is complete

- [x] T002 Add `_category_cache` dict and `_get_categories()` function to src/tools/ynab.py — fetch all categories from GET `/budgets/{id}/categories`, cache as name→{id, group, budgeted, activity, balance} map with 1-hour TTL, skip hidden/deleted
- [x] T003 [P] Add `_payee_cache` dict and `_get_payees()` function to src/tools/ynab.py — fetch all payees from GET `/budgets/{id}/payees`, cache as name→id map with 1-hour TTL, skip deleted
- [x] T004 [P] Add `_get_accounts()` function to src/tools/ynab.py — fetch accounts from GET `/budgets/{id}/accounts`, return list of {id, name, type, closed, balance}, cache with 1-hour TTL
- [x] T005 Add `_fuzzy_match_category(name)` and `_fuzzy_match_payee(name)` helper functions to src/tools/ynab.py — case-insensitive exact match first, then substring contains match, return (id, canonical_name) tuple or None

**Checkpoint**: Caching and matching infrastructure ready — user story implementation can begin

---

## Phase 3: User Story 1 — Transaction Management (Priority: P1) MVP

**Goal**: Users can search, recategorize, and create transactions via WhatsApp

**Independent Test**: Send "what did we spend at Costco this month?" and verify transaction list; send "categorize the Target charge as Home Supplies" and verify update in YNAB

- [x] T006 [US1] Implement `search_transactions(payee, category, since_date, uncategorized_only)` in src/tools/ynab.py — GET `/budgets/{id}/transactions` with optional `since_date` (default: first of current month) and `type=uncategorized` filter, client-side fuzzy filter by payee_name and category_name, return formatted text list sorted by date descending with payee, amount (milliunits→dollars), date, and category
- [x] T007 [US1] Implement `recategorize_transaction(payee, amount, date, new_category)` in src/tools/ynab.py — search transactions matching payee/amount/date, fuzzy-match new_category via `_fuzzy_match_category()`, if 1 match → PUT `/budgets/{id}/transactions/{txn_id}` with new category_id and return confirmation, if 2-5 matches → return numbered list for user to pick, if 0 matches → suggest alternatives, if >5 → ask user to narrow search
- [x] T008 [US1] Implement `create_transaction(payee, amount, category, date, memo, account)` in src/tools/ynab.py — fuzzy-match category, resolve account (default: first non-closed checking account from `_get_accounts()`), POST `/budgets/{id}/transactions` with payee_name, negative amount (milliunits), category_id, date (default: today), optional memo, set approved=True and cleared="uncleared", return confirmation with transaction details
- [x] T009 [US1] Register search_transactions, recategorize_transaction, and create_transaction tools in src/assistant.py — add 3 tool definitions to TOOLS array with parameter schemas per contracts/budget-endpoints.md, add 3 entries to TOOL_FUNCTIONS dict, update system prompt with budget management guidelines: "For transaction searches, show amounts as dollars. For recategorization, confirm the change. For manual transactions, default to checking account and today's date."

**Checkpoint**: Transaction management fully functional — search, recategorize, and create via WhatsApp

---

## Phase 4: User Story 3 — Budget Rebalancing (Priority: P3)

**Goal**: Users can adjust budget amounts and move money between categories via WhatsApp

**Independent Test**: Send "move $100 from Dining Out to Groceries" and verify both categories updated in YNAB

- [x] T010 [US3] Implement `update_category_budget(category, amount)` in src/tools/ynab.py — fuzzy-match category, GET current budgeted amount from `/budgets/{id}/months/current/categories/{cat_id}`, compute new budgeted = current + amount (in milliunits), PATCH `/budgets/{id}/months/current/categories/{cat_id}` with new budgeted value, return confirmation with old and new amounts
- [x] T011 [US3] Implement `move_money(from_category, to_category, amount)` in src/tools/ynab.py — fuzzy-match both categories, GET current budgeted amounts for both, validate source has sufficient budget (warn if not, suggest available amount), PATCH source with (current - amount_milliunits), PATCH destination with (current + amount_milliunits), return confirmation with both categories' new budgeted amounts
- [x] T012 [US3] Register update_category_budget and move_money tools in src/assistant.py — add 2 tool definitions to TOOLS array per contracts/budget-endpoints.md, add 2 entries to TOOL_FUNCTIONS dict, update system prompt: "For budget moves, always confirm both categories' new amounts. Warn if source category would go negative."

**Checkpoint**: Budget rebalancing functional — adjust and move money via WhatsApp

---

## Phase 5: User Story 2 — Smart Spending Insights (Priority: P2)

**Goal**: Bot proactively alerts about overspending, uncategorized transactions, anomalies, and savings goal gaps

**Independent Test**: Trigger budget scan endpoint and verify WhatsApp nudge for any category >80% spent

- [x] T013 [P] [US2] Implement `check_overspend_warnings()` in src/tools/ynab.py — GET `/budgets/{id}/months/current` for all categories, for each non-hidden category calculate percent_used = abs(activity) / budgeted * 100, if percent_used > 80 AND today is before the 20th of the month, return list of {category_name, spent, budgeted, percent_used, days_remaining}
- [x] T014 [P] [US2] Implement `check_uncategorized_pileup()` in src/tools/ynab.py — GET `/budgets/{id}/transactions?type=uncategorized`, filter to transactions older than 48 hours, if count >= 3 return {count, total_amount, oldest_date}
- [x] T015 [US2] Implement `check_spending_anomalies()` in src/tools/ynab.py — GET current month + previous 2 months from `/budgets/{id}/months/{month}`, for each category compute 3-month rolling average of abs(activity), if current month is 50%+ above average return list of {category_name, current_amount, average_amount, percent_above}
- [x] T016 [US2] Implement `check_savings_goals()` in src/tools/ynab.py — from current month categories data, find categories with goal_type set, compute expected_progress = (day_of_month / days_in_month) * 100, if goal_percentage_complete is more than 15 points below expected_progress, return {category_name, goal_target, funded, shortfall, percent_complete, expected_percent}
- [x] T017 [US2] Add POST `/api/v1/budget/scan` endpoint to src/app.py — protected by `verify_n8n_auth`, check quiet day first, call check_overspend_warnings() + check_uncategorized_pileup() daily, call check_spending_anomalies() + check_savings_goals() on Mondays only, create "budget" type nudges in Nudge Queue for each insight with appropriate message text and Context JSON, dedup by checking existing pending/sent budget nudges for same category today, cap at 2 budget nudges per scan (NFR-002), process pending nudges, return JSON response per contracts/budget-endpoints.md
- [x] T018 [US2] Create n8n workflow WF-010 (Budget Scanner) — cron `0 9 * * *` (daily at 9am Pacific), HTTP POST to `http://fastapi:8000/api/v1/budget/scan` with X-N8N-Auth header

**Checkpoint**: Proactive insights live — overspend, uncategorized, anomaly, and goal gap alerts via WhatsApp

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: System prompt refinements, deployment, and validation

- [x] T019 Update system prompt in src/assistant.py with comprehensive budget interaction guidelines — explain all 7 budget tools (search, recategorize, create, update_budget, move_money, plus existing get_budget_summary), instruct warm helpful tone for financial conversations, examples of natural language patterns ("what did we spend on X" → search_transactions, "categorize" → recategorize_transaction, "move $X from A to B" → move_money)
- [x] T020 Deploy to NUC via ./scripts/nuc.sh deploy
- [x] T021 Run quickstart.md validation — Test 1 (transaction search), Test 2 (recategorize), Test 3 (create manual transaction), Test 4 (budget rebalancing), Test 5 (overspend alert), Test 6 (uncategorized nudge), Test 7 (model quality)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — model upgrade is independent
- **Phase 2 (Foundational)**: No dependencies on Phase 1 — can run in parallel
- **Phase 3 (US1)**: Depends on Phase 2 (needs category/payee caching)
- **Phase 4 (US3)**: Depends on Phase 2 (needs category caching)
- **Phase 5 (US2)**: Depends on Phase 2 (needs category caching) + can reference Phase 3 helpers
- **Phase 6 (Polish)**: Depends on all phases complete

### User Story Dependencies

- **US4 (Model Upgrade)**: Independent — can deploy at any time
- **US1 (Transactions)**: Depends on Phase 2 only — no other story dependencies
- **US3 (Rebalancing)**: Depends on Phase 2 only — independent of US1
- **US2 (Insights)**: Depends on Phase 2 — uses same YNAB helpers, independent of US1/US3

### Parallel Opportunities

- T001 (model upgrade) can run in parallel with T002-T005 (foundational)
- T003 and T004 can run in parallel with T002 (different cache functions)
- T013 and T014 can run in parallel (different insight functions)
- US1 (Phase 3) and US3 (Phase 4) can run in parallel after Phase 2

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2 + Phase 3)

1. T001: Upgrade model → immediate quality improvement
2. T002-T005: Build YNAB caching layer
3. T006-T009: Transaction search, recategorize, create → deploy and validate
4. **STOP and VALIDATE**: Test transactions via WhatsApp

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. Phase 3 (US1) → Transaction management live (MVP)
3. Phase 4 (US3) → Budget rebalancing live
4. Phase 5 (US2) → Proactive insights live
5. Phase 6 → Polish and full validation

---

## Notes

- All amounts in YNAB API use milliunits (multiply dollars by 1000, outflows are negative)
- Cache TTL of 1 hour means category/payee changes may take up to 1 hour to reflect
- YNAB rate limit: 200 requests/hour — budget scan uses ~5-10 calls, leaving plenty for user queries
- Budget nudges use existing Nudge Queue with nudge_type="budget" — same delivery pipeline as Feature 003
