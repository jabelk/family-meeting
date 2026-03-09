# Implementation Plan: Template Repo Readiness & Service Packaging

**Branch**: `028-template-repo-readiness` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/028-template-repo-readiness/spec.md`

## Summary

Externalize all hardcoded family identity from the codebase into a single `config/family.yaml` file so the repo can be cloned, configured, and deployed for any family without code changes. Enhance the health check endpoint to report per-integration status. Create onboarding documentation (WhatsApp setup, pricing tiers, service agreement). Single-tenant deployment model — each client gets their own Railway service.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK, PyYAML (new — for family config loading), existing deps unchanged
**Storage**: YAML config file at `config/family.yaml` (human-edited, committed per instance) + existing JSON data files
**Testing**: pytest (existing `tests/` directory)
**Target Platform**: Linux server (Docker/Railway), development on macOS
**Project Type**: Web service (existing FastAPI app)
**Performance Goals**: Health check responds in <10 seconds; config loading adds <100ms to startup
**Constraints**: Single uvicorn worker (APScheduler), backward-compatible with existing Jason/Erin instance
**Scale/Scope**: 1-10 client deployments (single-tenant), ~35-40 hardcoded values to externalize across 20+ files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Uses existing services (WhatsApp, Calendar, YNAB, Notion). Config externalization enables reuse, doesn't rebuild anything. |
| II. Mobile-First Access | PASS | WhatsApp remains primary interface. No UI changes. |
| III. Simplicity & Low Friction | PASS | End users (family members) experience zero changes. Operator fills out one config file. No terminal commands for end users. |
| IV. Structured Output | PASS | No changes to output format. Config values flow into existing structured outputs. |
| V. Incremental Value | PASS | Each user story delivers standalone value. Config externalization (US1) works without WhatsApp docs (US2) or pricing (US3). |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/028-template-repo-readiness/
├── plan.md              # This file
├── research.md          # Phase 0: hardcoded reference audit + config strategy
├── data-model.md        # Phase 1: family config schema
├── quickstart.md        # Phase 1: test scenarios
├── contracts/
│   └── health-endpoint.md  # Enhanced health check contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
config/
└── family.yaml              # NEW: family identity config (human-edited per instance)

src/
├── family_config.py          # NEW: YAML loader + validation + accessor functions
├── config.py                 # MODIFIED: add family config validation to startup
├── app.py                    # MODIFIED: enhanced health check endpoint
├── assistant.py              # MODIFIED: use family config for welcome message, tool descriptions
├── context.py                # MODIFIED: use family config for person labels, childcare keywords
├── scheduler.py              # MODIFIED: use family config for scheduled message content
├── mcp_server.py             # MODIFIED: use family config for MCP tool descriptions
├── prompts/
│   ├── __init__.py           # MODIFIED: add render_system_prompt() with family config injection
│   ├── system/
│   │   ├── 01-identity.md    # MODIFIED: replace hardcoded names with {placeholders}
│   │   ├── 02-response-rules.md  # MODIFIED: parameterize name references
│   │   ├── 03-daily-planner.md   # MODIFIED: parameterize name references
│   │   ├── 04-grocery-recipes.md # MODIFIED: parameterize recipe source
│   │   ├── 05-chores-nudges.md   # MODIFIED: parameterize name references
│   │   ├── 07-calendar-reminders.md  # MODIFIED: parameterize event mappings
│   │   └── 08-advanced.md       # MODIFIED: parameterize examples
│   ├── tools/
│   │   ├── anylist.md        # MODIFIED: parameterize store name
│   │   ├── calendar.md       # MODIFIED: parameterize person names
│   │   ├── chores.md         # MODIFIED: parameterize person names
│   │   ├── context.md        # MODIFIED: parameterize person names
│   │   ├── email.md          # MODIFIED: parameterize person names
│   │   ├── notion.md         # MODIFIED: parameterize person names
│   │   └── preferences.md   # MODIFIED: parameterize person names
│   └── templates/
│       ├── conflict_detection.md  # MODIFIED: parameterize name references
│       └── meal_plan_generation.md  # MODIFIED: parameterize family details
└── tools/
    ├── anylist_bridge.py     # MODIFIED: use family config for store name
    ├── recipes.py            # MODIFIED: use family config for default store
    └── proactive.py          # MODIFIED: use family config for default store

docs/
├── ONBOARDING.md             # NEW: end-to-end client setup guide
├── WHATSAPP_SETUP.md         # NEW: WhatsApp number provisioning guide
├── PRICING.md                # NEW: pricing tiers and cost breakdown
└── SERVICE_AGREEMENT.md      # NEW: template service agreement

tests/
├── test_family_config.py     # NEW: config loading and validation tests
└── test_prompts.py           # MODIFIED: update for parameterized prompts
```

