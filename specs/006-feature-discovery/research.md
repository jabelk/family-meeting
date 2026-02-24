# Research: Feature Discovery & Onboarding

## R1: Help Response — Tool vs System Prompt

**Decision**: ~~System prompt template + Claude orchestration.~~ **Superseded by R6** — use a dedicated `get_help()` tool function.

**Original rationale**: The help menu could be defined as a structured template in the system prompt, with Claude using existing tools to personalize. This was reconsidered in R6 because a dedicated tool keeps personalization logic testable, the system prompt clean, and allows the function to accept a `phone` parameter for usage-aware suggestions (US4).

**See R6** for the final approach.

## R2: "Did You Know?" Tips — Implementation Strategy

**Decision**: System prompt instructions with a static tip mapping (trigger context → related tips). Claude picks from matching tips, preferring underused categories (US4) when usage data is available. Last-shown tip ID is tracked per user in `data/usage_counters.json` to avoid consecutive repeats.

**Rationale**: Each WhatsApp message is a fresh Claude API call with no conversation memory. Claude can easily append a tip when contextually relevant by checking what tools were just used. The usage counters file (introduced for US4) provides a lightweight place to store the last-shown tip ID per phone, avoiding consecutive repeats without a full history database.

**Alternatives considered**: (1) Notion-based tip history DB — overkill for 2 users, adds API calls to every message. (2) In-memory tip cache — lost on container restart, unreliable. (3) Pure random with no tracking — acceptable but improved with last-tip tracking at near-zero cost since the usage counters file already exists.

## R3: Tip Frequency Control

**Decision**: Instruct Claude in the system prompt to append tips only when a "tip-worthy" context is detected (e.g., after meal plans, recipe searches, budget summaries) and limit to at most 1 tip per response. No programmatic rate limiting.

**Rationale**: Claude processes one message at a time. Each response is independent. Telling Claude "append a tip at most once, and only when the response involves [meal planning, recipes, budget, chores]" naturally limits frequency without code changes.

## R4: First-Time User Detection

**Decision**: Use an in-memory set in the assistant module to track which phone numbers have received a welcome message. Persists for the container lifetime; on restart, the welcome may re-trigger once (acceptable).

**Rationale**: The family has only 2 users. A module-level `_welcomed_phones: set[str]` in assistant.py is the simplest approach. No Notion writes needed. If the container restarts and Erin sees a welcome again, that's harmless — she can just say "help" to see the full menu.

**Alternatives considered**: (1) Notion Family Profile flag — adds an API read to every message for negligible benefit. (2) File-based persistence — overcomplicated for 2 users.

## R5: Personalization Data Sources

**Decision**: The help tool calls existing tools to fetch live data for personalized examples. Fallback to hardcoded family-relevant examples if tools fail.

**Available personalization data**:

| Category | Live Source | Example Output |
|----------|-----------|----------------|
| Recipes | list_cookbooks() | "Search your Downshiftology recipes" |
| Budget | get_budget_summary() | "Check your Groceries or Restaurants budget" |
| Grocery | get_staple_items() | "Your staples like chicken breast, eggs, olive oil" |
| Calendar | get_calendar_events() | "See this week's family calendar" |
| Chores | query_all_chores() | "Your chores like vacuum, laundry, meal prep" |

**Static fallbacks** (hardcoded, based on known family data):
- Recipes: "find me a chicken dinner recipe"
- Budget: "what did we spend at Costco?"
- Grocery: "order groceries for this week"
- Calendar: "what's on our calendar this week?"
- Chores: "started laundry"
- Reminders: "remind Jason to pick up dog at 12:30"

## R6: Help Response Structure

**Decision**: Use a `get_help` tool function that builds a personalized help response by fetching live data, with static fallbacks. This keeps the logic testable and the system prompt clean.

**Rationale**: While pure system prompt guidance works, a dedicated tool gives Claude a concrete function to call when "help" is requested. The tool can try to personalize examples using live data and fall back gracefully. This is cleaner than cramming personalization logic into the system prompt.

**Help categories** (6 categories, matching spec FR-002):
1. Recipes & Cooking — search Downshiftology, browse saved recipes, import recipes
2. Budget & Spending — check budget, search transactions, move money
3. Calendar & Reminders — view calendar, create reminders, daily plan
4. Groceries & Meal Planning — meal plans, grocery list, push to AnyList
5. Chores & Home — chore tracking, laundry timer, preferences
6. Family Management — action items, backlog, meeting agenda, family profile
