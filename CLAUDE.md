# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Family meeting assistant for Jason & Erin (+ Vienna 5, Zoey 3) in Reno, NV. WhatsApp group chat → FastAPI webhook → Claude agentic tool loop with 30+ tools. Integrates Notion, Google Calendar, YNAB, AnyList, Gmail. Also uses Specify spec-driven development framework for feature planning.

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

## Family Configuration

Family-specific values are externalized in `config/family.yaml` (YAML format, human-edited). The config loader (`src/family_config.py`) validates required fields, computes derived values, and produces a placeholder dict used to render system prompts, tool descriptions, and templates.

**Key files:**
- `config/family.yaml` — Per-instance family config (names, ages, preferences, integrations)
- `config/family.yaml.example` — Blank template with comments for new deployments
- `src/family_config.py` — YAML loader with validation + placeholder dict builder (`load_family_config()`)

**How it works:** System prompts and tool descriptions use `{placeholder}` syntax (e.g., `{partner1_name}`, `{grocery_store}`). At startup, `render_system_prompt(family_config)` and `render_tool_descriptions(family_config)` replace placeholders with config values using `str.format_map()` with a `_PassthroughDict` that passes through unknown keys unchanged.

**Adding a new family-specific value:** Add the field to `config/family.yaml`, add a derived key in `_build_placeholder_dict()` in `src/family_config.py`, then use `{new_key}` in prompt files.

## Integration Registry

The integration registry (`src/integrations.py`) is the single source of truth for which integrations exist, what env vars they need, and which tools they provide. It drives tool filtering, prompt section filtering, health checks, and the validation script.

**Key concepts:**
- `INTEGRATION_REGISTRY` — dict mapping integration name → `Integration` dataclass (display_name, required, env_vars, tools, prompt_tag, always_enabled)
- 9 integrations: `core`, `whatsapp`, `ai_api`, `notion`, `google_calendar`, `outlook`, `ynab`, `anylist`, `recipes`
- `core` is a pseudo-integration (always_enabled=True, no env vars) — represents base tools available in every deployment
- `get_enabled_integrations()` — checks `os.environ` directly (not config.py defaults) and returns set of enabled integration names
- `ENABLED_INTEGRATIONS` in `src/config.py` — computed once at startup from registry

**Adding a new integration:** Add an `Integration` entry to `INTEGRATION_REGISTRY` in `src/integrations.py` with its env vars and tools. Add a frontmatter tag to relevant prompt files. The tool filtering, health endpoint, and validation script automatically pick it up.

**Adding a tool to an existing integration:** Add the tool name to the integration's `tools` tuple in `INTEGRATION_REGISTRY`. It will automatically be included/excluded based on whether that integration is enabled.

## Prompt Architecture

All LLM prompts live in `src/prompts/` as external Markdown files, loaded at startup via `@lru_cache`, then rendered with family config placeholders.

**Directory structure:**
- `src/prompts/system/` — System prompt sections (10 numbered `.md` files, concatenated in sort order, filtered by YAML frontmatter)
- `src/prompts/tools/` — Tool descriptions (12 module-grouped `.md` files, parsed by `## tool_name` headers, filtered by enabled tools)
- `src/prompts/templates/` — Classification/generation prompt templates (10 `.md` files with `{placeholder}` syntax)
- `src/prompts/__init__.py` — Loader module: `load_system_prompt()`, `render_system_prompt()`, `load_tool_descriptions()`, `render_tool_descriptions()`, `render_template(name, **kwargs)`

**Prompt frontmatter convention:** System prompt files use YAML frontmatter to declare which integrations they require:
```yaml
---
requires: [core]           # ALL listed integrations must be enabled
---
```
```yaml
---
requires_any: [notion, google_calendar]  # ANY listed integration suffices
---
```
Sections without frontmatter are always included. The `_parse_frontmatter()` and `_should_include_section()` helpers in `src/prompts/__init__.py` handle filtering. Tool descriptions are filtered by tool name (matching `TOOLS` list from `src/assistant.py`).

**Adding/editing prompts:**
- System prompt: Add/edit numbered files in `system/` (e.g., `10-new-section.md`). Order matters. Add frontmatter if the section is integration-specific.
- Tool descriptions: Add `## tool_name` section in the appropriate module file in `tools/`.
- Templates: Create `name.md` in `templates/`, use `{placeholder}` for dynamic values. Escape literal braces as `{{` / `}}`.
- Use `{partner1_name}`, `{partner2_name}`, `{bot_name}`, `{grocery_store}`, etc. for family-specific values — never hardcode names.

