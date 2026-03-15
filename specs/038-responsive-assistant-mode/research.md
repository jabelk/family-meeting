# Research: Responsive Assistant Mode

**Feature**: 038-responsive-assistant-mode | **Date**: 2026-03-15

## Decision 1: How to Disable Proactive Suggestions

**Decision**: Edit prompt rules directly — remove Rule 12, modify Rules 23-26, update communication mode descriptions. No code changes needed for US1.

**Rationale**: The proactive behavior is driven entirely by system prompt instructions. The LLM follows these rules to call `get_backlog_items` during free time. Removing the rule stops the behavior at the source. No code guards needed because the tools themselves are passive — they only run when called.

**Alternatives considered**:
- Code-level blocking (prevent `get_backlog_items` from being called during plan generation): Over-engineered — the tool is useful when explicitly requested
- Preference-based toggle (check a "no proactive" preference before each suggestion): Adds complexity; the default should just be quiet

## Decision 2: How to Store Dietary Preferences

**Decision**: Use the existing `save_preference` tool with a new `dietary` category. Dietary preferences are stored as structured descriptions in the same `user_preferences.json` file, using a consistent format the LLM can parse.

**Rationale**:
- The preference system already handles persistence, deduplication, injection into the system prompt, and CRUD operations
- Adding a new category ("dietary") is a one-line change in the valid categories list
- The LLM already sees user preferences in the system prompt — dietary preferences will appear alongside notification opt-outs
- No new storage, no new tools, no new data model required

**Format**: Dietary preferences stored as: `[dietary] No vegetarian meals — family preference` or `[dietary] Jason doesn't eat fish — exclude fish when Jason is eating`

**Alternatives considered**:
- Separate dietary_preferences.json file: Unnecessary complexity, splits preference management
- Structured database/schema for dietary rules: Over-engineered for 2 users with ~3-5 dietary constraints
- Family Profile section: Already tried (free-text notes in Notion) — not enforced by tools

## Decision 3: How to Enforce Dietary Preferences in Meal Planning

**Decision**: Prompt-level enforcement — add explicit instructions in the meal planning prompt sections telling the LLM to check dietary preferences before suggesting recipes. The preferences are already injected into the system prompt (Rule 55), so the LLM has access to them.

**Rationale**:
- Dietary preferences are already visible in the system prompt via the preference injection mechanism
- The LLM can filter its own suggestions based on these constraints
- Code-level filtering would require modifying `search_downshiftology` and `search_recipes` to accept exclude parameters — unnecessary complexity
- The LLM already successfully filters by other criteria ("make sure it's not vegetarian") when told in-conversation; making it persistent is the fix

**Alternatives considered**:
- API-level filtering (add `exclude` parameter to recipe search tools): Would require modifying tool schemas and implementations. Downshiftology search is a scraper — can't filter server-side anyway
- Post-search filtering in code: Complex, fragile, and the LLM already does this naturally when instructed

## Decision 4: Communication Mode Updates

**Decision**: Change mode descriptions in `src/context.py` (where `MODE_BOUNDARIES` and mode descriptions are defined) and in `src/prompts/system/08-advanced.md` (Rule 68).

**Rationale**: Two places define mode behavior — the context module (which returns the mode label + description to the LLM) and the system prompt (which instructs the LLM how to behave in each mode). Both need updating for consistency.

**New mode descriptions**:
- morning (7am-12pm): "responsive, answer questions directly"
- afternoon (12pm-5pm): "responsive, answer questions directly"
- evening (5pm-9pm): "responsive, answer questions directly, no unsolicited content"
- late_night (9pm-7am): "direct answers only, no follow-up prompts"

## Decision 5: What to Do with Rule 13 (Explicit Backlog Requests)

**Decision**: Keep Rule 13 unchanged — it handles the case where Erin explicitly asks "what should I do?" which is pull-based behavior we want to preserve.

**Rationale**: Rule 13 says "When {partner2_name} says 'I have X minutes, what should I do?', ALWAYS call get_backlog_items." This is the user explicitly requesting suggestions — exactly what responsive mode should support. Only Rule 12 (auto-suggest for ANY free time) needs removal.
