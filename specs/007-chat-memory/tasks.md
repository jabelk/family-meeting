# Tasks: Chat Memory & Conversation Persistence

**Input**: Design documents from `/specs/007-chat-memory/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/conversation-module.md, quickstart.md

**Tests**: No automated tests requested. Validation via manual SSH + docker compose exec testing per quickstart.md.

**Organization**: Tasks are grouped by user story. US1 contains the core implementation; US2 and US3 are primarily validation phases since the same conversation module powers all three stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the conversation module skeleton and file persistence layer

- [x] T001 Create `src/conversation.py` with module docstring, imports (json, logging, pathlib, datetime), constants (CONVERSATION_TIMEOUT=1800, MAX_CONVERSATION_TURNS=10), file path detection (`_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")`), `_CONVERSATIONS_FILE = _DATA_DIR / "conversations.json"`, and module-level `_conversations: dict[str, dict] = {}` cache
- [x] T002 Implement `_load_conversations()` and `_save_conversations()` in `src/conversation.py` — follow atomic write pattern from `src/tools/discovery.py` (write to `.tmp` then `os.replace()`), call `_load_conversations()` at module level on import

---

## Phase 2: User Story 1 — Conversational Follow-Ups (Priority: P1) 🎯 MVP

**Goal**: When Erin sends a follow-up message, the bot remembers what was discussed in the recent exchange and responds correctly. This is the core feature that makes multi-turn conversations work.

**Independent Test**: Send "what's on our calendar this week?" then follow up with "what about next week?" — verify the bot understands the calendar context without re-specifying it.

### Implementation for User Story 1

- [x] T003 [US1] Implement `_serialize_message(msg: dict) -> dict` in `src/conversation.py` — for each message in a turn: if `msg["role"]` is "assistant" and `msg["content"]` is a list of Anthropic SDK content block objects (check for `model_dump` attribute), serialize each block via `block.model_dump(mode="json", exclude_unset=True)`; for user messages with image content blocks (type "image" with base64 source), replace with `{"type": "text", "text": "[Image sent: photo]"}`; pass through plain dicts and strings unchanged
- [x] T004 [US1] Implement `get_history(phone: str) -> list[dict]` in `src/conversation.py` — if phone not in `_conversations` return `[]`; check if `last_active` is older than `CONVERSATION_TIMEOUT` seconds ago (parse ISO timestamp, compare to `datetime.now()`); if expired, delete the phone entry and return `[]`; otherwise flatten all turns' `messages` lists into a single list and return it
- [x] T005 [US1] Implement `save_turn(phone: str, turn_messages: list[dict]) -> None` in `src/conversation.py` — create phone entry if needed with empty turns list; update `last_active` to `datetime.now().isoformat()`; serialize each message in `turn_messages` via `_serialize_message()`; append as a new turn `{"messages": serialized_list}`; if `len(turns) > MAX_CONVERSATION_TURNS` drop the oldest turn (pop index 0); call `_save_conversations()`
- [x] T006 [US1] Implement `clear_history(phone: str) -> None` in `src/conversation.py` — remove phone from `_conversations` if present, call `_save_conversations()`
- [x] T007 [US1] Add `from src import conversation` to imports section in `src/assistant.py`
- [x] T008 [US1] Modify `handle_message()` in `src/assistant.py` — before the Claude API call (before the `while True` loop), load history for non-system senders: `history = conversation.get_history(sender_phone) if sender_phone != "system" else []`; change `messages = [{"role": "user", "content": user_content}]` to `messages = history + [{"role": "user", "content": user_content}]`; store `history_len = len(history)` for later extraction
- [x] T009 [US1] Modify `handle_message()` in `src/assistant.py` — before each `return` statement in the tool loop and final response, add conversation save: `if sender_phone != "system": conversation.save_turn(sender_phone, messages[history_len:])`

**Checkpoint**: Follow-up questions work within a 30-minute window. Validate with quickstart.md Test 1.

---

## Phase 3: User Story 2 — Multi-Step Workflows (Priority: P2)

**Goal**: Multi-step tool-driven workflows (recipe search → details → save → grocery list) work without repeating context at each step. This validates that tool call results are properly preserved in conversation history.

**Independent Test**: Run a 3-step recipe workflow: "find me a chicken dinner" → "tell me more about number 1" → "save that one" — verify each step works without re-stating context.

### Implementation for User Story 2

