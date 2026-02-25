# Feature Specification: Email-YNAB Smart Sync (PayPal, Venmo, Apple)

**Feature Branch**: `011-email-ynab-sync`
**Created**: 2026-02-25
**Status**: Draft
**Input**: User description: "Automated PayPal, Venmo, and Apple subscription categorization for YNAB — use the existing Gmail API integration to parse transaction confirmation emails from PayPal, Venmo, and Apple (App Store/iCloud/subscriptions), match them to YNAB transactions by date and amount, enrich transaction memos with actual merchant/service names (instead of generic 'PayPal' or 'Apple.com/bill'), and classify into appropriate YNAB budget categories. Same architecture as Feature 010 (Amazon-YNAB sync) — Gmail email parsing, LLM classification, memo enrichment, suggestion flow via WhatsApp. Should handle PayPal (merchant name buried in email), Venmo (person-to-person with notes), and Apple subscriptions (which just say 'APPLE.COM/BILL' in YNAB but the email has the actual app/service name). Nightly sync via n8n, same suggestion/auto-split graduation as Amazon sync."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Memo Enrichment & Category Suggestion (Priority: P1)

When PayPal, Venmo, or Apple transactions appear in the family's budget as generic charges ("PayPal", "APPLE.COM/BILL", "Venmo"), the bot automatically fetches the actual transaction details from confirmation emails, adds real merchant/service names to the transaction memos, classifies each into the appropriate budget category, and sends Erin a WhatsApp message with suggestions for her to approve or adjust.

This transforms three of the family's most opaque payee names into properly categorized, memo-enriched transactions — without Erin having to open her email, cross-reference charges, or manually edit YNAB.

**Why this priority**: PayPal, Venmo, and Apple are among the hardest transactions to categorize because the bank feed payee name tells you nothing about what was actually purchased. PayPal could be anything from a restaurant to a donation to an online store. "APPLE.COM/BILL" could be iCloud storage, a kids' game, or a music subscription. Without the email details, these transactions are effectively uncategorizable. This story alone delivers the core value.

**Independent Test**: Make a PayPal purchase, wait for the nightly sync, and verify the YNAB transaction memo now contains the actual merchant name and Erin receives a WhatsApp suggestion for the correct category.

**Acceptance Scenarios**:

1. **Given** a PayPal transaction for $45.00 has imported into YNAB with payee "PayPal" and no memo, **When** the sync runs, **Then** the transaction memo is updated with the actual merchant name (e.g., "DoorDash via PayPal") and Erin receives a message like: "Your $45.00 PayPal charge was to DoorDash — I'd categorize as Eating Out. Want me to apply? (yes/adjust/skip)"
2. **Given** an Apple transaction for $12.99 has imported into YNAB with payee "APPLE.COM/BILL", **When** the sync runs, **Then** the memo is updated with the actual subscription name (e.g., "iCloud+ 200GB") and the bot categorizes it directly as a recurring subscription without asking (known recurring charge)
3. **Given** a Venmo transaction for $30.00 has imported with payee "Venmo", **When** the sync runs, **Then** the memo is updated with the recipient name and payment note from the Venmo email (e.g., "To Sarah M. — dinner split") and Erin receives a category suggestion
4. **Given** Erin replies "yes" to a category suggestion, **When** the bot processes her reply, **Then** the transaction category is updated in YNAB to the suggested category
5. **Given** Erin replies "adjust" with a correction (e.g., "put it in Jason Fun Money"), **When** the bot processes her reply, **Then** the category is updated to the specified one and the mapping is saved for future use
6. **Given** the sync finds only one transaction for a provider and the bot is confident in its classification (known recurring charge or high-confidence match), **When** the sync runs, **Then** the bot categorizes it directly without asking and includes it in a brief summary: "Auto-categorized: $12.99 iCloud+ → Subscriptions"

---

### User Story 2 - Automated Nightly Sync (Priority: P2)

The sync runs automatically each night alongside the existing Amazon sync, processing any new PayPal, Venmo, or Apple transactions that appeared in YNAB that day. Erin wakes up to enriched memos and pending category suggestions in her WhatsApp — no manual trigger needed.

**Why this priority**: Manual syncing defeats the purpose. The value of this feature is that it works in the background, keeping YNAB accurate without effort. This story transforms US1 from a tool into a system.

**Independent Test**: After a day where PayPal/Venmo/Apple purchases were made, verify that the next morning Erin has WhatsApp messages with category suggestions for each new transaction, and all memos are already enriched.

**Acceptance Scenarios**:

