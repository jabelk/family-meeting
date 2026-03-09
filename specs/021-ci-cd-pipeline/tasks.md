# Tasks: CI/CD Pipeline

**Input**: Design documents from `/specs/021-ci-cd-pipeline/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, contracts/

**Tests**: No test tasks — tests not explicitly requested in the spec. Verification is via quickstart.md scenarios.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create new files and add dependencies needed by subsequent phases

- [x] T001 Create pyproject.toml with Ruff config (target-version py312, line-length 120, select E/F/I) and pytest config (testpaths=tests) at /pyproject.toml
- [x] T002 [P] Add ruff and pytest to requirements.txt (dev dependencies section or inline comment) at /requirements.txt
- [x] T003 [P] Create .github/workflows/ directory and empty ci.yml placeholder at /.github/workflows/ci.yml
- [x] T004 [P] Create tests/ directory with empty __init__.py and a minimal smoke test (test_smoke.py: imports src.app, asserts app is a FastAPI instance) at /tests/test_smoke.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix existing code to pass Ruff linting — MUST complete before CI workflow can pass

**CRITICAL**: The existing codebase has never been linted. Ruff will flag errors that must be fixed before CI can report green.

- [x] T005 Run `ruff check src/` locally and fix all E (pycodestyle) and F (pyflakes) errors across src/ files — auto-fix with `ruff check --fix src/` then review and manually fix remaining issues
- [x] T006 Run `ruff format --check src/` locally and fix formatting issues — auto-format with `ruff format src/` then review changes
- [x] T007 Verify `pytest tests/` passes locally with the smoke test from T004

**Checkpoint**: `ruff check src/` and `ruff format --check src/` both pass cleanly; `pytest tests/` passes

---

## Phase 3: User Story 1 — Automated Testing on Every Push (Priority: P1) MVP

**Goal**: PRs and pushes to main trigger automated lint, test, and quality checks with results visible on the PR

**Independent Test**: Open a PR with a change to src/; verify lint, test, and gate jobs run and report status

### Implementation for User Story 1

- [x] T008 [US1] Write ci.yml change detection job — use dorny/paths-filter@v3 to detect `app` changes (src/**, tests/**, requirements.txt, Dockerfile, pyproject.toml) at /.github/workflows/ci.yml
- [x] T009 [US1] Write ci.yml lint-format job — setup Python 3.12, pip cache, install ruff, run `ruff check src/` and `ruff format --check src/`; condition on app changes at /.github/workflows/ci.yml
- [x] T010 [US1] Write ci.yml test job — setup Python 3.12, pip cache, install requirements.txt + pytest, run `pytest tests/`; condition on app changes at /.github/workflows/ci.yml
- [x] T011 [US1] Write ci.yml gate job — aggregate all job statuses using `if: always()` and check that no required job failed; this is the single status check for branch protection at /.github/workflows/ci.yml
- [x] T012 [US1] Add concurrency control to ci.yml — `concurrency: group: ci-${{ github.ref }}, cancel-in-progress: true` at /.github/workflows/ci.yml
- [x] T013 [US1] Add RAILWAY_TOKEN secret to GitHub repo via `gh secret set RAILWAY_TOKEN` using the Railway token from Railway dashboard
- [x] T014 [US1] Push branch, open PR, verify all CI jobs run and gate reports status on the PR

**Checkpoint**: PRs show CI check results; lint, test, gate jobs all pass

---

## Phase 4: User Story 2 — Automated Deployment to Railway (Priority: P1)

**Goal**: Pushes to main automatically deploy to Railway after checks pass

**Independent Test**: Merge a change to main; verify Railway deploys and health check passes

### Implementation for User Story 2

- [x] T015 [US2] Write ci.yml deploy-railway job — install Railway CLI via `npm i -g @railway/cli`, run `railway up --detach` with RAILWAY_TOKEN secret; condition on main push + gate passing; add concurrency group `deploy-railway` with cancel-in-progress false (serial deploys) at /.github/workflows/ci.yml
- [x] T016 [US2] Add post-deploy health check step to deploy-railway job — `curl -sf https://mombot.sierracodeco.com/health` with retry logic (sleep 30, retry 3 times) at /.github/workflows/ci.yml
- [x] T017 [US2] Disable Railway's GitHub auto-deploy integration (if enabled) so deploys are gated on CI — check Railway dashboard settings
- [x] T018 [US2] Merge to main and verify: CI runs → deploy-railway job triggers → health check passes → new code is live

**Checkpoint**: Every merge to main auto-deploys to Railway; health check verified in pipeline

---

## Phase 5: User Story 3 — Security Scanning (Priority: P2)

**Goal**: PRs are scanned for dependency vulnerabilities before merge

**Independent Test**: Add a dependency with a known CVE; verify Trivy flags it

### Implementation for User Story 3

- [x] T019 [US3] Write ci.yml security-scan job — use aquasecurity/trivy-action@master with scan-type=fs, severity=CRITICAL,HIGH, exit-code=1; condition on app changes at /.github/workflows/ci.yml
- [x] T020 [US3] Add security-scan to gate job's dependency list so vulnerabilities block merge at /.github/workflows/ci.yml
- [x] T021 [US3] Push and verify Trivy scan runs on PR and reports findings (if any)

**Checkpoint**: PRs with vulnerable dependencies are flagged; clean PRs pass

---

## Phase 6: User Story 4 — Docker Image Registry (Priority: P2)

