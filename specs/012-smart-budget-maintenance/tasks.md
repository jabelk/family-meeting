# Tasks: Smart Budget Maintenance

**Input**: Design documents from `/specs/012-smart-budget-maintenance/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project setup needed — extending existing `src/tools/ynab.py` module. This phase adds the shared data persistence helpers.

- [X] T001 Implement `_save_pending_suggestions(suggestions: list[dict])` and `_load_pending_suggestions() -> list[dict]` in src/tools/ynab.py — save/load pending goal suggestions to `data/budget_pending_suggestions.json`, following the same atomic write pattern used by `data/email_pending_suggestions.json` in src/tools/email_sync.py
- [X] T002 [P] Implement `_save_pending_allocation(plan: dict)` and `_load_pending_allocation() -> dict | None` in src/tools/ynab.py — save/load pending allocation plan to `data/budget_pending_allocation.json`, same atomic write pattern

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data retrieval and analysis infrastructure that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Implement `_fetch_month_data(month: str) -> list[dict]` in src/tools/ynab.py — call GET `/budgets/{YNAB_BUDGET_ID}/months/{month}`, return list of category dicts with fields: id, name, category_group_name (mapped to "group"), budgeted, activity, balance, goal_type, goal_target, goal_percentage_complete, goal_overall_funded, goal_under_funded, hidden, deleted. Filter out hidden/deleted categories. Convert milliunits to dollars for budgeted/activity/balance/goal_target. Use existing `BASE_URL`, `HEADERS`, `YNAB_BUDGET_ID` constants and httpx
- [X] T004 Implement `_build_category_profiles(lookback_months: int = 3, drift_threshold: float = 30) -> list[dict]` in src/tools/ynab.py — call `_fetch_month_data()` for current month + (lookback_months - 1) prior months, then for each category compute: spending_avg (mean of abs(activity)), spending_months (list of per-month spending), budgeted_avg, drift_pct ((spending_avg - goal_target) / goal_target * 100 when goal_target > 0), drift_type ("underfunded" if spending_avg > goal * (1 + threshold/100), "overfunded" if goal > spending_avg * (1 + threshold/100), "missing_goal" if goal_type is null and spending_avg > 0, else "aligned"), trend ("increasing" if each month > prior, "decreasing" if each month < prior, else "stable" — requires 2+ months), is_sinking_fund (True if goal_type in ("TB", "TBD"), else pattern check: any single month with activity > 3x average suggests periodic), is_spiky (coefficient of variation > 1.0 with 3+ months data), months_since_last_txn (count trailing months with $0 activity), is_stale (months_since_last_txn >= 3 and not is_sinking_fund)
- [X] T005 [P] Implement `_update_goal_target(category_id: str, goal_target_milliunits: int) -> str` in src/tools/ynab.py — new YNAB API call: PATCH `/budgets/{YNAB_BUDGET_ID}/categories/{category_id}` with JSON body `{"category": {"goal_target": goal_target_milliunits}}`. Return success message or error. This is distinct from the existing `update_category_budget()` which patches `budgeted` via `/months/{month}/categories/{id}`
- [X] T006 Implement `_calculate_health_score(profiles: list[dict]) -> float` in src/tools/ynab.py — dollar-weighted alignment formula: for each profile with a goal (goal_target > 0 and drift_type != "missing_goal"), compute drift = abs(spending_avg - goal_target) and weight = max(spending_avg, goal_target). Return max(0, (1 - sum(drift) / sum(weight)) * 100). Round to 1 decimal place

**Checkpoint**: Foundation ready — category profiling, goal updating, and health scoring all functional

---

## Phase 3: User Story 1 — Goal Drift Detection & Suggestions (Priority: P1) MVP

**Goal**: Detect goal drift, present suggestions, let user approve/skip individual goal updates, integrate into weekly meeting prep

**Independent Test**: Send "how are my budget goals?" in WhatsApp, receive ranked drift report, reply "yes to restaurants" and verify YNAB goal_target is updated

### Implementation for User Story 1

- [X] T007 [US1] Implement `budget_health_check(lookback_months: int = 3, drift_threshold: float = 30) -> str` in src/tools/ynab.py — call `_build_category_profiles()`, call `_calculate_health_score()`, build GoalSuggestion list for all profiles with drift_type != "aligned" (set recommended_goal = round(spending_avg / 25) * 25 for clean numbers, has_existing_goal = goal_type is not None), save suggestions via `_save_pending_suggestions()`, format and return WhatsApp report
- [X] T008 [US1] Implement `_format_health_report(health_score: float, profiles: list[dict], suggestions: list[dict]) -> str` in src/tools/ynab.py — format WhatsApp message following quickstart.md Scenario 1 format: health score header, underfunded section (numbered, ranked by dollar gap desc), overfunded section, missing goals section, spiky category notes, and actionable prompt ("Reply 'update all', 'yes to 1', 'skip 3', or 'set 2 to $2000'"). Respect WhatsApp ~4096 char limit — truncate to top 10 suggestions if needed
- [X] T009 [US1] Implement `apply_goal_suggestion(category: str = "", amount: float = 0, apply_all: bool = False) -> str` in src/tools/ynab.py — if apply_all: load all pending suggestions, for each with has_existing_goal=True call `_update_goal_target()`, skip those without goals (return instructions to create in YNAB app), return summary. If category specified: fuzzy match via `_fuzzy_match_category()`, find in pending suggestions, update goal_target (use amount if provided, else recommended_goal), save updated suggestions, return confirmation with old/new goal and remaining count. Handle error: no pending suggestions, category not found, category has no existing goal
- [X] T010 [US1] Add `budget_health_check` and `apply_goal_suggestion` tool definitions to the TOOLS list in src/assistant.py — use exact JSON schemas from contracts/api-endpoints.md. Add corresponding entries to TOOL_FUNCTIONS dict: `"budget_health_check": lambda **kw: ynab.budget_health_check(kw.get("lookback_months", 3), kw.get("drift_threshold", 30))` and `"apply_goal_suggestion": lambda **kw: ynab.apply_goal_suggestion(kw.get("category", ""), kw.get("amount", 0), kw.get("apply_all", False))`
- [X] T011 [US1] Add system prompt rules for budget health check in src/assistant.py — add 2 new rules: (1) When user asks about budget goals, goal health, or budget drift, use `budget_health_check` tool. (2) When user replies with "yes to [category]", "update all", "skip [category]", or "set [category] to $X" after a budget health check, use `apply_goal_suggestion` with appropriate params
- [X] T012 [US1] Enhance meeting prep in src/assistant.py — find where `create_meeting` tool builds the agenda (in the system prompt or tool function), add instruction: "Include a 'Budget Goal Health' section in the meeting agenda. Call `budget_health_check` silently and if any categories have >30% drift, add a brief summary: count of drifted categories, the largest drift, count of missing goals, health score, and a pointer to say 'budget health check' for full details"

**Checkpoint**: US1 complete — on-demand health check, individual/bulk goal updates, meeting prep integration. Manually testable via WhatsApp.

---

## Phase 4: User Story 2 — Bonus & Large Deposit Allocation (Priority: P2)

**Goal**: Generate prioritized allocation plans for bonus income, let user approve/adjust, execute money moves in YNAB

**Independent Test**: Send "where should this $5,000 bonus go?" in WhatsApp, receive tiered allocation plan, reply "approve" and verify YNAB budgeted amounts updated

### Implementation for User Story 2

- [X] T013 [US2] Implement `_classify_priority_tiers(profiles: list[dict]) -> list[dict]` in src/tools/ynab.py — for each profile, infer priority_tier from group_name: groups containing keywords like "bills", "mortgage", "insurance", "utilities", "healthcare", "food", "groceries", "car", "kids" → "essential"; groups containing "savings", "emergency", "fund", "debt" → "savings"; everything else → "discretionary". Return profiles with priority_tier field added. This is a heuristic classification — Claude refines at presentation time
- [X] T014 [US2] Implement `allocate_bonus(amount: float = 0, description: str = "") -> str` in src/tools/ynab.py — if amount is 0, search recent YNAB transactions for large inflows (> $1000 in last 14 days) and use the largest; if still 0, return "Please specify the bonus amount". Call `_build_category_profiles(lookback_months=1)` for current month only, call `_classify_priority_tiers()`, compute shortfall for each category (goal_target - budgeted + abs(activity) or shortfall from goal_under_funded field), build allocation list ordered by tier then shortfall desc, distribute amount: fill essentials first (up to shortfall), then savings, then discretionary, remaining goes to largest underfunded. Save plan via `_save_pending_allocation()`. Format and return via `_format_allocation_plan()`
- [X] T015 [US2] Implement `_format_allocation_plan(plan: dict) -> str` in src/tools/ynab.py — format WhatsApp message following quickstart.md Scenario 3 format: header with total amount and source, Essential tier section, Savings tier section, Discretionary tier section, each with bullet points showing category +$amount (rationale), total line, and prompt "Reply 'approve' to move money, or adjust: 'put $3000 in emergency fund'"
- [X] T016 [US2] Implement `approve_allocation(adjustments: str = "") -> str` in src/tools/ynab.py — load pending allocation via `_load_pending_allocation()`. If adjustments provided, re-run allocate_bonus with parsed adjustments (simple pattern matching: "put $X in [category]" adjusts that allocation, redistributes remainder). If no adjustments: for each allocation, call existing `update_category_budget(category_name, allocated_amount)`. Return confirmation per quickstart.md Scenario 4 format with per-category results and updated health score. Clear pending allocation file after execution
- [X] T017 [P] [US2] Add `allocate_bonus` and `approve_allocation` tool definitions to TOOLS list in src/assistant.py — use exact JSON schemas from contracts/api-endpoints.md. Add to TOOL_FUNCTIONS: `"allocate_bonus": lambda **kw: ynab.allocate_bonus(kw.get("amount", 0), kw.get("description", ""))` and `"approve_allocation": lambda **kw: ynab.approve_allocation(kw.get("adjustments", ""))`
- [X] T018 [US2] Add system prompt rules for bonus allocation in src/assistant.py — add 2 new rules: (1) When user mentions bonus, stock vesting, extra income, or asks "where should this money go?", use `allocate_bonus`. Extract dollar amount if mentioned. (2) When user says "approve", "do it", "yes" after seeing an allocation plan, use `approve_allocation`. When user provides adjustments like "put more in X", use `approve_allocation` with adjustments param

**Checkpoint**: US2 complete — bonus allocation plans with tier prioritization, approval/adjustment flow, money moves in YNAB. Independently testable.

---

## Phase 5: User Story 3 — Monthly Budget Health Check (Priority: P3)

**Goal**: Automated monthly health check via n8n, sends WhatsApp report directly, brief message when healthy

**Independent Test**: Curl `POST /api/v1/budget/health-check` with auth header, verify WhatsApp message received with health score and suggestions

### Implementation for User Story 3

- [X] T019 [US3] Implement `run_budget_health_check() -> str | None` in src/tools/ynab.py — orchestrator for scheduled runs: call `budget_health_check()` to get the full report string, compute health_score separately via `_build_category_profiles()` + `_calculate_health_score()`. If health_score >= 90 and no drifted categories: send brief "budget is healthy" message via `send_sync_message_direct()` (imported from src.assistant). Otherwise: send the full report. Return status string with health_score and drifted_count. Wrap in try/except for YNAB API errors — log errors, do NOT send technical errors to WhatsApp
- [X] T020 [US3] Add `POST /api/v1/budget/health-check` endpoint to src/app.py — follow exact pattern of existing email_sync_endpoint: `@app.post("/api/v1/budget/health-check")`, depends on `verify_n8n_auth`, uses `BackgroundTasks` to run `ynab.run_budget_health_check()` asynchronously, returns `{"status": "sent"}`
- [X] T021 [US3] Create n8n workflow JSON in scripts/n8n-workflows/monthly-budget-health.json — Schedule Trigger node: Cron expression for 1st of each month at 9:00am Pacific (0 9 1 * *), timezone America/Los_Angeles. HTTP Request node: POST to http://fastapi:8000/api/v1/budget/health-check, header X-N8N-Auth with value {{$env.N8N_WEBHOOK_SECRET}}, timeout 300000ms

**Checkpoint**: US3 complete — monthly scheduled health check, brief/detailed message logic, n8n workflow ready

---

## Phase 6: User Story 4 — Stale Category & Merge Detection (Priority: P4)

**Goal**: Detect stale categories and merge candidates, present cleanup suggestions, handle user responses

**Independent Test**: Send "are there any budget categories I should clean up?" in WhatsApp, receive stale/merge report with sinking funds correctly excluded

### Implementation for User Story 4

- [X] T022 [US4] Implement `_detect_merge_candidates(profiles: list[dict]) -> list[dict]` in src/tools/ynab.py — find categories where: (a) both have avg spending < $200/mo, AND (b) at least one similarity signal: names share a common word (case-insensitive, excluding stop words like "the", "and"), OR categories are in the same YNAB group with combined spending < $300/mo. Return list of MergeCandidate dicts: {categories: [name1, name2], combined_avg_spending, rationale, suggested_name}
- [X] T023 [US4] Implement `_format_cleanup_report(stale_profiles: list[dict], sinking_fund_profiles: list[dict], merge_candidates: list[dict]) -> str` in src/tools/ynab.py — format WhatsApp message per quickstart.md Scenario 6: numbered stale categories with goal amount and months of $0, "NOT stale" section showing sinking funds with checkmarks, numbered merge candidates with combined spending and suggested name, prompt "Reply 'remove 1', 'merge 3', or 'skip all'"
- [X] T024 [US4] Enhance `budget_health_check()` in src/tools/ynab.py — after computing profiles and health report, also call `_detect_merge_candidates()`, filter profiles for stale and sinking fund, append stale/merge sections to the report using `_format_cleanup_report()`. Only include these sections when stale_count > 0 or merge_candidates > 0
- [X] T025 [US4] Add system prompt rules for category cleanup in src/assistant.py — add rules: (1) When user asks about cleaning up budget, stale categories, or merging categories, use `budget_health_check` tool. (2) When user says "remove [N]" or "remove [category]" after cleanup report, use `apply_goal_suggestion` with amount=0 to zero out the goal. (3) Merge operations: bot advises user to merge categories manually in YNAB app (not API-supported), then re-run health check to verify

**Checkpoint**: US4 complete — stale detection with sinking fund exclusion, merge candidates, cleanup suggestions

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Help menu integration, validation, deployment

- [X] T026 Add budget maintenance tools to src/tools/discovery.py — add `budget_health_check`, `apply_goal_suggestion`, `allocate_bonus`, `approve_allocation` to TOOL_TO_CATEGORY mapping (all → "budget"). Update budget category capabilities text to include "check budget health, update drifted goals, allocate bonus income". Add static_example "how are my budget goals?". Add 2 TIP_DEFINITIONS: (1) tip_budget_health triggered by get_budget_summary/search_transactions → "Say 'how are my budget goals?' to check for goal drift and get update suggestions", (2) tip_bonus_allocate triggered by budget_health_check → "Got a bonus? Say 'where should this $X go?' for a prioritized allocation plan"
- [X] T027 Syntax validation — run `python -c "import src.tools.ynab"` and `python -c "import src.assistant"` to verify no import or syntax errors in modified files
- [X] T028 End-to-end validation — deploy to NUC via `./scripts/nuc.sh deploy`, trigger health check via curl `POST /api/v1/budget/health-check`, verify WhatsApp message received, test on-demand via WhatsApp "how are my budget goals?", verify suggestions can be approved

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: T003 first, then T004 (depends on T003). T005 is parallel (independent API endpoint). T006 depends on T004 (needs profiles structure)
- **User Story 1 (Phase 3)**: Depends on Phase 2 (T003-T006) — BLOCKS on foundational data infrastructure
- **User Story 2 (Phase 4)**: Depends on Phase 2 (needs `_build_category_profiles` and `update_category_budget`). Independent of US1
- **User Story 3 (Phase 5)**: Depends on US1 T007 (`budget_health_check` function must exist). Adds scheduling and direct WhatsApp send
- **User Story 4 (Phase 6)**: Depends on Phase 2 (needs profiles). T024 depends on US1 T007 (enhances `budget_health_check`)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2. No dependencies on other stories. **This is the MVP.**
- **User Story 2 (P2)**: Can start after Phase 2. Independent of US1 — uses `_build_category_profiles` directly
- **User Story 3 (P3)**: Depends on US1 T007 (`budget_health_check` function). Adds scheduled orchestrator wrapping US1's core function
- **User Story 4 (P4)**: Depends on Phase 2 for profiles. T024 modifies US1's `budget_health_check` to include stale/merge sections

### Within Each User Story

- Functions before formatters
- Core logic before tool definitions (assistant.py)
- Tool definitions before system prompt rules
- All implementation before checkpoint validation

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T001, T002 can run in parallel (different files/functions)
```

