# Research: CI/CD Pipeline

## Decision 1: Python Linter

**Decision**: Ruff
**Rationale**: Ruff is the modern standard for Python linting — 10-100x faster than flake8/pylint, supports formatting (replaces Black), and consolidates multiple tools into one. The companion-ai project uses ESLint+Prettier for JS; Ruff is the Python equivalent. Single tool, single config section in pyproject.toml.
**Alternatives considered**:
- flake8 + Black: Two separate tools, slower, more config files
- pylint: Very slow, overly opinionated for a small project
- mypy (type checking): Could add later but the codebase has no type annotations — would generate hundreds of errors. Defer to a future feature.

## Decision 2: Test Framework

**Decision**: pytest
**Rationale**: Industry standard for Python testing. The existing `test_work_calendar_e2e.py` uses a custom test harness — can coexist initially and be migrated to pytest later. pytest auto-discovers `test_*.py` files, supports fixtures, and integrates with GitHub Actions natively.
**Alternatives considered**:
- unittest: Built-in but verbose — pytest is strictly better for new projects
- Custom harness (existing): Not compatible with CI reporting, no proper exit codes for pass/fail

## Decision 3: Security Scanner

**Decision**: Trivy (Aqua Security)
**Rationale**: Same tool used by companion-ai. Free, open-source, scans both filesystem (pip dependencies) and Docker images. Integrates natively with GitHub Actions via `aquasecurity/trivy-action`. Reports CRITICAL and HIGH severity only to reduce noise.
**Alternatives considered**:
- Snyk: Requires account, more complex setup
- Safety: Python-only, doesn't scan Docker images
- GitHub Dependabot: Complementary (alerts on dependencies) but doesn't scan images

## Decision 4: Container Registry

**Decision**: GitHub Container Registry (GHCR)
**Rationale**: Free for public repos, included with GitHub Actions. Same pattern as companion-ai. Images tagged with commit SHA for traceability + `latest` for convenience. Native integration with GitHub permissions.
**Alternatives considered**:
- Docker Hub: Rate limits on free tier, separate authentication
- Railway's built-in registry: Not accessible for external rollbacks
- AWS ECR: Overkill, requires AWS account

## Decision 5: Railway Deployment Method

**Decision**: Railway CLI via `RAILWAY_TOKEN` in GitHub Actions
**Rationale**: Railway provides a deploy token that can be used in CI. The `railway up` command uploads and deploys from the current directory. The companion-ai project uses this exact pattern. Alternative: Railway's GitHub integration (auto-deploy on push) — but we want deployment gated on CI checks passing, so explicit CLI deploy after checks is better.
**Alternatives considered**:
- Railway GitHub integration (auto-deploy): No gate on CI checks — deploys even if tests fail
- Docker image deploy: Push GHCR image, then tell Railway to pull it — more complex, Railway prefers source deploys
- Railway API directly: Lower-level than CLI, more fragile

## Decision 6: Path-Based Job Filtering

**Decision**: dorny/paths-filter GitHub Action
**Rationale**: Same approach as companion-ai. Detects which files changed and sets output variables used in job `if:` conditions. Prevents running Python lint/tests when only markdown/spec files change. Saves CI minutes.
**Alternatives considered**:
- Manual git diff parsing: Error-prone, reinventing the wheel
- No filtering: Wastes CI minutes on doc-only changes

## Decision 7: Branch Protection

**Decision**: Require CI status checks to pass before merging to main
**Rationale**: Prevents broken code from reaching production. The companion-ai project enforces this via Terraform; we'll configure it manually via GitHub UI (IaC is out of scope for this feature).
**Alternatives considered**:
- No branch protection: Defeats the purpose of CI
- Terraform-managed: Out of scope per spec; can add later

## Decision 8: Test Strategy for Existing Codebase

**Decision**: Start with import validation + the existing custom test file, add pytest structure for new tests
**Rationale**: The codebase has no pytest tests. Rather than converting `test_work_calendar_e2e.py` immediately, the pipeline will: (1) run `python -m py_compile` on all src/ files to catch syntax errors, (2) run `pytest` which will find any new test files, (3) optionally run the existing custom test. Future features add proper pytest tests incrementally.
**Alternatives considered**:
- Convert all existing tests to pytest first: Scope creep — separate task
- Skip testing entirely: Defeats US1's purpose
- Only run existing custom test: Doesn't establish pytest infrastructure for future use
