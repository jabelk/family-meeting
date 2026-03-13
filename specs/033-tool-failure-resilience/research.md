# Research: Tool Failure Resilience

## R1: Current Error Handling Architecture

**Decision**: Refactor the single catch-all handler in `src/assistant.py:1853-1855` into a classified retry + error reporting system.

**Rationale**: The current handler catches ALL exceptions uniformly and produces `"Error: {tool_name} is currently unavailable. Skip this section."` This has two critical flaws: (1) it doesn't retry transient failures that would succeed on a second attempt, and (2) the "Skip this section" instruction gives Claude permission to silently ignore the failure.

**Alternatives considered**:
- Per-tool try/except (rejected — 30+ tools, unmaintainable)
- Retry at the HTTP client level via httpx transport (rejected — only covers httpx-based tools, not Google API or Notion client)
- Wrapper-per-tool-function (rejected — too many functions to wrap individually)

## R2: Exception Classification

**Decision**: Classify exceptions into 3 categories: retryable, non-retryable, and input-error.

**Rationale**: Based on analysis of all tool implementations:

| Category | Exception Types | Action |
|----------|----------------|--------|
| **Retryable** | `httpx.TimeoutException`, `httpx.ConnectError`, `notion_client.errors.RequestTimeoutError`, `httpx.HTTPStatusError(5xx)`, `googleapiclient.errors.HttpError(5xx)` | Retry up to 2 times with 1s/2s delays |
| **Non-retryable** | `httpx.HTTPStatusError(4xx)`, `googleapiclient.errors.HttpError(4xx)`, `notion_client.errors.APIResponseError`, auth failures | Report to AI with integration name + reason |
| **Input-error** | `ValueError`, `json.JSONDecodeError` | Report to AI as input issue (no retry, no fallback) |

**Alternatives considered**:
- Catch only specific exceptions (rejected — too fragile, new exception types would fall through)
- Treat all errors as retryable (rejected — wastes time retrying permanent failures)

## R3: Tool-to-Integration Reverse Mapping

**Decision**: Add a `get_integration_for_tool(tool_name)` helper in `src/integrations.py` that returns the integration's `display_name` (e.g., "Google Calendar" not "google_calendar").

**Rationale**: The `INTEGRATION_REGISTRY` already maps integration → tools. A reverse lookup is needed for error messages like "Google Calendar is down." Building the reverse map once at import time from the existing registry is trivial and doesn't require maintaining a separate data structure.

**Alternatives considered**:
- Hardcoded tool→integration dict (rejected — would drift from registry)
- Decorator on each tool function (rejected — invasive, 30+ functions to modify)

## R4: Retry Strategy

**Decision**: Fixed delays of 1 second (first retry) and 2 seconds (second retry). Max 2 retries.

**Rationale**: Based on the existing exponential backoff pattern in `src/tools/calendar.py:86-97` (Google token refresh uses `2^attempt` delays). Most transient failures (DNS, connection reset, rate limit) resolve within 1-3 seconds. Two retries with 1s+2s delays = 3 seconds total overhead, well within the 30-second response time budget. Full exponential backoff is overkill for 2 retries.

**Alternatives considered**:
- Exponential backoff with jitter (rejected — complexity not warranted for max 2 retries)
- No delay between retries (rejected — hammering a failing service doesn't help)
- 3+ retries (rejected — extends response time too much; 2 retries catches most transient issues)

## R5: Fallback Mapping Strategy

**Decision**: Define fallback mappings as a dict in a new module (`src/tool_resilience.py`), keyed by tool name, mapping to a fallback function or action type.

**Rationale**: Only write/create operations need fallback mappings (per clarification). The existing `INTEGRATION_REGISTRY` tracks which tools belong to which integration but doesn't know which tools are write vs. read. A small explicit mapping of ~10 write tools to their fallbacks is maintainable and clear.

**Write tools requiring fallbacks**:
- `create_quick_event` → `add_action_item` (Calendar → Notion)
- `write_calendar_blocks` → `add_action_item` (Calendar → Notion)
- `push_grocery_list` → WhatsApp message with formatted list
- `add_action_item` → WhatsApp message with item details
- `save_meal_plan` → WhatsApp message with meal plan text
- `add_topic` → WhatsApp message with topic text
- `complete_action_item` → WhatsApp message confirming intent
- `add_backlog_item` → WhatsApp message with item details

**Alternatives considered**:
- Auto-derive fallbacks from integration registry (rejected — no way to know the semantics of each tool)
- Fallback chains in the integration registry (rejected — mixes concerns; registry is about env vars and enablement, not failure recovery)

## R6: Error Message Format for Claude

**Decision**: Replace the "Skip this section" error message with a structured, actionable message:

Format: `"TOOL FAILED: {tool_name} ({integration_display_name}) — {human_readable_reason}. DO NOT skip this — you MUST tell the user that {integration_display_name} is currently having issues and their {action_description} was NOT completed. Suggest an alternative."`

**Rationale**: The current message explicitly says "Skip this section" which instructs Claude to ignore the failure. The replacement must do the opposite — explicitly instruct Claude to inform the user. Testing shows Claude follows explicit instructions in tool results reliably.

**Alternatives considered**:
- Return a structured JSON error (rejected — Claude handles natural language instructions better than structured data for behavioral guidance)
- Add system prompt instructions about never skipping failures (rejected — tool-level instruction is more reliable and doesn't bloat the system prompt)