1. **Given** the nightly sync is scheduled, **When** 2 new PayPal transactions and 1 new Apple transaction appeared in YNAB today, **Then** all 3 are enriched with memos and Erin receives a single consolidated WhatsApp message with any suggestions
2. **Given** no new PayPal/Venmo/Apple transactions appeared today, **When** the nightly sync runs, **Then** it completes silently without messaging Erin
3. **Given** a transaction was already synced in a previous run, **When** the nightly sync runs again, **Then** it skips already-processed transactions
4. **Given** the nightly sync encounters an error (e.g., Gmail token expired), **When** the error occurs, **Then** it logs the error, skips the sync gracefully, and retries the next night — it does not send Erin error messages

---

### User Story 3 - Auto-Categorize Mode (Priority: P3)

After Erin has used the suggestion-and-confirm flow (US1/US2) and the bot achieves high acceptance rates, the bot suggests enabling auto-categorize mode for these providers. In this mode, the bot applies categories automatically for high-confidence matches — using learned mappings from past approvals and known recurring charges.

**Why this priority**: This is the end-state goal but requires trust built through US1/US2. Recurring charges (Apple subscriptions, regular Venmo splits with the same people) are especially well-suited to auto-categorization since they repeat monthly.

**Independent Test**: Enable auto-categorize mode, wait for the next Apple subscription charge, and verify it was automatically categorized without any WhatsApp confirmation required.

**Acceptance Scenarios**:

1. **Given** auto-categorize mode is enabled, **When** a known recurring Apple subscription charges ($12.99 iCloud+ — same amount and merchant as last month), **Then** the bot categorizes it automatically and sends a brief summary: "Auto-categorized: $12.99 iCloud+ → Subscriptions. Reply 'undo' to revert."
2. **Given** auto-categorize mode is enabled but the bot encounters a new PayPal merchant it hasn't seen before, **When** the sync processes that transaction, **Then** it falls back to the suggestion flow for that specific transaction while auto-categorizing the known ones
3. **Given** Erin replies "undo" to an auto-categorization, **When** the bot processes the undo, **Then** the category is reverted and Erin can re-categorize manually
4. **Given** Erin says "turn off auto-categorize" or "go back to asking me", **When** the bot processes the command, **Then** auto-categorize mode is disabled and future syncs return to the suggestion-and-confirm flow

---

### Edge Cases

- What happens when a PayPal transaction is a refund (negative amount)? The bot should detect refund transactions, match them to the original purchase by amount and date proximity, and categorize the refund to the same category as the original charge. If the refund can't be matched, ask Erin.
- What happens when a Venmo payment is person-to-person with no merchant context (e.g., "paid Jason $20 — pizza")? The bot should use the payment note from the Venmo email to infer category. If the note is too vague (e.g., "thanks"), flag it for Erin with the recipient name and amount.
- What happens when the same Apple subscription amount changes (e.g., price increase from $9.99 to $10.99)? The bot should still recognize it as the same subscription by matching the service name from the email, even if the amount differs from the previous charge.
- What happens when a PayPal email contains a multi-item purchase (e.g., eBay order with 3 items)? The bot should extract all item details and suggest a split, similar to the Amazon multi-item flow.
- What happens when the Gmail OAuth token expires? The bot should detect the auth failure, log the error, and skip the sync silently — it does not send Erin technical error messages. The sync retries the next night and resumes automatically once the token is refreshed (same behavior as Amazon sync).
- What happens when a transaction amount doesn't match any email (e.g., PayPal instant transfer, Apple gift card reload)? The bot should tag the memo with "Unmatched [Provider] charge" and ask Erin to categorize via WhatsApp.
- What happens when Venmo is used to pay a business (e.g., a food truck or small shop)? The Venmo email should contain the business name — treat it like a merchant transaction, not a person-to-person payment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST search confirmation emails from PayPal (`service@paypal.com`, `paypal@mail.paypal.com`), Venmo (`venmo@venmo.com`), and Apple (`no_reply@email.apple.com`) and extract transaction details including merchant/recipient name, amount, date, and item descriptions where available
- **FR-002**: The system MUST match email-extracted transaction data to YNAB transactions using a ±3 day date window and exact penny amount matching (same algorithm as Amazon sync)
- **FR-003**: The system MUST update YNAB transaction memos with enriched details: actual merchant name for PayPal, recipient name + payment note for Venmo, subscription/service name for Apple — preserving any existing memo content
- **FR-004**: The system MUST classify each transaction into the family's existing YNAB budget categories using the enriched merchant/service details, with confidence scoring
- **FR-005**: The system MUST send Erin a WhatsApp message with suggested categories for transactions where confirmation is needed, allowing her to approve, adjust, or skip — consolidated into a single message per sync run
- **FR-006**: The system MUST auto-categorize high-confidence transactions without asking (known recurring subscriptions, previously approved merchant-to-category mappings) and include them in a brief summary
- **FR-007**: The system MUST track which transactions have already been processed to prevent duplicate syncs, using the same sync record mechanism as Amazon sync
- **FR-008**: The system MUST run on the existing nightly schedule and process all new PayPal, Venmo, and Apple transactions since the last sync
- **FR-009**: The system MUST handle refunds (negative amounts) by detecting them, matching to the original purchase when possible, and categorizing to the same category as the original charge
- **FR-010**: The system MUST learn from Erin's past approvals and corrections to improve future categorization accuracy, sharing the learned mappings across all email-synced providers
- **FR-011**: The system MUST support an auto-categorize mode that applies learned categories without confirmation, with an undo capability
- **FR-012**: The system MUST recognize known recurring charges (same merchant/service name + similar amount within 20%) and categorize them automatically after the first manual approval
- **FR-013**: The system MUST handle PayPal multi-item purchases by extracting individual item details from the email and suggesting a split across categories
- **FR-014**: The system MUST tag unmatched transactions (no corresponding email found) with "Unmatched [Provider] charge" in the memo and ask Erin to categorize via WhatsApp
- **FR-015**: The system MUST gracefully handle Gmail OAuth token expiration by logging the error, skipping the sync, and notifying that re-authentication is needed — without sending technical error details to Erin

