# Tasks: Proactive Automations & Recipe Management

**Input**: Design documents from `/specs/002-proactive-recipes-automation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: No formal test suite requested. Each user story has an E2E validation task for manual testing.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Status (2026-02-23)**: 48/57 tasks complete. All implementation code is on `main` and deployed to NUC. Remaining: n8n workflow creation (T041 — manual UI), quickstart validation (T056), and E2E manual validations (T032, T038, T042, T046, T049, T052, T057).

## Design Decisions & Troubleshooting Log

### Image Data Flow — Module-Level Buffer (T016/T022)
**Problem**: Claude truncates large base64 strings (~700KB) when passing them as tool-call JSON arguments, causing `invalid base64 data` errors on the downstream Claude vision API call.
**Solution**: Store image data in a module-level `_buffered_images` list in `assistant.py` when `handle_message()` receives `image_data`. The `extract_and_save_recipe` tool definition only requires `cookbook_name` — the handler retrieves buffered images directly. Buffer is cleared after extraction.

### Multi-Page Recipe Support (T016)
**Problem**: Some recipes span multiple cookbook pages. WhatsApp sends each photo as a separate message.
**Solution**: Images accumulate in `_buffered_images` across consecutive `handle_message()` calls. When Claude calls `extract_and_save_recipe`, all buffered images are sent to the vision API as multiple image content blocks. A `[SYSTEM: N recipe photos buffered]` note is injected into the message text so Claude knows how many pages are available. The system prompt instructs Claude to wait for all pages before calling the tool.

### Model Swap: Haiku → Sonnet (temporary)
**Problem**: Claude Haiku 4.5 returned 529 Overloaded errors during testing (2026-02-23).
**Solution**: Swapped all 3 source files (assistant.py, recipes.py, proactive.py) to `claude-sonnet-4-20250514`. Should swap back to Haiku when available for cost savings. The model ID is hardcoded in 3 places.

### Notion Property Graceful Handling (T014/T028/T048)
**Problem**: `get_pending_orders()` and `check_action_item_progress()` crashed with 500 errors when Notion database properties (Pending Order, Last Push Date) didn't exist yet.
**Solution**: Wrapped Notion queries in try/except blocks that return empty/default results when properties are missing. This makes the endpoints safe to call before manual Notion setup is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependencies, environment configuration, and Notion database setup

- [x] T001 Add boto3>=1.35.0 to requirements.txt and rebuild Docker image
- [x] T002 [P] Add new environment variables to src/config.py: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, NOTION_RECIPES_DB, NOTION_COOKBOOKS_DB, N8N_WEBHOOK_SECRET
- [x] T003 [P] Update .env with all new variables (R2, Notion recipe/cookbook DBs, n8n-mombot credentials, N8N_WEBHOOK_SECRET)
- [x] T004 [P] Create Notion Recipes database with properties per data-model.md (Name, Cookbook relation, Ingredients, Instructions, Prep Time, Cook Time, Servings, Photo URL, Tags, Cuisine, Date Added, Times Used, Last Used) and connect Family Meeting Bot integration. Add DB ID to .env as NOTION_RECIPES_DB
- [x] T005 [P] Create Notion Cookbooks database with properties per data-model.md (Name, Description) and connect Family Meeting Bot integration. Add DB ID to .env as NOTION_COOKBOOKS_DB
- [x] T006 [P] Create Cloudflare R2 bucket `family-recipes` with API token (Object Read & Write, scoped to bucket). Add R2 credentials to .env
- [x] T007 Update docs/notion-setup.md with Recipes and Cookbooks database setup instructions, Grocery History property additions (Pending Order checkbox, Last Push Date), and R2 setup steps

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T008 Extend src/whatsapp.py extract_message() to detect image messages (type=="image") and return media_id, mime_type, and caption alongside existing text extraction
- [x] T009 Add download_media(media_id) function to src/whatsapp.py — two-step Meta Graph API flow: GET media URL from https://graph.facebook.com/v21.0/{media_id}, then GET binary data. Returns bytes + mime_type. Must complete within 5-minute URL expiry window
- [x] T010 [P] Add send_template_message(phone, template_name, parameters) function to src/whatsapp.py — sends pre-approved Meta template messages. Include fallback logic: try free-form message first, if Meta returns error 131026 (outside 24h window), retry with template
- [x] T011 [P] Implement R2 upload utility functions in src/tools/recipes.py: upload_photo(image_bytes, recipe_id, mime_type) → uploads to R2 bucket at key `recipes/{recipe_id}.{ext}`, returns public URL. Use boto3 S3-compatible client with endpoint https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com
- [x] T012 [P] Add Notion CRUD for Recipes database in src/tools/notion.py: create_recipe(name, cookbook_id, ingredients_json, instructions, prep_time, cook_time, servings, photo_url, tags, cuisine), get_recipe(page_id), search_recipes(title_contains, cookbook_id, tags), get_all_recipes(), update_recipe(page_id, properties)
- [x] T013 Add Notion CRUD for Cookbooks database in src/tools/notion.py: create_cookbook(name, description), get_cookbook(page_id), get_cookbook_by_name(name) with case-insensitive matching, list_cookbooks()
- [x] T014 [P] Add Pending Order (checkbox) and Last Push Date (date) properties to Grocery History database via Notion API databases.update() call in src/tools/notion.py. Add helper functions: set_pending_order(item_ids, push_date), clear_pending_order(item_ids), get_pending_orders()
- [x] T015 Add API auth middleware to src/app.py — verify X-N8N-Auth header matches N8N_WEBHOOK_SECRET for all /api/v1/* endpoints (except /webhook which uses Meta verification). Return 401 if missing/invalid

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Recipe Cookbook Catalogue (Priority: P1) MVP

**Goal**: Erin photographs a cookbook page via WhatsApp, Mom Bot extracts the recipe with Claude vision, saves to Notion with R2 photo storage, and supports search + grocery list generation from recipes.

**Independent Test**: Send a cookbook photo via WhatsApp → recipe appears in Notion with correct ingredients, instructions, and R2 photo link. Search by name/cookbook returns the recipe. "Add ingredients to grocery list" pushes needed items to AnyList.

### Implementation for User Story 1

- [x] T016 [US1] Implement extract_and_save_recipe() in src/tools/recipes.py — accepts list of image dicts (base64 + mime_type) + optional cookbook_name. Uses Claude Sonnet vision to extract recipe JSON. Uploads photo to R2. Finds or creates cookbook. Saves to Notion. Returns recipe summary with unclear_portions flagged. **Design change**: images passed via module-level buffer in assistant.py (not through Claude tool-call JSON) to avoid base64 truncation. Supports multi-page recipes (multiple images combined into one extraction).
- [x] T017 [US1] Implement search_recipes() in src/tools/recipes.py — accepts query + optional cookbook_name + optional tags. Queries Notion Recipes DB with filters. Returns results with name, cookbook, tags, prep/cook time, times_used
- [x] T018 [P] [US1] Implement get_recipe_details() in src/tools/recipes.py — accepts recipe Notion page_id, returns full recipe with parsed ingredients JSON, instructions, photo_url, all metadata
- [x] T019 [P] [US1] Implement list_cookbooks() in src/tools/recipes.py — queries Cookbooks DB, returns list with name and recipe count
- [x] T020 [US1] Implement recipe_to_grocery_list() in src/tools/recipes.py — accepts recipe_id + optional servings_multiplier. Gets recipe ingredients, cross-references against Grocery History. Categorizes as needed/already_have/unknown
- [x] T021 [US1] Implement duplicate recipe detection in extract_and_save_recipe() — before saving, query Recipes DB for same name + same cookbook. If found, return prompt asking user to update or save as new version
- [x] T022 [US1] Update POST /webhook handler in src/app.py to detect image messages: call extract_message() for image type → download_media(media_id) → base64 encode → pass to handle_message() as image_data dict (so Claude sees the image and user's caption)
- [x] T023 [US1] Register 5 recipe tools in src/assistant.py: tool definitions for extract_and_save_recipe (cookbook_name only — image auto-retrieved from buffer), search_recipes, get_recipe_details, recipe_to_grocery_list, list_cookbooks. Updated SYSTEM_PROMPT with recipe rules (18-21)
- [x] T024 [US1] Add 5 recipe tools to MCP server in src/mcp_server.py following existing tool registration pattern
- [x] T025 [US1] E2E validation: Sent "Raspberry Crumble Bars" from "Downshiftology Healthy Meal Prep" cookbook via WhatsApp → recipe extracted, saved to Notion, photo uploaded to R2, WhatsApp reply confirmed. Full pipeline verified 2026-02-23

**Checkpoint**: Recipe catalogue fully functional — Erin can photograph, search, and shop from recipes

---

## Phase 4: User Story 2 — Proactive Grocery Reorder Suggestions (Priority: P2)

**Goal**: Weekly check identifies staple/regular grocery items due for reorder based on purchase intervals, sends grouped suggestions via WhatsApp, and handles order confirmation with 2-day reminder.

**Independent Test**: Call POST /api/v1/grocery/reorder-check → get items grouped by store. Approve items → pushed to AnyList. Confirm "groceries ordered" → Last Ordered updated. No confirmation after 2 days → reminder sent.

### Implementation for User Story 2

- [x] T026 [US2] Implement check_reorder_items() in src/tools/proactive.py — query Grocery History for items where Type is Staple or Regular. Calculate days_since_last_ordered. Filter where days_since >= avg_reorder_days. Group by Store. Sort by days overdue
- [x] T027 [US2] Implement handle_order_confirmation() in src/tools/proactive.py — update Last Ordered date for all Pending Order items, clear flags
- [x] T028 [US2] Implement check_grocery_confirmation() in src/tools/proactive.py — query for Pending Order = true, send reminder if 2+ days old. Graceful handling if Pending Order property doesn't exist yet
- [x] T029 [US2] Add POST /api/v1/grocery/reorder-check endpoint in src/app.py — protected by N8N_WEBHOOK_SECRET auth
- [x] T030 [US2] Add POST /api/v1/reminders/grocery-confirmation endpoint in src/app.py — protected by auth
- [x] T031 [US2] Register reorder and confirmation tools in src/assistant.py (check_reorder_items, confirm_groceries_ordered)
- [ ] T032 [US2] E2E validation: Full manual test with grocery history data — endpoints return 200 but full AnyList flow not yet validated

**Checkpoint**: Grocery reorder suggestions working — items detected, approved, pushed to AnyList, confirmation tracked

---

## Phase 5: User Story 3 — Smart Meal Plan with Auto Grocery List (Priority: P3)

**Goal**: Saturday morning combined message: 6-night dinner plan (considering recipes, preferences, schedule density, no-repeat) + merged grocery list (meal ingredients + reorder staples - recently ordered) sent via WhatsApp.

**Independent Test**: Call POST /api/v1/meals/plan-week → receive 6-night dinner plan using saved recipes where applicable + merged grocery list with store grouping. Swap a meal → grocery list updates. Approve → items pushed to AnyList.

### Implementation for User Story 3

- [x] T033 [US3] Implement generate_meal_plan() in src/tools/proactive.py — gathers recipes, meal history, schedule, preferences. Uses Claude Sonnet to generate 6-night dinner plan JSON
- [x] T034 [US3] Implement merge_grocery_list() in src/tools/proactive.py — integrated into generate_meal_plan (dedup, deduct recently ordered, group by store)
- [x] T035 [US3] Implement handle_meal_swap() in src/tools/proactive.py — swaps day's meal, recalculates grocery list
- [x] T036 [US3] Add POST /api/v1/meals/plan-week endpoint in src/app.py — protected by auth
- [x] T037 [US3] Register meal plan tools in src/assistant.py (generate_meal_plan, handle_meal_swap)
- [ ] T038 [US3] E2E validation: Full meal plan flow with saved recipes — endpoint returns 200 but not yet tested with real recipe data

**Checkpoint**: Meal planning + grocery automation working — Saturday combined message functional

---

## Phase 6: User Story 4 — n8n Scheduled Workflows (Priority: P4)

**Goal**: Dedicated n8n-mombot Docker instance running 8 scheduled workflows that trigger FastAPI endpoints at configured cron times.

**Independent Test**: Deploy n8n-mombot container, create WF-001 (daily briefing), verify it fires at 7:00 AM and sends Erin her morning plan via WhatsApp. Verify all 8 workflows are configured and scheduled.

### Implementation for User Story 4

- [x] T039 [US4] Add n8n-mombot service to docker-compose.yml — port 5679:5678, basic auth, timezone, encryption key, named volume, family-net network. Container running on NUC
- [x] T040 [US4] Create docs/n8n-setup.md documenting step-by-step n8n workflow creation for all 8 workflows (WF-001 through WF-008 per contracts/n8n-workflows.md)
- [ ] T041 [US4] Deploy n8n-mombot workflows — access UI at :5679, create all 8 workflows (manual UI task)
- [ ] T042 [US4] E2E validation: Verify all 8 workflows fire at expected times and produce correct output

**Checkpoint**: n8n scheduling infrastructure operational — all proactive features now fire automatically

---

## Phase 7: User Story 5 — Calendar Conflict Detection (Priority: P5)

**Goal**: Detect time conflicts across all 4 calendars (Jason Google, Erin Google, Family shared, Jason Outlook) and soft conflicts against family routines. Report in daily briefing and weekly scan.

**Independent Test**: Create a test Google Calendar event overlapping Vienna's Tuesday 3:15 pickup. Run conflict check → alert flags the conflict with suggested resolution.

### Implementation for User Story 5

- [x] T043 [US5] Implement detect_conflicts(days_ahead) in src/tools/proactive.py — fetches events from all 4 calendars, parses routine templates, detects hard and soft conflicts
- [x] T044 [US5] Add POST /api/v1/calendar/conflict-check endpoint in src/app.py — protected by auth
- [x] T045 [US5] Integrate conflict detection into daily briefing in src/app.py
- [ ] T046 [US5] E2E validation: Create test overlapping calendar event → verify conflict detection and briefing integration

**Checkpoint**: Conflict detection working — no more missed pickups or double-bookings

---

## Phase 8: User Story 6 — Mid-Week Action Item Reminders (Priority: P6)

**Goal**: Wednesday noon check-in showing action item progress, flagging at-risk and rolled-over items.

**Independent Test**: Create 4 action items for "This Week" (2 done, 2 not started, 1 rolled over) → call endpoint → verify progress report with rollover flag.

### Implementation for User Story 6

- [x] T047 [US6] Implement check_action_item_progress() in src/tools/proactive.py — queries Notion directly for This Week items, counts by status, flags rolled-over items
- [x] T048 [US6] Add POST /api/v1/reminders/action-items endpoint in src/app.py — protected by auth. Fixed graceful handling when query returns no items
- [ ] T049 [US6] E2E validation: Create test action items in Notion and verify progress report

**Checkpoint**: Mid-week nudge working — action items tracked and flagged

---

## Phase 9: User Story 7 — Weekly Budget Summary (Priority: P7)

**Goal**: Sunday afternoon YNAB spending summary sent via WhatsApp highlighting over-budget categories and trends.

**Independent Test**: Call POST /api/v1/budget/weekly-summary → verify formatted spending report arrives via WhatsApp with over/under budget categories.

### Implementation for User Story 7

- [x] T050 [US7] Implement format_budget_summary() in src/tools/proactive.py — calls get_budget_summary(), formats WhatsApp-ready message
- [x] T051 [US7] Add POST /api/v1/budget/weekly-summary endpoint in src/app.py — protected by auth
- [ ] T052 [US7] E2E validation: Call /api/v1/budget/weekly-summary → verify YNAB data fetched and WhatsApp message sent

**Checkpoint**: Budget summary working — ready for Sunday family meeting discussion

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, deployment, and full system validation

- [x] T053 [P] Verify .env.example completeness — all Feature 002 variables present (R2, Notion recipe/cookbook DBs, n8n-mombot, N8N_WEBHOOK_SECRET)
- [x] T054 [P] Update src/mcp_server.py to include all new proactive tools (reorder, meal plan, conflict check, etc.) for Claude Desktop access — 11 new tools registered
- [x] T055 Deploy full stack to NUC via docker-compose (including n8n-mombot). All 4 containers healthy: fastapi, anylist-sidecar, cloudflared, n8n-mombot
- [ ] T056 Run quickstart.md validation: verify all setup steps can be followed from scratch
- [ ] T057 Full system validation: let all 8 n8n workflows run for 3+ consecutive days

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
