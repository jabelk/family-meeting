# Tasks: Post-Migration Cleanup

**Input**: Design documents from `/specs/023-post-migration-cleanup/`
**Prerequisites**: spec.md (no plan.md needed — this is a cleanup/maintenance feature)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No setup needed — this is a cleanup feature operating on existing repo infrastructure.

*(No tasks)*

---

## Phase 2: Foundational — Verify Merge Status (BLOCKS branch deletion)

**Purpose**: Confirm every feature branch is safe to delete before any destructive action.

**CRITICAL**: Must complete before US1 (branch deletion) can proceed.

- [x] T001 Run `git log main..<branch> --oneline` for every local feature branch and document results. Confirm all 12 local branches (003, 004, 005, 006, 007, 008, 010, 011, 012, 018, 019, 020) are 0 commits ahead. Output results to console.
- [x] T002 Run `git log main..origin/<branch> --oneline` for every remote feature branch (004, 005, 010, 011, 021). Confirm which are 0 ahead and flag any with unmerged commits.
- [x] T003 Review the 3 unmerged commits on origin/021-ci-cd-pipeline (`git diff main..origin/021-ci-cd-pipeline`). Determine if the commits (ruff lint fixes, CI/CD YAML, test mode config) are already on main via other PRs or need to be cherry-picked. Document the decision.

**Checkpoint**: Merge status verified for all branches. Safe-to-delete list confirmed.

---

## Phase 3: User Story 1 — Delete Stale Feature Branches (Priority: P1) MVP

**Goal**: Remove all fully-merged local and remote feature branches from the repository.

**Independent Test**: `git branch` shows only `main` (and current work branch). `git ls-remote --heads origin` shows only `main`.

**Depends on**: Phase 2 (merge verification must complete first)

### Implementation for User Story 1

- [x] T004 [US1] Delete all fully-merged local feature branches: `git branch -d <branch>` for each of the 12 confirmed-merged local branches (003, 004, 005, 006, 007, 008, 010, 011, 012, 018, 019, 020). Log each deletion.
- [x] T005 [US1] Delete all fully-merged remote feature branches: `git push origin --delete <branch>` for each confirmed-merged remote branch (004, 005, 010, 011). Log each deletion.
- [x] T006 [US1] Handle the 021-ci-cd-pipeline branch based on T003 decision: either merge/cherry-pick the needed commits and then delete, or delete if all changes are already on main.
- [x] T007 [US1] Run `git fetch --prune` then verify: `git branch` shows only `main` + current work branch. `git ls-remote --heads origin` shows only `main` + current work branch.

**Checkpoint**: Repository has 0 stale branches locally and remotely.

---

## Phase 4: User Story 2 — Update Documentation for Railway-Primary Deployment (Priority: P1)

**Goal**: CLAUDE.md, README.md, and NUC docs accurately reflect Railway as primary, NUC as secondary.

**Independent Test**: Read CLAUDE.md — Railway deployment section appears first, NUC section labeled "NUC (Home Server — Secondary)". Active Technologies section is consolidated (not per-feature duplicated).

### Implementation for User Story 2

- [x] T008 [P] [US2] Consolidate the "Active Technologies" section in CLAUDE.md. Replace the 20+ per-feature duplicate entries with a single consolidated list of current technologies and integrations. Keep one entry per unique technology/integration.
- [x] T009 [P] [US2] Consolidate the "Recent Changes" section in CLAUDE.md. Replace per-feature changelog entries with a compact summary of the current system state (e.g., "Features 001-022 implemented and deployed").
- [x] T010 [US2] Reorganize the "Deployment" section in CLAUDE.md: rename "NUC (Home Server)" to "NUC (Home Server — Secondary)", add a one-line note at the top of Deployment section stating Railway is the primary deployment target.
- [x] T011 [P] [US2] Update README.md: ensure the project description and getting-started section reference Railway as primary deployment. Keep NUC instructions but label them as secondary/optional.
- [x] T012 [P] [US2] Update docs/n8n-setup.md: add a header note clarifying "This guide applies to NUC home-server deployment only. Railway deployment uses in-app APScheduler (see CLAUDE.md)."