**Phase 2 (Foundational)**:
```
T005 can run in parallel with T003-T004 (independent API endpoint)
```

**Phase 3 (US1)**:
```
T010, T011 can run in parallel after T009 (different sections of assistant.py, but T010 is TOOLS list, T011 is system prompt)
```

**Phase 4 (US2)**:
```
T017 can run in parallel with T016 (assistant.py tool defs vs ynab.py implementation)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T006)
3. Complete Phase 3: User Story 1 (T007-T012)
4. **STOP and VALIDATE**: Deploy to NUC, send "how are my budget goals?" in WhatsApp, verify report, approve a suggestion, verify YNAB updated
5. Deploy if ready — family can immediately start fixing drifted goals

### Incremental Delivery

1. Setup + Foundational → profile building and goal update infrastructure ready
2. Add User Story 1 → on-demand health check + goal suggestions working (MVP!)
3. Add User Story 2 → bonus allocation flow working
4. Add User Story 3 → monthly scheduled health check automated
5. Add User Story 4 → stale/merge detection added to health reports
6. Polish → help menu, E2E validation, deployment
7. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All new functions go in src/tools/ynab.py (extending existing module, not creating new one)
- YNAB API limitation: `goal_type` is read-only — cannot create new goals, only update `goal_target` on existing goals
- Pending suggestions and allocation plans use `data/*.json` atomic write pattern (same as Amazon/email sync)
- WhatsApp message limit ~4096 chars — health reports truncate to top 10 suggestions if needed
- YNAB rate limit: 200 requests/hour — health check uses 3-6 calls, well within limits
- Priority tier classification is heuristic (keyword-based) in the tool function, with Claude refining at presentation time
