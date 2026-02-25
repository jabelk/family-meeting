# Tasks: Holistic Family Intelligence

**Input**: Design documents from `/specs/008-holistic-family-intelligence/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/system-prompt-additions.md, contracts/meeting-prep-endpoint.md, quickstart.md

**Tests**: No automated tests requested. Validation via manual SSH + docker compose exec testing per quickstart.md.

**Organization**: Tasks are grouped by user story. All three stories modify the same file (`src/assistant.py`) so they must be sequential. US1 is the foundational behavioral change; US2 and US3 build on the same cross-domain reasoning rules.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Read Current State)

**Purpose**: Read and understand the current system prompt and daily plan function before making changes

- [x] T001 Read the current system prompt in `src/assistant.py` (lines 24-230) and identify the exact insertion point after Rule 38 (the last existing rule) where new cross-domain rules will be appended
- [x] T002 Read the current `generate_daily_plan()` function in `src/assistant.py` (lines 1114-1126) and the current `generate_meeting_prep()` if it exists, to understand the exact prompt strings to modify

---

## Phase 2: User Story 1 — Cross-Domain Questions (Priority: P1) 🎯 MVP

**Goal**: When Erin asks broad questions that span multiple areas of family life, the bot connects dots across calendar, budget, meals, chores, and action items — giving unified advice instead of siloed tool responses.

**Independent Test**: Ask "how's our week looking?" and verify the response weaves together 2+ domains into narrative advice with specific recommendations.

### Implementation for User Story 1

- [x] T003 [US1] Append Rule 39 (Recognize Cross-Domain Questions) to the system prompt in `src/assistant.py` — add after the last existing rule. The rule should list broad question triggers ("how's our week", "are we on track", "I feel behind", "can we afford to", "give me the big picture") and specify that single-domain questions ("what's on the calendar", "check the budget") should be answered directly without cross-domain additions. Use the exact rule text from `contracts/system-prompt-additions.md`.
- [x] T004 [US1] Append Rule 40 (Synthesize, Don't Stack) to the system prompt in `src/assistant.py` — instructs Claude to weave cross-domain insights into coherent narrative, not separate bulleted sections per tool. Include the good/bad example from the contract.
- [x] T005 [US1] Append Rule 41 (Be a Strategist, Not a Reporter) to the system prompt in `src/assistant.py` — instructs Claude to include specific actionable recommendations, connect dots for Erin, and suggest concrete actions (swap meals, use pantry staples, etc.)
- [x] T006 [US1] Append Rule 42 (Know When NOT to Cross Domains) to the system prompt in `src/assistant.py` — instructs Claude not to force connections when irrelevant, and that cross-domain reasoning should feel natural not shoehorned
- [x] T007 [US1] Append Rule 43 (Conflicting Priorities) to the system prompt in `src/assistant.py` — instructs Claude to present tradeoffs honestly with a recommendation when domains conflict
- [x] T008 [US1] Append Rule 44 (Think Deeper, Not Just Wider) to the system prompt in `src/assistant.py` — instructs Claude to dig into root causes for "why" questions, check transaction patterns, and connect causes to effects. Include the DoorDash/late meetings example.
- [x] T009 [US1] Append Rule 45 (Track Progress Over Time) to the system prompt in `src/assistant.py` — instructs Claude to look for trends when asked about goals/progress, compare current to historical data, and celebrate wins. Include the restaurant spending example.
- [ ] T010 [US1] Test cross-domain question on NUC via quickstart.md Test 1 — ask "how's our week looking?" and verify response references 2+ domains with narrative advice
- [ ] T011 [US1] Test cross-domain decision question on NUC via quickstart.md Test 2 — ask "can we afford to eat out this weekend?" and verify it checks budget + calendar + meal plan
- [ ] T012 [US1] Test single-domain stays focused on NUC via quickstart.md Test 3 — ask "what did we spend at Costco this month?" and verify response stays focused without unnecessary cross-domain padding

**Checkpoint**: Cross-domain questions work with holistic reasoning. Single-domain questions stay focused. Validate with quickstart.md Tests 1-3.

---

## Phase 3: User Story 2 — Smarter Daily Briefing (Priority: P2)

**Goal**: The daily briefing includes cross-domain insights connecting schedule to meals, budget, and tasks — not just a calendar dump.

**Independent Test**: Trigger the daily briefing and verify it includes at least one cross-domain insight.

### Implementation for User Story 2

- [x] T013 [US2] Append Rule 46 (Daily Briefing Cross-Domain Synthesis) to the system prompt in `src/assistant.py` — instructs Claude to also check budget health, tonight's meal plan, overdue action items, and pending grocery orders when generating the daily plan, weaving insights in naturally
- [x] T014 [US2] Append Rule 47 (Briefing Conversation Continuity) to the system prompt in `src/assistant.py` — instructs Claude to handle follow-up adjustments to the briefing using existing tools and conversation memory
- [x] T015 [US2] Modify `generate_daily_plan()` in `src/assistant.py` — expand the prompt string to include cross-domain synthesis instructions: "Also check: budget health (any notable over/under?), tonight's meal plan (does complexity match schedule density?), and any overdue action items or pending grocery orders. Weave cross-domain insights into the briefing naturally — don't add separate sections."
- [ ] T016 [US2] Test enhanced daily briefing on NUC via quickstart.md Test 4 — call `generate_daily_plan('erin')` and verify it includes traditional elements plus at least one cross-domain insight
- [ ] T017 [US2] Test briefing conversation follow-up on NUC via quickstart.md Test 5 — send a briefing request via handle_message, then follow up with an adjustment request and verify it acts on it

**Checkpoint**: Daily briefing includes cross-domain insights. Erin can reply to adjust. Validate with quickstart.md Tests 4-5.

---

## Phase 4: User Story 3 — Weekly Meeting Prep (Priority: P3)

**Goal**: The bot generates a comprehensive meeting agenda synthesizing budget, calendar, action items, meals, and priorities.

**Independent Test**: Ask "prep me for our family meeting" and verify the response covers all 5 agenda sections with headline insights.

### Implementation for User Story 3

- [x] T018 [US3] Append Rule 48 (Meeting Prep Trigger) to the system prompt in `src/assistant.py` — defines trigger phrases and the 5-section agenda structure (budget snapshot, calendar review, action items, meal plan, priorities)
- [x] T019 [US3] Append Rule 49 (Meeting Prep Format) to the system prompt in `src/assistant.py` — defines the WhatsApp formatting with bold headline insights per section, bullet details, and synthesized discussion points at the end
- [x] T020 [US3] Add `generate_meeting_prep()` function in `src/assistant.py` — lightweight trigger function (like `generate_daily_plan()`) that calls `handle_message("system", prompt)` with a prompt referencing Rules 48-49. Place it after `generate_daily_plan()`.
- [x] T021 [P] [US3] Add `POST /api/v1/meetings/prep-agenda` endpoint in `src/app.py` — follows the same pattern as `/api/v1/briefing/daily`, calls `generate_meeting_prep()`, sends result to Erin's phone via `send_message()`, returns `{"status": "ok", "agenda": ...}`. Include n8n auth verification.
- [ ] T022 [US3] Test meeting prep via WhatsApp on NUC via quickstart.md Test 6 — ask "prep me for our family meeting" and verify all 5 sections appear with headline insights
- [ ] T023 [US3] Test meeting prep endpoint on NUC via quickstart.md Test 7 — call `generate_meeting_prep()` directly and verify it returns a complete agenda

**Checkpoint**: Meeting prep works both ad-hoc and via endpoint. All 5 sections present with insights. Validate with quickstart.md Tests 6-7.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Syntax check, deploy, and validate all scenarios

- [x] T024 Python syntax check both `src/assistant.py` and `src/app.py` via `python3 -c "import py_compile; py_compile.compile('src/assistant.py', doraise=True); py_compile.compile('src/app.py', doraise=True)"`
- [ ] T025 Deploy to NUC via `./scripts/nuc.sh deploy` and run full quickstart.md validation (all 7 test scenarios)
- [x] T026 Verify that the system prompt size is reasonable — check the token count increase is ~1-1.5K tokens, not dramatically inflating the prompt

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — read existing code to understand insertion points
- **US1 (Phase 2)**: Depends on Phase 1 — needs to know where to insert rules
- **US2 (Phase 3)**: Depends on US1 — the cross-domain reasoning rules from US1 are prerequisites for the enhanced briefing
- **US3 (Phase 4)**: Depends on US1 — the cross-domain reasoning rules inform meeting prep behavior
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 1 — contains the core behavioral rules (Rules 39-45)
- **US2 (P2)**: Depends on US1 — enhanced briefing relies on cross-domain reasoning rules being in place
- **US3 (P3)**: Depends on US1 — meeting prep relies on cross-domain reasoning rules. T021 (app.py endpoint) can run in parallel with T018-T020 since it's a different file.

### Within User Story 1

- T003-T009 must be sequential (same file, appending rules in order)
- T010-T012 (validation) must wait for T003-T009

### Within User Story 3

- T018-T020 (assistant.py changes) must be sequential
- T021 (app.py endpoint) can run in parallel with T018-T020 [P]

### Files Modified

- `src/assistant.py` — **MODIFIED** (T003-T009, T013-T015, T018-T020): system prompt rules + enhanced briefing + meeting prep function
- `src/app.py` — **MODIFIED** (T021): meeting prep endpoint

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: User Story 1 (T003-T012)
3. **STOP and VALIDATE**: Send broad questions and verify cross-domain reasoning
4. Deploy if ready — Erin immediately gets smarter responses

### Incremental Delivery

1. Setup + US1 → Cross-domain questions work → Deploy (MVP!)
2. Add US2 → Enhanced daily briefing → Deploy
3. Add US3 → Meeting prep capability → Deploy
4. Each phase adds strategic intelligence without breaking previous behavior

### Full Build Order (Sequential)

1. T001 → T002
2. T003 → T004 → T005 → T006 → T007 → T008 → T009
3. T010 → T011 → T012
4. T013 → T014 → T015
5. T016 → T017
6. T018 → T019 → T020 (parallel: T021)
7. T022 → T023
8. T024 → T025 → T026

---

## Notes

- This feature is primarily **prompt engineering** — no new tools, databases, or modules
- All system prompt rules are appended sequentially to the same string in `src/assistant.py`
- The rules follow the same numbered format (39-49) as the existing 38 rules
- T021 is the only task that touches a different file (`src/app.py`), making it the only parallelizable implementation task
- Validation tasks (T010-T012, T016-T017, T022-T023) require deployment to NUC first
- The system prompt changes are universal — they improve ALL interactions, not just briefings
- Commit after each phase or logical group
- Stop at any checkpoint to validate story independently
