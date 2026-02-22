# Tasks: AI-Powered Weekly Family Meeting Assistant

**Input**: Design documents from `/specs/001-ai-meeting-assistant/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in feature specification. Test tasks omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, configuration, and Notion workspace

- [x] T001 Create project directory structure: `src/`, `src/tools/`, `tests/`, `tests/test_tools/`, `scripts/`
- [x] T002 Create `requirements.txt` with dependencies: anthropic, fastapi, uvicorn, notion-client, google-api-python-client, google-auth-oauthlib, google-auth-httplib2, ynab, python-dotenv, httpx
- [x] T003 [P] Create `.env.example` with all required environment variables per `specs/001-ai-meeting-assistant/quickstart.md` Environment Variables section
- [x] T004 [P] Implement environment variable loading and validation in `src/config.py` — load from .env, validate all required keys present, export as typed constants
- [ ] T005 Set up Notion workspace — manually create the 3 databases (Action Items, Meal Plans, Meetings) and Family Profile page with schema per `contracts/notion-schema.md`, share with Notion integration, record database IDs in `.env`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core WhatsApp ↔ Claude pipeline that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Implement WhatsApp webhook verification endpoint (`GET /webhook`) in `src/app.py` — handle `hub.mode`, `hub.verify_token`, return `hub.challenge` per `contracts/whatsapp-webhook.md`
- [x] T007 Implement WhatsApp inbound message handler (`POST /webhook`) in `src/app.py` — extract sender phone number, message text, and contact name from Meta payload per `contracts/whatsapp-webhook.md`; return 200 immediately, process asynchronously. Reject messages from unrecognized phone numbers with a log warning (do not reply).
- [x] T008 [P] Implement WhatsApp outbound message helper in `src/whatsapp.py` — send text messages via Meta Graph API (`POST https://graph.facebook.com/v21.0/{phone-number-id}/messages`), handle 1,600 character limit by splitting long responses into multiple messages
- [x] T009 Implement Claude assistant core in `src/assistant.py` — initialize Anthropic client, define system prompt with family context and formatting instructions (ALL responses MUST use structured checklists with WhatsApp bold/list formatting per FR-005), set up tool runner with `model="claude-haiku-4-5"` and `max_tokens=1024`
- [x] T010 Implement Notion base client and `get_family_profile()` tool in `src/tools/notion.py` — connect to Notion API, read Family Profile page blocks, parse member info and preferences and recurring topics per `contracts/notion-schema.md`
- [x] T011 [P] Implement `update_family_profile(section, content)` tool in `src/tools/notion.py` — append or update a specific section of the Family Profile page (e.g., add a dietary preference like "Zoey doesn't like mushrooms", update recurring topics). Claude calls this when a partner mentions a persistent preference in conversation.
- [x] T012 Implement phone-number-to-partner-name mapping in `src/config.py` using `JASON_PHONE` and `SARAH_PHONE` env vars
- [x] T013 Wire the full message pipeline in `src/app.py` — on inbound message: identify sender via phone mapping (T012), call `assistant.handle_message()` (T009), send response via `whatsapp.send_message()` (T008)

**Checkpoint**: At this point, sending a WhatsApp message to the bot should get a conversational Claude response (no tools yet). The pipeline works end-to-end.

---

## Phase 3: User Story 1 — Weekly Meeting Agenda Generation (Priority: P1) 🎯 MVP

**Goal**: Generate a structured weekly meeting agenda from a single WhatsApp message, pulling calendar events and open action items

**Independent Test**: Send "prepare this week's agenda" in WhatsApp → receive formatted checklist agenda with real calendar events and any existing action items per `quickstart.md` Scenario 1

**Note**: US1 acceptance scenario 2 (rolled-over action items in Review section) only fully passes after US2 is implemented. MVP agenda will show any manually-created Notion action items but auto-rollover logic comes in Phase 4.

### Implementation for User Story 1

