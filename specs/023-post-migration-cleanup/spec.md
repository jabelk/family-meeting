# Feature Specification: Post-Migration Cleanup

**Feature Branch**: `023-post-migration-cleanup`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "Post-migration cleanup — clean up old feature branches, stale NUC-only config/docs/scripts, dead code from completed features, verify all merged work is on main, update docs to reflect Railway as primary deployment"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Delete Stale Feature Branches (Priority: P1)

As a developer, I want all fully-merged local and remote feature branches deleted so that the repository is clean and only contains active work.

**Why this priority**: Stale branches create confusion about what's in-progress vs. completed. This is the safest, most impactful cleanup — zero risk to running code.

**Independent Test**: Run `git branch` and `git ls-remote --heads origin` — only `main` and any actively in-progress branches remain.

**Acceptance Scenarios**:

1. **Given** 12 local branches that are 0 commits ahead of main, **When** cleanup runs, **Then** all 12 are deleted locally and the user is informed which branches were removed.
2. **Given** 4 remote branches that are fully merged (0 commits ahead), **When** cleanup runs, **Then** all 4 are deleted on the remote.
3. **Given** 1 remote branch (021-ci-cd-pipeline) with 3 unmerged commits, **When** cleanup runs, **Then** this branch is flagged for review rather than deleted.
4. **Given** branch deletion completes, **When** user checks the repository, **Then** no orphaned tracking references remain.

---

### User Story 2 - Update Documentation for Railway-Primary Deployment (Priority: P1)

As a developer, I want CLAUDE.md, README.md, and other documentation updated so they accurately reflect Railway as the primary deployment target, with NUC as secondary/legacy.

**Why this priority**: Stale documentation causes confusion and wasted effort. CLAUDE.md is loaded into every AI conversation and drives development decisions.

**Independent Test**: Read CLAUDE.md and README.md — Railway is described as the primary deployment, NUC sections are clearly marked as legacy or secondary, and no instructions assume NUC-first workflows.

**Acceptance Scenarios**:

1. **Given** CLAUDE.md has separate NUC and Railway deployment sections, **When** cleanup completes, **Then** Railway is listed first and NUC is clearly labeled as the secondary/home-server option.
2. **Given** README.md describes the project setup, **When** cleanup completes, **Then** getting-started instructions reference Railway deployment and the NUC path is optional.
3. **Given** docs/n8n-setup.md exists, **When** cleanup completes, **Then** it is either updated to note that Railway uses in-app APScheduler (no n8n) or archived if only relevant to the NUC path.

---

### User Story 3 - Verify All Completed Work Is on Main (Priority: P2)

As a developer, I want confirmation that every feature that was implemented and deployed is fully present on the main branch, with no code accidentally left only on a feature branch.

**Why this priority**: Prevents losing work — if a feature branch is deleted but its code was never merged, functionality disappears.

**Independent Test**: For each feature branch that will be deleted, run a diff against main — 0 commits ahead confirms all work is merged.

**Acceptance Scenarios**:

1. **Given** all feature branches listed locally, **When** each is compared to main, **Then** every branch with 0 commits ahead is confirmed safe to delete.
2. **Given** the 021-ci-cd-pipeline branch has 3 unmerged commits, **When** reviewed, **Then** a determination is made whether those commits should be merged or discarded, and the decision is documented.

---

### User Story 4 - Clean Up NUC-Only Configuration Files (Priority: P3)

As a developer, I want NUC-specific configuration and scripts reviewed and updated so that the codebase doesn't have confusing references to infrastructure that is no longer the primary deployment target.

**Why this priority**: Lower priority because the NUC still exists as a secondary deployment. The goal is not to remove NUC support but to ensure the codebase clearly distinguishes primary (Railway) from secondary (NUC) and doesn't have stale/misleading references.

**Independent Test**: Search the codebase for NUC-specific references — all remaining references are intentional and clearly contextualized.

**Acceptance Scenarios**:

1. **Given** docker-compose.yml, scripts/nuc.sh, and docs/n8n-setup.md exist, **When** cleanup completes, **Then** each file either has a clear header indicating it is for NUC/home-server use or is updated to be deployment-agnostic.
2. **Given** source code references N8N_WEBHOOK_SECRET for auth, **When** cleanup completes, **Then** in-code comments or documentation clarify that this secret is reused for general API auth (not NUC-specific).

---

### Edge Cases

- What if a feature branch has partial work that was never merged but is still valuable? Flag it for review rather than deleting.
- What if the 021-ci-cd-pipeline unmerged commits contain important fixes? Review the diff before deciding.
- What if NUC is still actively used alongside Railway? Keep NUC configuration functional but clearly secondary.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All local feature branches that are 0 commits ahead of main MUST be deleted.
- **FR-002**: All remote feature branches that are 0 commits ahead of main MUST be deleted.
- **FR-003**: Any branch with unmerged commits MUST be flagged for manual review before deletion.
- **FR-004**: CLAUDE.md MUST list Railway as the primary deployment target.
- **FR-005**: CLAUDE.md deployment section MUST be reorganized with Railway first, NUC second.
- **FR-006**: README.md MUST be updated to reflect the current deployment architecture.
- **FR-007**: The n8n-setup documentation MUST clarify that n8n is NUC-only (Railway uses in-app scheduling).
- **FR-008**: The 012-smart-budget-maintenance branch (unmerged on remote as 021) MUST be reviewed for merge-or-discard decision.
- **FR-009**: No functional source code MUST be removed — NUC deployment path remains operational.
- **FR-010**: All stale spec directories that correspond to completed and merged features MUST be retained (they serve as project history).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Repository has 0 stale local feature branches (only `main` and any active work branches remain).
- **SC-002**: Repository has 0 stale remote feature branches that are fully merged into main.
- **SC-003**: CLAUDE.md deployment section mentions Railway before NUC, with clear labels for each.
- **SC-004**: A developer reading CLAUDE.md for the first time correctly identifies Railway as the primary deployment within 30 seconds.
- **SC-005**: All files referencing NUC/n8n infrastructure have contextual labels (e.g., "NUC home server" or "legacy") distinguishing them from the primary Railway deployment.
- **SC-006**: `ruff check src/` and `pytest tests/` both pass after all changes.

## Assumptions

- The NUC remains a functional secondary deployment — we are not decommissioning it, just clarifying that Railway is primary.
- `N8N_WEBHOOK_SECRET` is reused as general API auth on Railway (not renamed) — only documentation needs updating, not code.
- The 22 spec directories under `specs/` are project history and should NOT be deleted.
- `scripts/nuc.sh` and `docker-compose.yml` remain useful for NUC operations and are kept.
