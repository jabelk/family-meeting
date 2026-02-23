# Tasks: Proactive Automations & Recipe Management

**Input**: Design documents from `/specs/002-proactive-recipes-automation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: No formal test suite requested. Each user story has an E2E validation task for manual testing.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependencies, environment configuration, and Notion database setup

- [ ] T001 Add boto3>=1.35.0 to requirements.txt and rebuild Docker image
- [ ] T002 [P] Add new environment variables to src/config.py: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, NOTION_RECIPES_DB, NOTION_COOKBOOKS_DB, N8N_WEBHOOK_SECRET
- [ ] T003 [P] Update .env.example with all new variables (R2, Notion recipe/cookbook DBs, n8n-mombot credentials, N8N_WEBHOOK_SECRET)
- [ ] T004 [P] Create Notion Recipes database with properties per data-model.md (Name, Cookbook relation, Ingredients, Instructions, Prep Time, Cook Time, Servings, Photo URL, Tags, Cuisine, Date Added, Times Used, Last Used) and connect Family Meeting Bot integration. Add DB ID to .env as NOTION_RECIPES_DB
- [ ] T005 [P] Create Notion Cookbooks database with properties per data-model.md (Name, Description) and connect Family Meeting Bot integration. Add DB ID to .env as NOTION_COOKBOOKS_DB
- [ ] T006 [P] Create Cloudflare R2 bucket `family-recipes` with API token (Object Read & Write, scoped to bucket). Add R2 credentials to .env
- [ ] T007 Update docs/notion-setup.md with Recipes and Cookbooks database setup instructions, Grocery History property additions (Pending Order checkbox, Last Push Date), and R2 setup steps

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Extend src/whatsapp.py extract_message() to detect image messages (type=="image") and return media_id, mime_type, and caption alongside existing text extraction
- [ ] T009 Add download_media(media_id) function to src/whatsapp.py — two-step Meta Graph API flow: GET media URL from https://graph.facebook.com/v21.0/{media_id}, then GET binary data. Returns bytes + mime_type. Must complete within 5-minute URL expiry window
- [ ] T010 [P] Add send_template_message(phone, template_name, parameters) function to src/whatsapp.py — sends pre-approved Meta template messages. Include fallback logic: try free-form message first, if Meta returns error 131026 (outside 24h window), retry with template
- [ ] T011 [P] Implement R2 upload utility functions in src/tools/recipes.py: upload_photo(image_bytes, recipe_id, mime_type) → uploads to R2 bucket at key `recipes/{recipe_id}.{ext}`, returns public URL. Use boto3 S3-compatible client with endpoint https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com
- [ ] T012 [P] Add Notion CRUD for Recipes database in src/tools/notion.py: create_recipe(name, cookbook_id, ingredients_json, instructions, prep_time, cook_time, servings, photo_url, tags, cuisine), get_recipe(page_id), search_recipes(title_contains, cookbook_id, tags), get_all_recipes(), update_recipe(page_id, properties)
- [ ] T013 Add Notion CRUD for Cookbooks database in src/tools/notion.py: create_cookbook(name, description), get_cookbook(page_id), get_cookbook_by_name(name) with case-insensitive matching, list_cookbooks()
- [ ] T014 [P] Add Pending Order (checkbox) and Last Push Date (date) properties to Grocery History database via Notion API databases.update() call in src/tools/notion.py. Add helper functions: set_pending_order(item_ids, push_date), clear_pending_order(item_ids), get_pending_orders()
- [ ] T015 Add API auth middleware to src/app.py — verify X-N8N-Auth header matches N8N_WEBHOOK_SECRET for all /api/v1/* endpoints (except /webhook which uses Meta verification). Return 401 if missing/invalid

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Recipe Cookbook Catalogue (Priority: P1) MVP

**Goal**: Erin photographs a cookbook page via WhatsApp, Mom Bot extracts the recipe with Claude vision, saves to Notion with R2 photo storage, and supports search + grocery list generation from recipes.

**Independent Test**: Send a cookbook photo via WhatsApp → recipe appears in Notion with correct ingredients, instructions, and R2 photo link. Search by name/cookbook returns the recipe. "Add ingredients to grocery list" pushes needed items to AnyList.

### Implementation for User Story 1

- [ ] T016 [US1] Implement extract_and_save_recipe() in src/tools/recipes.py — accepts base64 image + mime_type + optional cookbook_name. Uses Claude Haiku 4.5 vision to extract recipe JSON (name, ingredients [{name, quantity, unit}], instructions [steps], prep_time, cook_time, servings). Uploads photo to R2 via upload_photo(). Finds or creates cookbook via get_cookbook_by_name()/create_cookbook(). Saves to Notion via create_recipe(). Returns recipe summary with unclear_portions flagged
- [ ] T017 [US1] Implement search_recipes() in src/tools/recipes.py — accepts natural language query + optional cookbook_name + optional tags. Uses Claude to interpret query into Notion filter parameters (title contains, cookbook relation, tags multi-select). Queries Notion Recipes DB. Returns ranked results with name, cookbook, tags, prep/cook time, times_used
- [ ] T018 [P] [US1] Implement get_recipe_details() in src/tools/recipes.py — accepts recipe Notion page_id, returns full recipe with parsed ingredients JSON, instructions, photo_url, all metadata
- [ ] T019 [P] [US1] Implement list_cookbooks() in src/tools/recipes.py — queries Cookbooks DB, returns list with name and recipe count (via Notion rollup or manual count query)
- [ ] T020 [US1] Implement recipe_to_grocery_list() in src/tools/recipes.py — accepts recipe_id + optional servings_multiplier. Gets recipe ingredients, cross-references each against Grocery History (match by normalized name). Categorizes as: needed (not recently ordered), already_have (ordered within 50% of avg_reorder_days), unknown (not in history). Assigns store from Grocery History or defaults to "Whole Foods"
- [ ] T021 [US1] Implement duplicate recipe detection in extract_and_save_recipe() in src/tools/recipes.py — before saving, query Recipes DB for same name + same cookbook. If found, return prompt asking user to update existing or save as new version
- [ ] T022 [US1] Update POST /webhook handler in src/app.py to detect image messages: call extract_message() for image type → download_media(media_id) → base64 encode → pass to handle_message() as image content block + caption text (so Claude sees the image and user's caption)
- [ ] T023 [US1] Register 5 recipe tools in src/assistant.py: add tool definitions for extract_and_save_recipe, search_recipes, get_recipe_details, recipe_to_grocery_list, list_cookbooks per contracts/recipe-endpoints.md. Map each to TOOL_FUNCTIONS dict. Update SYSTEM_PROMPT with recipe-related instructions (how to handle cookbook photos, search behavior, grocery list generation)
- [ ] T024 [US1] Add 5 recipe tools to MCP server in src/mcp_server.py following existing tool registration pattern
- [ ] T025 [US1] E2E validation: Send a cookbook photo via WhatsApp with caption "save this from the keto book" → verify recipe appears in Notion Recipes DB with correct fields + photo in R2. Then send "what was that steak recipe from the keto book?" → verify recipe returned. Then "add those ingredients to the grocery list" → verify AnyList receives items

**Checkpoint**: Recipe catalogue fully functional — Erin can photograph, search, and shop from recipes

---

## Phase 4: User Story 2 — Proactive Grocery Reorder Suggestions (Priority: P2)

**Goal**: Weekly check identifies staple/regular grocery items due for reorder based on purchase intervals, sends grouped suggestions via WhatsApp, and handles order confirmation with 2-day reminder.

**Independent Test**: Call POST /api/v1/grocery/reorder-check → get items grouped by store. Approve items → pushed to AnyList. Confirm "groceries ordered" → Last Ordered updated. No confirmation after 2 days → reminder sent.

### Implementation for User Story 2

- [ ] T026 [US2] Implement check_reorder_items() in src/tools/proactive.py — query Grocery History for items where Type is Staple or Regular. Calculate days_since_last_ordered for each. Filter where days_since >= avg_reorder_days. Group by Store multi-select. Sort by days overdue (most overdue first). Return structured dict per contracts/automation-endpoints.md
- [ ] T027 [US2] Implement handle_order_confirmation() in src/tools/proactive.py — when Erin says "groceries ordered" or similar, update Last Ordered date to today for all items with Pending Order = true via Notion API. Clear Pending Order flags
- [ ] T028 [US2] Implement check_grocery_confirmation() in src/tools/proactive.py — query Grocery History for Pending Order = true. If Last Push Date was 2+ days ago, format and send gentle reminder via WhatsApp. If no pending items, return no_pending status
- [ ] T029 [US2] Add POST /api/v1/grocery/reorder-check endpoint in src/app.py — calls check_reorder_items(), formats WhatsApp message grouped by store with item names and days overdue, sends to Erin's phone. Protected by N8N_WEBHOOK_SECRET auth
- [ ] T030 [US2] Add POST /api/v1/reminders/grocery-confirmation endpoint in src/app.py — calls check_grocery_confirmation(). Protected by auth
- [ ] T031 [US2] Register reorder and confirmation tools in src/assistant.py — add tool for approving/modifying grocery suggestions (approve_reorder_items with item selection), add handler for "groceries ordered" confirmation intent. Update push_grocery_list flow to set Pending Order + Last Push Date on pushed items
- [ ] T032 [US2] E2E validation: Manually insert test items in Grocery History with old Last Ordered dates → call /api/v1/grocery/reorder-check → verify WhatsApp message lists overdue items grouped by store. Reply "add the Whole Foods ones" → verify AnyList receives items + Pending Order set. Wait or manually trigger /api/v1/reminders/grocery-confirmation → verify reminder sent

**Checkpoint**: Grocery reorder suggestions working — items detected, approved, pushed to AnyList, confirmation tracked

---

## Phase 5: User Story 3 — Smart Meal Plan with Auto Grocery List (Priority: P3)

**Goal**: Saturday morning combined message: 6-night dinner plan (considering recipes, preferences, schedule density, no-repeat) + merged grocery list (meal ingredients + reorder staples - recently ordered) sent via WhatsApp.

**Independent Test**: Call POST /api/v1/meals/plan-week → receive 6-night dinner plan using saved recipes where applicable + merged grocery list with store grouping. Swap a meal → grocery list updates. Approve → items pushed to AnyList.

### Implementation for User Story 3

- [ ] T033 [US3] Implement generate_meal_plan() in src/tools/proactive.py — gather context: all saved recipes from Notion, last 2 meal plans, weekly schedule from Family Profile, family dietary preferences. Build Claude prompt requesting 6-night dinner plan (Mon-Sat). Claude returns structured JSON: [{day, meal_name, source (recipe_id or "general"), ingredients, complexity}]. Simpler meals on busy days (Tue gymnastics, Wed-Fri both kids). Use saved recipes when good fits exist. Avoid meals from last 2 weeks
- [ ] T034 [US3] Implement merge_grocery_list() in src/tools/proactive.py — takes meal plan ingredients + reorder-due staples from check_reorder_items(). Deduplicates by normalized item name. Deducts items where last_ordered is within 50% of avg_reorder_days. Groups by store (Grocery History store data for known items, "Whole Foods" default for unknown). Returns structured list per contracts/automation-endpoints.md
- [ ] T035 [US3] Implement handle_meal_swap() in src/tools/proactive.py — given a day and new meal name, regenerate ingredients for that day's meal (from recipe or Claude), recalculate merged grocery list with the swap applied. Return updated plan + updated grocery list
- [ ] T036 [US3] Add POST /api/v1/meals/plan-week endpoint in src/app.py — calls generate_meal_plan() + merge_grocery_list(). Formats single combined WhatsApp message: dinner plan table (day, meal, source, complexity) + grocery list grouped by store. Sends to Erin. Protected by auth
- [ ] T037 [US3] Register meal plan tools in src/assistant.py — add tool definitions for generate_meal_plan (for on-demand use), handle_meal_swap (for adjustments). Update SYSTEM_PROMPT with meal planning instructions (how to present plan, handle swaps, approve and push to AnyList)
- [ ] T038 [US3] E2E validation: Save 3+ recipes via US1 flow first. Call /api/v1/meals/plan-week → verify 6-night plan uses saved recipes where appropriate, avoids recent repeats, includes merged grocery list. Send "swap Wednesday for tacos" → verify updated plan + grocery list. Send "approve and send to AnyList" → verify items pushed

**Checkpoint**: Meal planning + grocery automation working — Saturday combined message functional

---

## Phase 6: User Story 4 — n8n Scheduled Workflows (Priority: P4)

**Goal**: Dedicated n8n-mombot Docker instance running 8 scheduled workflows that trigger FastAPI endpoints at configured cron times.

**Independent Test**: Deploy n8n-mombot container, create WF-001 (daily briefing), verify it fires at 7:00 AM and sends Erin her morning plan via WhatsApp. Verify all 8 workflows are configured and scheduled.

### Implementation for User Story 4

- [ ] T039 [US4] Add n8n-mombot service to docker-compose.yml — image n8nio/n8n:latest, port 5679:5678, env vars for basic auth + timezone America/Los_Angeles + encryption key, named volume n8n_mombot_data, on family-net network, restart unless-stopped. Add N8N_MOMBOT_USER, N8N_MOMBOT_PASSWORD, N8N_MOMBOT_ENCRYPTION_KEY to .env
- [ ] T040 [US4] Create docs/n8n-setup.md documenting step-by-step n8n workflow creation for all 8 workflows (WF-001 through WF-008 per contracts/n8n-workflows.md): workflow name, cron expression, HTTP request node config (URL, method, headers including X-N8N-Auth, body), retry settings (1 retry, 5 min delay). Include screenshots placeholders for n8n UI
- [ ] T041 [US4] Deploy n8n-mombot container on NUC via docker-compose up, access UI at :5679, create all 8 workflows per docs/n8n-setup.md: WF-001 Daily Briefing (0 7 * * 1-5), WF-002 Weekly Calendar (0 19 * * 0), WF-003 Grandma Prompt (0 9 * * 1), WF-004 Saturday Meal+Grocery (0 9 * * 6), WF-005 Budget Summary (0 17 * * 0), WF-006 Mid-Week Check-In (0 12 * * 3), WF-007 Conflict Scan (30 19 * * 0), WF-008 Grocery Confirmation (0 10 * * *)
- [ ] T042 [US4] E2E validation: Verify n8n-mombot container running on port 5679. Manually trigger WF-001 (daily briefing) from n8n UI → verify FastAPI receives request with valid auth → WhatsApp message sent. Check all 8 workflows show correct cron schedules in n8n UI

**Checkpoint**: n8n scheduling infrastructure operational — all proactive features now fire automatically

---

## Phase 7: User Story 5 — Calendar Conflict Detection (Priority: P5)

**Goal**: Detect time conflicts across all 4 calendars (Jason Google, Erin Google, Family shared, Jason Outlook) and soft conflicts against family routines. Report in daily briefing and weekly scan.

**Independent Test**: Create a test Google Calendar event overlapping Vienna's Tuesday 3:15 pickup. Run conflict check → alert flags the conflict with suggested resolution.

### Implementation for User Story 5

- [ ] T043 [US5] Implement detect_conflicts(days_ahead) in src/tools/proactive.py — fetch events from all 4 calendars for the date range using existing get_calendar_events() + get_outlook_events(). Parse routine templates from Family Profile for each day. Detect hard conflicts (two events with overlapping time ranges across any calendars). Detect soft conflicts (event overlaps routine entry — specifically pickup times, dropoff times, Sandy schedule). Return list of {day, type, event, routine, suggestion}
- [ ] T044 [US5] Add POST /api/v1/calendar/conflict-check endpoint in src/app.py — accepts optional days_ahead param (default 1). Calls detect_conflicts(). If days_ahead > 1 (weekly scan), formats full conflict report and sends via WhatsApp. If days_ahead == 1 (daily), returns conflicts for embedding in briefing. Protected by auth
- [ ] T045 [US5] Integrate conflict detection into daily briefing in src/app.py — in the existing POST /api/v1/briefing/daily handler, call detect_conflicts(days_ahead=1) before generating the plan. If conflicts found, prepend conflict alerts to the briefing message. Update generate_daily_plan() prompt in src/assistant.py to include conflict context
- [ ] T046 [US5] E2E validation: Create a test event on Jason's Google Calendar overlapping Vienna's Tuesday 3:15 pickup time. Call /api/v1/calendar/conflict-check with days_ahead=7 → verify conflict appears with type "soft" and suggestion for Erin to cover. Trigger daily briefing for that day → verify conflict alert at top of briefing

**Checkpoint**: Conflict detection working — no more missed pickups or double-bookings

---

## Phase 8: User Story 6 — Mid-Week Action Item Reminders (Priority: P6)

**Goal**: Wednesday noon check-in showing action item progress, flagging at-risk and rolled-over items.

**Independent Test**: Create 4 action items for "This Week" (2 done, 2 not started, 1 rolled over) → call endpoint → verify progress report with rollover flag.

### Implementation for User Story 6

- [ ] T047 [US6] Implement check_action_item_progress() in src/tools/proactive.py — query Notion Action Items where Due Context = "This Week". Count total, done (Status = Done), in_progress, not_started. Identify items with Rolled Over = true and count how many times (check previous weeks). If all done, return "all_complete" status. Otherwise return structured summary with items grouped by assignee, flagging rolled-over items with count
- [ ] T048 [US6] Add POST /api/v1/reminders/action-items endpoint in src/app.py — calls check_action_item_progress(). If incomplete items exist, format WhatsApp message: "3 of 6 items done" + remaining items by assignee + rolled-over flags. If all done, optionally send brief "all caught up!" or skip. Protected by auth
- [ ] T049 [US6] E2E validation: Create test action items in Notion — 3 done, 2 not started (1 with Rolled Over = true). Call /api/v1/reminders/action-items → verify message shows "3 of 5 done", lists 2 remaining, flags rolled-over item as "rolled over — still relevant?"

**Checkpoint**: Mid-week nudge working — action items tracked and flagged

---

## Phase 9: User Story 7 — Weekly Budget Summary (Priority: P7)

**Goal**: Sunday afternoon YNAB spending summary sent via WhatsApp highlighting over-budget categories and trends.

**Independent Test**: Call POST /api/v1/budget/weekly-summary → verify formatted spending report arrives via WhatsApp with over/under budget categories.

### Implementation for User Story 7

- [ ] T050 [US7] Implement format_budget_summary() in src/tools/proactive.py — call existing get_budget_summary() from src/tools/ynab.py. Format into structured WhatsApp message: "Over Budget" section (category, amount over, percentage), "On Track" top categories, total spent vs total budget. If nothing over budget, send brief "all on track" summary
- [ ] T051 [US7] Add POST /api/v1/budget/weekly-summary endpoint in src/app.py — calls format_budget_summary(), sends formatted message via WhatsApp (with template fallback for Sunday outside 24h window). Protected by auth
- [ ] T052 [US7] E2E validation: Call /api/v1/budget/weekly-summary → verify YNAB data fetched, formatted message sent to WhatsApp with correct budget categories and amounts

**Checkpoint**: Budget summary working — ready for Sunday family meeting discussion

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, deployment, and full system validation

- [ ] T053 [P] Verify .env.example completeness — confirm all new environment variables from this feature are present with inline comments
- [ ] T054 [P] Update src/mcp_server.py to include all new proactive tools (reorder, meal plan, conflict check, etc.) for Claude Desktop access
- [ ] T055 Deploy full stack to NUC via docker-compose (including n8n-mombot). Verify all containers healthy: fastapi, anylist-sidecar, cloudflared, n8n-mombot
- [ ] T056 Run quickstart.md validation: verify all setup steps can be followed from scratch, all env vars documented, all Notion databases match schema, R2 bucket accessible
- [ ] T057 Full system validation: let all 8 n8n workflows run for 3+ consecutive days. Verify daily briefing (Mon-Fri 7am), Wednesday check-in (noon), Saturday meal plan (9am), Sunday budget+calendar (5pm, 7pm, 7:30pm). Confirm no silent failures in n8n execution history

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion (T001-T007) — BLOCKS all user stories
- **US1 Recipe Catalogue (Phase 3)**: Depends on Phase 2 (T008-T015)
- **US2 Grocery Reorder (Phase 4)**: Depends on Phase 2 (T008-T015). Does NOT depend on US1
- **US3 Meal Planning (Phase 5)**: Depends on Phase 2. Benefits from US1 (uses saved recipes) and US2 (reorder data), but can function with general suggestions only
- **US4 n8n Workflows (Phase 6)**: Depends on endpoints from US2-US7 existing. Best done after US2-US3 endpoints are ready
- **US5 Conflict Detection (Phase 7)**: Depends on Phase 2 only. Independent of US1-US3
- **US6 Action Items (Phase 8)**: Depends on Phase 2 only. Independent of all other stories
- **US7 Budget Summary (Phase 9)**: Depends on Phase 2 only. Independent of all other stories
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Phase 1 (Setup) ─────────────────────────────────────────────
         │
Phase 2 (Foundational) ──────────────────────────────────────
         │
         ├── US1 Recipe Catalogue (P1) ── MVP
         │        │
         ├── US2 Grocery Reorder (P2) ───┐
         │                                │
         ├── US5 Conflict Detection (P5) ─┤
         │                                │
         ├── US6 Action Items (P6) ───────┤
         │                                │
         ├── US7 Budget Summary (P7) ─────┤
         │                                │
         ├── US3 Meal Planning (P3) ──────┤  (uses US1 recipes + US2 reorder data)
         │                                │
         └── US4 n8n Workflows (P4) ──────┘  (wires up endpoints from US2-US7)
                                          │
Phase 10 (Polish) ───────────────────────┘
```

