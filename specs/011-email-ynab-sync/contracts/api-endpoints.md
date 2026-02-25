# API Contracts: Email-YNAB Smart Sync (PayPal, Venmo, Apple)

**Feature**: 011-email-ynab-sync | **Date**: 2026-02-25

## N8N Scheduled Endpoint

### POST /api/v1/email/sync

Triggers nightly email-YNAB sync for PayPal, Venmo, and Apple transactions. Called by n8n on schedule (default: 10:05pm daily, 5 minutes after Amazon sync).

**Auth**: `X-N8N-Auth` header (same as existing endpoints)

**Request**: No body required.

**Response** (immediate — sync runs in background):
```json
{
  "status": "sent"
}
```

**Background behavior**:
1. Checks YNAB for unprocessed PayPal/Venmo/Apple transactions (fast — returns silently if none)
2. For each provider with unprocessed transactions:
   a. Searches Gmail for matching confirmation emails (last 30 days)
   b. Parses emails with Claude Haiku (provider-specific parser)
   c. Matches to YNAB transactions by date (±3 days) + exact penny amount
3. Enriches transaction memos with actual merchant/service names
4. Classifies into budget categories (cached mappings → Claude Haiku fallback)
5. Sends consolidated WhatsApp message to Erin (if any transactions need attention)
6. Logs sync results

**WhatsApp message format (suggestion mode)**:
```
💳 Email Sync — 3 new transactions

1️⃣ $45.00 PayPal (Feb 22) — DoorDash
→ Eating Out
Reply "1 yes" to apply, "1 adjust" to modify, "1 skip" to leave

2️⃣ $12.99 Apple (Feb 23) — iCloud+ 200GB
✅ Auto-categorized → Subscriptions (recurring)

3️⃣ $30.00 Venmo (Feb 24) — To Sarah M. — dinner split
→ Eating Out
Reply "3 yes" to apply, "3 adjust" to modify, "3 skip" to leave
```

**WhatsApp message format (auto-categorize mode)**:
```
💳 Email Auto-Categorized — 3 transactions

1️⃣ $45.00 PayPal → DoorDash → Eating Out
2️⃣ $12.99 Apple → iCloud+ → Subscriptions
3️⃣ $30.00 Venmo → Sarah M. (dinner split) → Eating Out

Reply "undo 1" to revert any categorization.
```

**Error behavior**: Logs error, completes silently, retries next night. Does NOT message Erin about errors.

## Claude Tool Definitions

### email_sync_status

Returns current email sync status and statistics.

**Parameters**: None

**Returns**: String with sync stats (last sync time, transactions processed by provider, acceptance rate, auto-categorize status)

### email_sync_trigger

Manually triggers an email sync (same as n8n endpoint, but invoked via WhatsApp).

**Parameters**: None

**Returns**: String confirming sync started, with results sent directly to Erin

### email_set_auto_categorize

Enables or disables auto-categorize mode for email-synced providers.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| enabled | boolean | yes | true to enable, false to disable |

**Returns**: Confirmation message

### email_undo_categorize

Reverts a categorized transaction back to its original state.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| transaction_index | integer | yes | Transaction number from the sync message (1-based) |

**Returns**: Confirmation of undo or error if transaction not found

## WhatsApp Reply Handling

Extends existing reply handling pattern from Amazon sync. Erin's replies to email sync messages are handled the same way — pending suggestions stored to disk, loaded on reply.

| Erin says | Bot action |
|-----------|------------|
| "1 yes" or "yes" (if only one pending) | Apply suggested category for transaction 1 |
| "1 adjust — put it in Jason Fun Money" | Modify category, apply corrected version |
| "1 skip" or "skip" | Mark as skipped, no category applied |
| "undo 1" | Revert categorization on transaction 1 |
| "turn on auto-categorize" | Enable auto-categorize mode for email providers |
| "turn off auto-categorize" | Disable auto-categorize mode |
| "email sync status" | Show email sync statistics |
