# Tasks: Email-YNAB Smart Sync (PayPal, Venmo, Apple)

**Input**: Design documents from `/specs/011-email-ynab-sync/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Extend existing amazon_sync infrastructure to support multiple providers

- [X] T001 Add `provider` field to SyncRecord dataclass in src/tools/amazon_sync.py — default to `"amazon"` for backward compatibility, add provider parameter to `save_sync_record()`
- [X] T002 Create src/tools/email_sync.py with module docstring, imports from amazon_sync (\_get_gmail_service, \_extract_html_body, \_strip_html, classify_item, load_category_mappings, save_category_mapping, SyncRecord, MatchedItem, load_sync_records, save_sync_record, is_transaction_processed, load_sync_config, save_sync_config, set_pending_suggestions), and provider config constants (PROVIDER_CONFIGS dict with gmail_query, ynab_payee_filter, memo_format for each of paypal/venmo/apple)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core provider-agnostic infrastructure in email_sync.py that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Implement `find_provider_transactions(provider: str, days: int = 30) -> list[dict]` in src/tools/email_sync.py — query YNAB API for unprocessed transactions where payee contains the provider's filter string (case-insensitive), excluding transactions already in sync records and excluding amazon/amzn payees
- [X] T004 Implement `_search_provider_emails(provider: str, days: int = 30) -> list[dict]` in src/tools/email_sync.py — use \_get_gmail_service() to search Gmail with the provider's gmail_query, return list of {email_id, email_date, html_body, stripped_text}
- [X] T005 Implement `match_emails_to_transactions(ynab_transactions: list[dict], parsed_emails: list[dict]) -> list[dict]` in src/tools/email_sync.py — same ±3 day date window + exact penny-match algorithm as amazon_sync.match_orders_to_transactions(), returns list of {ynab_transaction, matched_email, match_type}

**Checkpoint**: Foundation ready — provider-specific parsers can now be implemented

---

## Phase 3: User Story 1 — Memo Enrichment & Category Suggestion (Priority: P1) 🎯 MVP

**Goal**: Parse PayPal/Venmo/Apple emails, match to YNAB transactions, enrich memos with real merchant/service names, classify into categories, and send Erin WhatsApp suggestions

**Independent Test**: Make a PayPal purchase, trigger sync manually, verify YNAB memo updated and Erin receives WhatsApp category suggestion

### Implementation for User Story 1

- [X] T006 [P] [US1] Implement `_parse_paypal_email(stripped_text: str, email_date: str) -> list[dict]` in src/tools/email_sync.py — Claude Haiku prompt to extract merchant_name, amount, items (supports multi-item), is_refund from PayPal confirmation email text. Return list of EmailTransaction-shaped dicts
- [X] T007 [P] [US1] Implement `_parse_venmo_email(stripped_text: str, email_date: str) -> list[dict]` in src/tools/email_sync.py — Claude Haiku prompt to extract recipient/sender name, payment_note, amount, direction (sent/received), is_refund from Venmo notification email text
- [X] T008 [P] [US1] Implement `_parse_apple_email(stripped_text: str, email_date: str) -> list[dict]` in src/tools/email_sync.py — Claude Haiku prompt to extract subscription/service name, amount, is_refund from Apple receipt email text
- [X] T009 [US1] Implement `_parse_provider_emails(provider: str, raw_emails: list[dict]) -> list[dict]` in src/tools/email_sync.py — dispatcher that calls the correct parser based on provider, validates output, logs parse errors gracefully
- [X] T010 [US1] Implement `enrich_and_classify_email(matched_transactions: list[dict], provider: str) -> list[dict]` in src/tools/email_sync.py — update YNAB memos with provider-specific format (PayPal: "[merchant] via PayPal", Venmo: "To [name] — [note]", Apple: "[service name]"), classify items using amazon_sync.classify_item(), create SyncRecords with provider field. Refund handling: if is_refund=True, search sync records for same merchant + similar amount within 30 days to find original transaction, categorize refund to same category; if no match found, flag for Erin via suggestion message
- [X] T011 [US1] Implement `_is_recurring_charge(merchant_name: str, amount: float) -> bool` and `format_email_suggestion_message(enriched_transactions: list[dict]) -> str` in src/tools/email_sync.py — recurring check: lookup merchant in category_mappings with source="user_approved" and confidence >= 0.9, amount within ±20% of previous. Format consolidated WhatsApp message with provider labels, merchant names, amounts, category suggestions. Auto-categorize recurring charges and previously approved mappings (confidence >= 0.9). Use "💳 Email Sync" header format from contracts
- [X] T012 [US1] Implement `run_email_sync() -> str | None` in src/tools/email_sync.py — main orchestrator: check YNAB for unprocessed transactions (fast exit if none), for each provider with transactions search Gmail → parse emails → match → enrich/classify → format message. Send consolidated suggestion message directly to Erin via `send_sync_message_direct()` (public function in assistant.py). Save pending suggestions to separate `data/email_pending_suggestions.json` file (NOT shared with Amazon). Return short status string
- [X] T013 [US1] Implement `handle_email_sync_reply(message_text: str) -> str` in src/tools/email_sync.py — parse Erin's replies ("N yes", "N adjust — [correction]", "N skip") for email sync pending suggestions, load from `data/email_pending_suggestions.json` (separate from Amazon), apply category to YNAB, save updated mapping. Follow same pattern as amazon_sync.handle_sync_reply()
- [X] T014 [US1] Add email_sync tool definitions to src/assistant.py — add `email_sync_trigger` and `email_sync_status` tools to TOOLS list and system prompt, add email_sync_reply handling to the message handler (detect replies to email sync suggestions). Also rename `_send_sync_message_direct` to `send_sync_message_direct` (remove leading underscore to make it public for cross-module import by email_sync.py), update all existing call sites
- [X] T015 [US1] Add `POST /api/v1/email/sync` endpoint to src/app.py — follow same pattern as amazon_sync_endpoint (BackgroundTasks, verify_n8n_auth dependency, background async task that calls email_sync.run_email_sync(), return {"status": "sent"})

**Checkpoint**: US1 complete — PayPal/Venmo/Apple transactions matched, memos enriched, categories suggested via WhatsApp. Manually testable via curl or WhatsApp trigger.

---

## Phase 4: User Story 2 — Automated Nightly Sync (Priority: P2)

**Goal**: Sync runs automatically each night via n8n, processes all new transactions, Erin wakes up to enriched memos and pending suggestions

**Independent Test**: After a day with PayPal/Venmo/Apple purchases, verify next morning Erin has WhatsApp messages with suggestions and all memos enriched

### Implementation for User Story 2

- [X] T016 [US2] Add silent-exit logic to run_email_sync() in src/tools/email_sync.py — ensure sync returns None (no WhatsApp message) when no new transactions found, logs "no new transactions to process" at info level
- [X] T017 [US2] Add error handling and graceful degradation to run_email_sync() in src/tools/email_sync.py — catch Gmail OAuth expiration (log error, skip sync, do NOT message Erin with technical errors), catch per-provider failures independently (one provider failing doesn't block others), log all errors with provider context
- [X] T018 [US2] Create n8n workflow JSON for email sync in scripts/n8n-workflows/ — Schedule Trigger at 10:05pm daily Pacific, HTTP Request to http://fastapi:8000/api/v1/email/sync with X-N8N-Auth header, 300000ms timeout
- [X] T019 [US2] Deploy and activate n8n workflow on NUC — copy workflow JSON, import via n8n CLI, activate, verify in n8n UI

**Checkpoint**: US2 complete — nightly sync runs automatically, Erin receives consolidated suggestions each morning

---

## Phase 5: User Story 3 — Auto-Categorize Mode (Priority: P3)

**Goal**: After building trust through US1/US2 suggestion flow, enable auto-categorize mode for high-confidence matches and known recurring charges

**Independent Test**: Enable auto-categorize, wait for next Apple subscription charge, verify it was automatically categorized without WhatsApp confirmation

### Implementation for User Story 3

- [X] T020 [US3] Add `email_auto_categorize_enabled`, `email_last_sync`, `email_total_suggestions`, `email_unmodified_accepts` fields to SyncConfig in src/tools/amazon_sync.py — extend existing SyncConfig dataclass, default new fields to False/empty/0
- [X] T021 [US3] Enhance `_is_recurring_charge()` in src/tools/email_sync.py — extend the function (already created in T011) to also check sync record history for frequency patterns (e.g., monthly recurrence), and log recurring charge detections for the graduation check in T024
- [X] T022 [US3] Update enrich_and_classify_email() in src/tools/email_sync.py to auto-categorize when: (a) email_auto_categorize_enabled is True, OR (b) transaction matches a known recurring charge (\_is_recurring_charge returns True). Auto-categorized items get status "auto_split", skipping the suggestion flow
- [X] T023 [US3] Update format_email_suggestion_message() in src/tools/email_sync.py to include auto-categorized items in a brief summary section ("Auto-categorized: $12.99 iCloud+ → Subscriptions") separate from items needing confirmation
- [X] T024 [US3] Implement `get_email_acceptance_rate() -> float` and `check_email_auto_categorize_graduation() -> str | None` in src/tools/email_sync.py — track acceptance rate from email sync suggestions, suggest enabling auto-categorize when >= 80% unmodified acceptance over 2+ weeks
- [X] T025 [US3] Implement `set_email_auto_categorize(enabled: bool) -> str` in src/tools/email_sync.py — toggle auto-categorize mode, save to SyncConfig
- [X] T026 [US3] Implement `handle_email_undo(transaction_index: int) -> str` in src/tools/email_sync.py — revert auto-categorized transaction, restore original memo and category from SyncRecord
- [X] T027 [US3] Add `email_set_auto_categorize` and `email_undo_categorize` tool definitions to src/assistant.py — add to TOOLS list and system prompt, handle "turn on/off auto-categorize" and "undo N" for email sync

**Checkpoint**: US3 complete — auto-categorize mode available, recurring charges detected, undo capability functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, hardening, and validation across all stories

- [X] T028 Add unmatched transaction handling to run_email_sync() in src/tools/email_sync.py — for YNAB transactions with no matching email, tag memo with "Unmatched [Provider] charge" and include in suggestion message asking Erin to categorize
- [X] T029 Add PayPal multi-item split support to enrich_and_classify_email() in src/tools/email_sync.py — when PayPal email contains multiple items, suggest YNAB transaction split across categories (same pattern as Amazon multi-item flow)
- [X] T030 [P] Add Venmo business payment detection to \_parse_venmo_email() in src/tools/email_sync.py — detect when Venmo payment is to a business (not person-to-person) and treat merchant name as the business name
- [X] T031 [P] Add email_sync_status tool implementation in src/tools/email_sync.py — `get_email_sync_status() -> str` returning last sync time, transactions processed by provider, acceptance rate, auto-categorize status
- [X] T032 End-to-end validation: deploy to NUC, trigger sync with real PayPal/Venmo/Apple transactions, verify memos enriched in YNAB and WhatsApp suggestions received by Erin

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001-T002)
- **User Story 1 (Phase 3)**: Depends on Phase 2 (T003-T005) — BLOCKS all stories
- **User Story 2 (Phase 4)**: Depends on US1 (T012 run_email_sync must exist)
- **User Story 3 (Phase 5)**: Depends on US1 (needs suggestion flow working first)
- **Polish (Phase 6)**: Depends on US1 at minimum

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependencies on other stories. **This is the MVP.**
- **User Story 2 (P2)**: Depends on US1 T012 (run_email_sync orchestrator). Adds nightly automation and error handling.
- **User Story 3 (P3)**: Depends on US1 working (needs suggestion acceptance data). Adds auto-categorize graduation.

### Within Each User Story

- Parser functions (T006-T008) are parallelizable — different providers, no shared state
- Dispatcher (T009) depends on parsers
- Enrich/classify (T010) depends on dispatcher
- Formatter (T011) depends on enrich/classify
- Orchestrator (T012) depends on all above
- Reply handler (T013) depends on orchestrator
- Tool definitions (T014) and endpoint (T015) depend on orchestrator

### Parallel Opportunities

**Phase 3 (US1)**:
```
T006, T007, T008 can run in parallel (different provider parsers)
T014, T015 can run in parallel after T012 (different files: assistant.py, app.py)
```

**Phase 5 (US3)**:
```
T021, T024, T025, T026 can run in parallel after T020 (different functions)
```

**Phase 6 (Polish)**:
```
T030, T031 can run in parallel (different functions, no dependencies)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T005)
3. Complete Phase 3: User Story 1 (T006-T015)
4. **STOP and VALIDATE**: Deploy to NUC, trigger sync with real transactions, verify end-to-end
5. Deploy if ready — Erin can start using suggestion flow immediately

### Incremental Delivery

1. Setup + Foundational → provider infrastructure ready
2. Add User Story 1 → manual and endpoint-triggered sync working (MVP!)
3. Add User Story 2 → nightly automation, error resilience
4. Add User Story 3 → auto-categorize mode for power users
5. Polish → edge cases, multi-item splits, unmatched handling
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All provider parsers use Claude Haiku with structured JSON output (same pattern as amazon_sync._parse_order_email)
- Category mappings are shared across all providers — learning from one provider benefits others
- Sync records use a single file with provider field to distinguish
- WhatsApp direct send (bypassing Claude summarization) is reused from Feature 010
- The `_send_sync_message_direct` function is imported from assistant.py
