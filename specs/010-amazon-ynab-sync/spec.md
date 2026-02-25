# Feature Specification: Amazon-YNAB Smart Sync

**Feature Branch**: `010-amazon-ynab-sync`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Automated Amazon order categorization for YNAB — fetch Amazon order history, match to YNAB transactions, enrich memos with item details, and use AI to classify items into budget categories. Start with suggested splits (Level 2) then graduate to auto-split (Level 3). Incorporate YNAB best practices into the flow."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Memo Enrichment & Smart Suggestions (Priority: P1)

When Amazon transactions appear in the family's budget as generic "Amazon.com" charges, the bot automatically fetches the actual order details, adds item names to the transaction memos, classifies each item into the appropriate budget category, and sends Erin a WhatsApp message with a suggested split for her to approve or adjust.

This transforms Amazon from a budget black hole into properly categorized spending — without Erin having to open Amazon, cross-reference order numbers, or manually split transactions.

**Why this priority**: Amazon is the single hardest category to budget. The family averages $524/month across vitamins, kids toys, house supplies, and electronics all lumped into one "Amazon" line. Without item-level visibility, budget tracking is meaningless for this spending. This story alone delivers the core value.

**Independent Test**: Trigger a sync after an Amazon purchase has posted to YNAB. Verify the transaction memo now contains item names, and Erin receives a WhatsApp message suggesting how to split the charge across budget categories. Erin can approve, adjust, or skip.

**Acceptance Scenarios**:

