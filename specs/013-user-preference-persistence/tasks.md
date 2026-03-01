# Tasks: User Preference Persistence

**Input**: Design documents from `/specs/013-user-preference-persistence/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Phase 1: Setup

**Purpose**: Verify data directory and gitignore are ready

- [x] T001 [P] Verify `data/` directory exists and `data/*.json` is in `.gitignore` (already true -- confirmed)

---

## Phase 2: Foundational (Preference Store Module)

**Purpose**: Core preference CRUD that all user stories depend on

- [x] T002 Create `src/preferences.py` with module-level cache, `_load_preferences()`, `_save_preferences()` (atomic write), and `_DATA_DIR` detection following `src/conversation.py` pattern
- [x] T003 Implement `get_preferences(phone)` -> list[dict] in `src/preferences.py`
- [x] T004 Implement `add_preference(phone, category, description, raw_text)` -> dict in `src/preferences.py` with ID generation, 50-preference cap, and duplicate detection
- [x] T005 Implement `remove_preference(phone, preference_id)` -> bool in `src/preferences.py`
- [x] T006 Implement `remove_preference_by_description(phone, search_text)` -> bool in `src/preferences.py` with fuzzy matching
- [x] T007 Implement `clear_preferences(phone)` -> int in `src/preferences.py`
- [x] T008 Verify module import: `python3 -c "import src.preferences; print('OK')"` -- PASSED

**Checkpoint**: Preference store ready -- user story implementation can begin

---

## Phase 3: User Story 1 -- Capture & Store Preferences (Priority: P1)

**Goal**: When Erin or Jason states a lasting preference, the bot recognizes it, stores it persistently, and confirms.

**Independent Test**: Send "don't remind me about groceries unless I ask" in WhatsApp. Restart container. Ask "what are my preferences?" and see the grocery opt-out listed.

### Implementation

- [x] T009 [US1] Add `save_preference` tool definition to TOOLS list in `src/assistant.py` with category enum, description, and raw_text parameters
- [x] T010 [US1] Add `save_preference` handler to TOOL_FUNCTIONS dict in `src/assistant.py` that extracts sender phone from context and calls `preferences.add_preference()`
- [x] T011 [US1] Add system prompt rules 68-70 in `src/assistant.py` SYSTEM_PROMPT for preference detection: when to call save_preference, when NOT to (one-time requests), and ambiguity handling

**Checkpoint**: Preferences can be captured and stored via WhatsApp

---

## Phase 4: User Story 2 -- Honor Stored Preferences (Priority: P1)

**Goal**: Bot actively honors stored preferences in all interactions -- system prompt injection for conversational behavior, nudge filtering for proactive messages.

**Independent Test**: Store a grocery opt-out. Trigger daily briefing. Verify it omits grocery content. Trigger nudge scan. Verify grocery nudges are filtered.

### Implementation

- [x] T012 [US2] Add preference injection in `handle_message()` in `src/assistant.py`: after date_line injection, load preferences for sender_phone and append to system prompt
- [x] T013 [US2] Add preference-based nudge filtering in `process_pending_nudges()` in `src/tools/nudges.py`: before sending each nudge, check if user has matching opt-out preference

**Checkpoint**: Preferences are honored in both interactive and automated paths

---

## Phase 5: User Story 3 -- List & Manage Preferences (Priority: P2)

**Goal**: Users can list, remove individual, and clear all preferences via natural language.

**Independent Test**: Store two preferences. Send "what are my preferences?". Verify both listed. Send "start reminding me about groceries again". Verify removal.

### Implementation

- [x] T014 [US3] Add `list_preferences` tool definition and handler in `src/assistant.py` (phone injected from sender context)
- [x] T015 [US3] Add `remove_preference` tool definition and handler in `src/assistant.py` with search_text parameter; handle "ALL" for clear-all
- [x] T016 [US3] Verify tool count: 3 new tools added (save_preference, list_preferences, remove_preference) -- confirmed via grep

**Checkpoint**: Full preference CRUD available via WhatsApp

---

## Phase 6: User Story 4 -- Preference Categories (Priority: P3)

**Goal**: Preferences are categorized (notification_optout, topic_filter, communication_style, quiet_hours) and applied in the correct pipeline stage.

**Independent Test**: Store one preference in each category. Verify notification opt-outs filter nudges, topic filters modify briefings, communication style changes responses, quiet hours suppress time-windowed nudges.

### Implementation

- [x] T017 [US4] Enhance nudge filtering in `src/tools/nudges.py` to match by category: `notification_optout` suppresses nudges with keyword matching, `quiet_hours` placeholder for time-window checks
- [x] T018 [US4] Enhance system prompt injection in `src/assistant.py` to group preferences by category label in the injected text for clearer Claude interpretation

**Checkpoint**: All four preference categories functional

---

## Phase 7: Polish & Edge Cases

**Purpose**: Handle edge cases from spec, add validation, verify persistence

- [x] T019 [P] Add duplicate/conflicting preference handling in `add_preference()`: if a preference for the same topic exists, replace it and note the update -- uses word overlap detection with stop word filtering
- [x] T020 [P] Add graceful corruption recovery in `_load_preferences()`: malformed JSON logs warning and starts with empty dict
- [x] T021 Verify end-to-end: import, tool count, preference CRUD cycle via python3 -c -- ALL TESTS PASSED

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies -- confirm existing infrastructure
- **Foundational (Phase 2)**: Depends on Phase 1 -- creates the preference module
- **US1 (Phase 3)**: Depends on Phase 2 -- needs preference store to save to
- **US2 (Phase 4)**: Depends on Phase 2 -- needs preference store to read from
- **US3 (Phase 5)**: Depends on Phase 2 -- needs preference store for list/remove
- **US4 (Phase 6)**: Depends on Phases 3 + 4 -- refines category behavior
- **Polish (Phase 7)**: Depends on all user stories

### Parallel Opportunities

- T001 can run independently
- T009, T010, T011 (US1) can run in parallel with T012, T013 (US2) since they modify different sections of assistant.py
- T014, T015 (US3) can start as soon as Phase 2 is complete
- T017, T018 (US4) depend on US1 + US2 being in place
- T019, T020 (Polish) can run in parallel
