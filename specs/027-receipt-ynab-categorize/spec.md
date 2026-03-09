# Feature Specification: Receipt Photo → YNAB Categorization

**Feature Branch**: `027-receipt-ynab-categorize`
**Created**: 2026-03-09
**Status**: Draft
**Input**: GitHub issue #27 — Receipt/Purchase Photo → YNAB Categorization

## User Scenarios & Testing

### User Story 1 - Receipt Photo Categorization (Priority: P1)

Erin or Jason photos a receipt and sends it to the bot. The bot extracts store name, date, line items, and total from the image. It then matches the receipt to an existing uncategorized YNAB transaction by amount and payee, suggests a budget category based on existing category mappings, and asks for confirmation before updating YNAB.

**Why this priority**: This is the core value — turning a photo into a categorized YNAB transaction. Jason had $264 in uncategorized transactions; Erin already tells the bot category rules like "glue sticks are kids toys." Photos are faster than typing.

**Independent Test**: Send a receipt photo to the bot. Confirm it extracts the store, total, and items. Confirm it finds the matching YNAB transaction and suggests the right category. Approve and confirm the transaction is updated in YNAB.

**Acceptance Scenarios**:

1. **Given** a clear receipt photo is sent, **When** the bot processes it, **Then** it extracts store name, date, line items with amounts, and total, and presents them to the user for review.
2. **Given** extracted receipt data matches an uncategorized YNAB transaction (by amount and payee within a date window), **When** the bot presents the match, **Then** it suggests a category based on existing mappings and asks for confirmation.
3. **Given** the user confirms the categorization, **When** the bot processes the approval, **Then** it updates the YNAB transaction category and confirms success.
4. **Given** the user rejects the suggested category, **When** they provide a different category, **Then** the bot uses their choice, updates YNAB, and learns the new mapping for future use.

---

### User Story 2 - No YNAB Match Handling (Priority: P2)

When the bot extracts receipt data but can't find a matching YNAB transaction (timing delays, pending charges, amount mismatch), it still provides value by recording the categorization for later matching or simply confirming the extracted data.

**Why this priority**: Receipts often arrive before transactions post to YNAB (credit card pending periods). The bot should still be useful even when it can't auto-match.

**Independent Test**: Send a receipt photo where no matching YNAB transaction exists. Confirm the bot extracts data, explains no match was found, and offers to remember it for later or simply confirms the extraction.

**Acceptance Scenarios**:

1. **Given** a receipt photo is sent but no matching YNAB transaction exists, **When** the bot processes it, **Then** it still extracts and displays the receipt data and informs the user no matching transaction was found.
2. **Given** no YNAB match is found, **When** the bot informs the user, **Then** it offers to save the categorization so it can be applied when the transaction appears.
3. **Given** multiple YNAB transactions could match (same store, similar amount, same day), **When** the bot finds ambiguous matches, **Then** it presents the options and asks the user to pick the correct one.

---

### User Story 3 - Multi-Item Receipt Splitting (Priority: P3)

