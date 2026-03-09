# Research: Quick Start Onboarding

**Feature**: 030-quick-start-onboarding
**Date**: 2026-03-09

## R1: Conditional System Prompt Assembly

**Decision**: Python-side filter using YAML frontmatter metadata tags in Markdown files.

**Rationale**: At our scale (9 system prompt files, 13 tool description files, 6 integration groups), YAML frontmatter provides the best balance of simplicity, self-documentation, and zero new dependencies. Each prompt file declares its required integrations via a `requires:` field in YAML frontmatter. The loader strips frontmatter before concatenation and skips files whose requirements aren't met. This is ~15-25 lines of code change to `src/prompts/__init__.py`.

**Alternatives considered**:
- **Convention-based filename mapping** (e.g., `06-budget.md` → requires YNAB): Simpler but fragile — survives poorly when files are renamed or when one file covers multiple integrations. No self-documentation.
- **Jinja2 templating**: Overkill. Adds a dependency and new syntax. Only worthwhile for intra-section conditionals (e.g., "show Outlook paragraph only if configured"), which we don't need — our file boundaries already map to integration groups.
- **Dynamic/just-in-time loading**: Pattern from Anthropic's agent skills guidance. Not applicable to our static system prompt chatbot model.

**Key pitfall — prompt coherence**: Removing sections can break cross-references ("the action items mentioned above" when the Notion section was filtered out). Mitigation: make each section self-contained, keep identity (01) and response rules (02) as always-included, and add a stub line for disabled integrations so the bot knows what's not available.

**Sources**:
- [Anthropic: Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [PromptLayer: Prompt Coherence](https://www.promptlayer.com/glossary/prompt-coherence)
- [Banks: Jinja2-based LLM Prompt Management](https://github.com/masci/banks)

## R2: Integration Registry Architecture

**Decision**: Centralized integration registry in `src/integrations.py` — a single dict mapping integration names to their required env vars, associated tools, associated system prompt files, and associated tool description sections.

**Rationale**: Currently integration detection is scattered: `OPTIONAL_GROUPS` in `config.py` knows env vars, `assistant.py` has the static tools list, `prompts/__init__.py` loads all prompts unconditionally, and the health endpoint has its own hardcoded integration checks. A single registry normalizes all of this.

**Registry structure** (conceptual):
```python
INTEGRATIONS = {
    "notion": {
        "env_vars": ["NOTION_TOKEN", "NOTION_ACTION_ITEMS_DB", ...],
        "tools": ["get_action_items", "add_action_item", ...],
        "system_prompts": ["03-daily-planner.md"],  # or use frontmatter
        "tool_files": ["notion.md", "proactive.md"],
        "health_check": check_notion_health,
    },
    "google_calendar": { ... },
    ...
}
```

**Alternatives considered**:
- **Keep detection distributed**: Each module checks its own config. Leads to inconsistency (health endpoint might report Notion as "not configured" while the tools list still includes Notion tools).
- **family.yaml declares integrations explicitly**: User would add `integrations: [notion, google_calendar]` to YAML. Adds manual step that can drift from .env reality. Better to auto-detect from env vars and use the registry as the source of truth.

**Decision**: Auto-detect enabled integrations from env vars using the registry, rather than requiring explicit declaration in family.yaml. This means the operator only needs to add credentials to .env — no need to also declare them in family.yaml.

## R3: Setup/Validation Command Design

**Decision**: Single Python script `scripts/validate_setup.py` that reads both family.yaml and .env, cross-references against the integration registry, and reports readiness.

**Rationale**: A validation-focused command is more useful than a generator. The operator still fills in family.yaml and .env manually (they already do this), but the validation command catches errors before deployment. This avoids the complexity of generating .env from YAML while delivering the core value: "did I configure everything correctly?"

**What it checks**:
1. family.yaml parses correctly with all required fields
2. Required env vars are present (ANTHROPIC_API_KEY, WHATSAPP_*)
3. Phone numbers match expected format (digits only, 10-15 chars)
4. API keys match expected format patterns (sk-ant-* for Anthropic, etc.)
5. Optional integration groups are all-or-nothing (no partial configs)
6. Reports enabled/disabled/partial integrations summary

**Alternatives considered**:
- **Generate .env from YAML**: Attractive but introduces security concerns (credentials in YAML) and the split-file decision (from clarification) makes this moot.
- **Interactive wizard**: Out of scope per spec.

## R4: Health Endpoint "Healthy" vs "Degraded" Logic

**Decision**: Change health logic so "degraded" only applies to integrations that are both *configured* AND *failing*. Unconfigured integrations are reported as `"status": "not_configured"` and do not affect the overall status.

**Current logic** (`src/app.py` lines 419-428):
```python
optional_ok = all(i["connected"] for i in integrations if not i["required"] and i["configured"])
if not optional_ok:
    status = "degraded"
```

**New logic**:
```python
configured_optional = [i for i in integrations if not i["required"] and i["configured"]]
optional_ok = all(i["connected"] for i in configured_optional)
# If no optional integrations are configured, optional_ok is True (vacuous truth)
```

This is a 2-line change. Unconfigured integrations already show `"configured": false` in the response — they just need to stop affecting the status calculation.

## R5: Tool Filtering Mechanism

**Decision**: Filter the `TOOLS` list at startup time based on enabled integrations. Build `TOOLS` dynamically instead of statically.

**Current state**: `TOOLS` is a module-level list of ~70 tool dicts defined statically in `assistant.py` lines 51-1265. All tools are always included.

**New approach**:
1. Tag each tool with its required integration (via the integration registry or inline metadata)
2. At module load time, check which integrations are enabled
3. Build `TOOLS` by filtering the full list to only include tools for enabled integrations
4. `TOOL_FUNCTIONS` dict (lines 1428-1587) also filtered to match

**Why startup-time, not per-request**: Claude's tool list is fixed per conversation. Changing it mid-conversation is not supported. Since integrations can only change on restart (env vars), filtering at startup is correct.

**Tool-to-integration mapping** (derived from tool description files):
- `notion`: get_action_items, add_action_item, complete_action_item, rollover_incomplete_items, get_family_profile, update_family_profile, add_topic, create_meeting, save_meal_plan, get_meal_plan, get_backlog_items, add_backlog_item, complete_backlog_item, get_routine_templates
- `google_calendar`: get_calendar_events, write_calendar_blocks, create_quick_event, delete_calendar_event, list_recurring_events, batch_create_events, batch_delete_events
- `outlook`: get_outlook_events
- `ynab`: get_budget_summary, search_transactions, recategorize_transaction, create_transaction, update_category_budget
- `anylist`: push_grocery_list
- `recipes` (requires notion + r2): extract_and_save_recipe, search_recipes, get_recipe_details, recipe_to_grocery_list, list_cookbooks
- `core` (always available): get_daily_context, save_preference, list_preferences, remove_preference, get_drive_times
