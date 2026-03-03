# Tasks: Time Awareness & Extended Conversation Context

**Input**: Design documents from `/specs/016-time-and-context-fix/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No setup needed — existing Python 3.12 + FastAPI project. No new dependencies required.

*(No tasks — all dependencies already installed)*

---

## Phase 2: User Story 1 — Time-Aware Responses (Priority: P1) MVP

**Goal**: Claude reliably uses the current time when generating schedules, setting reminders, and resolving relative time references. No more morning activities suggested at noon, no more wrong-date reminders.

**Independent Test**: Send a WhatsApp message at 2:00 PM asking "plan my day" — response should only include afternoon/evening items.

### Implementation for User Story 1

- [x] T001 [US1] Add time-awareness rules to SYSTEM_PROMPT in src/assistant.py. After rule 11 (Outlook/work calendar), add a new rule block: "**Time awareness (CRITICAL):** ALWAYS check the **Right now** timestamp at the top of this prompt before generating any schedule, plan, reminder, or time-based recommendation. (a) Never suggest activities or time blocks for hours that have already passed today. If it's 1 PM, start the plan from 1 PM. (b) When a user says 'today,' 'tomorrow,' 'tonight,' or 'this afternoon,' resolve it against the current date and time shown above. (c) If a user requests a reminder or event for a time that has already passed today, point this out and ask if they mean tomorrow. (d) When generating a daily plan partway through the day, acknowledge what time it is and show only remaining activities."
- [x] T002 [US1] Fix date format consistency in src/assistant.py. On the `date_line` (line ~1617), change `%B %d` to `%B %-d` and `%I:%M` to `%-I:%M` so the format matches context.py (unpadded: "March 3" not "March 03", "1:30 PM" not "01:30 PM").
- [x] T003 [US1] Inject current timestamp into user message content in src/assistant.py. In the `handle_message` function, after the `date_line` is computed (~line 1617) and before the messages list is built (~line 1610), prepend a time context string to `user_content`. For string content: `user_content = f"[Current time: {now.strftime('%A, %B %-d, %Y at %-I:%M %p Pacific')}]\n{user_content}"`. For image content (list format): insert a text block at position 0 with the same time prefix before the `[From sender_name]` block. This ensures the timestamp is directly adjacent to the user's message, not just in the distant system prompt.
- [x] T004 [US1] Verify time awareness: start the server locally, check that the system prompt includes the new time-awareness rules, and confirm the user message content includes the `[Current time: ...]` prefix in the log output.

**Checkpoint**: Claude now sees the current time adjacent to every user message and has explicit rules about using it. Time-aware scheduling should work.

---

## Phase 3: User Story 2 — Extended Conversation Memory (Priority: P1)

**Goal**: Conversation history retained for 7 days / 100 turns instead of 24 hours / 25 turns. The bot remembers what was discussed earlier in the week.

**Independent Test**: Send a message, wait 25+ hours, send another message referencing the first — the bot should recall it.

**Depends on**: No dependency on US1 (different file). Can run in parallel.

### Implementation for User Story 2

- [x] T005 [P] [US2] Update conversation retention constants in src/conversation.py. Change `CONVERSATION_TIMEOUT = 86400` to `CONVERSATION_TIMEOUT = 604800` (7 days in seconds). Change `MAX_CONVERSATION_TURNS = 25` to `MAX_CONVERSATION_TURNS = 100`.
- [x] T006 [US2] Add per-turn timestamps to `save_turn()` in src/conversation.py. When appending a new turn (~line 176), change from `conv["turns"].append({"messages": serialized})` to `conv["turns"].append({"messages": serialized, "timestamp": datetime.now().isoformat()})`. This enables per-turn pruning in T007.
- [x] T007 [US2] Add per-turn age-based pruning to `get_history()` in src/conversation.py. After the existing expiry check (~line 138-144), add turn-level pruning: iterate through `conv["turns"]` and remove any turn whose `timestamp` is older than 7 days. Turns without a `timestamp` field (old data) should be kept (they'll fall off the 100-turn limit naturally). Replace the existing whole-conversation expiry check with this per-turn approach — remove the `last_active` timeout check that deletes the entire conversation, and instead prune individual old turns. If all turns are pruned, delete the conversation entry.
- [x] T008 [US2] Verify extended context: activate the venv, push a test conversation turn, confirm the turn has a `timestamp` field in `data/conversations.json`, and verify the constants are correct per quickstart.md Scenario 8.

**Checkpoint**: Conversations now persist for 7 days with per-turn pruning. The bot remembers earlier-in-the-week discussions.

---

## Phase 4: Polish & Deployment

**Purpose**: Deploy, validate end-to-end, and close GitHub issue.

- [ ] T009 Commit all changes, push to branch, deploy to NUC via `./scripts/nuc.sh deploy`.
- [ ] T010 Run quickstart.md Scenarios 1-4 (time awareness) against production: send a WhatsApp message after noon asking for a daily plan, verify no morning items appear. Check server logs for `[Current time: ...]` prefix in user messages.
- [ ] T011 Run quickstart.md Scenarios 5-6 (extended context) against production: send a message, wait, then reference it hours later — verify the bot recalls it.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A — no setup needed
- **US1 (Phase 2)**: T001-T004 — changes to src/assistant.py only
- **US2 (Phase 3)**: T005-T008 — changes to src/conversation.py only
- **Polish (Phase 4)**: T009-T011 — depends on both user stories complete

### User Story Dependencies

- **US1 (P1)**: Independent. Modifies only src/assistant.py.
- **US2 (P1)**: Independent. Modifies only src/conversation.py.

### Parallel Opportunities

- T001, T002, T003 are sequential (same file, same area of code)
- T005 can run in parallel with T001-T004 (different file entirely)
- T006 and T007 are sequential (T007 depends on T006's timestamp field)
- US1 and US2 are fully parallelizable (different files, no shared code)

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete T001-T003 (time-awareness rules + timestamp injection)
2. Complete T004 (verify locally)
3. **STOP and VALIDATE**: Send test messages, confirm time-aware responses
4. Deploy if ready — Erin immediately gets better scheduling responses

### Incremental Delivery

1. T001-T004 → US1 complete → Time-aware responses work
2. T005-T008 → US2 complete → 7-day conversation memory
3. T009-T011 → Deployed and validated on NUC

---

## Notes

- Total: 11 tasks
- No new Python dependencies needed
- ~15 lines of changes across 2 files (assistant.py, conversation.py)
- US1 and US2 are fully independent — can be implemented in any order
- Closes GitHub Issue #7 (Time-context-aware recommendations)