### Within Each User Story

- Implementation tasks in dependency order (data layer → business logic → endpoint → assistant registration → E2E)
- Each story independently testable via its E2E validation task
- Commit after each task or logical group

### Parallel Opportunities

**Phase 1**: T002, T003, T004, T005, T006 can all run in parallel
**Phase 2**: T010, T011, T012, T013, T014 can all run in parallel (different files). T008 and T009 are sequential (same file: whatsapp.py)
**After Phase 2**: US1, US2, US5, US6, US7 can all start in parallel (independent stories). US3 benefits from US1+US2 completion. US4 should come last (needs endpoints)

---

## Parallel Example: Phase 2 Foundational

```bash
# These can all run in parallel (different files):
Task: "Implement R2 upload utility in src/tools/recipes.py"         # T011
Task: "Add Notion CRUD for Recipes DB in src/tools/notion.py"       # T012
Task: "Add Notion CRUD for Cookbooks DB in src/tools/notion.py"     # T013
Task: "Add Pending Order properties to Grocery History in notion.py" # T014
Task: "Add template message send in src/whatsapp.py"                 # T010

# These must be sequential (same file: whatsapp.py):
Task: "Extend extract_message() for images in src/whatsapp.py"      # T008
Task: "Add download_media() in src/whatsapp.py"                      # T009
# Then T010 (template send) can parallel with T008-T009 if different functions
```

