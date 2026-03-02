# Tasks: iOS Work Calendar Sync

**Input**: Design documents from `/specs/015-ios-work-calendar/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/work-events-endpoint.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No setup needed — existing Python 3.12 + FastAPI project. No new dependencies required.

*(No tasks — all dependencies already installed: FastAPI, Pydantic, json stdlib)*

---

## Phase 2: Foundational (Storage Helpers)

**Purpose**: Shared file I/O helpers that BOTH US1 (endpoint writes) and US2 (tool reads) depend on.

**CRITICAL**: Must complete before user story work begins.

- [x] T001 Add `_load_work_calendar()`, `save_work_calendar()`, and `_prune_expired()` helper functions to src/tools/outlook.py. Storage file: `data/work_calendar.json`. Use atomic write pattern (write to `.tmp` then rename) matching `src/preferences.py`. `_load_work_calendar(target_date: str)` returns list of event dicts for that date (or None if no data/expired). `save_work_calendar(events_by_date: dict)` writes grouped events with `received_at` timestamp and prunes entries older than 7 days. Docker-aware path: `Path("/app/data")` if exists else `Path("data")`.

**Checkpoint**: Storage helpers ready — US1 and US2 can now proceed.

---

## Phase 3: User Story 1 — Weekly Work Calendar Push (Priority: P1) MVP

**Goal**: iOS Shortcut POSTs work calendar events to an authenticated endpoint; events are stored keyed by date.

**Independent Test**: `curl -X POST http://localhost:8000/api/v1/calendar/work-events -H "X-N8N-Auth: $SECRET" -H "Content-Type: application/json" -d '{"events":[{"title":"Standup","start":"2026-03-03T09:00:00","end":"2026-03-03T09:30:00"}]}'` — returns 200 with `events_received: 1` and data appears in `data/work_calendar.json`.

### Implementation for User Story 1

- [x] T002 [US1] Add Pydantic request model `WorkEventInput(title: str, start: str, end: str)` and `WorkEventsRequest(events: list[WorkEventInput])` in src/app.py. Add response fields: `status`, `events_received`, `dates_covered`, `message`.
- [x] T003 [US1] Add `POST /api/v1/calendar/work-events` endpoint in src/app.py with `dependencies=[Depends(verify_n8n_auth)]`. Parse events, group by date (extract date from `start` field), call `save_work_calendar()` from outlook.py. Return summary with event count and covered dates. Synchronous — no background task needed. Import `save_work_calendar` from `src.tools.outlook`.
- [x] T004 [US1] Verify endpoint works: start server locally, POST sample events via curl (per quickstart.md Scenario 1 and Scenario 6), confirm `data/work_calendar.json` is created with correct structure. Verify auth rejection (Scenario 4).

**Checkpoint**: Endpoint accepts and stores work events. US1 is testable independently.

---

## Phase 4: User Story 2 — Daily Plan Uses Work Calendar (Priority: P1)

**Goal**: `get_outlook_events()` and `get_outlook_busy_windows()` read from pushed data when ICS URL is not configured. Daily plan shows Jason's meeting windows.

**Independent Test**: Push sample events for today via curl, then run `python3 -c "from src.tools.outlook import get_outlook_events; print(get_outlook_events())"` — output shows the pushed meetings with times.

**Depends on**: Phase 2 (storage helpers) and Phase 3 (data must exist to read)

### Implementation for User Story 2

- [x] T005 [US2] Modify `get_outlook_events()` in src/tools/outlook.py: after the `if not OUTLOOK_CALENDAR_ICS_URL` check, call `_load_work_calendar(dt.isoformat())`. If it returns a list (even empty), format events as time-block lines (same format as ICS path). If it returns `None`, return the existing "not configured" message. Empty list → "Jason has no work meetings on [day]." This preserves ICS URL priority: if ICS URL is set, it's tried first (existing behavior).
- [x] T006 [US2] Modify `get_outlook_busy_windows()` in src/tools/outlook.py: same fallback pattern. If `OUTLOOK_CALENDAR_ICS_URL` is empty, call `_load_work_calendar()`. If data exists, parse start/end times and return `(title, start_time, end_time)` tuples. If no data, return empty list (existing behavior).
- [x] T007 [US2] Verify integration: push events for today via curl, then call `get_outlook_events()` and `get_outlook_busy_windows()` — confirm both return the pushed data. Also verify expired data (>7 days old) returns "unavailable" per quickstart.md Scenario 5.

