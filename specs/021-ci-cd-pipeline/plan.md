# Implementation Plan: CI/CD Pipeline

**Branch**: `021-ci-cd-pipeline` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/021-ci-cd-pipeline/spec.md`

## Summary

Add GitHub Actions CI/CD pipeline for automated testing and deployment to Railway. Pipeline runs linting (Ruff), tests (pytest), security scanning (Trivy), Docker image builds (GHCR), and auto-deploys to Railway on main branch push. Adapted from companion-ai patterns for Python/FastAPI stack.

## Technical Context

**Language/Version**: GitHub Actions YAML + Python 3.12 (existing app)
**Primary Dependencies**: GitHub Actions (runners), Ruff (linting), pytest (testing), Trivy (security scanning), Railway CLI (deployment), Docker (container builds)
**Storage**: N/A — pipeline configuration only, no new data storage
**Testing**: pytest (new — project currently has no formal test framework; one custom test file exists)
**Target Platform**: GitHub-hosted runners (ubuntu-latest), deploying to Railway (Linux containers)
**Project Type**: CI/CD pipeline configuration (YAML workflow files + minimal Python tooling config)
**Performance Goals**: Pipeline completes in <10 minutes; deployment in <5 minutes post-checks
**Constraints**: GitHub Actions free tier (2,000 minutes/month for private repos); single Railway project
**Scale/Scope**: Single pipeline, 1 deployment target (Railway), ~20 src/ Python files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Uses existing services (GitHub Actions, Railway, GHCR, Trivy) — no custom CI system |
| II. Mobile-First Access | N/A | CI/CD is developer infrastructure, not end-user-facing |
| III. Simplicity & Low Friction | PASS | Pipeline runs automatically on push/PR — zero manual steps for developers. End users (Erin) unaffected |
| IV. Structured Output | N/A | Pipeline produces status checks, not user-facing content |
| V. Incremental Value | PASS | US1 (testing) delivers value alone; US2 (deploy) adds value independently; each story is independently useful |

**Gate Result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/021-ci-cd-pipeline/
├── plan.md              # This file
├── research.md          # Phase 0: tool decisions
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   └── workflow-config.md  # GitHub Actions workflow contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
.github/
└── workflows/
    ├── ci.yml               # Main CI/CD pipeline (US1 + US2 + US3 + US4)
    └── cleanup-ghcr.yml     # Weekly image cleanup (US4)

pyproject.toml               # Ruff + pytest configuration (new file)
```

**Structure Decision**: All CI/CD configuration lives in `.github/workflows/` (standard GitHub Actions location). Python tooling config consolidated in `pyproject.toml` (modern Python standard). No new src/ files needed — this feature is purely pipeline infrastructure.

## Complexity Tracking

No constitution violations — no entries needed.
