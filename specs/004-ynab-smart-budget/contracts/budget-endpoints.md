# Contract: Budget Scan Endpoint

## POST /api/v1/budget/scan

**Purpose**: Proactive budget insight scanner — checks for overspending, uncategorized transactions, anomalies, and savings goal gaps. Called by n8n cron (daily).

**Auth**: `X-N8N-Auth` header (same as existing endpoints)

### Response

```json
{
  "insights_created": 1,
  "uncategorized_count": 5,
  "overspend_warnings": 1,
  "anomalies_detected": 0,
  "goal_gaps": 0,
  "nudges_sent": 1,
  "daily_count": 3,
  "daily_cap": 8,
  "quiet_day": false,
  "errors": []
}
```

### Behavior

1. Check quiet day → skip if active
2. Fetch current month budget categories
3. Check each category for overspend (>80% before 20th)
4. Fetch uncategorized transactions → count if 3+ older than 48h
5. Weekly only: fetch 3-month history for anomaly detection
6. Weekly only: check savings goals for pace gaps
7. Create budget nudges in Nudge Queue
8. Process pending nudges (deliver via WhatsApp)

### Dedup

- Only one overspend warning per category per day
- Only one uncategorized nudge per day
- Anomaly and goal checks run weekly (not daily)

---

# Contract: Claude Tool Definitions

## search_transactions

**Description**: Search recent transactions by payee name, category, or amount.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| payee | string | No | Payee name to search for (fuzzy match) |
| category | string | No | Category name to filter by |
| since_date | string | No | ISO date floor (default: first of current month) |
| uncategorized_only | boolean | No | If true, return only uncategorized transactions |

**Returns**: Formatted text list of matching transactions with date, payee, amount, category.

## recategorize_transaction

**Description**: Change the category of an existing transaction.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| payee | string | No | Payee name to find the transaction |
| amount | number | No | Dollar amount to match (helps disambiguate) |
| date | string | No | Date to match (ISO format) |
| new_category | string | Yes | Target category name (fuzzy matched) |

**Returns**: Confirmation text with transaction details and new category, or list of candidates if ambiguous.

## create_transaction

**Description**: Create a manual transaction (e.g., cash purchase).

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| payee | string | Yes | Payee/merchant name |
| amount | number | Yes | Dollar amount (positive number — system makes it negative for outflow) |
| category | string | Yes | Category name (fuzzy matched) |
| date | string | No | ISO date (default: today) |
| memo | string | No | Optional memo/note |
| account | string | No | Account name (default: primary checking) |

**Returns**: Confirmation text with created transaction details.

## update_category_budget

**Description**: Adjust the budgeted amount for a category this month.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| category | string | Yes | Category name (fuzzy matched) |
| amount | number | Yes | Dollar amount to add (positive) or subtract (negative) |

**Returns**: Confirmation text with old and new budgeted amounts.

## move_money

**Description**: Move budgeted money from one category to another.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| from_category | string | Yes | Source category name (fuzzy matched) |
| to_category | string | Yes | Destination category name (fuzzy matched) |
| amount | number | Yes | Dollar amount to move (positive number) |

**Returns**: Confirmation text with both categories' new budgeted amounts, or warning if source has insufficient budget.