For receipts with items spanning multiple budget categories (e.g., Costco run with groceries, household supplies, and kids' items), the bot can suggest splitting across categories or let the user assign the dominant category.

**Why this priority**: Split transactions are an advanced YNAB feature. Most receipts map to a single category. This adds power-user value but isn't essential for MVP.

**Independent Test**: Send a receipt with mixed-category items (e.g., groceries + toiletries from Target). Confirm the bot identifies the mix and offers to split or assign a single category.

**Acceptance Scenarios**:

1. **Given** a receipt contains items from clearly different budget categories, **When** the bot analyzes it, **Then** it identifies the category mix and asks whether the user wants to split or use a single category.
2. **Given** the user chooses to split, **When** they confirm the split amounts, **Then** the bot creates a split transaction in YNAB with the correct sub-amounts per category.
3. **Given** the user chooses a single category, **When** they confirm, **Then** the bot categorizes the full amount under that one category.

---

### Edge Cases

- **Blurry or partial receipt**: Bot should gracefully handle unreadable images — inform the user it couldn't extract enough data and ask for a clearer photo.
- **Receipt total doesn't match any YNAB transaction**: Amount rounding, tax differences, or timing. Bot should search with a small tolerance (e.g., within $1) and wider date range (up to 7 days).
- **Multiple transactions at same store on same day**: Present all candidates and let the user pick.
- **Non-receipt images**: User sends a random photo — bot should recognize it's not a receipt and respond naturally instead of forcing extraction.
- **Already-categorized transaction**: If the matching YNAB transaction already has a category, inform the user and ask if they want to re-categorize.
- **Store name variations**: "WHOLEFDS MKT" on a receipt should match "Whole Foods" in YNAB — fuzzy matching needed.

## Requirements

### Functional Requirements

- **FR-001**: System MUST extract store name, date, individual line items with prices, and total amount from a receipt photo.
- **FR-002**: System MUST search YNAB for uncategorized transactions matching the receipt's total amount and approximate payee name within a configurable date window (default: 7 days).
- **FR-003**: System MUST suggest a budget category for the transaction based on existing category mappings (from the category mapping store used by Amazon/email sync).
- **FR-004**: System MUST wait for user confirmation before updating any YNAB transaction.
- **FR-005**: System MUST update the YNAB transaction category upon user approval.
- **FR-006**: System MUST learn new category mappings when the user provides a correction — storing them for future auto-categorization.
- **FR-007**: System MUST handle the case where no matching YNAB transaction is found by displaying extracted data and informing the user.
- **FR-008**: System MUST use fuzzy matching for payee names (receipt abbreviations vs. YNAB payee names).
- **FR-009**: System MUST support split transactions across multiple YNAB categories when the user requests it.
- **FR-010**: System MUST gracefully handle unreadable or non-receipt images with a helpful message.
- **FR-011**: System MUST use the most accurate available image recognition service for receipt extraction, as selected during implementation planning.

### Key Entities

- **Receipt Extraction**: Store name, date, line items (name + price), subtotal, tax, total. Extracted from photo.
- **YNAB Transaction Match**: Links an extracted receipt to an existing YNAB transaction by amount, payee, and date proximity.
- **Category Mapping**: Maps store names and item descriptions to YNAB budget categories. Shared with existing Amazon/email sync mappings.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 90% of clear receipt photos are correctly extracted (store name, total, and at least the main items) on the first attempt.
- **SC-002**: Matching a receipt to the correct YNAB transaction succeeds at least 80% of the time when the transaction exists.
- **SC-003**: End-to-end flow (photo → categorized transaction) completes in under 30 seconds.
- **SC-004**: Users categorize receipts via photo at least 3x faster than manually finding and categorizing in the YNAB app.
- **SC-005**: Category suggestion accuracy reaches 85% or higher after 2 weeks of use (based on user confirmations vs. corrections).

## Assumptions

- YNAB API supports updating transaction categories (write access already established in the codebase).
- Existing category mappings from Amazon/email sync can be reused for receipt categorization.
- The image recognition service (to be selected in planning) can handle standard US retail receipt formats — thermal paper receipts, credit card receipts, and digital receipt screenshots.
- Users will primarily send photos of receipts from their phone camera or screenshots of digital receipts.
- The bot already handles image messages through the WhatsApp pipeline — no new image ingestion infrastructure needed.
- The user prefers the most accurate image recognition available; an alternative to the current vision model may be used if it performs better on receipt text extraction (user noted preference based on experience).

## Out of Scope

- Automatic receipt scanning without user initiation (e.g., watching email for digital receipts — that's the email sync feature).
- Creating new YNAB transactions from receipts (only categorizing existing ones).
- Multi-currency support beyond USD.
- Receipt archival or storage (the photo stays in WhatsApp chat history).
- Integration with receipt-specific OCR services or dedicated receipt scanning apps.
- Batch processing of multiple receipts in a single message.
