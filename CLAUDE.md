# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Specify template project** — a spec-driven development framework. There is no application source code yet; the repository contains workflow scaffolding for structured feature development using AI agents.

## Development Workflow

Features are developed through a phased pipeline using slash commands, executed in order:

1. `/speckit.specify "feature description"` — Create feature spec from natural language
2. `/speckit.clarify` — Resolve ambiguities (up to 5 questions across 8 dimensions)
3. `/speckit.plan` — Generate technical plan (research, data model, contracts, quickstart)
4. `/speckit.checklist "purpose"` — Generate domain-specific quality checklists
5. `/speckit.tasks` — Break plan into dependency-ordered, actionable tasks
6. `/speckit.analyze` — Non-destructive consistency analysis across spec/plan/tasks
7. `/speckit.implement` — Execute tasks in phases with checkpoint gates
8. `/speckit.taskstoissues` — Convert tasks to GitHub issues
9. `/speckit.constitution` — Create/update project governance principles

## Conventions

**Branch naming**: `###-short-name` (e.g., `001-user-auth`). The 3-digit prefix auto-increments from the highest existing feature number across branches and `specs/`.

**Feature artifacts** live under `specs/###-feature-name/`:
- `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`
- `contracts/` — API/CLI/UI interface definitions
- `checklists/` — Quality validation checklists

## Architecture

- `.specify/templates/` — Markdown templates that define the structure for each artifact type
- `.specify/scripts/bash/` — Automation scripts (feature creation, prerequisite checks, planning setup, agent context updates)
- `.specify/memory/constitution.md` — Project governance principles; plans are validated against these
- `.claude/commands/speckit.*.md` — Slash command definitions for the 9 workflow phases

All bash scripts use strict mode (`set -e -u -o pipefail`) and support both git and non-git repositories.

## Key Constraints

- Specifications must be user-focused and tech-agnostic (no implementation details in specs)
- Each user story must be independently testable and deployable
- Plans must comply with constitution principles; violations require explicit justification
- Tasks specify full file paths and mark parallel-safe items with `[P]`

## Active Technologies
- Python 3.12 + FastAPI, anthropic SDK, notion-client, google-api-python-client, google-auth-oauthlib, icalendar, recurring-ical-events, ynab, uvicorn, httpx
- Notion API (free plan) — 5 databases (Action Items, Meal Plans, Meetings, Backlog, Grocery History) + Family Profile page
- Node.js sidecar (Express + codetheweb/anylist@^0.8.5) for AnyList grocery integration
- Docker Compose on NUC (`warp-nuc`) + Cloudflare Tunnel + n8n for scheduling
- WhatsApp Cloud API (Meta) for messaging interface
- Public URL: `https://mombot.sierrastoryco.com`
- Python 3.12 (existing codebase) + FastAPI, anthropic SDK (Claude Haiku 4.5 + Claude vision for OCR), notion-client >=2.2.0,<2.3.0, boto3 (Cloudflare R2 S3-compatible API), httpx, google-api-python-client, google-auth-oauthlib, icalendar, recurring-ical-events, ynab, uvicorn (002-proactive-recipes-automation)
- Notion (2 new databases: Recipes, Cookbooks) + Cloudflare R2 (recipe photo storage) + existing 5 Notion databases (002-proactive-recipes-automation)
- Python 3.12 (existing codebase) + FastAPI, anthropic SDK (Claude Sonnet 4), notion-client >=2.2.0,<2.3.0, httpx, google-api-python-clien (003-smart-nudges-chores)
- Notion API (2 new databases: Nudge Queue, Chores) + existing Google Calendar read (003-smart-nudges-chores)
- Python 3.12 (existing codebase) + FastAPI, anthropic SDK (Claude Opus), httpx (YNAB API calls), notion-client >=2.2.0,<2.3.0 (004-ynab-smart-budget)
- YNAB API (external, transactions + budgets), Notion Nudge Queue (budget insights as nudges) (004-ynab-smart-budget)
- Python 3.12 (existing codebase) + FastAPI, anthropic SDK (Claude Opus), httpx (Downshiftology API calls), notion-client >=2.2.0,<2.3.0 (005-downshiftology-recipes)
- Downshiftology API (external, read-only), Notion Recipes + Cookbooks databases (read/write) (005-downshiftology-recipes)

## Deployment (NUC)

The production stack runs on `warp-nuc` (Ubuntu 24.04, Intel NUC at 192.168.4.152) via Docker Compose. SSH access is configured via `ssh warp-nuc`.

**Helper script** — use `./scripts/nuc.sh` for all NUC operations:
```bash
./scripts/nuc.sh logs [service] [n]  # Show last n log lines (default: fastapi, 30)
./scripts/nuc.sh follow [service]    # Follow logs in real-time
./scripts/nuc.sh ps                  # Show container status
./scripts/nuc.sh restart [service]   # Restart service (or all)
./scripts/nuc.sh deploy              # Pull latest, rebuild, restart
./scripts/nuc.sh env                 # Push .env from laptop to NUC + restart fastapi
./scripts/nuc.sh ssh                 # Open SSH session
./scripts/nuc.sh shell [service]     # Shell into container
```

**Services**: fastapi (port 8000), anylist-sidecar (port 3000), cloudflared (tunnel). n8n runs separately on the NUC (port 5678).

**Updating code**: Edit locally, commit, push to main, then `./scripts/nuc.sh deploy`.
**Updating .env**: Edit locally, then `./scripts/nuc.sh env` (copies .env and restarts fastapi).

## API Safety Thresholds

All destructive operations have hard caps to prevent accidental mass changes. Thresholds are module-level constants — adjust if legitimate use cases exceed them.

| Operation | File | Constant | Limit | Behavior |
|-----------|------|----------|-------|----------|
| Calendar delete | `src/tools/calendar.py` | `MAX_CALENDAR_DELETES` | 50 | Raises `ValueError` |
| Calendar batch create | `src/tools/calendar.py` | `MAX_CALENDAR_CREATES` | 50 | Raises `ValueError` |
| Action item rollover | `src/tools/notion.py` | `MAX_ROLLOVER_ITEMS` | 25 | Returns error message |
| Template block delete | `src/tools/notion.py` | `MAX_TEMPLATE_BLOCK_DELETES` | 50 | Returns error message |
| Pending order clear | `src/tools/notion.py` | `MAX_PENDING_ORDER_CLEAR` | 100 | Raises `ValueError` |
| AnyList push | `src/tools/anylist_bridge.py` | `MAX_ANYLIST_PUSH` | 200 | Raises `ValueError` |
| AnyList clear | `src/tools/anylist_bridge.py` | `MAX_ANYLIST_CLEAR` | 150 | Logs warning |

## Recent Changes
- 005-downshiftology-recipes: Added Python 3.12 (existing codebase) + FastAPI, anthropic SDK (Claude Opus), httpx (Downshiftology API calls), notion-client >=2.2.0,<2.3.0
- 004-ynab-smart-budget: Added Python 3.12 (existing codebase) + FastAPI, anthropic SDK (Claude Opus), httpx (YNAB API calls), notion-client >=2.2.0,<2.3.0
- 003-smart-nudges-chores: Added Python 3.12 (existing codebase) + FastAPI, anthropic SDK (Claude Sonnet 4), notion-client >=2.2.0,<2.3.0, httpx, google-api-python-clien
