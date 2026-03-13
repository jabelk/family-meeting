"""Tool failure resilience — retry, error reporting, and fallback actions.

Classifies exceptions, retries transient failures, formats service-aware
error messages for Claude, and executes fallback actions for write tools.
"""

import json
import logging
import time
from enum import Enum
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)


class ExceptionCategory(Enum):
    """Classification of a tool exception for routing decisions."""

    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    INPUT_ERROR = "input_error"


def _get_http_status(exc: Exception) -> int | None:
    """Extract HTTP status code from httpx or Google API exceptions."""
    # httpx.HTTPStatusError
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    # googleapiclient.errors.HttpError
    if hasattr(exc, "resp") and hasattr(exc.resp, "status"):
        try:
            return int(exc.resp.status)
        except (ValueError, TypeError):
            pass
    return None


def classify_exception(exc: Exception) -> ExceptionCategory:
    """Classify an exception to determine retry/report strategy."""
    # Input errors — never retry
    if isinstance(exc, (ValueError, json.JSONDecodeError)):
        return ExceptionCategory.INPUT_ERROR

    # Transient network errors — always retry
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return ExceptionCategory.RETRYABLE

    # Notion timeout — retry
    try:
        from notion_client.errors import RequestTimeoutError as NotionTimeout

        if isinstance(exc, NotionTimeout):
            return ExceptionCategory.RETRYABLE
    except ImportError:
        pass

    # HTTP status-based classification (httpx + Google API)
    status = _get_http_status(exc)
    if status is not None:
        if status >= 500 or status == 429:
            return ExceptionCategory.RETRYABLE
        return ExceptionCategory.NON_RETRYABLE

    # Notion API response errors (non-timeout) — non-retryable
    try:
        from notion_client.errors import APIResponseError

        if isinstance(exc, APIResponseError):
            return ExceptionCategory.NON_RETRYABLE
    except ImportError:
        pass

    # Unknown exceptions default to non-retryable
    return ExceptionCategory.NON_RETRYABLE


def _human_readable_reason(exc: Exception) -> str:
    """Extract a concise human-readable reason from an exception."""
    status = _get_http_status(exc)
    if status is not None:
        if status == 429:
            return "rate limited"
        if status >= 500:
            return "service unavailable (server error)"
        if status == 401 or status == 403:
            return "authentication/permission error"
        if status == 404:
            return "resource not found"
        return f"HTTP error {status}"
    exc_name = type(exc).__name__
    msg = str(exc)
    if len(msg) > 120:
        msg = msg[:120] + "..."
    return f"{exc_name}: {msg}" if msg else exc_name


def format_error_message(tool_name: str, exc: Exception, category: ExceptionCategory) -> str:
    """Format a service-aware error message that instructs Claude to inform the user."""
    from src.integrations import get_integration_for_tool

    display_name = get_integration_for_tool(tool_name)
    reason = _human_readable_reason(exc)

    if category == ExceptionCategory.INPUT_ERROR:
        return (
            f"TOOL FAILED: {tool_name} — invalid input: {reason}. "
            f"DO NOT skip this — you MUST tell the user that the request had an issue "
            f"and ask them to clarify or correct the input."
        )

    if category == ExceptionCategory.RETRYABLE:
        return (
            f"TOOL FAILED: {tool_name} ({display_name}) — {reason} "
            f"(failed after retries). "
            f"DO NOT skip this — you MUST tell the user that {display_name} is "
            f"currently having issues and their request was NOT completed. "
            f"Suggest an alternative."
        )

    # NON_RETRYABLE
    return (
        f"TOOL FAILED: {tool_name} ({display_name}) — {reason}. "
        f"DO NOT skip this — you MUST tell the user that {display_name} "
        f"encountered an error and their request was NOT completed. "
        f"Suggest an alternative."
    )


# Retry delays in seconds for attempt 1 and attempt 2
_RETRY_DELAYS = (1, 2)
_MAX_RETRIES = 2


def execute_with_retry(
    func: Callable[..., Any],
    tool_name: str,
    tool_input: dict[str, Any],
) -> str:
    """Execute a tool function with automatic retry for transient failures.

    Returns the tool result as a string. On permanent failure, returns a
    formatted error message for Claude (never raises).
    """
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES + 1):  # 0, 1, 2
        try:
            result = func(**tool_input)
            if attempt > 0:
                logger.info("Tool %s succeeded on retry attempt %d", tool_name, attempt)
            return str(result)
        except Exception as exc:
            last_exc = exc
            category = classify_exception(exc)

            if category == ExceptionCategory.INPUT_ERROR:
                logger.warning("Tool %s input error (no retry): %s", tool_name, exc)
                return format_error_message(tool_name, exc, category)

            if category == ExceptionCategory.NON_RETRYABLE:
                logger.warning("Tool %s non-retryable error: %s", tool_name, exc)
                # Try fallback for write tools before returning error
                if tool_name in FALLBACK_MAPPINGS:
                    return _handle_exhausted_retries(tool_name, tool_input, exc)
                return format_error_message(tool_name, exc, category)

            # RETRYABLE — retry if attempts remain
            if attempt < _MAX_RETRIES:
                delay = _RETRY_DELAYS[attempt]
                logger.info(
                    "Tool %s failed (attempt %d/%d, %s), retrying in %ds: %s",
                    tool_name,
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    category.value,
                    delay,
                    exc,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Tool %s failed after %d attempts: %s",
                    tool_name,
                    _MAX_RETRIES + 1,
                    exc,
                )

    # All retries exhausted for a retryable error — try fallback
    return _handle_exhausted_retries(tool_name, tool_input, last_exc)


# ---------------------------------------------------------------------------
# Fallback mappings for write/create tools
# ---------------------------------------------------------------------------

