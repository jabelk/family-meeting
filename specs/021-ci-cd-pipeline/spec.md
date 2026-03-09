# Feature Specification: CI/CD Pipeline

**Feature Branch**: `021-ci-cd-pipeline`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "Set up GitHub Actions pipeline for tests and deploy to Railway, referencing companion-ai project patterns"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Testing on Every Push (Priority: P1)

When a developer pushes code or opens a pull request, the system automatically runs quality checks — linting, type checking, and tests — and reports results on the PR before merging.

**Why this priority**: Prevents broken code from reaching production. Without automated testing, bugs only surface after manual deployment, causing downtime for a live family assistant.

**Independent Test**: Open a PR with a deliberately failing test; verify the CI check blocks merging. Fix the test; verify the check passes.

**Acceptance Scenarios**:

1. **Given** a developer opens a pull request, **When** the PR targets the main branch, **Then** automated quality checks run and report pass/fail status on the PR within 10 minutes.
2. **Given** a PR has failing checks, **When** a reviewer views the PR, **Then** the failing check details are visible and the PR cannot be merged while checks fail.
3. **Given** a push to the main branch, **When** all quality checks pass, **Then** the deployment pipeline is triggered automatically.
4. **Given** only documentation or spec files change, **When** the pipeline runs, **Then** code quality checks are skipped (no unnecessary compute).

---

### User Story 2 - Automated Deployment to Railway (Priority: P1)

When code is merged to the main branch and all checks pass, the system automatically deploys to Railway without manual intervention (no more `railway up` or SSH-based deploys).

**Why this priority**: Equally critical to testing — eliminates manual deployment steps and ensures every merge reaches production consistently.

**Independent Test**: Merge a small change to main; verify Railway deployment completes and the health check passes on the live URL within 5 minutes.

**Acceptance Scenarios**:

1. **Given** a push to main with passing checks, **When** the deploy job runs, **Then** the new version is live on Railway and the health check returns success.
2. **Given** a deployment fails (build error, health check timeout), **When** the failure is detected, **Then** the developer is notified via the pipeline status and the previous version remains running.
3. **Given** a deployment is in progress, **When** another push arrives, **Then** the previous deployment is cancelled to avoid conflicts.

---

### User Story 3 - Security Scanning (Priority: P2)

The pipeline scans for known vulnerabilities in dependencies and container images, alerting developers before insecure code reaches production.

**Why this priority**: The system handles sensitive data (calendar, budget, personal messages). Catching vulnerable dependencies early prevents security incidents, but is less urgent than basic CI/CD flow.

**Independent Test**: Introduce a dependency with a known vulnerability; verify the pipeline flags it.

**Acceptance Scenarios**:

1. **Given** the pipeline runs on a PR, **When** a dependency has a known critical or high-severity vulnerability, **Then** the scan reports the finding on the PR.
2. **Given** a container image is built, **When** the image is scanned, **Then** critical vulnerabilities are reported (informational, non-blocking).

---

### User Story 4 - Docker Image Registry (Priority: P2)

Built container images are pushed to a registry with version tags, enabling rollbacks and consistent deployments across environments.

**Why this priority**: Supports deployment reliability and rollback capability. Less critical than the core CI/CD flow but important for operational maturity.

**Independent Test**: Trigger a build; verify the image appears in the registry with the correct tag.

**Acceptance Scenarios**:

1. **Given** a successful build on the main branch, **When** the image is pushed, **Then** it is tagged with the commit SHA and `latest`.
2. **Given** images accumulate in the registry over time, **When** the cleanup job runs, **Then** images older than 30 days are removed (keeping the 20 most recent).

---

### User Story 5 - NUC Deployment Continuity (Priority: P3)

The existing NUC (home server) deployment continues to work alongside Railway. The pipeline can optionally deploy to the NUC for A/B testing or fallback scenarios.

**Why this priority**: Nice-to-have for the transition period. Railway is the primary target; NUC deployment is already handled by `nuc.sh` scripts and doesn't need immediate automation.

**Independent Test**: Verify `nuc.sh deploy` still works independently of the pipeline. Optionally trigger NUC deploy from a manual workflow.

