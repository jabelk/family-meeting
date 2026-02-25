# Data Model: Amazon-YNAB Smart Sync

**Feature**: 010-amazon-ynab-sync | **Date**: 2026-02-24

## Entities

### SyncRecord

Tracks which YNAB transactions have been processed to prevent duplicates.

| Field | Type | Description |
|-------|------|-------------|
| ynab_transaction_id | string (PK) | YNAB transaction UUID |
| amazon_order_number | string | Amazon order ID (e.g., "111-1234567-1234567"), null if unmatched |
| status | enum | `matched`, `enriched`, `split_pending`, `split_applied`, `auto_split`, `skipped`, `unmatched`, `refund_applied` |
| matched_at | datetime | When the match was found |
| enriched_at | datetime | When memo was updated |
| split_applied_at | datetime | When split was applied (null if pending/skipped) |
| ynab_amount | int | Transaction amount in milliunits |
| ynab_date | date | Transaction date from YNAB |
| items | list[MatchedItem] | Items matched to this transaction |
| suggestion_message_id | string | WhatsApp message ID for tracking replies (null if auto-split) |
| original_memo | string | Memo before enrichment (for undo) |
| original_category_id | string | Category before split (for undo) |

**State Transitions**:
```
unprocessed → matched → enriched → split_pending → split_applied
                                  → skipped (24h timeout or user skip)
                                  → auto_split (auto-split mode)
unprocessed → unmatched (no Amazon order found)
split_applied → undone → split_pending (undo flow)
```

### MatchedItem

An Amazon item matched to a YNAB transaction, with its classification.

| Field | Type | Description |
|-------|------|-------------|
| title | string | Amazon item title |
| price | float | Item price in dollars |
| quantity | int | Quantity ordered |
| seller | string | Seller name (null if unavailable) |
| classified_category | string | YNAB category name assigned |
| classified_category_id | string | YNAB category UUID |
| confidence | float | Classification confidence (0.0-1.0) |
| allocated_amount | int | Amount in milliunits after tax/shipping proration |

### CategoryMapping

Learned association between Amazon item characteristics and YNAB budget categories.

| Field | Type | Description |
|-------|------|-------------|
| item_title_normalized | string (PK) | Lowercased, trimmed item title |
| category_name | string | YNAB category name |
| category_id | string | YNAB category UUID |
| confidence | float | Confidence level from classification |
| source | enum | `llm_initial`, `user_approved`, `user_corrected` |
| times_used | int | How many times this mapping has been applied |
| last_used | datetime | Last time this mapping was used |
| corrections | list[Correction] | History of user corrections for this item |

### Correction

A record of Erin correcting a category assignment.

| Field | Type | Description |
|-------|------|-------------|
| timestamp | datetime | When correction was made |
| from_category | string | Original suggested category |
| to_category | string | Corrected category |
| context | string | Erin's adjustment message (e.g., "put the charger in Home instead") |

### SyncConfig

Global configuration for the sync feature.

| Field | Type | Description |
|-------|------|-------------|
| auto_split_enabled | bool | Whether auto-split mode is active (default: false) |
| last_sync | datetime | Timestamp of last successful sync run |
| total_suggestions | int | Total split suggestions sent |
| unmodified_accepts | int | Suggestions accepted without changes |
| modified_accepts | int | Suggestions accepted with corrections |
| skips | int | Suggestions skipped or timed out |
| first_suggestion_date | date | Date of first suggestion (for 2-week threshold) |
| known_charge_patterns | dict | Non-order Amazon charge type → category mapping |

### KnownChargePattern

Pre-configured mapping for non-order Amazon charges.

| Pattern (payee/memo contains) | Default Category |
|-------------------------------|-----------------|
| "Prime" or "PRIME" | Subscriptions |
| "Kindle" | Entertainment |
| "Audible" | Entertainment |
| "Amazon Music" | Entertainment |
| "AWS" | (flag for manual review — likely not consumer) |
| "Gift Card" | (flag for manual review — transfer, not expense) |
| "Amazon Fresh" | Groceries |
| "Whole Foods" | Groceries |

## Relationships

```
SyncRecord 1──* MatchedItem       (one transaction has multiple items)
MatchedItem *──1 CategoryMapping   (each item maps to a learned category)
CategoryMapping 1──* Correction    (category can be corrected over time)
SyncConfig 1──1 (singleton)        (global sync state)
```

## Validation Rules

- SyncRecord.ynab_transaction_id must be unique (prevents duplicate processing)
- MatchedItem.allocated_amount values must sum to SyncRecord.ynab_amount exactly
- CategoryMapping.confidence must be between 0.0 and 1.0
- SyncConfig.auto_split_enabled can only be set to true if unmodified_accepts / total_suggestions >= 0.8 AND days since first_suggestion_date >= 14
- KnownChargePattern categories must exist in the family's YNAB budget
