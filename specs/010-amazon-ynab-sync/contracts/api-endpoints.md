# API Contracts: Amazon-YNAB Smart Sync

**Feature**: 010-amazon-ynab-sync | **Date**: 2026-02-24

## N8N Scheduled Endpoint

### POST /api/v1/amazon/sync

Triggers nightly Amazon-YNAB sync. Called by n8n on schedule (default: 10pm daily).

**Auth**: `X-N8N-Auth` header (same as existing endpoints)

**Request**: No body required.

**Response** (immediate — sync runs in background):
```json
{
  "status": "sent"
}
```

**Background behavior**:
1. Fetches Amazon order confirmation emails via Gmail API (last 30 days), parses with Claude
2. Fetches YNAB transactions with Amazon payee (last 30 days)
3. Matches unprocessed transactions to orders
4. Enriches memos with item names
5. Classifies items into categories (cached mappings → Claude Haiku fallback)
6. Sends consolidated WhatsApp message to Erin (if any transactions need attention)
7. Logs sync results

**WhatsApp message format (suggestion mode)**:
```
📦 Amazon Sync — 3 new transactions

1️⃣ $87.42 (Feb 22) — 3 items:
• Vitamin D3 → Healthcare ($25.00)
• LEGO train set → Kids Toys ($43.42)
• Phone charger → Electronics ($19.00)
Reply "1 yes" to split, "1 adjust" to modify, "1 skip" to leave as-is

2️⃣ $15.99 (Feb 23) — 1 item:
• Baby wipes → Kids
✅ Auto-categorized (single item)

3️⃣ $12.99 (Feb 23) — unmatched
Tagged as "Unmatched Amazon charge" — what category?
```

**WhatsApp message format (auto-split mode)**:
```
📦 Amazon Auto-Split — 2 transactions

1️⃣ $87.42 → $25 Healthcare, $43.42 Kids, $19 Electronics
2️⃣ $15.99 → Kids (baby wipes)

Reply "undo 1" to revert any split.
```

**Error behavior**: Logs error, completes silently, retries next night. Does NOT message Erin about errors.

## Claude Tool Definitions

### amazon_sync_status

Returns current sync status and statistics.

**Parameters**: None

**Returns**: String with sync stats (last sync time, transactions processed, acceptance rate, auto-split status)

### amazon_sync_trigger

Manually triggers an Amazon sync (same as n8n endpoint, but invoked via WhatsApp).

**Parameters**: None

**Returns**: String confirming sync started

### amazon_set_auto_split

Enables or disables auto-split mode.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| enabled | boolean | yes | true to enable, false to disable |

**Returns**: Confirmation message

### amazon_undo_split

Reverts a split transaction back to its original unsplit state.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| transaction_index | integer | yes | Transaction number from the sync message (1-based) |

**Returns**: Confirmation of undo or error if transaction not found

## YNAB Tool Additions (to existing ynab.py)

### split_transaction

Splits a YNAB transaction into sub-transactions by category.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| transaction_id | string | yes | YNAB transaction UUID |
| subtransactions | list | yes | Array of {amount_milliunits, category_id, memo} |

**Returns**: Confirmation string or error

### update_transaction_memo

Updates the memo field on an existing YNAB transaction.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| transaction_id | string | yes | YNAB transaction UUID |
| memo | string | yes | New memo text (appended to existing if present) |

**Returns**: Confirmation string or error

## WhatsApp Reply Handling

Erin's replies to sync messages are handled by the existing `handle_message` flow in assistant.py. The system prompt includes context about pending Amazon sync suggestions. Claude interprets natural language replies:

| Erin says | Bot action |
|-----------|------------|
| "1 yes" or "yes" (if only one pending) | Apply suggested split for transaction 1 |
| "1 adjust — put charger in Home" | Modify split, apply corrected version |
| "1 skip" or "skip" | Mark as skipped, no split applied |
| "undo 1" | Revert split on transaction 1 |
| "turn on auto-split" | Enable auto-split mode |
| "turn off auto-split" | Disable auto-split mode |
| "amazon sync status" | Show sync statistics |