**Acceptance Scenarios**:

1. **Given** the existing NUC deployment scripts, **When** the CI/CD pipeline is added, **Then** the `nuc.sh` workflow continues to work unchanged.
2. **Given** a developer wants to deploy to the NUC, **When** they trigger a manual workflow, **Then** the code is deployed to the NUC via the existing SSH-based approach.

---

### Edge Cases

- What happens when the Railway deployment fails mid-deploy (partial rollout)?
- How does the pipeline handle secrets rotation (expired tokens, new API keys)?
- What happens when the Docker build fails due to a transient network error during pip install?
- How does the system handle concurrent deployments from rapid successive merges?
- What happens when the health check passes but the application is functionally broken (scheduler not starting, integrations failing)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST run automated quality checks (linting, formatting, type checking) on every pull request and push to the main branch.
- **FR-002**: System MUST run automated tests on every pull request and push to the main branch.
- **FR-003**: System MUST deploy to Railway automatically when code is pushed to the main branch and all checks pass.
- **FR-004**: System MUST detect which files changed and skip irrelevant jobs (e.g., skip code checks when only documentation changes).
- **FR-005**: System MUST cancel in-progress pipeline runs when a new push arrives on the same branch.
- **FR-006**: System MUST build a container image and push it to a container registry with SHA-based tags on main branch builds.
- **FR-007**: System MUST scan dependencies for known vulnerabilities and report findings on pull requests.
- **FR-008**: System MUST scan built container images for vulnerabilities (informational, non-blocking).
- **FR-009**: System MUST verify deployment success via health check after Railway deployment.
- **FR-010**: System MUST clean up old container images from the registry on a scheduled basis.
- **FR-011**: System MUST NOT expose secrets (API keys, tokens) in pipeline logs or artifacts.
- **FR-012**: System MUST support manual trigger of NUC deployment as an optional workflow.

### Non-Functional Requirements

- **NFR-001**: Pipeline MUST complete all checks within 10 minutes for a typical code change.
- **NFR-002**: Deployment to Railway MUST complete within 5 minutes after checks pass.
- **NFR-003**: Pipeline MUST NOT require any manual approval steps for main branch deployments (fully automated).
- **NFR-004**: Pipeline configuration MUST be version-controlled alongside application code.

### Key Entities

- **Pipeline Run**: A single execution of the CI/CD workflow, triggered by a push or PR. Has status (pass/fail), duration, and associated commit.
- **Container Image**: A built Docker image stored in a registry. Has a SHA tag, build timestamp, and vulnerability scan results.
- **Deployment**: An instance of the application deployed to Railway or NUC. Has a version (commit SHA), health status, and deployment timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every pull request receives automated check results within 10 minutes of opening.
- **SC-002**: Code merged to main is live on Railway within 15 minutes of merge (checks + deployment combined).
- **SC-003**: Zero manual steps required for production deployment after code is merged to main.
- **SC-004**: All known critical/high-severity dependency vulnerabilities are surfaced before code reaches production.
- **SC-005**: Container images are available in the registry for rollback, with at least 20 recent versions retained.
- **SC-006**: No secrets are exposed in pipeline logs, PR comments, or build artifacts.

## Assumptions

- The existing test suite (if any) can be run via a standard command (e.g., `pytest`). If no tests exist yet, the pipeline will include a placeholder test job that succeeds.
- Railway deployment will use the Railway CLI or API token, consistent with the existing `railway up` approach.
- GitHub Container Registry (GHCR) will be used for container images, consistent with the companion-ai pattern.
- The repository will remain on GitHub (not migrating to another Git host).
- Branch protection rules for main will be configured as part of this feature.

## Out of Scope

- Staging environment on Railway (can be added later as a separate feature)
- Infrastructure as Code (Terraform/OpenTofu) for Railway or Cloudflare resources — the companion-ai pattern is noted for future reference but not needed for MVP
- End-to-end testing in the pipeline (no Playwright or similar — the app is tested via WhatsApp interaction)
- Automated rollback on deployment failure beyond Railway's built-in behavior
- Self-hosted runners (will use GitHub-hosted runners)
