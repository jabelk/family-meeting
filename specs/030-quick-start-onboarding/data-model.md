# Data Model: Quick Start Onboarding

**Feature**: 030-quick-start-onboarding
**Date**: 2026-03-09

## Entities

### Integration

Represents a configurable external service connection.

| Field | Type | Description |
|-------|------|-------------|
| name | string | Unique identifier (e.g., "notion", "google_calendar", "ynab") |
| display_name | string | Human-readable name (e.g., "Notion", "Google Calendar") |
| required | boolean | Whether the integration is required for the app to start (only whatsapp and ai_api are required) |
| env_vars | list[string] | Environment variables needed to enable this integration (all must be present) |
| tools | list[string] | Tool names associated with this integration |
| system_prompt_tag | string | Tag used in system prompt frontmatter to identify sections for this integration |
| health_check | callable or None | Function to verify live connectivity (None for env-var-only checks) |
| status | enum | Runtime status: "enabled", "disabled", "partial", "error" |

**Status transitions**:
- `disabled` → `enabled`: Operator adds all required env vars and restarts
- `enabled` → `disabled`: Operator removes env vars and restarts
- `enabled` → `error`: Integration configured but connectivity check fails at runtime
- `partial`: Some but not all required env vars are set (treated as disabled with a warning)

### IntegrationGroup

Predefined set of integrations with their configuration.

| Integration | Required Env Vars | Tools Count | System Prompt Files |
|-------------|-------------------|-------------|---------------------|
| core | *(always enabled — no env vars)* | ~3 tools (preferences, daily context) | 01-identity.md, 02-response-rules.md, 05-chores-nudges.md |
| whatsapp | WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET | 0 (infrastructure) | *(none — infrastructure only)* |
| ai_api | ANTHROPIC_API_KEY | 0 (infrastructure) | 01-identity.md |
| notion | NOTION_TOKEN, NOTION_ACTION_ITEMS_DB, NOTION_MEAL_PLANS_DB, NOTION_MEETINGS_DB, NOTION_FAMILY_PROFILE_PAGE | ~14 tools | 03-daily-planner.md (partial) |
| google_calendar | GOOGLE_CALENDAR_FAMILY_ID + GOOGLE_TOKEN_JSON | ~7 tools | 03-daily-planner.md (partial), 07-calendar-reminders.md, 09-forward-to-calendar.md |
| outlook | OUTLOOK_CALENDAR_ICS_URL | 1 tool | 03-daily-planner.md (partial) |
| ynab | YNAB_ACCESS_TOKEN, YNAB_BUDGET_ID | ~5 tools | 06-budget.md, 10-receipt-categorization.md |
| anylist | ANYLIST_SIDECAR_URL (with reachable sidecar) | 1 tool | 04-grocery-recipes.md (partial) |
| recipes | NOTION_RECIPES_DB, NOTION_COOKBOOKS_DB, R2_ACCOUNT_ID | ~5 tools | 04-grocery-recipes.md (partial) |

## Relationships

- An **Integration** has many **Tools** (1:N)
- An **Integration** tags many **System Prompt Sections** (1:N via frontmatter)
- A **Tool Description** belongs to one **Integration** (N:1)
- The **Health Endpoint** queries all enabled **Integrations** for status

## Validation Rules

- Required integrations (whatsapp, ai_api) must be enabled — app exits on startup if missing
- Optional integrations are all-or-nothing: all env vars for a group must be set, or none
- Partial configuration (some env vars set) triggers a warning and the integration is treated as disabled
- Phone numbers: digits only, 10-15 characters, no + prefix
- API keys: format-checked by prefix pattern (e.g., `sk-ant-` for Anthropic)
