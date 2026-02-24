# Data Model: YNAB Smart Budget Management

## External Entities (YNAB API — read/write)

### Transaction

Represents a YNAB transaction. Read from API, can be created and updated.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | YNAB transaction ID |
| date | Date (ISO) | Transaction date |
| amount | Integer (milliunits) | Negative = outflow, positive = inflow |
| payee_id | UUID (nullable) | Reference to payee |
| payee_name | String | Denormalized payee name |
| category_id | UUID (nullable) | Null = uncategorized |
| category_name | String | Denormalized category name |
| account_id | UUID | Which account |
| memo | String (nullable) | Max 500 chars |
| cleared | Enum | "cleared", "uncleared", "reconciled" |
| approved | Boolean | Whether transaction is approved |

**Write operations**:
- Create: requires account_id, date, amount. Optional: payee_name, category_id, memo, cleared.
- Update (recategorize): PUT with transaction id + new category_id.

### Budget Category

Represents a YNAB budget category with month-specific amounts.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | YNAB category ID |
| name | String | Category display name |
| category_group_id | UUID | Parent group |
| category_group_name | String | Group display name (e.g., "Immediate Obligations") |
| budgeted | Integer (milliunits) | Amount budgeted this month |
| activity | Integer (milliunits) | Amount spent this month (negative) |
| balance | Integer (milliunits) | Remaining = budgeted + activity |
| hidden | Boolean | Whether category is hidden |
| deleted | Boolean | Whether category is deleted |
| goal_type | String (nullable) | "TB" (target balance), "TBD" (target by date), "MF" (monthly funding), "NEED" (spending) |
| goal_target | Integer (milliunits, nullable) | Goal target amount |
| goal_percentage_complete | Integer (nullable) | 0-100 |
| goal_overall_funded | Integer (milliunits, nullable) | Total funded toward goal |

**Write operations**:
- Update budgeted amount: PATCH with new `budgeted` value (milliunits).

### Payee

Represents a YNAB payee for name → ID resolution.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | YNAB payee ID |
| name | String | Payee display name |
| deleted | Boolean | Whether payee is deleted |

**Read-only** — used for transaction search by payee name.

### Account

Represents a YNAB account for manual transaction creation.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | YNAB account ID |
| name | String | Account display name |
| type | String | "checking", "savings", "creditCard", "cash", etc. |
| closed | Boolean | Whether account is closed |
| balance | Integer (milliunits) | Current balance |

**Read-only** — used to determine default account for manual transactions.

## Internal Entities (Nudge Queue — existing Notion DB)

### Budget Insight (stored as Nudge)

Budget insights are stored in the existing Nudge Queue database as nudge records with `nudge_type = "budget"`.

| Field | Nudge Queue Property | Notes |
|-------|---------------------|-------|
| Summary | Summary (Title) | e.g., "Groceries overspend warning" |
| Type | Nudge Type (Select) | "budget" |
| Status | Status | Pending → Sent → Done |
| Scheduled Time | Scheduled Time (Date) | When to deliver |
| Message | Message (Rich Text) | The insight text sent to user |
| Context | Context (Rich Text) | JSON: insight_type, category_name, amounts |

**Insight types stored in Context JSON**:
- `overspend_warning`: category_name, spent, budgeted, percent_used, days_remaining
- `uncategorized_pileup`: count, total_amount, oldest_date
- `spending_anomaly`: category_name, current_month, rolling_average, percent_above
- `savings_goal_gap`: goal_name, funded, target, shortfall, days_remaining

## Caching Strategy

To minimize API calls (200/hour limit):

| Data | Cache Duration | Refresh Trigger |
|------|---------------|-----------------|
| Categories (name → id map) | 1 hour | On cache miss |
| Payees (name → id map) | 1 hour | On cache miss |
| Accounts list | 1 hour | On cache miss |
| Monthly category data | 15 minutes | Budget scan |
| Transactions (current month) | No cache | Always fresh for searches |

## Milliunits Conversion

```
To milliunits:   dollars * 1000  →  $45.50 = 45500
From milliunits: milliunits / 1000  →  45500 = $45.50
Outflow (spending): negative  →  -$100.00 = -100000
Inflow (income): positive  →  $3000.00 = 3000000
```
