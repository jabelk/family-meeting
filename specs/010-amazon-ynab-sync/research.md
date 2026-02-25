# Research: Amazon-YNAB Smart Sync

**Feature**: 010-amazon-ynab-sync | **Date**: 2026-02-24

## R1: Amazon Order Data Extraction

**Decision**: Use Gmail API to fetch Amazon order confirmation emails, then Claude to parse email HTML into structured order data.

**Rationale**: The original plan used the `amazon-orders` Python scraping library, but Amazon's JavaScript CAPTCHA/WAF bot detection blocked headless login from the Docker container. There is no official Amazon API for consumer purchase history (SP-API is seller-only). Gmail API is already configured with OAuth for Google Calendar, making this a zero-new-dependency approach. Amazon sends detailed order confirmation emails with all needed data.

**Previous approach (abandoned)**: `amazon-orders` v4.0.18 scraping library — blocked by Amazon's JavaScript authentication challenge. See https://amazon-orders.readthedocs.io/troubleshooting.html#captcha-blocking-login

**Alternatives considered**:
- Amazon SP-API: Seller-only, not consumer purchase history
- Browser extension approach: Requires user interaction, not automatable
- `amazon-orders` scraping library: Blocked by CAPTCHA/WAF on headless Docker environments
- Alexa APIs: Smart home only, no order data access
- Amazon order CSV export: Manual download required, not automatable

