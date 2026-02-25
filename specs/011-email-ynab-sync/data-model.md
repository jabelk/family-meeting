# Data Model: Email-YNAB Smart Sync (PayPal, Venmo, Apple)

**Feature**: 011-email-ynab-sync | **Date**: 2026-02-25

## Entities

### EmailTransaction

A parsed transaction from a provider confirmation email.

| Field | Type | Description |
|-------|------|-------------|
| provider | enum | `paypal`, `venmo`, `apple` |
| email_id | string | Gmail message ID (for dedup) |
| email_date | date | Date the email was received |
| merchant_name | string | Extracted merchant/recipient name (e.g., "DoorDash", "Sarah M.", "iCloud+ 200GB") |
| amount | float | Transaction amount in dollars |
| items | list[EmailItem] | Itemized details (PayPal multi-item only; usually 1 for Venmo/Apple) |
| payment_note | string | Venmo payment note (e.g., "dinner split"); null for PayPal/Apple |
| is_refund | bool | True if the email describes a refund |
| raw_text_snippet | string | First 200 chars of parsed text (for debugging) |

### EmailItem

An individual item within a provider email (mainly for PayPal multi-item purchases).

| Field | Type | Description |
|-------|------|-------------|
| title | string | Item/service name |
| price | float | Item price in dollars |
| quantity | int | Quantity (default 1) |

### SyncRecord (extended from Feature 010)

Existing `SyncRecord` from `amazon_sync.py` with one new field.

| Field | Type | Description |
|-------|------|-------------|
| provider | string (NEW) | `amazon`, `paypal`, `venmo`, `apple` — defaults to `amazon` for existing records |

All other fields remain unchanged from Feature 010: `ynab_transaction_id`, `amazon_order_number` (reused as `order_ref` for email IDs), `status`, `matched_at`, `enriched_at`, `split_applied_at`, `ynab_amount`, `ynab_date`, `items`, `suggestion_message_id`, `original_memo`, `original_category_id`.

**State Transitions** (same as Feature 010):
```
unprocessed → matched → enriched → split_pending → split_applied
                                  → skipped (24h timeout or user skip)
                                  → auto_split (auto-categorize mode)
unprocessed → unmatched (no email found)
split_applied → undone → split_pending (undo flow)
```

### CategoryMapping (shared — no changes)

Existing `CategoryMapping` from Feature 010 is shared across all providers. The `item_title_normalized` key is merchant/service name (provider-agnostic). If "DoorDash" is mapped to "Eating Out" via PayPal, the same mapping applies if DoorDash appears via Venmo.

No structural changes needed.

### SyncConfig (extended from Feature 010)

Existing `SyncConfig` with new fields for email sync.

| Field | Type | Description |
|-------|------|-------------|
| email_auto_categorize_enabled | bool (NEW) | Whether auto-categorize mode is active for email providers (default: false) |
| email_last_sync | datetime (NEW) | Timestamp of last email sync run |
| email_total_suggestions | int (NEW) | Total email sync suggestions sent |
| email_unmodified_accepts | int (NEW) | Email suggestions accepted without changes |

### ProviderConfig

Provider-specific search and matching configuration (compile-time constants, not persisted).

| Provider | Gmail Search Query | YNAB Payee Filter | Memo Prefix |
|----------|-------------------|-------------------|-------------|
| PayPal | `from:service@paypal.com OR from:paypal@mail.paypal.com` | payee contains "paypal" (case-insensitive) | "[merchant] via PayPal" |
| Venmo | `from:venmo@venmo.com` | payee contains "venmo" (case-insensitive) | "To [name] — [note]" or "From [name] — [note]" |
| Apple | `from:no_reply@email.apple.com` | payee contains "apple" (case-insensitive) | "[service name]" |

## Relationships

```
EmailTransaction 1──* EmailItem          (one email can have multiple items, mainly PayPal)
EmailTransaction *──1 SyncRecord         (matched email → tracked in sync records)
SyncRecord *──1 CategoryMapping          (each transaction maps to a learned category)
SyncConfig 1──1 (singleton)              (global sync state, extended with email fields)
```

## Validation Rules

- SyncRecord.ynab_transaction_id must be unique (prevents duplicate processing across all providers)
- SyncRecord.provider must be one of: `amazon`, `paypal`, `venmo`, `apple`
- EmailTransaction.amount must be positive (refunds have `is_refund=True`, amount is absolute value)
- CategoryMapping.confidence must be between 0.0 and 1.0
- Recurring charge detection: same merchant name + amount within ±20% of previous charge → auto-categorize after first approval
- YNAB transactions with payee containing "amazon" or "amzn" are excluded (handled by Feature 010)
