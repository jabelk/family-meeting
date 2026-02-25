# Tasks: Amazon-YNAB Smart Sync

**Input**: Design documents from `/specs/010-amazon-ynab-sync/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add amazon-orders dependency, configure credentials, initialize persistence layer

- [X] T001 Add `amazon-orders>=4.0.18` to requirements.txt
- [X] T002 Add AMAZON_USERNAME, AMAZON_PASSWORD, AMAZON_OTP_SECRET_KEY env var validation to src/config.py (optional — graceful degradation if missing, like existing optional services)
- [X] T003 Create data model classes and JSON persistence helpers in src/tools/amazon_sync.py — implement SyncRecord, MatchedItem, CategoryMapping, Correction, SyncConfig dataclasses plus atomic JSON read/write functions for data/amazon_sync_records.json, data/category_mappings.json, data/amazon_sync_config.json (follow data-model.md entities and the tmp-file+rename pattern from src/tools/discovery.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: YNAB split transaction support and Amazon session management — MUST complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement `split_transaction(transaction_id, subtransactions)` in src/tools/ynab.py — accepts YNAB transaction UUID and list of {amount_milliunits, category_id, memo} dicts, calls PUT /budgets/{id}/transactions/{id} with subtransactions array, validates amounts sum to parent total. Follow existing httpx + HEADERS pattern.
- [X] T005 Implement `update_transaction_memo(transaction_id, memo)` in src/tools/ynab.py — updates memo field on existing transaction via PUT, appends to existing memo if present (separated by " | ")
- [X] T006 [P] Implement `delete_transaction(transaction_id)` in src/tools/ynab.py — calls DELETE /budgets/{id}/transactions/{id} for the undo flow (reverting splits)
- [X] T007 [P] Implement Amazon session login helper in src/tools/amazon_sync.py — create `get_amazon_orders(days=30, full_details=True)` function that creates AmazonSession with credentials from config, calls login(), fetches order history with time_filter="last30", returns list of Order objects. Handle auth failures gracefully: log error, return empty list, and return an auth_failed flag so the caller (run_nightly_sync) can notify Erin that Amazon sync needs re-authentication (FR-015).

**Checkpoint**: YNAB split API and Amazon data access ready — user story implementation can begin

---

## Phase 3: User Story 1 — Memo Enrichment & Smart Suggestions (Priority: P1) 🎯 MVP

**Goal**: Match Amazon orders to YNAB transactions, enrich memos with item names, classify items into budget categories, send Erin split suggestions via WhatsApp

**Independent Test**: Trigger sync after an Amazon purchase posts to YNAB. Verify memo updated with item names and Erin receives WhatsApp split suggestion.

### Implementation for User Story 1

- [X] T008 [US1] Implement `find_amazon_transactions(days=30)` in src/tools/amazon_sync.py — fetch YNAB transactions with payee containing "Amazon" or "AMZN" (last 30 days), filter out already-processed transactions using sync records, return list of unprocessed transaction dicts with id, amount, date, memo, payee_name
- [X] T009 [US1] Implement `match_orders_to_transactions(ynab_transactions, amazon_orders)` in src/tools/amazon_sync.py — for each unprocessed YNAB transaction, find Amazon order where grand_total matches exact penny amount AND order_placed_date within ±3 days of transaction date. Try shipment subtotals for partial shipment matching. Return list of {ynab_transaction, matched_order, match_type} dicts.
- [X] T010 [US1] Implement `classify_item(item_title, item_price, category_list, past_mappings)` in src/tools/amazon_sync.py — first check category_mappings.json for exact title match, then keyword match from learned patterns, then call Claude Haiku 4.5 with item title + family's YNAB categories + recent mapping examples. Return {category_name, category_id, confidence} dict. Use anthropic SDK (existing client pattern from src/assistant.py).
- [X] T011 [US1] Implement `enrich_and_classify(matched_transactions)` in src/tools/amazon_sync.py — for each matched transaction: (1) update YNAB memo with item names via update_transaction_memo(), (2) classify each item via classify_item(), (3) calculate proportional tax/shipping allocation per item (FR-010), (4) create SyncRecord with status "enriched". For single-item orders: auto-categorize directly without confirmation (FR-006), set status "auto_split", call split_transaction().
- [X] T012 [US1] Implement `format_suggestion_message(enriched_transactions)` in src/tools/amazon_sync.py — build WhatsApp message per contracts/api-endpoints.md format: numbered transactions with items, suggested categories, amounts, and reply instructions. Consolidate into single message (FR-009). Flag uncertain items with confidence < 0.7 (acceptance scenario 6).
- [X] T013 [US1] Implement `handle_sync_reply(sender_phone, message_text)` in src/tools/amazon_sync.py — parse Erin's replies: "N yes" → apply split via split_transaction(), save sync record as "split_applied", update category mappings with "user_approved" source. "N adjust — [correction]" → parse correction, modify split, apply, save mapping with "user_corrected". "N skip" → mark as "skipped". Handle 24h timeout logic (check pending suggestions older than 24h, mark as skipped).
- [X] T014 [US1] Register amazon_sync_status, amazon_sync_trigger tools in src/assistant.py — add tool definitions to TOOLS list (JSON Schema) and handler lambdas to TOOL_FUNCTIONS dict. amazon_sync_status returns sync stats. amazon_sync_trigger calls the sync pipeline manually.
- [X] T015 [US1] Add POST /api/v1/amazon/sync endpoint to src/app.py — basic manual trigger following existing n8n endpoint pattern (verify_n8n_auth dependency, BackgroundTasks). Calls individual pipeline functions (find_amazon_transactions, match, enrich_and_classify, format, send_message). T018 later refactors this to call the full run_nightly_sync() orchestrator.
- [X] T016 [US1] Add Amazon sync context to system prompt in src/assistant.py — add rules so Claude understands pending Amazon sync suggestions and can interpret Erin's approval/adjustment/skip replies in context of the sync flow. Include sync_reply handling in the message processing path.

**Checkpoint**: US1 complete — Amazon transactions matched, memos enriched, split suggestions sent, Erin can approve/adjust/skip

---

## Phase 4: User Story 2 — Automated Nightly Sync (Priority: P2)

**Goal**: Sync runs automatically each night via n8n, processing all new Amazon transactions. Erin wakes up to enriched memos and pending suggestions.

**Independent Test**: After a day with Amazon purchases, verify next morning Erin has WhatsApp messages with suggestions and memos are enriched.

### Implementation for User Story 2

- [X] T017 [US2] Implement `run_nightly_sync()` orchestrator in src/tools/amazon_sync.py — full pipeline: get_amazon_orders() → find_amazon_transactions() → match_orders_to_transactions() → enrich_and_classify() → format_suggestion_message() → send via WhatsApp. Skip silently if no new transactions (AS2). Skip already-processed transactions via sync records (AS3). Catch and log all errors without messaging Erin (AS4). Update SyncConfig.last_sync timestamp.
- [X] T018 [US2] Update POST /api/v1/amazon/sync endpoint in src/app.py to call run_nightly_sync() — the endpoint from T015 should invoke the full orchestrator, not just individual pieces. Ensure background task pattern handles the complete flow.
- [X] T019 [US2] Document n8n workflow configuration for nightly 10pm trigger in specs/010-amazon-ynab-sync/quickstart.md — add n8n setup steps: HTTP Request node → POST to /api/v1/amazon/sync with X-N8N-Auth header, cron schedule at 22:00 daily.

**Checkpoint**: US2 complete — nightly sync runs automatically, consolidated messages, duplicate prevention, silent error handling

---

## Phase 5: User Story 3 — Full Auto-Split Mode (Priority: P3)

**Goal**: After 80%+ unmodified acceptance rate over 2 weeks, bot suggests enabling auto-split. Erin confirms. Bot then splits automatically with undo capability.

**Independent Test**: Enable auto-split, make Amazon purchase, wait for sync, verify auto-split applied without confirmation. Test undo.

### Implementation for User Story 3

- [X] T020 [US3] Implement acceptance rate tracking in src/tools/amazon_sync.py — update SyncConfig stats on every approval/correction/skip: increment total_suggestions, unmodified_accepts, modified_accepts, or skips. Set first_suggestion_date on first suggestion. Calculate acceptance_rate = unmodified_accepts / total_suggestions.
- [X] T021 [US3] Implement auto-split graduation check in src/tools/amazon_sync.py — after each sync run, check if (days since first_suggestion_date >= 14) AND (acceptance_rate >= 0.8) AND (auto_split_enabled == false) AND (total_suggestions >= 10). If all true, send WhatsApp: "I've been getting your Amazon categories right [X]% of the time — want me to start auto-splitting? You can always undo or turn it off." Track this as a pending graduation prompt.
- [X] T022 [US3] Implement auto-split execution path in run_nightly_sync() in src/tools/amazon_sync.py — when auto_split_enabled is true: skip suggestion message, apply splits automatically via split_transaction(), send brief summary per contracts format ("Auto-split your $87 Amazon order: ..."). For items with confidence < 0.7, fall back to suggestion flow for that specific transaction (AS3).
- [X] T023 [US3] Implement undo flow in src/tools/amazon_sync.py — `handle_undo(transaction_index)`: look up SyncRecord by index, call delete_transaction() on the split transaction, recreate as single transaction with original_memo and original_category_id. Update sync record status.
- [X] T024 [US3] Register amazon_set_auto_split and amazon_undo_split tools in src/assistant.py — add tool definitions and handlers. amazon_set_auto_split toggles SyncConfig.auto_split_enabled (with validation: only enable if acceptance rate qualifies). amazon_undo_split calls handle_undo().

**Checkpoint**: US3 complete — auto-split graduation, automatic splitting, undo capability, mode toggle

---

## Phase 6: User Story 4 — YNAB Best Practices Coaching (Priority: P4)

**Goal**: Bot provides contextual YNAB best practice guidance alongside sync flow — spending breakdowns, recurring purchase detection, goal adjustment suggestions.

**Independent Test**: After 2+ weeks of sync data, ask "how are we doing on Amazon spending?" and verify category breakdown with budget comparisons.

### Implementation for User Story 4

- [X] T025 [US4] Implement `get_amazon_spending_breakdown(month="")` in src/tools/amazon_sync.py — aggregate sync records by classified category for the given month, compare against YNAB budget goals via get_budget_summary(), return formatted breakdown: "Amazon spending this month: $180 Healthcare (mostly vitamins), $120 Kids, $95 Home. Healthcare within goal, Kids $30 over."
- [X] T026 [US4] Implement recurring purchase detection in src/tools/amazon_sync.py — scan category_mappings for items that appear monthly (same title, 25-35 day intervals in sync records). When detected during a sync suggestion, append tip: "This looks like a monthly subscription — want me to set up a $X/mo [Category] goal?"
- [X] T027 [US4] Implement large purchase handling in src/tools/amazon_sync.py — during classification, detect purchases > $200 (configurable threshold). Flag as potential one-time purchase and suggest: "This $500 item might come from your [Sinking Fund] — or should I just categorize it as [Category]?"
- [X] T028 [US4] Register amazon_spending_breakdown tool in src/assistant.py — add tool definition and handler so Claude can answer "how's our Amazon spending?" queries by calling get_amazon_spending_breakdown().

**Checkpoint**: US4 complete — spending breakdown, recurring detection, large purchase handling, best practice tips

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, refund handling, known charge patterns, deployment

- [X] T029 Implement refund matching in src/tools/amazon_sync.py — detect negative-amount Amazon transactions in YNAB. Match to original purchase in sync records by amount (exact or item-level match for partial refunds) + date proximity. Apply refund to same category split. If unmatched, ask Erin via WhatsApp. (FR-013, edge case: frequent returns)
- [X] T030 [P] Implement known charge pattern handling in src/tools/amazon_sync.py — check unmatched transactions against KnownChargePattern table (Prime → Subscriptions, Kindle → Entertainment, Amazon Fresh → Groceries, etc.). Auto-categorize matches. Tag truly unrecognizable as "Unmatched Amazon charge" and ask Erin. (FR-014)
- [X] T031 [P] Implement 24-hour timeout sweep in src/tools/amazon_sync.py — add function called during nightly sync that checks for pending suggestions older than 24 hours and marks them as "skipped" (AS4 from US1)
- [X] T032 Add Amazon sync to help system in src/tools/discovery.py — add "amazon_sync" entries to TOOL_TO_CATEGORY (under "budget" category), add tip definitions for Amazon sync features, update budget category capabilities text to mention Amazon sync
- [X] T033 Python syntax check — run `python -m py_compile src/tools/amazon_sync.py && python -m py_compile src/tools/ynab.py && python -m py_compile src/assistant.py && python -m py_compile src/app.py`
- [ ] T034 Deploy to NUC — commit changes, push to main, run `./scripts/nuc.sh deploy`, verify container starts cleanly via `./scripts/nuc.sh logs fastapi 50`
- [ ] T035 Add Amazon credentials to NUC .env — add AMAZON_USERNAME, AMAZON_PASSWORD, AMAZON_OTP_SECRET_KEY to .env, run `./scripts/nuc.sh env` to push and restart
- [ ] T036 Configure n8n nightly sync workflow — create new n8n workflow: HTTP Request node → POST https://mombot.sierrastoryco.com/api/v1/amazon/sync with X-N8N-Auth header, cron trigger at 22:00 daily
- [ ] T037 End-to-end validation — trigger manual sync via WhatsApp ("sync my Amazon"), verify: (1) Amazon orders fetched, (2) YNAB transactions matched, (3) memos enriched, (4) classification working, (5) WhatsApp suggestion received, (6) approval flow works, (7) YNAB split applied correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — this IS the MVP
- **US2 (Phase 4)**: Depends on US1 (orchestrator wraps US1 pipeline)
- **US3 (Phase 5)**: Depends on US1 (tracks acceptance stats from US1 flow)
- **US4 (Phase 6)**: Depends on US1 (analyzes sync record data from US1)
- **Polish (Phase 7)**: Can start after US1, but best after US2 for full nightly sync context

### User Story Dependencies

- **US1 (P1)**: After Foundational — core MVP, no other story dependencies
- **US2 (P2)**: After US1 — wraps US1 pipeline in automated orchestrator
- **US3 (P3)**: After US1 — adds auto-split mode on top of suggestion flow
- **US4 (P4)**: After US1 — analyzes accumulated sync data

### Within Each User Story

- Models/data access before business logic
- Business logic before message formatting
- Message formatting before tool registration
- Tool registration before endpoint creation

### Parallel Opportunities

- T006 and T007 (Foundational) can run in parallel — different files
- T029 and T030 (Polish) can run in parallel — independent edge case handlers
- US3 and US4 could run in parallel after US1 completes (independent features)

---

## Parallel Example: Phase 2 (Foundational)

```
Sequential: T004 → T005 (both modify ynab.py)
Parallel:   T006 (ynab.py delete) || T007 (amazon_sync.py session)
```

## Parallel Example: Phase 7 (Polish)

```
Parallel:   T029 (refund matching) || T030 (known charge patterns) || T031 (timeout sweep)
Sequential: T033 → T034 → T035 → T036 → T037
```

---

## Implementation Strategy

### MVP First (US1 Only — Phases 1-3)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: US1 (T008-T016)
4. **STOP and VALIDATE**: Manually trigger sync, verify memo enrichment + suggestion flow
5. Deploy if ready — Erin can start using suggestion mode immediately

### Incremental Delivery

1. Setup + Foundational + US1 → Manual sync with suggestions → Deploy (MVP!)
2. Add US2 → Nightly automated sync → Deploy
3. Add US3 → Auto-split graduation → Deploy (after 2+ weeks of US1/US2 usage)
4. Add US4 → Best practices coaching → Deploy
5. Polish → Refund handling, edge cases, help system → Deploy

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2 depends on US1; US3 depends on US1; US4 depends on US1 — all user stories build on US1 as the core
- JSON persistence in data/ follows existing discovery.py atomic write pattern
- YNAB milliunits: multiply dollars by 1000, outflows are negative
- Amazon scraping is slow (~1 req/order with full_details) — batch nightly, not real-time
- Commit after each phase completion for clean rollback points