1. **Given** an Amazon transaction for $87.42 has imported into YNAB with payee "Amazon.com" and no memo, **When** the sync runs, **Then** the transaction memo is updated with item names (e.g., "Vitamin D3, LEGO train set, phone charger") and Erin receives a message like: "Your $87.42 Amazon order had 3 items — I'd split it as $25 Healthcare, $43 Kids Toys, $18 Electronics. Want me to split it? (yes/adjust/skip)"
2. **Given** Erin replies "yes" to a split suggestion, **When** the bot processes her reply, **Then** the single Amazon transaction in YNAB is split into the suggested category amounts, each with the relevant item name in the memo
3. **Given** Erin replies "adjust" or provides a correction (e.g., "put the charger in Home instead"), **When** the bot processes her reply, **Then** the split is modified accordingly and applied
4. **Given** Erin replies "skip" or doesn't respond within 24 hours, **When** the timeout passes, **Then** the memo enrichment remains but no split is applied — the transaction stays in its current category
5. **Given** an Amazon order contains only one item, **When** the sync runs, **Then** the bot categorizes it directly without asking (single-item orders don't need split confirmation) and updates the memo
6. **Given** the bot suggests a category for an item but isn't confident (e.g., an ambiguous product name), **When** sending the suggestion, **Then** it flags the uncertain item: "Not sure about 'Novaalab' — Health & Beauty or Erin Shopping?"

---

### User Story 2 - Automated Nightly Sync (Priority: P2)

The sync runs automatically each night, processing any new Amazon transactions that appeared in YNAB that day. Erin wakes up to enriched memos and pending split suggestions in her WhatsApp — no manual trigger needed.

**Why this priority**: Manual syncing defeats the purpose. The value of this feature is that it works in the background, keeping YNAB accurate without effort. This story transforms US1 from a tool into a system.

**Independent Test**: After a day where Amazon purchases were made, verify that the next morning Erin has WhatsApp messages with split suggestions for each new Amazon transaction, and all memos are already enriched.

**Acceptance Scenarios**:

1. **Given** the nightly sync is scheduled, **When** 3 new Amazon transactions appeared in YNAB today, **Then** all 3 are enriched with memos and Erin receives suggestions for each in a single consolidated WhatsApp message (not 3 separate messages)
2. **Given** no new Amazon transactions appeared today, **When** the nightly sync runs, **Then** it completes silently without messaging Erin
3. **Given** a transaction was already synced and enriched in a previous run, **When** the nightly sync runs again, **Then** it skips already-processed transactions (no duplicate processing)
4. **Given** the nightly sync encounters an error fetching Amazon data, **When** the error occurs, **Then** it logs the error, skips the sync gracefully, and retries the next night — it does not send Erin error messages

---

### User Story 3 - Full Auto-Split Mode (Priority: P3)

After Erin has used the suggestion-and-confirm flow (US1/US2) and the bot achieves 80%+ unmodified acceptance rate over 2 weeks, the bot suggests enabling auto-split mode. Erin confirms to activate. In this mode, the bot applies splits automatically without asking — using the category mappings it has learned from her past approvals and corrections.

**Why this priority**: This is the end-state goal but requires trust built through US1/US2. Jumping straight to auto-split risks miscategorized spending going unnoticed. The approval flow in US1/US2 also trains the system on Erin's preferences.

**Independent Test**: Enable auto-split mode, make an Amazon purchase, wait for the nightly sync, and verify the transaction was automatically split into correct categories without any WhatsApp confirmation required.

**Acceptance Scenarios**:

1. **Given** auto-split mode is enabled, **When** a new Amazon transaction is synced, **Then** the bot applies the split automatically and sends a brief summary to Erin: "Auto-split your $87 Amazon order: $25 Healthcare, $43 Kids, $18 Home. Reply 'undo' to revert."
2. **Given** Erin replies "undo" to an auto-split notification, **When** the bot processes the undo, **Then** the split is reverted and the transaction returns to its original state, and Erin can re-categorize manually or provide corrections
3. **Given** auto-split mode is enabled but the bot encounters an item it can't classify with reasonable confidence, **When** the sync processes that order, **Then** it falls back to the suggestion flow for that specific transaction while auto-splitting the rest
4. **Given** Erin says "turn off auto-split" or "go back to asking me", **When** the bot processes the command, **Then** auto-split mode is disabled and future syncs return to the US1 suggestion-and-confirm flow

---

### User Story 4 - YNAB Best Practices Coaching (Priority: P4)

The bot incorporates YNAB best practices into the sync flow, teaching good budgeting habits through contextual guidance rather than separate lessons. When splitting transactions, it follows YNAB conventions (proper memo formatting, split transaction structure). When it notices patterns (e.g., recurring Subscribe & Save items), it suggests setting up dedicated budget categories or adjusting goals based on actual spending.

**Why this priority**: Making YNAB easier to maintain — not just dumping data into it — is the strategic goal. But the core sync must work first (US1-US3). This story adds the "smart advisor" layer that helps the family's budget evolve.

**Independent Test**: After several weeks of Amazon sync data, ask the bot "how are we doing on Amazon spending?" and verify it provides insights with YNAB best-practice recommendations.

**Acceptance Scenarios**:

1. **Given** the bot has processed 2+ weeks of Amazon transactions, **When** Erin asks "how are we doing on Amazon spending?", **Then** the bot breaks down Amazon spending by actual category (not just "Amazon") and compares to budget goals — e.g., "Your Amazon spending this month: $180 Healthcare (mostly vitamins), $120 Kids, $95 Home. Healthcare is within goal, Kids is $30 over."
2. **Given** the bot notices recurring Amazon purchases (e.g., monthly vitamin subscription), **When** suggesting a split, **Then** it adds a tip: "This looks like a monthly subscription — want me to set up a $25/mo Healthcare goal for recurring Amazon vitamins?"
3. **Given** Amazon spending in a category is consistently higher than the YNAB goal, **When** the monthly budget review happens, **Then** the bot flags it: "Your Amazon Home purchases have averaged $95/mo but your Home Repairs goal is $0 for Amazon items. Want to adjust?"
4. **Given** a large or unusual Amazon purchase occurs (e.g., $500+ electronics), **When** the sync processes it, **Then** the bot treats it as a one-time purchase and suggests whether it should come from an existing sinking fund or if the user wants to adjust this month's budget

---

### Edge Cases

- What happens when Amazon ships items from the same order separately (resulting in multiple charges that don't match a single order total)? The bot should handle partial shipments by matching individual charge amounts to shipment subtotals, not just order grand totals.
- What happens when Amazon issues a refund? (Frequent — Erin returns items regularly.) The bot should detect refund transactions (negative amounts with Amazon payee), match them to the original purchase by amount and date proximity, and reverse the original split proportionally. For partial refunds (returning 1 of 3 items), the bot should match the refund amount to the specific item and credit only that category. If the refund can't be matched to a specific original purchase, the bot should ask Erin which category to credit.
- What happens when a transaction amount doesn't match any Amazon order (e.g., gift card reload, Prime membership, digital purchase)? The bot should have fallback categories for known Amazon charge types (Prime → Subscriptions, Kindle → Entertainment). Truly unrecognizable charges get memo tagged "Unmatched Amazon charge" and Erin is asked to categorize via WhatsApp. After a few months of accumulated data, the bot should be able to suggest new YNAB categories based on emerging Amazon spending patterns and YNAB best practices.
- What happens when the Gmail OAuth token expires? (Google OAuth tokens in testing mode expire every 7 days.) The bot should detect the auth failure, notify Erin that the sync needs re-authentication (re-run OAuth flow on the NUC), and skip the sync gracefully until the token is refreshed.
- What happens when the same item could reasonably go in multiple categories (e.g., a kids' vitamin — Healthcare or Kids)? The bot should use the family's past categorization choices to break ties, and when no precedent exists, ask.
- What happens during high-volume periods (Prime Day, holiday shopping) when there might be 10+ Amazon transactions in a day? The bot should batch suggestions into a single consolidated message rather than spamming individual notifications.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST fetch Amazon order history including item-level details (title, price, quantity) and match orders to YNAB transactions using a ±3 day date window and exact penny amount matching
- **FR-002**: The system MUST update YNAB transaction memos with item names from matched Amazon orders, preserving any existing memo content
- **FR-003**: The system MUST classify each Amazon item into the family's existing YNAB budget categories using the item title, with confidence scoring
- **FR-004**: The system MUST send Erin a WhatsApp message with suggested category splits for multi-item Amazon transactions, allowing her to approve, adjust, or skip
- **FR-005**: The system MUST split YNAB transactions into sub-transactions by category when Erin approves a suggestion, following YNAB's split transaction format (each sub-transaction gets the item name as memo, category assignment, and proportional amount including tax/shipping)
- **FR-006**: The system MUST handle single-item Amazon orders by categorizing directly without requiring confirmation
- **FR-007**: The system MUST track which transactions have already been processed to prevent duplicate syncs
- **FR-008**: The system MUST run on a configurable schedule (default: nightly) and process all new Amazon transactions since the last sync
- **FR-009**: The system MUST consolidate multiple transaction suggestions into a single WhatsApp message when several Amazon transactions are pending
- **FR-010**: The system MUST distribute tax and shipping costs proportionally across items when splitting a transaction
- **FR-011**: The system MUST support an auto-split mode that applies categorization without confirmation, with an undo capability
- **FR-012**: The system MUST learn from Erin's past approvals and corrections to improve future categorization accuracy
- **FR-013**: The system MUST handle Amazon refunds (a frequent occurrence) by detecting negative-amount Amazon transactions, matching them to the original purchase when possible, and categorizing the refund to the same category as the original split — including reversing the proportional split if the original transaction was split across multiple categories
- **FR-014**: The system MUST recognize non-order Amazon charges (Prime membership, Kindle purchases, gift card reloads) and categorize them appropriately without requiring order matching. For truly unrecognizable charges, the system MUST tag the memo with "Unmatched Amazon charge" and ask Erin to categorize manually via WhatsApp
- **FR-015**: The system MUST gracefully handle Gmail OAuth token expiration by logging the error, notifying Erin that the sync is paused until re-authentication, and skipping the sync run without sending error details
- **FR-016**: The system MUST follow YNAB best practices: proper memo formatting (concise item descriptions), clean split structure, and never creating categories that don't already exist in the user's budget

### Key Entities

- **Amazon Order**: A purchase from Amazon containing one or more items, with order number, date, total, payment method, and shipping details. Orders may ship in multiple packages resulting in separate charges.
- **Amazon Item**: An individual product within an order, with title, price, quantity, and seller. The item title is the primary input for category classification.
- **YNAB Transaction**: A financial transaction imported into YNAB from a bank/credit card, with payee, amount, date, memo, and category. Amazon transactions arrive as generic "Amazon.com" charges.
- **Category Mapping**: A learned association between Amazon item characteristics (title keywords, price range, seller) and YNAB budget categories. Built from Erin's approvals and corrections over time.
- **Sync Record**: A log of which YNAB transactions have been matched, enriched, and/or split, preventing duplicate processing across sync runs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of Amazon transactions are matched to their corresponding orders and enriched with item details within 24 hours of appearing in YNAB
- **SC-002**: Category suggestions are accepted by Erin without modification at least 80% of the time after 2 weeks of use
- **SC-003**: The number of "Uncategorized" or generic "Amazon" transactions in YNAB drops to near zero (fewer than 2 per month unresolved after 7 days)
- **SC-004**: Erin spends less than 1 minute per week on Amazon transaction categorization (compared to the current approach of ignoring it entirely or spending 15+ minutes cross-referencing)
- **SC-005**: Amazon spending is accurately reflected across real budget categories (Healthcare, Kids, Home, etc.) enabling meaningful budget-vs-actual comparison for those categories
- **SC-006**: The sync process completes within 5 minutes and does not disrupt other bot functionality

## Clarifications

### Session 2026-02-24

- Q: What transaction matching tolerance should be used (date window and amount precision)? → A: ±3 day date window + exact penny amount matching
- Q: How should the transition from suggestion mode to auto-split mode work? → A: Bot suggests enabling auto-split after 80%+ unmodified acceptance rate over 2 weeks; Erin must confirm to activate
- Q: How should unmatched Amazon transactions (no order match, not a recognized charge type) be handled? → A: Tag memo with "Unmatched Amazon charge" and ask Erin via WhatsApp to categorize manually. Plan to revisit category structure after a few months of data — LLM can suggest new categories based on YNAB best practices and emerging spending patterns.

### Session 2026-02-25 — Data Source Pivot

- Q: How should the system fetch Amazon order data? → A: **Gmail API** (not `amazon-orders` scraping library)
- **Reason for pivot**: The `amazon-orders` Python library relies on scraping Amazon.com, which is blocked by Amazon's JavaScript CAPTCHA/WAF bot detection. There is no official Amazon API for consumer purchase history (SP-API is seller-only, Alexa APIs don't expose order data). Amazon order confirmation emails sent to Gmail contain all needed data: order numbers, item names, quantities, prices, shipping costs, and delivery dates. Refund/return emails are also available.
- **Benefits of Gmail approach**: (1) Google API OAuth already configured with `google-api-python-client`, (2) no bot detection issues, (3) Amazon emails include structured order data, (4) refund/return emails are also searchable, (5) more reliable long-term than web scraping
- **Implementation change**: Replace `get_amazon_orders()` (which used `amazon-orders` library) with Gmail API search for Amazon emails (`from:auto-confirm@amazon.com`, `from:shipment-tracking@amazon.com`, etc.), then use Claude to parse email HTML into structured order data. The rest of the pipeline (matching, classification, splitting, suggestions) remains unchanged.
- **Removed**: `amazon-orders>=4.0.18` from requirements.txt, `AMAZON_USERNAME`/`AMAZON_PASSWORD`/`AMAZON_OTP_SECRET_KEY` env vars no longer needed, Dockerfile C build deps (gcc/libjpeg/zlib) removed

## Assumptions

- The family uses a single Amazon account for all household purchases
- Amazon order confirmation emails are sent to Jason's Gmail (jbelk122@gmail.com), which already has Google API OAuth configured
- The family's existing YNAB categories are sufficient to cover Amazon purchases — the bot should map into existing categories, not create new ones
- YNAB's API supports split transactions (confirmed: YNAB API supports sub-transactions on a single transaction)
- Amazon order data is extracted from Gmail order confirmation/shipping/refund emails using Claude to parse HTML into structured data
- Most Amazon transactions can be matched to orders using ±3 day date window and exact penny amount, though partial shipments are matched against shipment subtotals rather than order grand totals
- The family is comfortable with a 24-hour delay between purchase and categorization (nightly sync)

## Out of Scope

- Syncing with other retailers (Costco, Target, Walmart) — this feature is Amazon-specific
- Creating new YNAB budget categories at launch — the bot maps into existing categories only. After a few months of data, category structure recommendations may be revisited (future enhancement)
- Amazon business/seller accounts — consumer purchase history only
- Real-time transaction categorization (at time of purchase) — batch processing via nightly sync is sufficient
- Amazon return processing beyond refund categorization — the bot doesn't track return shipping or replacement orders
- Budget goal recommendations based on Amazon data (covered partially in US4 but full budget advisory is a separate feature — see specs/009-ynab-budget-rebuild)
