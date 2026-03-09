# Tasks: Receipt Photo → YNAB Categorization

**Input**: Design documents from `/specs/027-receipt-ynab-categorize/`
**Prerequisites**: spec.md (no plan.md needed — feature extends existing YNAB + image patterns)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Add config for OpenAI vision (user prefers OpenAI over Claude for receipt OCR). OpenAI SDK already installed (`openai>=1.60.0`).

- [x] T001 Add `OPENAI_API_KEY` config var to src/config.py. `os.environ.get("OPENAI_API_KEY", "")`. Add to `OPTIONAL_GROUPS` under a "Receipt OCR" group. This key is already used by src/transcribe.py for Whisper — just ensure it's exported from config.py if not already.

---

## Phase 2: Foundational

**Purpose**: Create the receipt extraction tool that all user stories depend on.

- [x] T002 Create src/tools/receipt.py with the receipt extraction function. Add `async extract_receipt(image_base64: str, mime_type: str) -> dict` that calls the OpenAI `gpt-4o` vision API to extract receipt data. Use the same OpenAI client pattern as src/transcribe.py. Prompt: "Extract all data from this receipt image. Return JSON with: store_name, date (YYYY-MM-DD), line_items (array of {name, price}), subtotal, tax, total. If you cannot read the receipt clearly, set 'error' field explaining why." Parse the JSON response. Return dict with keys: `store_name`, `date`, `line_items`, `subtotal`, `tax`, `total`. On failure (blurry, not a receipt), return `{"error": "description"}`. Import OPENAI_API_KEY from src/config.py.
- [x] T003 Add `match_receipt_to_ynab(store_name: str, total: float, date: str) -> list[dict]` function to src/tools/receipt.py. Import `search_transactions` from src/tools/ynab. Search YNAB for uncategorized transactions: (1) Call `search_transactions(uncategorized_only=True, since_date=date_minus_7_days)`. (2) Filter results by amount match (within $1.00 tolerance of receipt total). (3) Fuzzy match payee name against store_name (use simple substring/lowercase containment — e.g., "WHOLEFDS" matches "Whole Foods"). (4) Return list of matching transactions sorted by date proximity, each with `{id, payee, amount, date, category}`. Return empty list if no matches.
- [x] T004 Add `suggest_category(store_name: str, line_items: list[dict]) -> dict` function to src/tools/receipt.py. Import `load_category_mappings` from src/tools/amazon_sync. (1) Normalize store_name (lowercase, strip). (2) Check category_mappings for exact or substring match on store_name. (3) If no store match, check mappings against individual line item names. (4) If still no match, use Claude Haiku 4.5 (same pattern as amazon_classification in src/tools/amazon_sync.py — import anthropic, use `render_template` or inline prompt) to classify based on store_name + top line items. (5) Return `{"category_name": str, "category_id": str, "confidence": float, "source": "cached"|"llm"}`.

**Checkpoint**: Receipt extraction and YNAB matching infrastructure ready.

---

## Phase 3: User Story 1 — Receipt Photo Categorization (Priority: P1) MVP

**Goal**: User sends a receipt photo → bot extracts data, matches YNAB transaction, suggests category, updates on confirmation.

**Independent Test**: Send a receipt photo. Confirm extraction, YNAB match, category suggestion, and update on approval.

### Implementation for User Story 1

