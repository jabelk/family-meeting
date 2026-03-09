# Research: Template Repo Readiness

## 1. Config File Format

**Decision**: YAML (`config/family.yaml`)
**Rationale**: Family config is human-edited by operators. YAML supports comments (helpful for explaining fields), cleaner nested structures, and no trailing comma issues. The codebase uses JSON for machine-generated data (`data/*.json`), but config files are a different concern.
**Alternatives considered**:
- JSON: Consistent with existing data files, but no comments, harder for humans to edit
- TOML: Good for flat config, less natural for deeply nested family structures
- .env additions: Already 20+ env vars; adding 35+ more would be unwieldy

## 2. Hardcoded Reference Audit

**Decision**: 35-40 values across 20+ files need externalization
**Key findings**:
- **System prompt files** (10 files in `src/prompts/system/`): Names, ages, schools, activities hardcoded throughout. `01-identity.md` is the most critical — defines the entire family structure.
- **Tool descriptions** (7 of 12 files in `src/prompts/tools/`): Person names in descriptions (calendar.md, chores.md, context.md, email.md, notion.md, anylist.md, preferences.md)
- **Templates** (2 of 10 in `src/prompts/templates/`): `meal_plan_generation.md` and `conflict_detection.md` reference family specifics
- **Python source**: `context.py` (childcare keywords, person labels), `config.py` (phone-to-name), `assistant.py` (welcome message), `scheduler.py` (scheduled messages), `mcp_server.py` (MCP descriptions), `tools/anylist_bridge.py` (Whole Foods), `tools/recipes.py` (Whole Foods default), `tools/proactive.py` (Whole Foods default)

## 3. Placeholder Strategy for Prompts

**Decision**: Use Python `str.format_map()` with a `defaultdict` fallback
**Rationale**: System prompts already use `{placeholder}` syntax in templates. Extending to system prompts is natural. `format_map()` with a `defaultdict` that returns the original `{key}` for unknown keys prevents breakage if a placeholder is missed.
**Alternatives considered**:
- Jinja2: Overkill for simple value substitution; adds a dependency
- String `.replace()`: Fragile, can't handle edge cases
- f-strings: Requires code changes everywhere, not file-based

**Implementation note**: Existing curly braces in prompt files (JSON examples, code blocks) must be escaped as `{{` / `}}`. An audit of current prompt files found minimal usage of literal braces.

## 4. Health Check Enhancement Strategy

**Decision**: Per-integration health probes with configurable timeouts
**Rationale**: Current health check returns `{"status": "ok"}` regardless of integration state. For multi-client deployment, operators need to quickly verify which integrations are working.
**Approach**:
- Check env var existence for required integrations (WhatsApp, AI API key)
- For optional integrations, attempt lightweight API call with 5-second timeout
  - Notion: `notion.users.me()` (cheapest API call)
  - Google Calendar: `service.calendarList.list()` (already used at startup)
  - YNAB: HEAD request to `api.ynab.com` with token
  - AnyList: HTTP ping to sidecar URL
  - Outlook: Check if ICS URL is configured (no live check — it's a static URL)

## 5. WhatsApp Setup Documentation

**Decision**: Step-by-step guide for Meta Direct Cloud API (first 10 clients)
**Rationale**: Embedded Signup is out of scope per clarification. Manual setup via Meta Business Portal is the current path. Documentation reduces operator time per client.
**Key sections**:
1. Prerequisites (Facebook Business Manager account, business verification)
2. Create WhatsApp Business Account
3. Add phone number (buy or port)
4. Generate permanent access token
5. Configure webhook URL and verify token
6. Set webhook subscriptions (messages, message_templates)
7. Troubleshooting (verification rejected, webhook not receiving)

## 6. Pricing Tiers

**Decision**: Two tiers — Family ($99/mo + $499 setup) and Corporate (custom)
**Rationale**: Based on competitive research:
- Human VAs: $380-3,000/mo (we're 75-90% cheaper)
- DIY/OpenClaw: $19-25/mo but requires technical skill
- Chatbot agencies: $2,500-7,500 setup
- Per-client cost: $12-28/mo → 65-72% margin at $99/mo
**Family tier includes**: WhatsApp assistant, calendar management, grocery lists, budget tracking, white-glove setup
**Corporate tier**: Volume pricing ($149+/mo per family), dedicated support, custom integrations, API access

## 7. PyYAML Dependency

**Decision**: Add `pyyaml>=6.0` to requirements
**Rationale**: Standard YAML library for Python. Already widely used, well-maintained, no security concerns. Only new dependency for this feature.
**Alternatives considered**:
- `ruamel.yaml`: Better YAML 1.2 support but overkill for config loading
- `strictyaml`: Type-safe but less flexible schema definition
- stdlib `json`: Would require JSON config, less human-friendly

## 8. Meta WhatsApp AI Chatbot Policy

**Decision**: Position as "family management service" with structured features
**Rationale**: Meta's January 2026 policy prohibits general-purpose AI chatbots on WhatsApp. The service must be presented as a tool for specific tasks (calendar, grocery, budget) where AI assists with structured operations. Avoid marketing language like "AI chatbot" or "ChatGPT for families."
**Documentation impact**: Service agreement and marketing materials must use "family management assistant" language. System prompt already positions the bot as a task-specific assistant with defined tools.
