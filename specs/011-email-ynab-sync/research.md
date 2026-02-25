# Research: Email-YNAB Smart Sync

## R1: Email Sender Addresses by Provider

**Decision**: Use the following Gmail search filters per provider:
- **PayPal**: `from:service@paypal.com OR from:paypal@mail.paypal.com` — covers payment receipts and payment confirmations
- **Venmo**: `from:venmo@venmo.com` — covers payment sent/received notifications
- **Apple**: `from:no_reply@email.apple.com` — covers App Store receipts, subscription renewals, iCloud billing

**Rationale**: These are the primary transactional sender addresses. PayPal has two common senders — `service@paypal.com` for payment receipts and `paypal@mail.paypal.com` for notifications. The Gmail API search supports OR syntax in the `q` parameter.

**Alternatives considered**:
- Broader wildcard search (`from:*@paypal.com`) — rejected because it would include marketing/promo emails
- Adding `from:noreply@venmo.com` — this is used for marketing, not transactions

## R2: Extending vs Duplicating Amazon Sync Infrastructure

**Decision**: Create a new `src/tools/email_sync.py` module that imports shared functions from `amazon_sync.py` rather than duplicating code or creating an abstract base.

**Rationale**: The Amazon sync module has stabilized in production. Refactoring it into an abstract base class would risk breaking working code. Instead, `email_sync.py` imports the utilities it needs (`_get_gmail_service`, `_extract_html_body`, `_strip_html`, `classify_item`, category mapping functions, sync record functions) and implements provider-specific parsing logic. This follows the constitution's "small surface area" principle.

**Alternatives considered**:
- Abstract `BaseEmailSync` class — rejected: over-engineering for 2 modules, increases complexity
- Adding providers to `amazon_sync.py` — rejected: file is already 1648 lines, would become unwieldy
- Shared `email_utils.py` module — viable long-term, but premature; import directly for now

## R3: Sync Record Sharing Strategy

**Decision**: Reuse the existing `amazon_sync_records.json` for all providers. Add a `provider` field to SyncRecord to distinguish Amazon/PayPal/Venmo/Apple records. The `is_transaction_processed()` check remains YNAB-transaction-ID-based (provider-agnostic).

**Rationale**: A YNAB transaction can only be from one provider (the payee name determines this). Using a single sync records file simplifies the deduplication logic — we just check by YNAB transaction ID regardless of provider. Adding a `provider` field enables filtering for reporting/debugging.

**Alternatives considered**:
- Separate JSON files per provider — rejected: more files to manage, complicates cross-provider reporting
- Database (SQLite) — rejected: JSON files work well at this scale (<100 records/month), lower complexity

## R4: Category Mapping Sharing

**Decision**: Share a single `category_mappings.json` across all providers. The mapping key is the normalized merchant/item title, not provider-specific. If "DoorDash" is approved as "Eating Out" via PayPal, the same mapping applies if DoorDash appears via Venmo.

**Rationale**: Merchants are cross-provider — the same restaurant could appear via PayPal or Venmo. Sharing mappings accelerates learning and reduces Erin's approval burden. The `source` field on CategoryMapping already tracks provenance.

**Alternatives considered**:
- Provider-scoped mappings — rejected: the same merchant can appear via different providers, would require duplicate approvals

## R5: YNAB Payee Name Patterns

**Decision**: Filter YNAB transactions using these payee patterns:
- **PayPal**: payee contains "paypal" (case-insensitive) — covers "PayPal", "PAYPAL", "Paypal *MerchantName"
- **Venmo**: payee contains "venmo" (case-insensitive)
- **Apple**: payee contains "apple.com" or "apple" (case-insensitive) — covers "APPLE.COM/BILL", "Apple.com", "Apple Services"
- **Exclude**: Skip transactions already processed (via sync records) or already containing "amazon"/"amzn" (handled by Feature 010)

**Rationale**: YNAB imports transactions with varying payee name formats depending on the bank feed. Using case-insensitive substring matching (same as Amazon sync's "amazon"/"amzn" filter) handles all known variations.

**Alternatives considered**:
- Exact payee match — rejected: too brittle, bank feeds format payee names inconsistently
- Regex patterns — rejected: substring match is simpler and sufficient

## R6: Nightly Sync Orchestration

**Decision**: Add a new n8n endpoint `POST /api/v1/email/sync` that runs immediately after the existing Amazon sync. The n8n workflow chains: Amazon sync (10pm) → Email sync (10:05pm, 5-minute delay to avoid overlap).

**Rationale**: Separate endpoints allow independent monitoring, error isolation, and scheduling flexibility. A 5-minute gap ensures the Amazon sync finishes before the email sync starts (Amazon sync takes up to 3 minutes for large batches). Both send results directly to Erin via WhatsApp.

**Alternatives considered**:
- Single combined endpoint — rejected: complicates error handling (one provider failure shouldn't block others), harder to debug
- Same time with locking — rejected: adds complexity, race conditions
- Extend existing Amazon endpoint — rejected: violates single-responsibility, makes the Amazon sync code responsible for other providers

## R7: Recurring Charge Detection (FR-012)

**Decision**: After the first manual approval for a merchant/service, auto-categorize future transactions from the same merchant when: (a) the merchant name matches (normalized), and (b) the amount is within ±20% of the previous charge. This uses the existing CategoryMapping with `source: "user_approved"` and `confidence >= 0.9`.

**Rationale**: Apple subscriptions and regular Venmo payments repeat with predictable amounts. The 20% tolerance handles minor price changes (tax adjustments, subscription tier changes). The first-approval requirement builds trust per US3 spec.

**Alternatives considered**:
- Exact amount match only — rejected: subscription price changes would break detection
- Time-based recurrence (monthly check) — rejected: adds complexity, amount-based matching is sufficient