- [x] T010 [US2] Review and validate that `_serialize_message()` in `src/conversation.py` correctly handles all 4 message content types from the tool-use loop: (1) user text string, (2) user content list with tool_result dicts, (3) assistant content list with TextBlock objects, (4) assistant content list with ToolUseBlock objects — fix any serialization gaps found
- [x] T011 [US2] Test multi-step recipe workflow on NUC via quickstart.md Test 2 — run a 3+ step chain and verify each step uses prior context

**Checkpoint**: Multi-step workflows complete without the user needing to repeat context. Validate with quickstart.md Test 2.

---

## Phase 4: User Story 3 — Conversation Boundaries (Priority: P3)

**Goal**: Conversations expire naturally after 30 minutes of inactivity so stale context doesn't confuse new topics. History persists across container restarts.

**Independent Test**: Have a conversation, expire it (manipulate last_active), send a new message on a different topic — verify no context bleed.

### Implementation for User Story 3

- [x] T012 [US3] Test conversation expiry behavior on NUC — run quickstart.md Test 3 (start conversation, manually expire by editing last_active in conversations.json, verify fresh context on next message)
- [x] T013 [US3] Test restart persistence on NUC — run quickstart.md Test 4 (start conversation, restart fastapi container, verify follow-up still works)
- [x] T014 [US3] Test per-user isolation on NUC — run quickstart.md Test 5 (two different phone numbers, verify independent histories)

**Checkpoint**: Expiry, persistence, and isolation all work correctly. Validate with quickstart.md Tests 3-5.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Deploy, validate all scenarios, and verify edge cases

- [x] T015 Python syntax check both `src/conversation.py` and `src/assistant.py` via `python3 -c "import py_compile; py_compile.compile('src/conversation.py', doraise=True); py_compile.compile('src/assistant.py', doraise=True)"`
- [x] T016 Deploy to NUC via `./scripts/nuc.sh deploy` and run full quickstart.md validation (all 6 test scenarios including Test 6: system messages excluded)
- [x] T017 Verify conversations.json file is reasonable size and format via SSH inspection on NUC after testing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US1 (Phase 2)**: Depends on Phase 1 (T001-T002) — needs conversation module skeleton
- **US2 (Phase 3)**: Depends on US1 — validates tool result serialization in existing module
- **US3 (Phase 4)**: Depends on US1 — validates expiry/persistence already built into get_history/save_turn
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 1 — contains ALL core implementation
- **US2 (P2)**: Depends on US1 — validation-focused phase (serialization review + multi-step test)
- **US3 (P3)**: Depends on US1 — validation-focused phase (expiry + persistence + isolation tests)

### Within User Story 1

- T003 (serialization) before T005 (save_turn uses it)
- T004 (get_history) and T005 (save_turn) before T008-T009 (integration)
- T007 (import) before T008-T009 (usage)
- T008 (load history) before T009 (save turn)

### Files Modified

- `src/conversation.py` — **NEW** (T001-T006, T010)
- `src/assistant.py` — **MODIFIED** (T007-T009)

---

## Parallel Example: Phase 1 + Early Phase 2

```bash
# T001 and T002 must be sequential (same file, T002 depends on T001)

# After T002, these can be developed together but must be sequential
# (same file, dependencies between functions):
# T003 → T004 → T005 → T006

# T007 can run in parallel with T003-T006 (different file):
Task: "T007 Add conversation import in src/assistant.py"

# T008 and T009 must wait for T004-T006 (need the functions to exist)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: User Story 1 (T003-T009)
3. **STOP and VALIDATE**: Send a follow-up question via SSH + docker compose exec
4. Deploy if ready — Erin immediately gets conversation memory

### Incremental Delivery

1. Setup + US1 → Follow-ups work → Deploy (MVP!)
2. Add US2 validation → Verify multi-step workflows → Deploy
3. Add US3 validation → Verify expiry + persistence → Deploy
4. Each validation phase confirms the core module handles the story's scenarios

### Full Build Order (Sequential)

1. T001 → T002
2. T003 → T004 → T005 → T006
3. T007 → T008 → T009
4. T010 → T011
5. T012 → T013 → T014
6. T015 → T016 → T017

---

## Notes

- **US2 and US3 are validation-focused**: The core code is in US1. US2 validates tool result serialization, US3 validates expiry/persistence. Both may surface bugs to fix in the conversation module, but the implementation work is in US1.
- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- The conversation module follows the same persistence pattern as `src/tools/discovery.py` (atomic JSON writes to `data/` directory)
- File path: `data/conversations.json` (local) or `/app/data/conversations.json` (Docker)
- The Docker volume mount `./data:/app/data` already exists in `docker-compose.yml` from feature 006
- Commit after each phase or logical group
- Stop at any checkpoint to validate story independently
