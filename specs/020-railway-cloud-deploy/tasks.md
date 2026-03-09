# Tasks: Railway Cloud Deployment

**Input**: Design documents from `/specs/020-railway-cloud-deploy/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: No test tasks — tests not explicitly requested in the spec. Verification is via quickstart.md scenarios.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create new files and add dependencies needed by subsequent phases

- [x] T001 Create railway.toml with Dockerfile build config and healthcheck at /railway.toml
- [x] T002 [P] Create data/schedules.json with 14 default scheduled jobs (timezone America/Los_Angeles) at data/schedules.json
- [x] T003 [P] Add apscheduler>=3.10.0 to requirements.txt

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Make integrations optional so the app can start with only ANTHROPIC_API_KEY + WhatsApp configured. This MUST complete before any user story work.

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Refactor src/config.py — change REQUIRED_VARS to require ANTHROPIC_API_KEY + WHATSAPP_PHONE_NUMBER_ID + WHATSAPP_ACCESS_TOKEN + WHATSAPP_VERIFY_TOKEN + WHATSAPP_APP_SECRET + N8N_WEBHOOK_SECRET (core required for any instance); move Notion, Google Calendar, and YNAB vars to optional with empty-string defaults using os.environ.get(); remove sys.exit(1) for optional vars
- [x] T005 Add new env vars to src/config.py: GOOGLE_TOKEN_JSON (str, default ""), GOOGLE_CREDENTIALS_JSON (str, default ""), SCHEDULER_ENABLED (bool, default True parsed from env)
- [x] T006 [P] Update .env.example — add GOOGLE_TOKEN_JSON, GOOGLE_CREDENTIALS_JSON, SCHEDULER_ENABLED, RAILWAY_RUN_UID sections with documented grouping (Required / Optional per integration / Railway-specific)

**Checkpoint**: App can start with ANTHROPIC_API_KEY + WhatsApp + N8N_WEBHOOK_SECRET set; missing optional integrations (Notion, Google Calendar, YNAB) log warnings but don't crash

---

## Phase 3: User Story 2 — Persistent Storage Without Local Files (Priority: P1)

**Goal**: All data persists across Railway redeploys via volume mount at /app/data

**Independent Test**: Push data via API, trigger redeploy, verify data intact

### Implementation for User Story 2

- [x] T007 [US2] Update Dockerfile to COPY data/ directory for default schedules.json template (add `COPY data/ data/` before CMD, but after pip install)
- [x] T008 [US2] Verify all data file paths in src/ use consistent /app/data prefix — grep for hardcoded `data/` paths and confirm they resolve correctly when WORKDIR=/app

**Checkpoint**: Data files persist across container restarts when /app/data is volume-mounted

---

## Phase 4: User Story 4 — Google OAuth in Containers (Priority: P1)

**Goal**: Google Calendar works without browser-based OAuth; tokens auto-refresh from env var

**Independent Test**: Set GOOGLE_TOKEN_JSON env var, start app, verify calendar reads work without browser flow

### Implementation for User Story 4

- [x] T009 [US4] Modify src/tools/calendar.py _get_service() — add env-var-first loading: if GOOGLE_TOKEN_JSON is set, use Credentials.from_authorized_user_info(json.loads(GOOGLE_TOKEN_JSON)); if GOOGLE_CREDENTIALS_JSON is set, use it for client config; fall back to existing file-based loading
- [x] T010 [US4] In src/tools/calendar.py _get_service() — after token refresh, write updated token to /app/data/token.json (volume-backed) so refreshed tokens survive redeploy even if env var has stale token

**Checkpoint**: Calendar works when GOOGLE_TOKEN_JSON env var is set; tokens auto-refresh and persist to volume

---

## Phase 5: User Story 3 — Scheduled Jobs Without n8n (Priority: P1)

**Goal**: All 14 scheduled automations run via in-app APScheduler, no n8n needed

**Independent Test**: Start app with SCHEDULER_ENABLED=true, check logs for scheduler startup message with job count, wait for a job to fire

### Implementation for User Story 3

- [x] T011 [US3] Create src/scheduler.py — AsyncIOScheduler with CronTrigger per job from data/schedules.json; define ENDPOINT_HANDLERS dict mapping endpoint paths (e.g. "briefing/daily") to async wrapper functions that call the underlying business logic directly (e.g. generate_daily_plan() + send_message(), NOT the FastAPI endpoint wrappers which depend on BackgroundTasks/Request objects); log job start/end/duration/errors
- [x] T012 [US3] Modify src/app.py — add async lifespan context manager that starts scheduler on startup (if SCHEDULER_ENABLED) and shuts it down on shutdown; pass lifespan to FastAPI() constructor
- [x] T013 [US3] Ensure Dockerfile CMD uses single uvicorn worker (no --workers flag) to prevent duplicate job execution — verify current CMD is correct (it is: no --workers flag)

**Checkpoint**: Scheduler starts with 14 jobs, logs show job executions at configured times

---

## Phase 6: User Story 1 — Deploy MomBot to Railway / A/B with NUC (Priority: P1) MVP

**Goal**: App runs on Railway with all integrations; Jason can switch between NUC and Railway by changing WhatsApp webhook URL

**Independent Test**: Deploy to Railway, hit /health, send WhatsApp message, receive response

### Implementation for User Story 1

- [x] T014 [US1] Deploy FastAPI service to Railway — create project, link GitHub repo, add volume at /app/data, set all required env vars (ANTHROPIC_API_KEY, WHATSAPP_*, N8N_WEBHOOK_SECRET, PORT=8000, RAILWAY_RUN_UID=0)
- [x] T015 [US1] Set optional integration env vars on Railway — GOOGLE_TOKEN_JSON, GOOGLE_CREDENTIALS_JSON, GOOGLE_CALENDAR_*_ID, NOTION_*, YNAB_*, OUTLOOK_CALENDAR_ICS_URL
- [x] T016 [US1] Verify end-to-end: health check returns 200, WhatsApp webhook responds, daily briefing fires, scheduler shows 14 jobs in logs, container starts serving within 60s (NFR-001), message response latency ≤15s (NFR-003)

**Checkpoint**: Railway instance fully operational, can switch WhatsApp webhook between NUC and Railway

---

## Phase 7: User Story 6 — Security Lockdown for Sensitive Integrations (Priority: P2)

**Goal**: No credentials in logs; all endpoints authenticated; graceful degradation

**Independent Test**: Audit Railway logs for secrets; send unauthenticated request and verify rejection

### Implementation for User Story 6

- [x] T017 [P] [US6] Audit all logger.* calls in src/ for potential credential leaks — ensure no log statement includes ANTHROPIC_API_KEY, WHATSAPP_ACCESS_TOKEN, WHATSAPP_APP_SECRET, N8N_WEBHOOK_SECRET, GOOGLE_TOKEN_JSON, NOTION_TOKEN, YNAB_ACCESS_TOKEN, or any other secret values
- [x] T018 [P] [US6] Add graceful degradation in src/assistant.py and tool modules — when an integration's env vars are empty, skip related tools and return user-friendly messages (e.g., "Calendar not configured" instead of crashing)
- [x] T019 [US6] Verify verify_n8n_auth dependency is applied to ALL /api/v1/* endpoints in src/app.py — scan for any endpoint missing the dependency

**Checkpoint**: No secrets in logs, unauthenticated requests rejected, missing integrations degrade gracefully

---

## Phase 8: User Story 5 — Template Repo for Self-Service Onboarding (Priority: P2)

**Goal**: Non-technical user can create their own MomBot instance using GitHub template + Claude Code guidance

**Independent Test**: Follow ONBOARDING.md from scratch, end up with a working instance

### Implementation for User Story 5

- [x] T020 [US5] Create ONBOARDING.md at repo root — step-by-step Claude Code guided setup covering: Railway account creation, GitHub template usage, WhatsApp Business setup (own Meta developer account), env var configuration, volume setup, Google OAuth app publishing, optional integrations (Notion, YNAB, AnyList)
- [x] T021 [P] [US5] Add upstream update section to ONBOARDING.md — document manual git remote add upstream pattern and git pull workflow for now; note that automated WhatsApp notification + rollback is planned for a future feature (see GitHub issue #30)
- [x] T022 [US5] Verify repo is ready for GitHub template — ensure no hardcoded family-specific values in committed code (calendar IDs, phone numbers, Notion DB IDs must all come from env vars); verify complete data isolation (FR-007) by confirming no cross-tenant data paths exist

**Checkpoint**: ONBOARDING.md provides complete self-service path; no hardcoded family data in codebase

---

## Phase 9: User Story 7 — AnyList Sidecar on Railway (Priority: P3)

**Goal**: Optional AnyList Node.js sidecar runs as separate Railway service with private networking

**Independent Test**: Deploy sidecar, set ANYLIST_SIDECAR_URL to railway.internal URL, verify grocery operations work

### Implementation for User Story 7

- [x] T023 [US7] Document AnyList sidecar Railway setup in ONBOARDING.md — second service in same Railway project, root directory /anylist-sidecar, no public domain, private networking via http://anylist-sidecar.railway.internal:3000, env vars ANYLIST_EMAIL + ANYLIST_PASSWORD
- [x] T024 [US7] Verify src/tools/anylist_bridge.py gracefully handles ANYLIST_SIDECAR_URL being unreachable (connection refused → user-friendly error, not crash)

**Checkpoint**: Sidecar deploys as optional service; main app works fine without it

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation updates

- [x] T025 Update CLAUDE.md — add Railway deployment section (020-railway-cloud-deploy), document new env vars, scheduler architecture
- [x] T026 [P] Run quickstart.md scenarios 1-7 as validation checklist
- [x] T027 Verify all 14 scheduled jobs have correct endpoint-to-handler mappings in src/scheduler.py by cross-referencing data/schedules.json endpoints with src/app.py endpoint definitions; verify non-Pacific timezone support (FR-013) by testing with a different timezone value in schedules.json

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US2 Storage (Phase 3)**: Depends on Foundational — can run in parallel with US4
- **US4 OAuth (Phase 4)**: Depends on Foundational (T005) — can run in parallel with US2
- **US3 Scheduler (Phase 5)**: Depends on Foundational + Setup (T002 for schedules.json, T003 for apscheduler)
- **US1 Deploy (Phase 6)**: Depends on US2, US3, US4 — integration/validation of all P1 stories
- **US6 Security (Phase 7)**: Depends on Foundational (T004 graceful config) — can start after Phase 2
- **US5 Template (Phase 8)**: Depends on US1 (proven deployment pattern)
- **US7 Sidecar (Phase 9)**: Depends on US1 (Railway project exists)
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US2 (Storage)**: Independent after Foundational — zero code changes (volume mount config only)
- **US4 (OAuth)**: Independent after Foundational — only touches calendar.py
- **US3 (Scheduler)**: Independent after Foundational — only touches scheduler.py (new) and app.py lifespan
- **US1 (Deploy)**: Integration story — needs US2 + US3 + US4 working first
- **US6 (Security)**: Independent after Foundational — audit/hardening pass
- **US5 (Template)**: Needs US1 validated first (proven deployment)
- **US7 (Sidecar)**: Needs US1 (Railway project) but otherwise independent

### Within Each User Story

- Config changes before feature code
- New files before modifications
- Core logic before integration/validation

### Parallel Opportunities

- T002 and T003 can run in parallel (Phase 1)
- T006 can run in parallel with T004/T005 (Phase 2)
- US2 and US4 can run in parallel after Foundational
- US6 can start as soon as Foundational is done (parallel with US3/US4)
- T017 and T018 can run in parallel (Phase 7)

---

## Parallel Example: After Foundational Phase

```text
# These can all start simultaneously after Phase 2:
Track A: T007 → T008 (US2: Storage)
Track B: T009 → T010 (US4: OAuth)
Track C: T011 → T012 → T013 (US3: Scheduler)
Track D: T017 → T018 → T019 (US6: Security)

