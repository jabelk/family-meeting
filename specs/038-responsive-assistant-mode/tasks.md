# Tasks: Responsive Assistant Mode

**Input**: Design documents from `/specs/038-responsive-assistant-mode/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Organization**: Tasks are grouped by user story. This is a lightweight feature — mostly prompt edits.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: No setup needed — all changes modify existing files. Proceed directly to user stories.

---

## Phase 2: User Story 1 — No Unsolicited Activity Suggestions (Priority: P1) 🎯 MVP

**Goal**: The bot never fills free time with backlog/chore suggestions unless the user explicitly asks.

**Independent Test**: Ask "schedule my day" with free time gaps — verify free time is shown as free, not filled with suggestions. Then ask "what should I do?" and verify it THEN suggests backlog items.

### Implementation for User Story 1

- [x] T001 [P] [US1] Remove Rule 12 from `src/prompts/system/03-daily-planner.md`. Delete the entire rule that says "For ANY free time slots in the daily plan (even 10-15 minutes), call get_backlog_items and suggest a specific backlog task that fits the window." Replace with: "For free time slots in a daily plan, show them as 'Free time' without suggesting activities. Only call get_backlog_items when the user explicitly asks 'what should I do?', 'what's on my backlog?', or similar direct requests for suggestions." Keep Rule 13 (explicit backlog requests) unchanged.

- [x] T002 [P] [US1] Update Rule 68 in `src/prompts/system/08-advanced.md` to remove proactive language from communication modes. Change the morning mode description from "energetic, proactive suggestions welcome, include tips" to "responsive, answer questions directly". Change afternoon from "normal, responsive to requests" to "responsive, answer questions directly". Change evening from "respond to questions, limit proactive content but still allow gentle nudges for imminent events" to "responsive, answer questions directly, no unsolicited content". Keep late_night unchanged ("direct answers only, no proactive suggestions").

- [x] T003 [P] [US1] Update communication mode descriptions in `src/context.py`. Find the `MODE_DESCRIPTIONS` or equivalent dict/tuple that maps mode names to description strings (around lines 32-37). Update to match the new descriptions from T002: morning → "responsive, answer questions directly", afternoon → "responsive, answer questions directly", evening → "responsive, answer questions directly, no unsolicited content", late_night → "direct answers only, no follow-up prompts".

- [x] T004 [US1] Modify proactive chore suggestion behavior in `src/prompts/system/05-chores-nudges.md`. In Rule 23, keep departure reminders (event-driven) but add: "Do NOT proactively suggest chores or activities. Only discuss chores when the user asks about them." In Rule 25, keep the "done"/"skip" handling for when the user brings up chores, but remove any language that implies the bot initiates chore suggestions.

- [x] T005 [US1] Update Rule 39 (contextual tips) in `src/prompts/system/08-advanced.md` or wherever Rule 39 is defined. Change "Maximum 1 tip per response" to "Maximum 1 tip per conversation. Only append a tip after the FIRST substantive tool interaction in a conversation, not on every tool-use response."

- [x] T006 [US1] Run `ruff check src/ && pytest tests/ -x -q` to verify all changes pass lint and existing tests.

**Checkpoint**: The bot no longer fills free time with suggestions, doesn't proactively suggest chores, and responds directly without appending tips on every message. This is the MVP — deploy and observe.

---

## Phase 3: User Story 2 — Structured Dietary Preferences (Priority: P2)

**Goal**: Dietary constraints persist across conversations and are automatically enforced during meal planning.

**Independent Test**: Say "no vegetarian meals" → verify it's saved as a dietary preference. Ask for dinner suggestions → verify no vegetarian options appear.

### Implementation for User Story 2

- [x] T007 [US2] Add `"dietary"` to the valid preference categories in `src/preferences.py`. Find the `VALID_CATEGORIES` tuple/set (around line 24-29) and add `"dietary"` alongside existing categories (notification_optout, topic_filter, communication_style, quiet_hours).

- [x] T008 [US2] Add dietary preference detection instruction to the system prompt. In `src/prompts/system/08-advanced.md`, near Rule 55 (preference persistence), add: "Rule 55b: When a user expresses a DIETARY constraint ('no vegetarian meals', 'Jason doesn't eat fish', 'no pork', 'we don't eat shellfish'), call save_preference with category='dietary'. Format the description as: '{constraint} — {context}' (e.g., 'No vegetarian meals — family preference', 'No fish for Jason — exclude when Jason is eating'). Dietary preferences are automatically enforced during meal planning."

- [x] T009 [US2] Add dietary preference enforcement instruction to the meal planning prompt. In `src/prompts/system/03-daily-planner.md` or wherever meal planning rules exist (check for meal plan references), add: "Before suggesting meals, recipes, or generating grocery lists, ALWAYS check the user's dietary preferences (visible in the preferences section above). If a dietary preference says 'no vegetarian', every suggested meal MUST include a protein source. If a preference says 'no fish for Jason', exclude fish dishes when planning meals Jason will eat. Never violate a dietary preference — if you can't find compliant options, say so."

- [x] T010 [US2] Run `ruff check src/ && pytest tests/ -x -q` to verify changes pass lint and tests.

**Checkpoint**: Dietary preferences are saved persistently and the LLM is instructed to check them before meal suggestions.

---

## Phase 4: User Story 3 — Quieter Communication Modes (Priority: P3)

**Goal**: All communication modes default to responsive behavior. No mode encourages proactive suggestions.

**Independent Test**: Already covered by T002 and T003. This phase validates the integration.

### Implementation for User Story 3

- [x] T011 [US3] Verify consistency between the communication mode descriptions in `src/context.py` (T003) and the Rule 68 instructions in `src/prompts/system/08-advanced.md` (T002). Read both files and confirm the mode names and descriptions match exactly. Fix any discrepancies.

- [x] T012 [US3] Run full test suite `pytest tests/ -v` and verify all tests pass. Fix any tests that depend on the old communication mode descriptions.

**Checkpoint**: Communication modes are consistently responsive across all code and prompt files.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all user stories.

- [x] T013 Run `ruff check src/ && ruff format --check src/` and fix any lint/format issues.
- [ ] T014 Run quickstart.md validation: manually test each scenario from `specs/038-responsive-assistant-mode/quickstart.md` against the deployed service.
- [ ] T015 Monitor WhatsApp conversations for 48 hours after deployment — verify zero unsolicited suggestions (SC-001) and that dietary preferences are enforced (SC-003).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (US1)**: No dependencies — start immediately
- **Phase 3 (US2)**: Independent of US1 — can run in parallel (different files)
- **Phase 4 (US3)**: Depends on T002 and T003 from US1 (mode descriptions must be updated first)
- **Phase 5 (Polish)**: Depends on all previous phases

### User Story Dependencies

- **US1 (P1)**: No dependencies — all prompt files
- **US2 (P2)**: No code dependencies on US1 — modifies preferences.py + different prompt sections
- **US3 (P3)**: Verifies US1 changes — sequential after US1

### Parallel Opportunities

- T001, T002, T003 can all run in parallel (different files)
- T007 and T008 can run in parallel (different files)
- US1 (prompt changes) and US2 (preference + prompt changes) can run in parallel — they modify different prompt sections

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001-T006 (remove proactive rules)
2. **STOP and VALIDATE**: Deploy, ask Erin to "schedule my day" — verify no nagging
3. If clean → continue to US2 (dietary preferences)

### Incremental Delivery

1. US1 (T001-T006) → Deploy → Monitor (MVP — no more nagging!)
2. US2 (T007-T010) → Deploy → Test dietary preferences via WhatsApp
3. US3 (T011-T012) → Deploy → Verify mode consistency
4. Polish (T013-T015) → Final validation + 48h monitoring

---

## Notes

- This is a prompt-heavy feature — most tasks are editing markdown prompt files
- No new Python code beyond adding "dietary" to a tuple in preferences.py
- Risk is low — worst case, reverting prompt files restores old behavior
- The "Did you know?" tip frequency change (T005) may need tuning after observation