# Each entry: primary_tool → (fallback_tool or None, last_resort_type)
FALLBACK_MAPPINGS: dict[str, tuple[str | None, str]] = {
    "create_quick_event": ("add_action_item", "calendar_event"),
    "write_calendar_blocks": ("add_action_item", "calendar_blocks"),
    "push_grocery_list": (None, "grocery_list"),
    "add_action_item": (None, "action_item"),
    "save_meal_plan": (None, "meal_plan"),
    "add_topic": (None, "meeting_topic"),
    "complete_action_item": (None, "action_completion"),
    "add_backlog_item": (None, "backlog_item"),
}


def _format_last_resort_message(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Format tool input as a human-readable summary for WhatsApp last-resort delivery."""
    mapping = FALLBACK_MAPPINGS.get(tool_name)
    last_resort_type = mapping[1] if mapping else "request"

    # Build a readable summary from tool_input, filtering internal keys
    parts = []
    for key, value in tool_input.items():
        if key.startswith("_"):
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        parts.append(f"  - {key}: {value}")

    details = "\n".join(parts) if parts else "  (no details available)"

    return (
        f"TOOL FAILED: {tool_name} and its fallback BOTH failed. "
        f"DO NOT skip this — you MUST send the following {last_resort_type} details "
        f"directly in your message to the user so they have the information:\n"
        f"{details}\n"
        f"Tell the user the service is down and you're providing the details "
        f"directly so nothing is lost."
    )


def attempt_fallback(
    tool_name: str,
    tool_input: dict[str, Any],
    available_tools: dict[str, Callable[..., Any]],
) -> tuple[bool, str, str | None]:
    """Attempt a fallback action for a failed write tool.

    Returns (success, result_message, fallback_tool_used).
    """
    mapping = FALLBACK_MAPPINGS.get(tool_name)
    if not mapping:
        return False, "", None

    fallback_tool, _ = mapping
    if not fallback_tool or fallback_tool not in available_tools:
        return False, "", None

    from src.integrations import get_integration_for_tool

    fallback_display = get_integration_for_tool(fallback_tool)
    primary_display = get_integration_for_tool(tool_name)

    # Adapt parameters for the fallback tool
    fallback_input = _adapt_params_for_fallback(tool_name, fallback_tool, tool_input)

    try:
        result = available_tools[fallback_tool](**fallback_input)
        logger.info(
            "Fallback succeeded: %s → %s for tool %s",
            tool_name,
            fallback_tool,
            tool_name,
        )
        return (
            True,
            (
                f"FALLBACK USED: {primary_display} is down, so I used "
                f"{fallback_display} instead. Result: {result}\n"
                f'Tell the user: "{primary_display} is having issues right now — '
                f'I added this as a {fallback_display} item instead so nothing is lost."'
            ),
            fallback_tool,
        )
    except Exception as fallback_exc:
        logger.error(
            "Fallback %s also failed for %s: %s",
            fallback_tool,
            tool_name,
            fallback_exc,
        )
        return False, "", fallback_tool


def _adapt_params_for_fallback(primary_tool: str, fallback_tool: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Adapt tool_input parameters from primary tool format to fallback tool format."""
    # Calendar → Notion action item: extract title/date/time into action item fields
    if primary_tool in ("create_quick_event", "write_calendar_blocks") and fallback_tool == "add_action_item":
        title = tool_input.get("title", tool_input.get("summary", "Calendar reminder"))
        date = tool_input.get("date", tool_input.get("start_date", ""))
        time_str = tool_input.get("time", tool_input.get("start_time", ""))
        desc = f"[Calendar fallback] {title}"
        if date:
            desc += f" on {date}"
        if time_str:
            desc += f" at {time_str}"
        # add_action_item requires: assignee (str), description (str)
        adapted: dict[str, Any] = {"assignee": "Family", "description": desc}
        # Pass through _phone if present
        if "_phone" in tool_input:
            adapted["_phone"] = tool_input["_phone"]
        return adapted

    # Default: pass through all non-internal params
    return {k: v for k, v in tool_input.items() if not k.startswith("_") or k == "_phone"}


def _handle_exhausted_retries(
    tool_name: str,
    tool_input: dict[str, Any],
    last_exc: Exception | None,
) -> str:
    """Handle a tool that failed all retry attempts — try fallback, then last resort."""
    from src.integrations import get_integration_for_tool

    # Only attempt fallback for tools that have mappings
    if tool_name in FALLBACK_MAPPINGS:
        # We need access to the tool functions for fallback execution.
        # Import here to avoid circular imports.
        try:
            from src.assistant import TOOL_FUNCTIONS

            success, result_msg, fallback_used = attempt_fallback(tool_name, tool_input, TOOL_FUNCTIONS)
            if success:
                return result_msg

            # Fallback was attempted but failed — use last resort
            if fallback_used:
                logger.error(
                    "Both %s and fallback %s failed — using WhatsApp last resort",
                    tool_name,
                    fallback_used,
                )
                return _format_last_resort_message(tool_name, tool_input)
        except ImportError:
            logger.warning("Could not import TOOL_FUNCTIONS for fallback")

        # No fallback tool available (fallback_tool is None) — use last resort
        if FALLBACK_MAPPINGS[tool_name][0] is None:
            return _format_last_resort_message(tool_name, tool_input)

    # No fallback mapping — just return the error message
    if last_exc is not None:
        return format_error_message(tool_name, last_exc, ExceptionCategory.RETRYABLE)
    display_name = get_integration_for_tool(tool_name)
    return (
        f"TOOL FAILED: {tool_name} ({display_name}) — failed after retries. "
        f"DO NOT skip this — you MUST tell the user that {display_name} is "
        f"currently having issues and their request was NOT completed. "
        f"Suggest an alternative."
    )