- [x] T014 [P] [US1] Implement `get_calendar_events(days_ahead)` tool in `src/tools/calendar.py` — authenticate via OAuth2 (Desktop app flow), fetch events from Google Calendar API v3 using `timeMin`/`timeMax`/`singleEvents=true`/`orderBy=startTime`, return list of event summaries with dates/times
- [x] T015 [P] [US1] Implement `get_action_items(assignee, status)` tool in `src/tools/notion.py` — query Action Items database with optional filters per `contracts/notion-schema.md`, return list of items with description, assignee, status, rolled-over flag
- [x] T016 [P] [US1] Implement `add_topic(description)` tool in `src/tools/notion.py` — store custom topics as Action Items with `Due Context = "Custom Topic"` so they appear in agenda queries and can be cleared after the meeting
- [x] T017 [US1] Implement `create_meeting(date)` tool in `src/tools/notion.py` — create a new Meeting page in Meetings database with status "Planned", save generated agenda as block content per `contracts/notion-schema.md`
- [x] T018 [US1] Register US1 tools (`get_calendar_events`, `get_action_items`, `add_topic`, `get_family_profile`, `update_family_profile`, `create_meeting`) in `src/assistant.py` tool definitions
- [x] T019 [US1] Add agenda-specific formatting instructions to Claude system prompt in `src/assistant.py` — sections: Calendar, Action Review, Chores, Meals, Finances, Goals, Custom Topics; use WhatsApp bold headers and bullet lists

**Checkpoint**: User Story 1 is fully functional. Sending "prepare this week's agenda" returns a complete formatted agenda. This is the MVP — deployable and usable independently.

---

## Phase 4: User Story 2 — Meeting Action Item Capture (Priority: P2)

**Goal**: Parse natural language action items, assign to partners, track completion through the week

**Independent Test**: Send "Jason: grocery shopping. Erin: schedule dentist" → items appear in Notion with correct assignees. Then send "what's on my list?" → see personalized checklist. Then send "done with grocery shopping" → item marked complete. Per `quickstart.md` Scenarios 2 and 3.

### Implementation for User Story 2

- [x] T020 [P] [US2] Implement `add_action_item(assignee, description, due_context)` tool in `src/tools/notion.py` — create page in Action Items database with properties: Assignee, Status="Not Started", Due Context, Created date, Meeting relation per `contracts/notion-schema.md`
- [x] T021 [P] [US2] Implement `complete_action_item(description)` tool in `src/tools/notion.py` — Claude identifies the correct item from `get_action_items` results by context (no custom fuzzy matching code needed), then update Status to "Done" by page ID
- [x] T022 [US2] Implement action item auto-rollover in `src/tools/notion.py` — when agenda is generated (T017), query items where `Status != Done AND Due Context = This Week`, set `Rolled Over = true` on carried-forward items
- [x] T023 [US2] Register US2 tools (`add_action_item`, `complete_action_item`) in `src/assistant.py` tool definitions
- [x] T024 [US2] Add action-item parsing instructions to Claude system prompt in `src/assistant.py` — handle bulk assignment format ("Jason: task1, task2. Erin: task3"), confirmation formatting, per-person checklist queries

**Checkpoint**: User Stories 1 AND 2 are both functional. Action items can be captured, tracked, and rolled over into agendas.

---

## Phase 5: User Story 3 — Weekly Meal Planning (Priority: P3)

**Goal**: Generate AI-powered weekly meal plans with grocery lists, save to Notion, allow conversational edits

**Independent Test**: Send "plan meals for this week" → receive 7-day plan + grocery list. Send "swap Wednesday for tacos" → updated plan. Per `quickstart.md` Scenario 4.

### Implementation for User Story 3

- [x] T025 [P] [US3] Implement `save_meal_plan(week_start, plan_content, grocery_list)` tool in `src/tools/notion.py` — create Meal Plan page with toggle headings per day, bullet items per meal, and grocery checklist blocks per `contracts/notion-schema.md`
- [x] T026 [P] [US3] Implement `get_meal_plan(week_start)` tool in `src/tools/notion.py` — query Meal Plans database by date, read page blocks, return structured plan and grocery list
- [x] T027 [US3] Register US3 tools (`save_meal_plan`, `get_meal_plan`) in `src/assistant.py` tool definitions
- [x] T028 [US3] Add meal planning instructions to Claude system prompt in `src/assistant.py` — kid-friendly defaults, 7-day format, consolidated grocery list, swap/edit handling, read preferences from family profile

**Checkpoint**: User Stories 1, 2, AND 3 are all functional. Meal plans can be generated, stored in Notion, and edited conversationally.

---