- [x] T005 [US1] Add `process_receipt(image_base64: str, mime_type: str) -> str` async function to src/tools/receipt.py. This is the main tool function Claude will call. Steps: (1) Call `await extract_receipt(image_base64, mime_type)`. (2) If error, return friendly message asking for clearer photo. (3) Call `match_receipt_to_ynab(store_name, total, date)`. (4) Call `suggest_category(store_name, line_items)`. (5) Format a response string showing: extracted receipt summary (store, date, total, items), YNAB match status (found/not found with transaction details), and suggested category. (6) If match found, include instructions: "Reply 'yes' to categorize as {category}, or tell me a different category." (7) Store pending receipt state in a module-level dict `_pending_receipts` keyed by phone number: `{transaction_id, category_name, category_id, store_name}`. Return the formatted string.
- [x] T006 [US1] Add `confirm_receipt_categorization(phone: str, category_override: str = "") -> str` async function to src/tools/receipt.py. (1) Check `_pending_receipts` for this phone. If none, return "No pending receipt to categorize." (2) If category_override provided, use that category instead (look up category_id from YNAB budget categories). (3) Call `recategorize_transaction(payee, amount, date, category_name)` from src/tools/ynab. (4) Save the mapping via `save_category_mapping()` from src/tools/amazon_sync (with source="user_approved" or "user_corrected" if override). (5) Clear pending state. (6) Return confirmation message.
- [x] T007 [P] [US1] Register `process_receipt` tool in src/assistant.py. Add to TOOLS list: `{"name": "process_receipt", "description": "...", "input_schema": {"type": "object", "properties": {}, "required": []}}` — no parameters needed since it uses the current image from the conversation. Add to TOOL_FUNCTIONS dict: `"process_receipt": lambda **kw: receipt.process_receipt(_current_image_data["base64"], _current_image_data["mime_type"])`. Import `src.tools.receipt as receipt` at top.
- [x] T008 [P] [US1] Register `confirm_receipt_categorization` tool in src/assistant.py. Add to TOOLS list with input_schema: `{"category_override": {"type": "string", "description": "Different category name if user rejects the suggestion. Leave empty to confirm suggested category."}}`. Add to TOOL_FUNCTIONS: `"confirm_receipt_categorization": lambda **kw: receipt.confirm_receipt_categorization(kw.get("phone", ""), kw.get("category_override", ""))`. Note: phone will need to come from conversation context — pass it via the tool call or use _current_phone module var.
- [x] T009 [P] [US1] Add tool descriptions to src/prompts/tools/ynab.md (or create src/prompts/tools/receipt.md). Add `## process_receipt` and `## confirm_receipt_categorization` sections describing when/how to use each tool.
- [x] T010 [US1] Create src/prompts/system/10-receipt-categorization.md with rules for receipt photo handling. Rules: (1) When a user sends a photo that appears to be a receipt, automatically call `process_receipt` to extract and match. (2) Present the extracted data and suggested category clearly. (3) Wait for user confirmation before calling `confirm_receipt_categorization`. (4) If user provides a different category, pass it as `category_override`. (5) If no YNAB match found, inform user and offer to remember for later. (6) Don't force receipt extraction on non-receipt images (food photos, screenshots of other things).
- [ ] T011 [US1] Verify US1 works: send a receipt photo to the bot. Confirm: (1) OpenAI vision extracts store, total, items correctly, (2) YNAB match found (if transaction exists), (3) category suggested, (4) on confirmation, YNAB transaction updated. Test with a blurry photo — confirm graceful error.

**Checkpoint**: Core receipt → YNAB flow works. MVP complete.

---

## Phase 4: User Story 2 — No YNAB Match Handling (Priority: P2)

**Goal**: Graceful handling when receipt doesn't match any YNAB transaction.

**Depends on**: US1 (needs receipt extraction and matching in place)

**Independent Test**: Send a receipt photo with no matching YNAB transaction. Confirm bot extracts data, explains no match, offers alternatives.

### Implementation for User Story 2

- [x] T012 [US2] Add `_pending_unmatched` dict to src/tools/receipt.py for storing unmatched receipts. When `process_receipt` finds no YNAB match, store `{store_name, total, date, category_suggestion, line_items}` in `_pending_unmatched[phone]`. Update the response message to say "No matching YNAB transaction found yet. I'll remember this — if the transaction appears later, just ask me to check again." Also handle multiple matches (US2 acceptance scenario 3): if more than one YNAB transaction matches, list them numbered and ask user to pick.
- [x] T013 [US2] Add `retry_receipt_match(phone: str) -> str` function to src/tools/receipt.py. Check `_pending_unmatched[phone]`. If exists, re-run `match_receipt_to_ynab()` with stored data. If match found now, proceed to category suggestion. If still no match, inform user.
- [x] T014 [P] [US2] Register `retry_receipt_match` tool in src/assistant.py. Add tool entry and lambda. Add tool description to prompts.
- [x] T015 [US2] Update src/prompts/system/10-receipt-categorization.md with rules for no-match scenarios: (1) When no match found, reassure user the transaction may still be pending. (2) If user asks to "check again" or "try matching receipt", call `retry_receipt_match`. (3) When multiple matches found, present numbered list and ask user to pick.
- [ ] T016 [US2] Verify US2 works: send receipt with no matching YNAB transaction. Confirm: (1) data extracted, (2) "no match" message with helpful context, (3) "check again" re-runs match. Test multiple matches — confirm user can pick.

**Checkpoint**: Receipt flow handles both matched and unmatched scenarios gracefully.

---

## Phase 5: User Story 3 — Multi-Item Receipt Splitting (Priority: P3)

**Goal**: Split one receipt across multiple YNAB budget categories.

**Depends on**: US1 (needs receipt extraction and categorization flow)

**Independent Test**: Send a receipt with mixed-category items. Confirm bot identifies the mix and offers to split or use single category.

### Implementation for User Story 3