**Goal**: Main branch builds push Docker images to GHCR with SHA tags

**Independent Test**: Push to main; verify image appears at ghcr.io/jabelk/family-meeting with correct SHA tag

### Implementation for User Story 4

- [x] T022 [US4] Write ci.yml docker-build job — use docker/setup-buildx-action, docker/login-action (ghcr.io), docker/build-push-action with tags sha+latest, cache-from/to type=gha; condition on main push + app changes at /.github/workflows/ci.yml
- [x] T023 [US4] Add packages write permission to ci.yml top-level permissions at /.github/workflows/ci.yml
- [x] T024 [US4] Create cleanup-ghcr.yml workflow — schedule weekly (Sunday 3 AM UTC), use snok/container-retention-policy@v3.0.0 keeping 20 recent images, deleting >30 days; requires PAT_PACKAGES secret at /.github/workflows/cleanup-ghcr.yml
- [x] T025 [US4] Create PAT_PACKAGES GitHub secret — generate a GitHub PAT with packages:delete scope via `gh auth token` or GitHub UI, set via `gh secret set PAT_PACKAGES`
- [x] T026 [US4] Push to main and verify image appears in GHCR (check via `gh api user/packages/container/family-meeting/versions`)

**Checkpoint**: Every main push creates a tagged Docker image in GHCR; cleanup runs weekly

---

## Phase 7: User Story 5 — NUC Deployment Continuity (Priority: P3)

**Goal**: Existing nuc.sh deploy workflow continues working; optional manual NUC deploy via GitHub Actions

**Independent Test**: Run `./scripts/nuc.sh deploy` manually; verify it works unchanged

### Implementation for User Story 5

- [ ] T027 [US5] Verify scripts/nuc.sh deploy still works after all CI/CD changes — run manually and confirm no conflicts (SKIPPED — NUC deferred)
- [ ] T028 [US5] (Optional) Add workflow_dispatch trigger to ci.yml with input for deploy target (railway/nuc); add nuc deploy job that SSHs to warp-nuc and runs the deploy script — only if NUC automation is desired at /.github/workflows/ci.yml (SKIPPED — NUC deferred)

**Checkpoint**: NUC deployment unchanged; optional manual workflow available

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, branch protection, and documentation

- [x] T029 Configure branch protection on main via GitHub — require `gate` status check to pass before merge; no force pushes; enforce for admins
- [x] T030 [P] Update CLAUDE.md — add CI/CD section documenting pipeline jobs, required secrets, Ruff/pytest config at /CLAUDE.md
- [x] T031 Run quickstart.md scenarios 1-7 as validation checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001 for pyproject.toml config) — BLOCKS user stories
- **US1 Testing (Phase 3)**: Depends on Foundational — CI can't pass until lint passes
- **US2 Deploy (Phase 4)**: Depends on US1 — deploy job needs gate job to exist
- **US3 Security (Phase 5)**: Depends on US1 — adds job to existing ci.yml
- **US4 Registry (Phase 6)**: Depends on US1 — adds job to existing ci.yml
- **US5 NUC (Phase 7)**: Independent — just verification
- **Polish (Phase 8)**: Depends on US1 + US2 at minimum

### User Story Dependencies

- **US1 (Testing)**: Independent after Foundational — core CI jobs
- **US2 (Deploy)**: Depends on US1 — deploy-railway job needs gate to exist
- **US3 (Security)**: Depends on US1 — adds Trivy job to existing pipeline
- **US4 (Registry)**: Depends on US1 — adds docker-build job to existing pipeline
- **US5 (NUC)**: Independent — verification only

### Within Each User Story

- Write workflow YAML before testing it
- Test via actual PR/push (not just local validation)

### Parallel Opportunities

- T002, T003, T004 can run in parallel (Phase 1)
- T005 and T006 are sequential (fix lint before format)
- US3 and US4 can run in parallel after US1 (different jobs in same file but independent sections)
- T029 and T030 can run in parallel (Phase 8)

---

## Implementation Strategy

### MVP First (Phase 1 + 2 + 3 + 4)

1. Complete Phase 1: Setup (pyproject.toml, ruff/pytest deps, tests dir)
2. Complete Phase 2: Fix existing code to pass Ruff
3. Complete Phase 3: US1 — CI pipeline with lint + test + gate
4. Complete Phase 4: US2 — Auto-deploy to Railway
5. **STOP and VALIDATE**: Merge a PR, verify full CI → deploy flow
6. Run for 1+ week to build confidence

### Incremental Delivery

1. Setup + Foundational → Ruff and pytest work locally
2. US1 → PRs get automated checks (MVP!)
3. US2 → Merges auto-deploy to Railway
4. US3 → Vulnerability scanning on PRs
5. US4 → Docker images in GHCR with rollback capability
6. US5 → NUC continuity verified
7. Polish → Branch protection, docs

### Suggested MVP Scope

**US1 + US2** (Phases 1-4, tasks T001-T018) — PRs get checked, merges auto-deploy. This is the core CI/CD value.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All US3/US4/US5 tasks add to the same ci.yml file but in independent job sections
- Ruff auto-fix (T005/T006) may produce a large diff — commit separately before CI workflow
- RAILWAY_TOKEN: Generate from Railway dashboard → Account → Tokens
- PAT_PACKAGES: Generate from GitHub → Settings → Developer Settings → PAT → packages:delete scope