## Phase 6: User Story 4 — Budget & Finance Check-In (Priority: P4)

**Goal**: Pull YNAB budget data and present a conversational financial summary during meetings

**Independent Test**: Send "budget summary" → receive formatted summary with over/under categories and savings goals. Send "how much on dining out?" → specific category answer. Per `quickstart.md` Scenario 5.

### Implementation for User Story 4

- [x] T029 [P] [US4] Implement `get_budget_summary(month, category)` tool in `src/tools/ynab.py` — authenticate with Personal Access Token, call `GET /budgets/{id}/months/{month}`, parse categories with budgeted/activity/balance/goal data, convert milliunits to dollars
- [x] T030 [US4] Register US4 tool (`get_budget_summary`) in `src/assistant.py` tool definitions
- [x] T031 [US4] Add budget formatting instructions to Claude system prompt in `src/assistant.py` — flag over-budget categories at top, show savings goal progress, support category-specific queries

**Checkpoint**: All four user stories are functional. The complete family meeting assistant is operational.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, deployment, and validation across all user stories

- [x] T032 Add graceful API outage handling in `src/assistant.py` — if a tool call raises an exception (Calendar, YNAB, Notion down), catch the error and return a user-friendly message telling Claude to skip that section per spec FR-012
- [x] T033 [P] Add request logging and response time tracking in `src/app.py` — log inbound messages (sender, timestamp), outbound responses (length, tool calls made, response time in seconds) for debugging and FR-011 monitoring
- [x] T034 [P] Create deployment configuration — `Procfile` or `railway.toml` or `render.yaml` for chosen hosting platform, with uvicorn start command
- [x] T035 [P] Create Google Calendar OAuth token initialization script in `scripts/setup_calendar.py` — run once locally to complete OAuth flow and save `token.json` for server use
- [ ] T036 Run `quickstart.md` end-to-end validation — test all 5 scenarios against live WhatsApp sandbox. Verify: (a) all responses use structured checklist formatting per FR-005, (b) responses arrive within 30 seconds per FR-011, (c) all Notion records are created with correct schema

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately. T005 (Notion workspace) is manual and must be done before any integration testing.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–6)**: All depend on Foundational phase completion
  - Stories can proceed sequentially in priority order (P1 → P2 → P3 → P4)
  - US2 depends lightly on US1 (auto-rollover reads action items during agenda generation)
  - US3 and US4 are fully independent of each other and of US1/US2
- **Polish (Phase 7)**: Can begin after US1 (MVP); remaining items after all stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — Integrates with US1 agenda (auto-rollover) but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) — Fully independent
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) — Fully independent

### Within Each User Story

- Tool implementations marked [P] can run in parallel (different files)
- Register tools in assistant.py after tool implementations are complete
- System prompt updates after tool registration

### Parallel Opportunities

- T003 and T004 can run in parallel (different files)
- T008 can run in parallel with T006/T007 (different file)
- T010 and T011 can run in parallel with T006–T008 (different file)
- T014, T015, T016 can all run in parallel (different files)
- T020, T021 can run in parallel (same file but independent functions)
- T025, T026 can run in parallel (same file but independent functions)
- T032, T033, T034, T035 can all run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (including T005 Notion workspace)
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test US1 against quickstart.md Scenario 1
5. Deploy to hosting platform (T034)

### Incremental Delivery

1. Setup + Foundational → Pipeline works (Claude responds via WhatsApp)
2. Add User Story 1 → Agenda generation works (MVP!)
3. Add User Story 2 → Action items tracked through the week
4. Add User Story 3 → Meal planning with grocery lists
5. Add User Story 4 → Budget check-ins during meetings
6. Polish → Error handling, logging, deployment hardened

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- `src/tools/notion.py` grows across stories — T010/T011 (base + profile), T015/T016/T017 (US1), T020/T021/T022 (US2), T025/T026 (US3)
- `src/assistant.py` grows across stories — T009 (core), T018/T019 (US1), T023/T024 (US2), T027/T028 (US3), T030/T031 (US4)
- T005 (Notion workspace setup) is a manual task in Phase 1 — must be done before any integration testing
- Dynamic learning: T011 (`update_family_profile`) lets the assistant update family preferences from conversation (e.g., "Zoey doesn't like mushrooms" → saved to Family Profile Preferences section)