**Key findings — Gmail approach**:
- Google API OAuth already configured (`google-api-python-client`, `google-auth-oauthlib`)
- Search queries: `from:auto-confirm@amazon.com`, `from:shipment-tracking@amazon.com`, `from:returns@amazon.com`
- Order confirmation emails contain: order number, item names, quantities, per-item prices, subtotal, tax, shipping, delivery date
- Refund/return emails also available via Gmail search
- Use Claude to parse email HTML into structured data (handles template variations without code changes)
- Gmail API quota: 250 quota units per user per second (more than sufficient)
- Reference project: [gbrodman/order-tracking](https://github.com/gbrodman/order-tracking) — parses Amazon emails from Gmail via IMAP

**Email senders to search**:
- `auto-confirm@amazon.com` — order confirmations (item names, prices, order total)
- `shipment-tracking@amazon.com` — shipping notifications (tracking, delivery dates)
- `returns@amazon.com` — refund confirmations (refund amounts, items returned)
- `no-reply@amazon.com` — digital orders, Prime, Kindle purchases

**Risks**:
- Amazon email template changes could affect Claude parsing (mitigated: LLM handles variations)
- Gmail OAuth token expires every 7 days in testing mode (existing issue, same as Calendar)
- Email may arrive before/after YNAB transaction posts — handled by ±3 day matching window

## R2: YNAB Split Transaction API

**Decision**: Use YNAB PUT endpoint to update existing Amazon transactions with subtransactions.

**Rationale**: YNAB API supports updating a single transaction to become a split by providing a `subtransactions` array. This preserves the bank-imported transaction (maintaining the `import_id` link) while adding category splits. Preferable to delete+recreate which loses import linkage.

**Alternatives considered**:
- Delete and recreate: Loses import_id and cleared status, may cause duplicate detection issues
- Create alongside: Would result in duplicate transactions

**Key findings**:
- PUT `/budgets/{budget_id}/transactions/{transaction_id}` accepts `subtransactions` array
- Each subtransaction: `amount` (milliunits), `category_id`, `memo`, optional `payee_name`
- Subtransaction amounts must sum exactly to parent transaction amount
- **Critical limitation**: Once a transaction IS a split, subtransactions cannot be modified via API — must delete and recreate
- For undo: delete split transaction, recreate as single unsplit transaction with original category
- Milliunits format: `$87.42` = `87420`, outflows are negative: `-87420`
- Category/payee resolution uses UUIDs, not names — must look up via API first
- Rate limit: 200 requests/hour (sufficient for nightly batch of ~5-10 transactions)

**YNAB API endpoints needed**:
- GET `/budgets/{id}/transactions` — fetch Amazon transactions (payee filter)
- PUT `/budgets/{id}/transactions/{id}` — update memo, apply split
- GET `/budgets/{id}/categories` — resolve category names to UUIDs
- DELETE `/budgets/{id}/transactions/{id}` — for undo flow

## R3: Transaction Matching Strategy

**Decision**: Match by exact penny amount + ±3 day date window + Amazon payee pattern.

**Rationale**: Amazon charges may post 1-3 days after order placement. Amount matching is exact (to the penny) to avoid false positives — even common amounts like $9.99 are unlikely to overlap within a 3-day window from the same payee. Partial shipments are matched against shipment subtotals from the order data.

**Algorithm**:
1. Fetch YNAB transactions with payee containing "Amazon" or "AMZN" (last 30 days)
2. Fetch Amazon orders with `full_details=True` (last 30 days)
3. For each unprocessed YNAB transaction:
   a. Find Amazon orders where `grand_total` matches YNAB amount (exact penny) AND `order_placed_date` within ±3 days of YNAB transaction date
   b. If no match on grand_total, try shipment subtotals (partial shipment matching)
   c. If still no match, check known non-order charge patterns (Prime, Kindle, etc.)
   d. If truly unmatched, tag as "Unmatched Amazon charge"
4. Matched orders get memo enrichment + classification

**Edge cases handled**:
- Multiple orders same day/amount: Match by order of appearance, flag duplicates for manual review
- Partial shipments: Match shipment subtotals, not just order grand totals
- Refunds: Negative amounts matched against original order's grand_total or item price

## R4: Item Classification Approach

**Decision**: Use Claude Haiku 4.5 for item-to-category classification with a learning feedback loop.

**Rationale**: LLM classification handles the long tail of Amazon product names (e.g., "Novaalab Red Light Therapy Device" → Healthcare) that keyword-based rules can't. Haiku is fast (<1s) and cheap (~$0.001/classification). Past approvals/corrections stored locally create a growing knowledge base that improves accuracy.

**Classification flow**:
1. Check `category_mappings.json` for exact title match (instant, free)
2. Check for keyword-based match from learned patterns (e.g., "vitamin" → Healthcare)
3. If no cached match: call Claude Haiku with item title + family's YNAB category list + past mapping examples
4. Return category + confidence score (0-1)
5. Confidence < 0.7 → flag as uncertain in WhatsApp message

**Prompt template**:
```
Given the family's YNAB budget categories: {category_list}
And these past categorization decisions: {recent_mappings}
Classify this Amazon item: "{item_title}" (${price})
Return JSON: {"category": "...", "confidence": 0.0-1.0, "reasoning": "..."}
```

**Learning loop**:
- Erin approves: save title→category mapping
- Erin adjusts: save corrected mapping, note the correction
- Over time, fewer LLM calls needed as cache grows

## R5: Persistence Strategy

**Decision**: JSON files in `data/` directory for all sync state.

**Rationale**: Sync records, category mappings, and config are internal bot state — not user-facing data that benefits from Notion's UI. JSON files are simpler, faster, and don't consume Notion API quota. Follows existing pattern (`data/usage_counters.json` in discovery.py).

**Files**:
- `data/amazon_sync_records.json`: Map of YNAB transaction_id → {matched_order, status, timestamp}
- `data/category_mappings.json`: Map of item_title_normalized → {category, confidence, source}
- `data/amazon_sync_config.json`: {auto_split_enabled, acceptance_stats, last_sync}

**Atomic writes**: Use tmp-file + rename pattern (same as discovery.py counters).

## R6: Refund Handling

**Decision**: Match refunds to original purchases by amount + date proximity, reverse proportional split.

**Rationale**: Erin returns items regularly. Refunds appear as negative-amount "Amazon.com" transactions in YNAB. Matching to the original purchase allows automatic category assignment for the refund.

**Algorithm**:
1. Detect negative-amount Amazon transactions in YNAB
2. Search sync records for original purchase with matching amount (or matching item price for partial refunds)
3. If matched: apply refund to same category (or proportional split for multi-item returns)
4. If partial refund amount matches a specific item price in the original order: credit that item's category only
5. If no match found: ask Erin via WhatsApp which category to credit

## R7: Auto-Split Transition

**Decision**: Bot suggests auto-split activation after 80%+ unmodified acceptance rate over 2 weeks. Erin must confirm.

**Rationale**: Builds trust through demonstrated accuracy. The 80% threshold ensures the bot is genuinely good at categorizing before removing the human checkpoint.

**Tracking**:
- `amazon_sync_config.json` stores: total_suggestions, unmodified_accepts, modified_accepts, skips, date_of_first_suggestion
- After 14+ days since first suggestion AND 80%+ unmodified rate: bot sends "I've been getting your Amazon categories right 85% of the time — want me to start auto-splitting? You can always undo or turn it off."
- Erin confirms → `auto_split_enabled: true`
- In auto-split mode: still sends summary notification with undo option