- [x] T017 [US3] Add `analyze_receipt_categories(line_items: list[dict]) -> dict` function to src/tools/receipt.py. For each line item, call `suggest_category()` to classify. Group items by category. Return `{"categories": [{"name": str, "items": list, "subtotal": float}], "is_mixed": bool}`. Set `is_mixed = True` if items span 2+ distinct categories.
- [x] T018 [US3] Update `process_receipt` in src/tools/receipt.py to call `analyze_receipt_categories()` when line items are present. If `is_mixed`, format response showing items grouped by category with subtotals. Add message: "This receipt has items in multiple categories. Reply 'split' to split the transaction, or just confirm to categorize all as {dominant_category}."
- [x] T019 [US3] Add `split_receipt_transaction(phone: str) -> str` async function to src/tools/receipt.py. Check `_pending_receipts[phone]`. Call `split_transaction(transaction_id, subtransactions)` from src/tools/ynab where subtransactions is the list of `{category_id, amount}` from the analyzed categories. Return confirmation with breakdown.
- [x] T020 [P] [US3] Register `split_receipt_transaction` tool in src/assistant.py. Add tool entry and lambda. Add tool description to prompts.
- [x] T021 [US3] Update src/prompts/system/10-receipt-categorization.md with split rules: when receipt has mixed categories, offer split option. If user says "split", call `split_receipt_transaction`.
- [ ] T022 [US3] Verify US3 works: send a receipt with items from different categories (e.g., groceries + household). Confirm: (1) items grouped by category, (2) "split" option offered, (3) split transaction created in YNAB. Test single-category confirmation — confirm no unnecessary split offer.

**Checkpoint**: Full receipt lifecycle — extract, match, categorize, split.

---

## Phase 6: Polish & Validation

**Purpose**: Final checks and deployment.

- [x] T023 Run `ruff check src/` and `ruff format --check src/` — fix any issues in new/modified files.
- [x] T024 Run `pytest tests/` — verify all existing tests still pass. Update test_prompts.py tool count if needed.
- [ ] T025 Commit all changes, push to branch, create PR for merge to main.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 — Config var. Quick.
- **Foundational (Phase 2)**: T002-T004 — Receipt extraction + YNAB matching + category suggestion. Blocks all user stories.
- **US1 (Phase 3)**: T005-T011 — Depends on Phase 2. Core receipt → YNAB flow.
- **US2 (Phase 4)**: T012-T016 — Depends on US1 (needs process_receipt flow). No-match handling.
- **US3 (Phase 5)**: T017-T022 — Depends on US1 (needs receipt extraction). Split transactions.
- **Polish (Phase 6)**: T023-T025 — After all user stories.

### User Story Dependencies

- **US1 (P1)**: Independent — MVP. Photo → extract → match → categorize.
- **US2 (P2)**: Depends on US1 (extends process_receipt with no-match path).
- **US3 (P3)**: Depends on US1 (extends process_receipt with split analysis).

### Parallel Opportunities

- T007, T008, T009 can run in parallel (different files — assistant.py tools, prompts)
- T002, T003, T004 are sequential (same file: receipt.py, each builds on previous)
- T014, T020 can run in parallel with their respective story implementation tasks (different files)

---

## Implementation Strategy

### MVP First (US1 Only)

1. T001 — Config var for OpenAI API key
2. T002-T004 — Receipt extraction, YNAB matching, category suggestion
3. T005-T010 — Process receipt tool, confirm tool, tool registration, system prompt
4. T011 — Verify end-to-end
5. **STOP and VALIDATE**: Send receipt photo, confirm full flow works
6. Deploy — users can categorize receipts via photos

### Incremental Delivery

1. T001-T011 → US1 complete → Receipt photo categorization works
2. T012-T016 → US2 complete → No-match handling + retry
3. T017-T022 → US3 complete → Multi-category split support
4. T023-T025 → Polish → CI passes, PR created

---

## Notes

- Total: 25 tasks
- New files: src/tools/receipt.py (core logic), src/prompts/system/10-receipt-categorization.md (system prompt), src/prompts/tools/receipt.md (tool descriptions)
- Modified files: src/config.py (1 var — may already exist), src/assistant.py (3-4 tool registrations), tests/test_prompts.py (tool count update)
- No new Python dependencies — OpenAI SDK already installed (`openai>=1.60.0` for Whisper)
- Uses OpenAI `gpt-4o` vision for receipt OCR (user preference over Claude vision for receipt extraction)
- Reuses existing `category_mappings.json`, `recategorize_transaction()`, `split_transaction()` from YNAB/Amazon sync
- Claude Haiku 4.5 used as fallback for category classification (same pattern as amazon_classification)
- `_pending_receipts` dict for conversation state (same pattern as multi-turn tool flows)