**Pre-deployment validation:** Run `python scripts/validate_setup.py` to check family.yaml + .env configuration, integration completeness, and deployment readiness before deploying.

## Key Constraints

- Specifications must be user-focused and tech-agnostic (no implementation details in specs)
- Each user story must be independently testable and deployable
- Plans must comply with constitution principles; violations require explicit justification
- Tasks specify full file paths and mark parallel-safe items with `[P]`

## Active Technologies
- Python 3.12 (existing codebase) + FastAPI, anthropic SDK, PyYAML (new — for family config loading), existing deps unchanged (028-template-repo-readiness)
- YAML config file at `config/family.yaml` (human-edited, committed per instance) + existing JSON data files (028-template-repo-readiness)
- Python 3.12 + FastAPI, anthropic SDK, PyYAML (existing) (030-quick-start-onboarding)
- JSON files in `data/` (unchanged) (030-quick-start-onboarding)
- Python 3.12 (existing) + FastAPI, anthropic SDK, PyYAML (existing — no new deps) (031-generic-template-repo)
- Python 3.12 (existing codebase) + FastAPI, anthropic SDK, existing deps — no new Python dependencies (032-siri-voice-access)
- JSON files in `data/` (existing pattern for conversation logs) (032-siri-voice-access)
- Python 3.12 (existing codebase) + FastAPI, anthropic SDK, httpx, notion-client, google-api-python-client — no new dependencies (033-tool-failure-resilience)
- N/A (no new storage; existing JSON files in `data/` unchanged) (033-tool-failure-resilience)
- Python 3.12 (existing codebase) + FastAPI, anthropic SDK, openai SDK (new), httpx, PyYAML (034-ai-failover-resilience)
- JSON files in `data/` (existing pattern, unchanged) (034-ai-failover-resilience)

**Core stack**: Python 3.12 + FastAPI, anthropic SDK (Claude Haiku 4.5 for chat, Claude vision for OCR), uvicorn, httpx, Pydantic

**Integrations**:
- Notion API (free plan) — 7 databases (Action Items, Meal Plans, Meetings, Backlog, Grocery History, Recipes, Cookbooks) + Family Profile page. notion-client >=2.2.0,<2.3.0
- Google Calendar — google-api-python-client, google-auth-oauthlib (3 calendars: Jason, Erin, Family)
- Outlook/Work Calendar — icalendar, recurring-ical-events (ICS feed) + iOS Shortcut push fallback
- YNAB — ynab SDK + httpx for transaction writes
- Gmail — google-api-python-client (Amazon/PayPal/Venmo/Apple receipt parsing)
- AnyList — Node.js 20 sidecar (Express + codetheweb/anylist@^0.8.5) for grocery lists
- Cloudflare R2 — boto3 (recipe photo storage)
- Downshiftology — httpx (recipe search, read-only)
- OpenAI — openai SDK (Whisper transcription for voice messages)
- WhatsApp Cloud API (Meta) for messaging interface

**Scheduling**: APScheduler (in-app, loads from `data/schedules.json`)

**Storage**: JSON files in `data/` directory (atomic write pattern), Railway Volume at `/app/data`

**Prompts**: External Markdown files in `src/prompts/` (system/, tools/, templates/), loaded at startup via `@lru_cache`

**CI/CD**: GitHub Actions (Ruff lint, pytest, Trivy security scan, Railway deploy, GHCR Docker images)

**Public URL**: `https://mombot.sierracodeco.com`

## Deployment

> **Primary deployment: Railway (cloud).** NUC is a secondary home-server option.

### Railway (Cloud) — Primary

CI/CD pipeline auto-deploys on push to main after checks pass.

- **Config**: `railway.toml` (build config, healthcheck)
- **Storage**: Railway Volume mounted at `/app/data` (persistent JSON files)
- **Scheduling**: In-app APScheduler (`src/scheduler.py`) — loads jobs from `data/schedules.json`
- **Google OAuth**: `GOOGLE_TOKEN_JSON` env var loaded via `Credentials.from_authorized_user_info()`; refreshed tokens written back to volume
- **Services**: FastAPI (public domain) + optional AnyList sidecar (private networking via `*.railway.internal`)
- **Required env vars**: `ANTHROPIC_API_KEY`, `WHATSAPP_*`, `N8N_WEBHOOK_SECRET` (reused as general API auth)
- **Optional integrations**: Notion, Google Calendar, YNAB, AnyList — app works as standalone chat assistant without them
- **Hard constraint**: Single uvicorn worker only (APScheduler requirement)
- **Onboarding**: See `ONBOARDING.md` for self-service setup guide

