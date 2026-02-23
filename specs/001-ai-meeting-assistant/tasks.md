# Tasks: AI-Powered Weekly Family Meeting Assistant

**Input**: Design documents from `/specs/001-ai-meeting-assistant/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Context**: A v1 implementation exists with core FastAPI webhook, Claude assistant (12 tools), Notion CRUD, single Google Calendar read, YNAB read, and WhatsApp send/receive. These tasks expand to v2: multi-calendar read/write, Outlook ICS, daily planner, backlog management, AnyList grocery bridge, n8n automation endpoints, and Docker Compose deployment.

**Tests**: Not explicitly requested — test tasks omitted. Each user story has an end-to-end validation task instead.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Update project configuration and dependencies for v2 scope

- [x] T001 Update requirements.txt to add icalendar, recurring-ical-events dependencies in requirements.txt
- [x] T002 [P] Update .env.example to add v2 env vars (OUTLOOK_CALENDAR_ICS_URL, GOOGLE_CALENDAR_JASON_ID, GOOGLE_CALENDAR_ERIN_ID, GOOGLE_CALENDAR_FAMILY_ID, ANYLIST_EMAIL, ANYLIST_PASSWORD, ANYLIST_SIDECAR_URL, NOTION_BACKLOG_DB, NOTION_GROCERY_HISTORY_DB) and replace old GOOGLE_CALENDAR_ID with the 3 new calendar IDs in .env.example
- [x] T003 [P] Update src/config.py to load and validate all new env vars (OUTLOOK_CALENDAR_ICS_URL, 3 Google Calendar IDs, AnyList credentials, ANYLIST_SIDECAR_URL, NOTION_BACKLOG_DB, NOTION_GROCERY_HISTORY_DB) with optional flags for services not yet configured in src/config.py
- [x] T004 [P] Create Dockerfile for FastAPI service: Python 3.12 slim, install requirements, copy src/, expose 8000, CMD uvicorn in Dockerfile
- [x] T005 Complete Notion workspace setup per docs/notion-setup.md: create Action Items, Meal Plans, Meetings databases with properties per contracts/notion-schema.md, create Backlog database (7 properties per data-model.md), create Grocery History database (5 properties per data-model.md), create Family Profile page with all sections, share all with integration, record database IDs in .env (manual step, paused mid-setup)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core tool modules that MUST be complete before ANY user story can be implemented

**Note**: Tasks touching the same file are sequential within that file. Tasks on different files are marked [P].

### Google Calendar (read + write)

- [x] T006 Refactor src/tools/calendar.py to support 3 named calendars: replace single GOOGLE_CALENDAR_ID with JASON/ERIN/FAMILY calendar IDs, update get_calendar_events to accept calendar_names parameter and merge results from multiple calendars in src/tools/calendar.py
- [x] T007 Add Google Calendar write capability to src/tools/calendar.py: create_event (single), batch_create_events (weekly population), delete_assistant_events (filter by extendedProperties.private.createdBy), color coding constants (Tangerine=chores, Sage=rest, Basil=development, Grape=exercise, Banana=side work, Lavender=backlog) in src/tools/calendar.py

### Outlook ICS

- [x] T008 [P] Create src/tools/outlook.py: fetch ICS from OUTLOOK_CALENDAR_ICS_URL via httpx, parse with icalendar library, expand recurring events with recurring-ical-events, return get_outlook_events(date) as list of (summary, start, end) tuples. Graceful fallback if URL not configured or fetch fails in src/tools/outlook.py

### Notion (backlog + routine templates + grocery history)

- [x] T009 Add Backlog CRUD to src/tools/notion.py: get_backlog_items(assignee, status), add_backlog_item(description, category, assignee, priority), complete_backlog_item(page_id), get_next_backlog_suggestion() that returns least-recently-surfaced incomplete item and updates Last Surfaced date in src/tools/notion.py
- [x] T010 Add routine template helpers to src/tools/notion.py: get_routine_templates() that reads "Routine Templates" section from Family Profile page and parses structured time block text, save_routine_templates(templates_text) that writes updated templates back in src/tools/notion.py
- [x] T011 Add Grocery History read to src/tools/notion.py: get_grocery_history(category) to list items, get_staple_items() to return items where Staple=true sorted by frequency. Skip gracefully if NOTION_GROCERY_HISTORY_DB not configured in src/tools/notion.py

### Assistant system prompt

- [x] T012 Update SYSTEM_PROMPT in src/assistant.py: add daily planner context (Erin's routine needs, breakfast details, childcare schedule, Vienna school 9:30am, backlog concept), instruct Claude to use routine templates for daily plans, reference grocery history for meal planning, explain calendar write capability in src/assistant.py

**Checkpoint**: All tool modules support v2 operations. User story implementation can begin.

---

## Phase 3: User Story 1 — Weekly Meeting Agenda Generation (Priority: P1) 🎯 MVP

**Goal**: Either partner sends "prepare this week's agenda" and receives a structured, scannable checklist agenda pulling from all calendar sources, pending action items, and recurring topics.

**Independent Test**: Send "prepare this week's agenda" → receive formatted agenda with events from all 3 Google Calendars + Outlook, action items with rollover status, and standard meeting categories.

- [x] T013 [US1] Update get_calendar_events tool definition in src/assistant.py to pass calendar_names=["jason","erin","family"] and label events by source calendar in src/assistant.py
- [x] T014 [US1] Add get_outlook_events tool definition to src/assistant.py: tool name "get_outlook_events", input_schema with date parameter, wire handler to src/tools/outlook.get_outlook_events in src/assistant.py
- [x] T015 [US1] Update agenda generation instructions in SYSTEM_PROMPT to include Outlook work events in the "This Week" section and label them as Jason's work calendar in src/assistant.py
- [ ] T016 [US1] End-to-end validation: send "prepare this week's agenda" via WhatsApp webhook, verify response includes events from multiple calendars, action item review section, and all standard categories per quickstart.md Scenario 1

**Checkpoint**: Weekly agenda generation works with all calendar sources. MVP deliverable.

---

## Phase 4: User Story 5 — Daily Planner & Morning Briefing (Priority: P2)

**Goal**: Each morning, Erin receives a structured daily plan (auto-sent at 7am or on-demand) that accounts for childcare, Jason's meetings, chore blocks, rest time, development time, and a backlog suggestion. Time blocks are written to her Google Calendar.

**Independent Test**: Trigger daily briefing endpoint or send "what's my day look like?" → receive structured daily plan with time blocks, childcare info, Jason's meeting windows → verify calendar events appear on Erin's Google Calendar.

### Assistant tools for daily planner

- [x] T017 [US5] Add get_backlog_items, add_backlog_item, and complete_backlog_item tool definitions to src/assistant.py: wire handlers to corresponding functions in src/tools/notion.py in src/assistant.py
- [x] T018 [US5] Add get_routine_templates tool definition to src/assistant.py: wire handler to src/tools/notion.get_routine_templates in src/assistant.py
- [x] T019 [US5] Add write_calendar_blocks tool definition to src/assistant.py: accepts list of time blocks (summary, start, end, color_category), calls src/tools/calendar.batch_create_events with extendedProperties tagging in src/assistant.py
- [x] T020 [US5] Add generate_daily_plan instructions to SYSTEM_PROMPT in src/assistant.py: when user asks "what's my day look like" or daily briefing is triggered, orchestrate: read routine templates → check childcare context → fetch Outlook + Google Calendar events → pick backlog item → select/adapt template → format plan → write calendar blocks → send WhatsApp in src/assistant.py

### n8n automation endpoints

- [x] T021 [US5] Add POST /api/v1/briefing/daily endpoint in src/app.py: accepts {"target": "erin"}, constructs daily plan prompt, runs through assistant, writes calendar blocks, sends WhatsApp. Returns {"status": "sent", "blocks_created": N} in src/app.py
- [x] T022 [US5] Add POST /api/v1/calendar/populate-week endpoint in src/app.py: accepts {"week_start": "YYYY-MM-DD"}, calls delete_assistant_events for the week then batch_create_events for Mon-Fri using routine templates adapted per day. Returns {"status": "populated", "events_created": N} in src/app.py
- [x] T023 [US5] Add POST /api/v1/prompt/grandma-schedule endpoint in src/app.py: sends WhatsApp message "What days is grandma taking Zoey this week?" to group chat. Claude parses the reply through regular webhook flow. Returns {"status": "prompted"} in src/app.py

### Context override handling

- [x] T024 [US5] Add childcare context override handling in src/assistant.py: when a partner says "mom isn't taking Zoey today" or "grandma has Zoey Wednesday", update stored context in Family Profile via update_family_profile and offer to regenerate today's plan in src/assistant.py

### Validation

- [ ] T025 [US5] End-to-end validation: POST /api/v1/briefing/daily → verify WhatsApp message with daily plan structure per quickstart.md Scenario 2, verify calendar events created on Erin's Google Calendar with correct color coding and extendedProperties tags

**Checkpoint**: Daily planner and morning briefing work. Erin can see her day in WhatsApp and Apple Calendar.

---

## Phase 5: User Story 2 — Meeting Action Item Capture (Priority: P3)

**Goal**: Partners capture action items conversationally and can query, complete, and review them. Incomplete items roll over to the next week's agenda. Weekly meeting now also reviews backlog items.

**Independent Test**: Send "Jason: grocery shopping, fix faucet. Erin: schedule dentist" → verify items created → "what's on my list?" → see personal items → "done with grocery shopping" → verify completion.

- [x] T026 [US2] Verify existing add_action_item, complete_action_item, get_action_items tools in src/assistant.py work correctly with current Notion implementation — test CRUD flow end-to-end in src/assistant.py
- [x] T027 [US2] Update rollover_incomplete_items in src/tools/notion.py to also generate a backlog review summary: list backlog items surfaced this week and their status (done/carry over) for inclusion in the weekly meeting agenda in src/tools/notion.py
- [ ] T028 [US2] End-to-end validation: send action items in natural language → verify parsed and stored in Notion → query "what's on my list?" → mark one complete → generate next week's agenda → verify rollover per quickstart.md Scenario 3

**Checkpoint**: Action item capture, tracking, and rollover work. Backlog items included in weekly review.

---

## Phase 6: User Story 3 — Weekly Meal Planning (Priority: P4)

**Goal**: Partners request a meal plan and receive a 7-day plan with grocery list. Claude uses grocery history for smarter suggestions and accurate item names.

**Independent Test**: Send "plan meals for this week" → receive 7-day plan + grocery list → "swap Wednesday for pasta" → updated plan.

- [x] T029 [US3] Verify existing save_meal_plan, get_meal_plan tools in src/assistant.py work with Notion implementation — test create and retrieve flow in src/assistant.py
- [x] T030 [US3] Add get_grocery_history and get_staple_items tool definitions to src/assistant.py: wire handlers to src/tools/notion.py functions. Update SYSTEM_PROMPT meal planning instructions to reference grocery history for item names and suggest staples in src/assistant.py
- [ ] T031 [US3] End-to-end validation: send "plan meals for this week" → verify 7-day plan with grocery list → test "swap Wednesday for pasta" → verify updated plan and grocery list per quickstart.md Scenario 5

**Checkpoint**: Meal planning works with grocery history context for smarter suggestions.

---

## Phase 7: User Story 4 — Budget & Finance Check-In (Priority: P5)

**Goal**: Partners ask for budget summary and receive a formatted overview from YNAB with overspent categories flagged.

**Independent Test**: Send "budget summary" → receive formatted budget with over/under categories, savings goals.

- [x] T032 [US4] Verify existing get_budget_summary tool in src/assistant.py works with YNAB API — test summary and single-category query in src/assistant.py
- [ ] T033 [US4] End-to-end validation: send "budget summary" → verify formatted output with over/under budget categories, savings goals → test "how much on dining out?" → verify single category response per quickstart.md Scenario 6

**Checkpoint**: Budget check-in works. YNAB integration complete.

---

## Phase 8: User Story 6 — Grocery List to Delivery (Priority: P6)

**Goal**: After meal plan generation, grocery list is pushed to AnyList for Whole Foods delivery. Fallback to formatted WhatsApp list if sidecar is unavailable.

**Independent Test**: Generate meal plan → "order groceries" → items appear in AnyList app → Erin taps "Order Pickup or Delivery" → Whole Foods.

### AnyList Node.js Sidecar

- [x] T034 [P] [US6] Create anylist-sidecar/package.json with dependencies: anylist (codetheweb/anylist), express, and start script in anylist-sidecar/package.json
- [x] T035 [US6] Create anylist-sidecar/server.js: Express REST API with GET /health, GET /items?list=, POST /add, POST /add-bulk, POST /remove, POST /clear endpoints. AnyList auth on startup from ANYLIST_EMAIL/ANYLIST_PASSWORD env vars. Re-auth on 401 in anylist-sidecar/server.js
- [x] T036 [US6] Create anylist-sidecar/Dockerfile: Node.js 20 Alpine, npm install, expose 3000, health check curl in anylist-sidecar/Dockerfile

### Python bridge + assistant integration

- [x] T037 [US6] Create src/tools/anylist_bridge.py: httpx async client for AnyList sidecar at ANYLIST_SIDECAR_URL (default http://anylist-sidecar:3000). Functions: push_grocery_list(items), clear_grocery_list(list_name), get_grocery_items(list_name). Graceful error handling — return error message on connection failure in src/tools/anylist_bridge.py
- [x] T038 [US6] Add push_grocery_list tool definition to src/assistant.py: accepts grocery list items, calls clear then add-bulk via anylist_bridge. On sidecar failure, fall back to sending formatted grocery list organized by store section (Produce, Meat, Dairy, Pantry, Frozen, Bakery, Beverages) via WhatsApp in src/assistant.py
- [x] T039 [US6] Update meal plan flow in SYSTEM_PROMPT in src/assistant.py: after generating a meal plan, offer "Want me to push this to AnyList for delivery?" and handle "order groceries" trigger in src/assistant.py

### Validation

- [ ] T040 [US6] End-to-end validation: generate meal plan → "order groceries" → verify items pushed to AnyList → test fallback when sidecar is unreachable → verify formatted WhatsApp list organized by store section per quickstart.md Scenario 7

**Checkpoint**: Grocery bridge works. Full meal-to-delivery pipeline complete.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Docker deployment, one-time setup scripts, and full system validation

- [x] T041 Create docker-compose.yml with services: fastapi (build ., port 8000), anylist-sidecar (build ./anylist-sidecar, port 3000), cloudflared (cloudflare/cloudflared image, tunnel run), n8n (n8nio/n8n, port 5678, GENERIC_TIMEZONE=America/Los_Angeles). Shared Docker network, volume mounts for n8n data and Google Calendar token in docker-compose.yml
- [x] T042 [P] Create scripts/import_grocery_history.py: parse Whole Foods order CSV or text export from Amazon, deduplicate item names, count frequency, calculate staples (50%+ threshold), write to Notion Grocery History database via API in scripts/import_grocery_history.py
- [x] T043 [P] Update docs/notion-setup.md to add steps for creating Backlog database (7 properties per data-model.md) and Grocery History database (5 properties per data-model.md) in docs/notion-setup.md
- [x] T044 Update .env.example with final complete variable list including ANYLIST_SIDECAR_URL, documentation comments for each section (Anthropic, WhatsApp, Notion, Google Calendar, Outlook, YNAB, AnyList, n8n) in .env.example
- [x] T045 Re-run Google Calendar OAuth setup with calendar.events scope: update scripts/setup_calendar.py to request calendar.events scope instead of calendar.readonly, add instructions to delete token.json before re-running in scripts/setup_calendar.py
- [ ] T046 Full system validation: run all 7 quickstart.md scenarios end-to-end with live services

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 Agenda (Phase 3)**: Depends on Phase 2 — MVP, implement first
- **US5 Daily Planner (Phase 4)**: Depends on Phase 2 — can start after or parallel with US1
- **US2 Action Items (Phase 5)**: Depends on Phase 2 — mostly verification of existing code
- **US3 Meal Planning (Phase 6)**: Depends on Phase 2 — mostly verification + grocery history
- **US4 Budget (Phase 7)**: Depends on Phase 2 — verification only
- **US6 Grocery Delivery (Phase 8)**: Depends on Phase 2 — independent new code (sidecar)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories. MVP standalone.
- **US5 (P2)**: No hard dependency on US1, but benefits from calendar refactoring done in Phase 2. Independent.
- **US2 (P3)**: No dependencies. Existing code mostly works.
- **US3 (P4)**: No dependencies. Existing code + grocery history enhancement.
- **US4 (P5)**: No dependencies. Existing code verification.
- **US6 (P6)**: Soft dependency on US3 (meal plan generates grocery list that US6 pushes). Can be tested independently with manual grocery list.

### Within Each User Story

- Tool module functions before assistant tool definitions
- Assistant tool definitions before endpoint wiring
- Endpoint wiring before validation
- Core implementation before fallback/error handling

### Parallel Opportunities

**Phase 1**: T002, T003, T004 can all run in parallel (different files)
**Phase 2**: T008 (outlook.py) can run in parallel with T006-T007 (calendar.py) and T009-T011 (notion.py)
**Phase 8**: T034 (package.json) can start in parallel with other US6 tasks since it's a different directory
**Phase 9**: T042 (import script) and T043 (docs) can run in parallel with each other and T041

---

## Parallel Examples

### Phase 1 — All setup tasks in parallel:
```
Task: "Update .env.example with v2 env vars" (T002)
Task: "Update src/config.py with new env vars" (T003)
Task: "Create Dockerfile for FastAPI" (T004)
```

### Phase 2 — Cross-file parallel:
```
Task: "Create src/tools/outlook.py" (T008) — in parallel with:
Task: "Refactor src/tools/calendar.py multi-calendar" (T006)
Task: "Add Backlog CRUD to src/tools/notion.py" (T009)
```

### Phase 8 — Sidecar + Python bridge in parallel:
```
Task: "Create anylist-sidecar/package.json" (T034) — in parallel with:
Task: "Create src/tools/anylist_bridge.py" (T037) — after T035 starts
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T012) — CRITICAL, blocks everything
3. Complete Phase 3: US1 Agenda (T013-T016)
4. **STOP and VALIDATE**: Test agenda generation with all calendar sources
5. Deploy to NUC if ready — immediate value from day one

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 Agenda → MVP! Deploy. Weekly meetings have structure.
3. US5 Daily Planner → Erin gets morning briefings + calendar blocks. **Biggest user impact.**
4. US2 Action Items → Capture and track meeting outcomes.
5. US3 Meal Planning → Weekly meal plans with grocery lists.
6. US4 Budget → Financial check-ins during meetings.
7. US6 Grocery Delivery → Last-mile: grocery list → AnyList → Whole Foods delivery.
8. Polish → Docker Compose, import scripts, full validation.

### Suggested MVP Scope

**Phase 1 + Phase 2 + Phase 3 (US1)** — 16 tasks. Delivers a working WhatsApp assistant that generates structured weekly meeting agendas from all calendar sources + Notion action items. Immediate value, minimal risk.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Existing v1 code (app.py, assistant.py, notion.py, calendar.py, ynab.py, whatsapp.py) is being UPDATED, not rewritten
- US2 (Action Items) and US4 (Budget) are mostly verification — existing code covers core functionality
- US5 (Daily Planner) is the highest-effort story — 9 tasks, new endpoints, calendar writes
- US6 (Grocery Delivery) is the most isolated — new sidecar, new bridge, minimal changes to existing code
- Commit after each completed phase or logical task group
- Stop at any checkpoint to validate the story independently
