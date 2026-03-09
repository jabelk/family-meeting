# Implementation Plan: Railway Cloud Deployment

**Branch**: `020-railway-cloud-deploy` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/020-railway-cloud-deploy/spec.md`

## Summary

Deploy MomBot to Railway for cloud hosting alongside the existing NUC, enabling A/B testing and eventual migration. Replace n8n with an in-app scheduler (APScheduler), persist data via Railway Volumes (zero code changes for storage), load Google OAuth tokens from env vars, and create a GitHub template repo so other families (starting with the pastor) can self-service deploy their own isolated instance with Claude Code guidance.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase) + Node.js 20 (AnyList sidecar)
**Primary Dependencies**: FastAPI, anthropic SDK, APScheduler (new), existing deps unchanged
**Storage**: Railway Volume mounted at `/app/data` (same JSON files, zero migration)
**Testing**: curl integration tests + FastAPI TestClient (existing pattern)
**Target Platform**: Railway (Linux container, Hobby plan $5/month)
**Project Type**: Web service (WhatsApp webhook + scheduled automations)
**Performance Goals**: <15s message response, <60s container startup
**Constraints**: Single uvicorn worker (APScheduler requirement), 1 volume per service
**Scale/Scope**: 1-10 family instances, each fully isolated Railway project

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Uses Railway (existing service), APScheduler (standard library). No equivalent SaaS for family-assistant scheduling exists. |
| II. Mobile-First Access | PASS | All interaction remains WhatsApp-based. Onboarding uses Claude Code (terminal, but guided). |
| III. Simplicity & Low Friction | PASS | End users interact only via WhatsApp. Onboarding is guided by Claude Code — no terminal commands for daily use. |
| IV. Structured Output | N/A | This feature is infrastructure, not user-facing output. |
| V. Incremental Value | PASS | US1 (Railway deploy) delivers standalone value. Each subsequent US adds capability independently. |

**Post-design re-check**: All gates still pass. APScheduler adds one dependency but replaces a full n8n service (net simplification). Railway Volumes require zero code changes (net simplification).

## Project Structure

### Documentation (this feature)

```text
specs/020-railway-cloud-deploy/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── railway-config.md
│   └── scheduler-config.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── app.py               # MODIFY — add scheduler lifespan, update config loading
├── config.py            # MODIFY — add GOOGLE_TOKEN_JSON, GOOGLE_CREDENTIALS_JSON, SCHEDULER_ENABLED
├── scheduler.py         # NEW — APScheduler setup, loads schedules.json, calls endpoint handlers
├── tools/
│   └── calendar.py      # MODIFY — load Google OAuth from env var with file fallback

data/
└── schedules.json       # NEW — default schedule configuration (shipped in template)

railway.toml             # NEW — Railway build config
ONBOARDING.md            # NEW — Claude Code guided setup for new families
.env.example             # MODIFY — add new env vars (GOOGLE_TOKEN_JSON, etc.)
```

**Structure Decision**: Existing single-project structure. Three files modified, three files added. No new directories, no architectural changes. The AnyList sidecar (`anylist-sidecar/`) is unchanged.

## Key Technical Decisions

### 1. Storage: Railway Volumes (not Postgres)

Mount Railway Volume at `/app/data`. The app already uses `Path("/app/data")` with atomic writes. Zero code changes for data persistence. Cost: ~$0/month for <1MB.

### 2. Scheduling: APScheduler (not n8n, not Railway cron)

`AsyncIOScheduler` in FastAPI's lifespan. Calls endpoint handler functions directly (no HTTP round-trip). Schedules loaded from `data/schedules.json` — configurable per instance. Supports any interval and full timezone support.

**Hard constraint**: single uvicorn worker only (multi-worker would duplicate all jobs).

### 3. Google OAuth: Env var + published app

`GOOGLE_TOKEN_JSON` env var loaded via `Credentials.from_authorized_user_info()`. Published OAuth app removes 7-day testing expiry. Token auto-refreshes indefinitely. Refreshed tokens written back to volume-backed `token.json`.

### 4. Multi-service: Monorepo with private networking

Two Railway services in one project, same GitHub repo. FastAPI at root, AnyList sidecar at `/anylist-sidecar`. Communicate via `http://anylist-sidecar.railway.internal:3000`. Sidecar is optional — skip deploy if not needed.

### 5. Template repo: GitHub "Use this template"

Clean copy, no fork relationship. Upstream updates via git remote + WhatsApp notification. Backup before update, rollback via WhatsApp.

## Complexity Tracking

No constitution violations. No complexity justification needed.