## Parallel Example: After Phase 2

```bash
# Independent stories can run in parallel:
Task: "US1 — Recipe extraction via Claude vision"    # Phase 3
Task: "US2 — Reorder check logic"                    # Phase 4
Task: "US5 — Conflict detection logic"               # Phase 7
Task: "US6 — Action item progress check"             # Phase 8
Task: "US7 — Budget summary formatter"               # Phase 9
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational (T008-T015) — CRITICAL, blocks all stories
3. Complete Phase 3: US1 Recipe Catalogue (T016-T025)
4. **STOP and VALIDATE**: Erin photographs a cookbook page → recipe saved → searchable → grocery list generated
5. Deploy to NUC if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 Recipe Catalogue → Test → Deploy (MVP!)
3. US2 Grocery Reorder → Test → Deploy
4. US3 Meal Planning → Test → Deploy (builds on US1 + US2 data)
5. US5 + US6 + US7 → Test → Deploy (independent automations)
6. US4 n8n Workflows → Configure → Deploy (makes everything proactive)
7. Polish → Full validation over 3+ days

### Single Developer Strategy (Recommended)

This is a solo project (Jason + Claude Code). Execute sequentially in priority order:

1. Phase 1 + Phase 2: Foundation (~1 session)
2. Phase 3 (US1): Recipe catalogue (~1-2 sessions)
3. Phase 4 (US2): Grocery reorder (~1 session)
4. Phase 5 (US3): Meal planning (~1 session)
5. Phase 6 (US4): n8n workflows (~1 session — mostly config)
6. Phase 7-9 (US5-US7): Conflict + reminders + budget (~1 session each)
7. Phase 10: Polish + validation (~1 session)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The n8n workflow creation (T041) is a manual UI task — document steps clearly so it can be reproduced
- WhatsApp template messages (T010) require Meta approval — submit early, can proceed with free-form messages in the meantime
