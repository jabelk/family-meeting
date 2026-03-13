# Data Model: Tool Failure Resilience

## Entities

### ExceptionCategory (enum)

Classifies a caught exception for routing decisions.

| Value | Description | Action |
|-------|-------------|--------|
| `RETRYABLE` | Transient failure likely to resolve on retry | Retry up to 2 times with 1s/2s delays |
| `NON_RETRYABLE` | Permanent failure (auth, permissions, 4xx) | Report to AI immediately, no retry |
| `INPUT_ERROR` | Bad input from the AI model (ValueError, JSON) | Report as input issue, no retry, no fallback |

### FallbackMapping

Maps a write tool to its fallback action when the primary tool fails after retries.

| Field | Type | Description |
|-------|------|-------------|
| `primary_tool` | `str` | Tool name that failed (e.g., `"create_quick_event"`) |
| `fallback_tool` | `str | None` | Alternative tool to try (e.g., `"add_action_item"`) |
| `last_resort` | `str` | Description type for WhatsApp message fallback (e.g., `"calendar_event"`) |

**Defined mappings** (from research R5):

| Primary Tool | Fallback Tool | Last Resort |
|-------------|---------------|-------------|
| `create_quick_event` | `add_action_item` | WhatsApp: event details |
| `write_calendar_blocks` | `add_action_item` | WhatsApp: calendar blocks |
| `push_grocery_list` | `None` | WhatsApp: formatted grocery list |
| `add_action_item` | `None` | WhatsApp: action item details |
| `save_meal_plan` | `None` | WhatsApp: meal plan text |
| `add_topic` | `None` | WhatsApp: topic text |
| `complete_action_item` | `None` | WhatsApp: completion intent |
| `add_backlog_item` | `None` | WhatsApp: backlog item details |

### Exception Classification Rules

Maps exception types to `ExceptionCategory`.

| Exception Type | Category | Notes |
|----------------|----------|-------|
| `httpx.TimeoutException` | RETRYABLE | Connection/read timeouts |
| `httpx.ConnectError` | RETRYABLE | DNS, connection refused |
| `httpx.HTTPStatusError` (5xx) | RETRYABLE | Server errors |
| `googleapiclient.errors.HttpError` (5xx) | RETRYABLE | Google API server errors |
| `notion_client.errors.RequestTimeoutError` | RETRYABLE | Notion timeout |
| `httpx.HTTPStatusError` (4xx) | NON_RETRYABLE | Client errors |
| `googleapiclient.errors.HttpError` (4xx) | NON_RETRYABLE | Google API client errors |
| `notion_client.errors.APIResponseError` | NON_RETRYABLE | Notion API errors |
| `ValueError` | INPUT_ERROR | Bad parameter values |
| `json.JSONDecodeError` | INPUT_ERROR | Malformed JSON input |
| `Exception` (catch-all) | NON_RETRYABLE | Unknown errors default to non-retryable |

## Relationships

- `FallbackMapping` references tool names from `INTEGRATION_REGISTRY` in `src/integrations.py`
- `get_integration_for_tool()` provides the reverse lookup: tool name → integration `display_name`
- The retry loop uses `ExceptionCategory` to decide whether to retry or report immediately
- Error messages include the integration `display_name` from the reverse lookup

## State Transitions

Tool execution flow with resilience:

```
Tool Call
  → Execute
    → Success → return result
    → Exception
      → classify_exception()
        → INPUT_ERROR → format_error_message() → return
        → NON_RETRYABLE → format_error_message() → return
        → RETRYABLE
          → retry (attempt 2, delay 1s)
            → Success → return result
            → retry (attempt 3, delay 2s)
              → Success → return result
              → Failure → check fallback_mappings
                → Has fallback tool → execute fallback
                  → Success → return result + fallback notice
                  → Failure → format_error_message() with WhatsApp last resort instruction
                → No fallback → format_error_message() → return
```