# After Tracks A+B+C complete:
Track E: T014 → T015 → T016 (US1: Deploy — MVP!)

# After Track E:
Track F: T020 → T021 → T022 (US5: Template)
Track G: T023 → T024 (US7: Sidecar)
```

---

## Implementation Strategy

### MVP First (Phase 1 + 2 + 3 + 4 + 5 + 6)

1. Complete Phase 1: Setup (railway.toml, schedules.json, apscheduler dep)
2. Complete Phase 2: Foundational (optional config, new env vars)
3. Complete Phases 3-5 in parallel: US2 (storage), US4 (OAuth), US3 (scheduler)
4. Complete Phase 6: US1 Deploy to Railway
5. **STOP and VALIDATE**: Run quickstart scenarios 1-4
6. A/B test with NUC for 7+ days

### Incremental Delivery

1. Setup + Foundational → App starts with minimal config
2. US2 + US4 + US3 → Cloud-ready features (storage, auth, scheduling)
3. US1 → Deploy to Railway, A/B test with NUC (MVP!)
4. US6 → Security hardening
5. US5 → Template repo, onboard pastor
6. US7 → Optional AnyList sidecar

### Suggested MVP Scope

**US1 + US2 + US3 + US4** (Phases 1-6, tasks T001-T016) — deploys Jason's family to Railway with all integrations working. This proves the platform before offering to anyone else.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Single uvicorn worker is a hard constraint (APScheduler requirement)
- Railway Volume at /app/data — zero data migration needed (same JSON files, same paths)
- schedules.json ships with defaults; customizable per instance on the volume
- Google OAuth: publish app (not testing mode) removes 7-day token expiry
- All integrations except WhatsApp are optional — app works as standalone chat assistant