**Structure Decision**: Extends existing single-project structure. New `config/` directory at repo root for human-edited configuration (distinct from `data/` which is runtime-generated). New `docs/` directory for client-facing documentation.

## Key Design Decisions

### 1. YAML over JSON for family config

The codebase uses JSON for machine-generated data (`data/*.json`). Family config is human-edited by operators, so YAML is more appropriate — supports comments, cleaner nested structure, no trailing comma issues. PyYAML is the only new dependency.

### 2. Placeholder injection in system prompts

Current `load_system_prompt()` concatenates markdown files and caches. New `render_system_prompt(family_config)` will:
1. Call `load_system_prompt()` to get the cached template
2. Apply `.format_map()` with family config values
3. Return the rendered prompt

System prompt markdown files will use `{partner1_name}`, `{partner2_name}`, `{bot_name}`, etc. Literal curly braces in existing prompts (e.g., JSON examples) must be escaped as `{{` / `}}`.

### 3. Tool descriptions remain static per-instance

Tool descriptions in `src/prompts/tools/*.md` will also use placeholders, rendered at load time via a new `render_tool_descriptions(family_config)` function. Since descriptions are cached with `@lru_cache`, the family config is applied once at startup.

### 4. Backward compatibility

The existing Jason/Erin instance will have a `config/family.yaml` populated with current values. The config loader provides sensible defaults so the app doesn't break if a field is missing. The existing `.env` approach for credentials remains unchanged.

### 5. Health check enhancement

Replace the simple `{"status": "ok"}` with per-integration checks:
- Required: WhatsApp (verify env vars exist), AI API key
- Optional: Notion (test API call), Google Calendar (test API call), YNAB (test API call), AnyList (test HTTP ping)
- Each reports: configured (bool), connected (bool), error (string if failed)
- Overall status: "healthy" if all required pass, "degraded" if optional fail, "unhealthy" if required fail

## Family Config Schema Overview

```yaml
# config/family.yaml
bot:
  name: "Mom Bot"                    # Assistant display name
  welcome_message: "Welcome to Mom Bot! I can help with..."

family:
  name: "The Belk Family"           # Family display name
  timezone: "America/Los_Angeles"
  location: "Reno, NV"

  partners:
    - name: "Jason"
      role: "partner"
      work: "works from home at Cisco"
      has_work_calendar: true
    - name: "Erin"
      role: "partner"
      work: "stays at home with the kids"

  children:                          # Optional — empty list if no kids
    - name: "Vienna"
      age: 5
      details: "kindergarten at Roy Gomm, M-F"
    - name: "Zoey"
      age: 3
      details: ""

  caregivers:                        # Optional — grandparents, nannies, etc.
    - name: "Sandy"
      role: "grandma"
      keywords: ["sandy", "grandma"]

preferences:
  grocery_store: "Whole Foods"
  recipe_source: "Downshiftology"    # Or empty if not using recipe search
  dietary_restrictions: []

calendar:
  event_mappings:                    # Event name → person association
    "BSF": "Erin"
    "Gymnastics": "Vienna"
    "Church": "Family"

childcare:
  keywords: ["zoey", "sandy", "preschool", "milestones", "grandma"]
  caregiver_mappings:
    "sandy": "Sandy"
    "milestones": "preschool"
```

Full schema defined in `data-model.md`.