**Checkpoint**: All documentation accurately reflects Railway-primary, NUC-secondary deployment model.

---

## Phase 5: User Story 3 — Verify All Completed Work Is on Main (Priority: P2)

**Goal**: Documented confirmation that no code was lost during branch cleanup.

**Independent Test**: T001-T003 results confirm 0 unmerged commits across all deleted branches.

**Depends on**: Phase 2 (already completed as foundational work)

### Implementation for User Story 3

- [x] T013 [US3] This story is satisfied by T001-T003 (foundational phase). Mark complete if all branches were confirmed merged before deletion. If T003 revealed unmerged work that was cherry-picked, verify those commits are now on main with `git log --oneline -5`.

**Checkpoint**: All completed work confirmed on main.

---

## Phase 6: User Story 4 — Clean Up NUC-Only Configuration References (Priority: P3)

**Goal**: NUC-specific files and references are clearly labeled so developers don't confuse NUC-only config with Railway config.

**Independent Test**: Search for "n8n" and "nuc" in non-spec source files — all hits are in clearly-labeled contexts.

### Implementation for User Story 4

- [x] T014 [P] [US4] Add a header comment to docker-compose.yml: "# NUC Home Server deployment configuration. For Railway deployment, see railway.toml."
- [x] T015 [P] [US4] Add a header comment to scripts/nuc.sh: "# Helper script for NUC home-server deployment. Not used for Railway deployment."
- [x] T016 [US4] Review N8N_WEBHOOK_SECRET usage in source code (src/app.py, src/config.py). If the variable name is misleading for Railway context, add a brief comment in src/config.py noting it is reused as general API auth on both NUC and Railway. Do NOT rename the variable.

**Checkpoint**: All NUC-specific files have clear contextual labels.

---

## Phase 7: Polish & Validation

**Purpose**: Final validation that everything is clean and tests pass.

- [x] T017 Run `ruff check src/` and `ruff format --check src/` — verify no lint/format issues introduced.
- [x] T018 Run `pytest tests/` — verify all tests pass.
- [x] T019 Commit all changes, push to branch, create PR for merge to main.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A — no setup needed
- **Foundational (Phase 2)**: T001-T003 — merge verification. BLOCKS US1 (branch deletion).
- **US1 (Phase 3)**: T004-T007 — depends on Phase 2. Branch deletion.
- **US2 (Phase 4)**: T008-T012 — independent of US1. Documentation updates.
- **US3 (Phase 5)**: T013 — satisfied by Phase 2 results. Just a verification checkpoint.
- **US4 (Phase 6)**: T014-T016 — independent of US1/US3. NUC labeling.
- **Polish (Phase 7)**: T017-T019 — depends on all user stories complete.

### User Story Dependencies

- **US1 (P1)**: Depends on foundational (T001-T003). Cannot delete branches without merge verification.
- **US2 (P1)**: Independent — can run in parallel with US1.
- **US3 (P2)**: Satisfied by foundational phase results.
- **US4 (P3)**: Independent — can run in parallel with US1 and US2.

### Parallel Opportunities

- T001 and T002 can run in parallel (local vs remote branch checks)
- T008, T009, T011, T012 can all run in parallel (different files)
- T014 and T015 can run in parallel (different files)
- US2 and US4 can run in parallel with US1 (different files, no dependencies)

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete T001-T003 (verify merge status)
2. Complete T004-T007 (delete stale branches)
3. Complete T008-T012 (update docs)
4. **STOP and VALIDATE**: Repo is clean, docs are accurate
5. Commit and PR

### Incremental Delivery

1. T001-T003 → Foundation verified
2. T004-T007 → US1 complete → Branches cleaned
3. T008-T012 → US2 complete → Docs updated (can run in parallel with US1)
4. T013 → US3 complete → Verification checkpoint
5. T014-T016 → US4 complete → NUC labels added
6. T017-T019 → Polish → CI passes, PR created

---

## Notes

- Total: 19 tasks
- No source code changes (only documentation, comments, and git operations)
- Branch deletion is irreversible — Phase 2 verification is critical
- Spec directories under `specs/` are NOT deleted (project history)
- `scripts/nuc.sh` and `docker-compose.yml` are kept (NUC still operational)