### Key Entities

- **Email Transaction**: A parsed transaction from a PayPal, Venmo, or Apple confirmation email, containing provider type, merchant/recipient name, amount, date, item details (if available), and payment note (Venmo). The enriched merchant name is the primary input for category classification.
- **YNAB Transaction**: A financial transaction imported into YNAB from a bank/credit card, with payee, amount, date, memo, and category. PayPal transactions arrive as "PayPal", Venmo as "Venmo", and Apple as "APPLE.COM/BILL" or similar generic payee names.
- **Provider**: One of the three supported email transaction sources (PayPal, Venmo, Apple), each with distinct email formats, sender addresses, and data extraction patterns.
- **Category Mapping**: A learned association between a merchant/service name and a YNAB budget category. Built from Erin's approvals and corrections. Shared across all providers — if "DoorDash" is mapped to "Eating Out" via PayPal, the same mapping applies if DoorDash appears via Venmo.
- **Sync Record**: A log of which YNAB transactions have been matched, enriched, and/or categorized, preventing duplicate processing across sync runs. Extends the existing Amazon sync record mechanism.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 85% of PayPal, Venmo, and Apple transactions are matched to their corresponding emails and enriched with actual merchant/service names within 24 hours of appearing in YNAB
- **SC-002**: Category suggestions are accepted by Erin without modification at least 80% of the time after 2 weeks of use
- **SC-003**: The number of generic "PayPal", "Venmo", or "APPLE.COM/BILL" transactions left uncategorized in YNAB drops to fewer than 3 per month after 30 days
- **SC-004**: Erin spends less than 1 minute per week on PayPal/Venmo/Apple transaction categorization
- **SC-005**: Recurring charges (Apple subscriptions, regular Venmo payments) are auto-categorized correctly 95% of the time after 1 month of learned mappings
- **SC-006**: The sync process completes within 3 minutes and does not disrupt other bot functionality or the Amazon sync

## Clarifications

### Session 2026-02-25

- Q: Which Gmail accounts contain the PayPal/Venmo/Apple confirmation emails that correspond to YNAB transactions? → A: Jason's Gmail only (jbelk122@gmail.com). Transactions from Erin's separate PayPal/Venmo/Apple accounts (which email erin.tahoe@gmail.com) will appear as unmatched and be tagged for manual categorization.

## Assumptions

- Only Jason's Gmail (jbelk122@gmail.com) is searched for confirmation emails, using the existing Gmail API OAuth from Feature 010. Transactions originating from Erin's separate provider accounts will not have matching emails and will be handled as unmatched (tagged for manual categorization via WhatsApp)
- The family's existing YNAB categories are sufficient to cover these transactions — the bot maps into existing categories, not create new ones
- PayPal transactions in YNAB appear with payee containing "PayPal" or "PAYPAL"; Venmo with "Venmo" or "VENMO"; Apple with "APPLE.COM/BILL", "Apple.com", or similar
- The existing Amazon sync infrastructure (sync records, category mappings, suggestion flow, WhatsApp direct send) can be extended to support additional providers
- Most PayPal/Venmo/Apple transactions can be matched to emails using ±3 day date window and exact penny amount
- Apple subscriptions are relatively stable (same service, similar amount monthly) making them excellent candidates for auto-categorization after first approval
- Venmo payments include a payment note in the confirmation email that provides useful context for categorization

## Out of Scope

- Other payment providers (Zelle, Cash App, Google Pay) — this feature covers only PayPal, Venmo, and Apple
- Creating new YNAB budget categories — the bot maps into existing categories only
- Real-time transaction categorization — batch processing via nightly sync is sufficient
- Splitting Apple family sharing charges by family member — all Apple charges are treated as household expenses
- Venmo request/charge flows (only completed payments are processed)
- PayPal business account transactions — consumer personal account only