### NUC (Home Server — Secondary)

Alternative deployment on `warp-nuc` (Ubuntu 24.04, Intel NUC at 192.168.4.152) via Docker Compose. Uses n8n for scheduling instead of APScheduler. SSH access via `ssh warp-nuc`.

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
./scripts/nuc.sh chat-logs           # List archived conversation dates
./scripts/nuc.sh chat-logs <date>    # Pull archive for YYYY-MM-DD
./scripts/nuc.sh chat-logs latest    # Pull most recent archive
```

**Services**: fastapi (port 8000), anylist-sidecar (port 3000), cloudflared (tunnel), n8n (port 5678).

**Updating code**: Edit locally, commit, push to main, then `./scripts/nuc.sh deploy`.
**Updating .env**: Edit locally, then `./scripts/nuc.sh env` (copies .env and restarts fastapi).

## CI/CD Pipeline

GitHub Actions pipeline at `.github/workflows/ci.yml`. Branch protection requires `gate` check to pass.

**PR checks** (on every pull request):
| Job | Tool | Purpose |
|-----|------|---------|
| `changes` | dorny/paths-filter | Skip CI for docs-only changes |
| `lint-format` | Ruff | `ruff check src/` + `ruff format --check src/` |
| `test` | pytest | `pytest tests/` (smoke tests) |
| `security-scan` | Trivy | Filesystem scan for CRITICAL/HIGH CVEs |
| `gate` | — | Aggregates all job statuses (branch protection target) |

**Deploy jobs** (on push to main, after gate passes):
| Job | Purpose |
|-----|---------|
| `deploy-railway` | `railway up --detach --service fastapi` + health check |
| `docker-build` | Build + push to `ghcr.io/jabelk/family-meeting:{sha}` |

**Config files**: `pyproject.toml` (Ruff line-length=120, select E/F/I, pytest testpaths), `.github/workflows/cleanup-ghcr.yml` (weekly image cleanup)

**Secrets**: `RAILWAY_TOKEN` (Railway project token), `PAT_PACKAGES` (GitHub PAT with packages:delete for GHCR cleanup)

**Running locally**:
```bash
ruff check src/           # Lint
ruff format --check src/  # Format check
pytest tests/             # Tests
```

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

## Health Check

`GET /health` returns per-integration status:
- **Status**: `healthy` (all OK), `degraded` (required OK, optional failing), `unhealthy` (required failing → 503)
- **Required integrations**: `whatsapp`, `ai_api` (env var checks)
- **Optional integrations**: `notion` (API call), `google_calendar` (API call), `ynab` (API call), `anylist` (sidecar ping), `outlook` (env var check)
- Response includes `family` name, `bot_name`, `uptime_seconds`, and per-integration `configured`/`connected`/`error` details

## Feature History

Features 001-028 are implemented and deployed. Spec artifacts for each live under `specs/###-feature-name/`. Key milestones:
- 001: Core assistant (WhatsApp + Notion + Calendar + YNAB + AnyList)
- 002: Recipe management (Notion + Cloudflare R2 photo storage)
- 010-012: Financial automation (Amazon/Gmail receipt parsing → YNAB)
- 015: iOS Shortcut → work calendar push
- 019: WhatsApp voice message transcription (OpenAI Whisper)
- 020: Railway cloud deployment (APScheduler replaces n8n)
- 021: CI/CD pipeline (GitHub Actions)
- 022: Prompt externalization (Markdown files in src/prompts/)
- 028: Template repo readiness (family config externalization, enhanced health check, onboarding/pricing docs)

## Recent Changes
- 034-ai-failover-resilience: Added Python 3.12 (existing codebase) + FastAPI, anthropic SDK, openai SDK (new), httpx, PyYAML
- 033-tool-failure-resilience: Added Python 3.12 (existing codebase) + FastAPI, anthropic SDK, httpx, notion-client, google-api-python-client — no new dependencies
- 032-siri-voice-access: Added Python 3.12 (existing codebase) + FastAPI, anthropic SDK, existing deps — no new Python dependencies