**Checkpoint**: Daily plan generation now includes Jason's work meetings from pushed data.

---

## Phase 5: User Story 3 — iOS Shortcut Setup Guide (Priority: P2)

**Goal**: Jason has clear step-by-step instructions to create the iOS Shortcut automation on his iPhone.

**Independent Test**: Follow the instructions on an iPhone and verify the shortcut sends a test request to the endpoint.

### Implementation for User Story 3

- [x] T008 [US3] Write iOS Shortcut setup guide at docs/ios-shortcut-setup.md. Include: (1) Overview of what the shortcut does, (2) Step-by-step shortcut creation: "Find Calendar Events" action filtered to Cisco/work calendar for the upcoming Mon-Fri, "Repeat with Each" to build JSON array of `{title, start, end}`, "Get Contents of URL" with POST to `https://mombot.sierrastoryco.com/api/v1/calendar/work-events` with `X-N8N-Auth` header and JSON body, (3) Automation setup: weekly trigger Sunday 7:00 PM, enable "Run Immediately", (4) Testing: how to manually trigger and verify the response, (5) Troubleshooting: common issues (no internet, wrong calendar selected, auth error).

**Checkpoint**: Jason can follow the guide to set up the shortcut.

---

## Phase 6: Polish & Deployment

**Purpose**: Deploy, validate end-to-end, and set up the actual automation.

- [x] T009 Commit all changes, push to branch, deploy to NUC via `./scripts/nuc.sh deploy`
- [ ] T010 Run quickstart.md Scenario 6 (full weekly push) against production endpoint on NUC. Verify `get_outlook_events` returns pushed data. Verify module imports work on NUC.
- [ ] T011 Set up iOS Shortcut on Jason's iPhone following docs/ios-shortcut-setup.md. Run manual test push. Verify events appear in daily plan generation.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A — no setup needed
- **Foundational (Phase 2)**: T001 — storage helpers. BLOCKS all user stories.
- **US1 (Phase 3)**: T002-T004 — depends on T001. Can proceed after foundational.
- **US2 (Phase 4)**: T005-T007 — depends on T001. Also needs T003 done (endpoint must exist to push test data).
- **US3 (Phase 5)**: T008 — depends on T003 (needs to reference the real endpoint URL). Can run in parallel with US2.
- **Polish (Phase 6)**: T009-T011 — depends on all user stories complete.

### User Story Dependencies

- **US1 (P1)**: Depends only on foundational (T001). Core data pipeline.
- **US2 (P1)**: Depends on foundational (T001). Needs US1 endpoint (T003) for test data.
- **US3 (P2)**: Documentation only. Needs endpoint URL from US1.

### Parallel Opportunities

- T005 and T006 can run in parallel (different functions in same file, but no conflicts)
- T008 (docs) can run in parallel with T005-T007 (code changes)

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete T001 (storage helpers)
2. Complete T002-T003 (endpoint)
3. Complete T004 (verify)
4. **STOP and VALIDATE**: curl test confirms events stored correctly
5. Deploy if ready — Jason can start pushing events immediately

### Incremental Delivery

1. T001 → Foundation ready
2. T002-T004 → US1 complete → Endpoint works, data stored
3. T005-T007 → US2 complete → Daily plan uses pushed data
4. T008 → US3 complete → Jason has setup instructions
5. T009-T011 → Deployed and live

---

## Notes

- Total: 11 tasks
- No new Python dependencies needed
- ~50 lines of new code across 2 files (app.py, outlook.py)
- 1 new documentation file (docs/ios-shortcut-setup.md)
- 1 new data file created at runtime (data/work_calendar.json)
