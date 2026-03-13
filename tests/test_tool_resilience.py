"""Tests for tool failure resilience (src/tool_resilience.py + src/integrations.py reverse lookup)."""

import json
from unittest.mock import MagicMock, patch

import httpx

from src.integrations import get_integration_for_tool
from src.tool_resilience import (
    FALLBACK_MAPPINGS,
    ExceptionCategory,
    attempt_fallback,
    classify_exception,
    execute_with_retry,
    format_error_message,
)

# ---------------------------------------------------------------------------
# T015: get_integration_for_tool reverse lookup
# ---------------------------------------------------------------------------


class TestGetIntegrationForTool:
    def test_calendar_tool(self):
        assert get_integration_for_tool("create_quick_event") == "Google Calendar"

    def test_notion_tool(self):
        assert get_integration_for_tool("add_action_item") == "Notion"

    def test_anylist_tool(self):
        assert get_integration_for_tool("push_grocery_list") == "AnyList"

    def test_ynab_tool(self):
        assert get_integration_for_tool("get_budget_summary") == "YNAB"

    def test_unknown_tool(self):
        assert get_integration_for_tool("nonexistent_tool") == "Unknown"

    def test_core_tool(self):
        assert get_integration_for_tool("get_daily_context") == "Core"

    def test_recipes_tool(self):
        assert get_integration_for_tool("search_recipes") == "Recipes"


# ---------------------------------------------------------------------------
# T014: classify_exception
# ---------------------------------------------------------------------------


class TestClassifyException:
    def test_timeout_is_retryable(self):
        exc = httpx.TimeoutException("read timed out")
        assert classify_exception(exc) == ExceptionCategory.RETRYABLE

    def test_connect_error_is_retryable(self):
        exc = httpx.ConnectError("connection refused")
        assert classify_exception(exc) == ExceptionCategory.RETRYABLE

    def test_http_500_is_retryable(self):
        response = httpx.Response(500, request=httpx.Request("GET", "https://example.com"))
        exc = httpx.HTTPStatusError("server error", request=response.request, response=response)
        assert classify_exception(exc) == ExceptionCategory.RETRYABLE

    def test_http_429_is_retryable(self):
        response = httpx.Response(429, request=httpx.Request("GET", "https://example.com"))
        exc = httpx.HTTPStatusError("rate limited", request=response.request, response=response)
        assert classify_exception(exc) == ExceptionCategory.RETRYABLE

    def test_http_403_is_non_retryable(self):
        response = httpx.Response(403, request=httpx.Request("GET", "https://example.com"))
        exc = httpx.HTTPStatusError("forbidden", request=response.request, response=response)
        assert classify_exception(exc) == ExceptionCategory.NON_RETRYABLE

    def test_http_404_is_non_retryable(self):
        response = httpx.Response(404, request=httpx.Request("GET", "https://example.com"))
        exc = httpx.HTTPStatusError("not found", request=response.request, response=response)
        assert classify_exception(exc) == ExceptionCategory.NON_RETRYABLE

    def test_value_error_is_input_error(self):
        assert classify_exception(ValueError("bad date")) == ExceptionCategory.INPUT_ERROR

    def test_json_decode_error_is_input_error(self):
        exc = json.JSONDecodeError("Expecting value", "", 0)
        assert classify_exception(exc) == ExceptionCategory.INPUT_ERROR

    def test_unknown_exception_is_non_retryable(self):
        assert classify_exception(RuntimeError("unknown")) == ExceptionCategory.NON_RETRYABLE

    def test_google_api_500(self):
        """Google API HttpError with 5xx should be retryable."""
        exc = Exception("Google API error")
        exc.resp = MagicMock()
        exc.resp.status = 503
        assert classify_exception(exc) == ExceptionCategory.RETRYABLE

    def test_google_api_404(self):
        """Google API HttpError with 4xx should be non-retryable."""
        exc = Exception("Google API error")
        exc.resp = MagicMock()
        exc.resp.status = 404
        assert classify_exception(exc) == ExceptionCategory.NON_RETRYABLE


# ---------------------------------------------------------------------------
# T014: format_error_message
# ---------------------------------------------------------------------------


class TestFormatErrorMessage:
    def test_retryable_message_contains_service_name(self):
        exc = httpx.TimeoutException("timeout")
        msg = format_error_message("create_quick_event", exc, ExceptionCategory.RETRYABLE)
        assert "Google Calendar" in msg
        assert "DO NOT skip" in msg
        assert "NOT completed" in msg

    def test_non_retryable_message(self):
        response = httpx.Response(403, request=httpx.Request("GET", "https://example.com"))
        exc = httpx.HTTPStatusError("forbidden", request=response.request, response=response)
        msg = format_error_message("add_action_item", exc, ExceptionCategory.NON_RETRYABLE)
        assert "Notion" in msg
        assert "DO NOT skip" in msg

    def test_input_error_message(self):
        exc = ValueError("invalid date format")
        msg = format_error_message("create_quick_event", exc, ExceptionCategory.INPUT_ERROR)
        assert "invalid input" in msg
        assert "DO NOT skip" in msg
        assert "Google Calendar" not in msg  # Input errors don't blame the service


# ---------------------------------------------------------------------------
# T014: execute_with_retry
# ---------------------------------------------------------------------------


class TestExecuteWithRetry:
    def test_success_on_first_try(self):
        func = MagicMock(return_value="event created")
        result = execute_with_retry(func, "create_quick_event", {"title": "test"})
        assert result == "event created"
        assert func.call_count == 1

    @patch("src.tool_resilience.time.sleep")
    def test_success_on_retry(self, mock_sleep):
        func = MagicMock(side_effect=[httpx.TimeoutException("timeout"), "event created"])
        result = execute_with_retry(func, "create_quick_event", {"title": "test"})
        assert result == "event created"
        assert func.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch("src.tool_resilience.time.sleep")
    def test_exhausted_retries_returns_error(self, mock_sleep):
        func = MagicMock(side_effect=httpx.TimeoutException("timeout"))
        result = execute_with_retry(func, "create_quick_event", {"title": "test"})
        assert func.call_count == 3  # 1 initial + 2 retries
        assert "TOOL FAILED" in result or "FALLBACK" in result
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    def test_non_retryable_no_retry(self):
        response = httpx.Response(403, request=httpx.Request("GET", "https://example.com"))
        func = MagicMock(side_effect=httpx.HTTPStatusError("forbidden", request=response.request, response=response))
        # Use a tool without fallback mapping to test pure non-retryable behavior
        result = execute_with_retry(func, "get_calendar_events", {"date": "today"})
        assert func.call_count == 1
        assert "TOOL FAILED" in result
        assert "Google Calendar" in result

    def test_non_retryable_write_tool_tries_fallback(self):
        """Non-retryable error on a write tool should attempt fallback."""
        response = httpx.Response(403, request=httpx.Request("GET", "https://example.com"))
        func = MagicMock(side_effect=httpx.HTTPStatusError("forbidden", request=response.request, response=response))
        fallback_result = (True, "FALLBACK USED: test", "add_action_item")
        with patch("src.tool_resilience.attempt_fallback", return_value=fallback_result):
            result = execute_with_retry(func, "create_quick_event", {"title": "test"})
        assert func.call_count == 1  # No retry for non-retryable
        assert "FALLBACK" in result

    def test_input_error_no_retry(self):
        func = MagicMock(side_effect=ValueError("bad date"))
        result = execute_with_retry(func, "create_quick_event", {"title": "test"})
        assert func.call_count == 1
        assert "invalid input" in result

    @patch("src.tool_resilience.time.sleep")
    def test_retry_timing(self, mock_sleep):
        """Verify retry delays are 1s then 2s."""
        func = MagicMock(side_effect=httpx.TimeoutException("timeout"))
        execute_with_retry(func, "test_tool", {"key": "val"})
        assert mock_sleep.call_args_list == [
            ((1,),),
            ((2,),),
        ]


# ---------------------------------------------------------------------------
# T014: attempt_fallback
# ---------------------------------------------------------------------------


class TestAttemptFallback:
    def test_calendar_fallback_to_action_item(self):
        mock_add = MagicMock(return_value="Action item created")
        tools = {"add_action_item": mock_add}
        success, msg, used = attempt_fallback(
            "create_quick_event",
            {"title": "Blood draw", "date": "2026-03-05", "time": "14:00"},
            tools,
        )
        assert success is True
        assert "FALLBACK USED" in msg
        assert used == "add_action_item"
        mock_add.assert_called_once()

    def test_no_fallback_mapping(self):
        success, msg, used = attempt_fallback("get_calendar_events", {}, {})
        assert success is False
        assert used is None

    def test_fallback_tool_not_available(self):
        success, msg, used = attempt_fallback("create_quick_event", {"title": "test"}, {})
        assert success is False
        assert used is None

    def test_fallback_tool_also_fails(self):
        mock_add = MagicMock(side_effect=RuntimeError("Notion also down"))
        tools = {"add_action_item": mock_add}
        success, msg, used = attempt_fallback("create_quick_event", {"title": "test"}, tools)
        assert success is False
        assert used == "add_action_item"

    def test_whatsapp_only_fallback(self):
        """Tools with None fallback_tool should return no success."""
        success, msg, used = attempt_fallback(
            "push_grocery_list", {"items": ["milk"]}, {"add_action_item": MagicMock()}
        )
        assert success is False
        assert used is None


# ---------------------------------------------------------------------------
# T014: FALLBACK_MAPPINGS coverage
# ---------------------------------------------------------------------------


class TestFallbackMappings:
    def test_all_write_tools_have_mappings(self):
        expected = {
            "create_quick_event",
            "write_calendar_blocks",
            "push_grocery_list",
            "add_action_item",
            "save_meal_plan",
            "add_topic",
            "complete_action_item",
            "add_backlog_item",
        }
        assert set(FALLBACK_MAPPINGS.keys()) == expected

    def test_calendar_tools_fallback_to_action_item(self):
        assert FALLBACK_MAPPINGS["create_quick_event"][0] == "add_action_item"
        assert FALLBACK_MAPPINGS["write_calendar_blocks"][0] == "add_action_item"

    def test_tools_without_fallback_have_last_resort(self):
        for tool, (fallback, last_resort) in FALLBACK_MAPPINGS.items():
            assert last_resort, f"{tool} missing last_resort_type"


# ---------------------------------------------------------------------------
# audit_tool_result tests
# ---------------------------------------------------------------------------


class TestAuditToolResult:
    def test_normal_result_passes(self):
        from src.tool_resilience import audit_tool_result

        is_err, result = audit_tool_result("get_calendar_events", '[{"summary": "Meeting"}]')
        assert not is_err
        assert result == '[{"summary": "Meeting"}]'

    def test_error_prefix_detected(self):
        from src.tool_resilience import audit_tool_result

        is_err, result = audit_tool_result("create_quick_event", "Error: currently unavailable")
        assert is_err
        assert "TOOL WARNING" in result

    def test_tool_failed_prefix_passthrough(self):
        from src.tool_resilience import audit_tool_result

        is_err, result = audit_tool_result("add_action_item", "TOOL FAILED: add_action_item — server error")
        assert is_err
        # Should not double-wrap with TOOL WARNING
        assert result.startswith("TOOL FAILED:")

    def test_unavailable_substring_detected(self):
        from src.tool_resilience import audit_tool_result

        is_err, result = audit_tool_result("get_budget_summary", "Service unavailable, try later")
        assert is_err
        assert "TOOL WARNING" in result

    def test_empty_result_detected(self):
        from src.tool_resilience import audit_tool_result

        is_err, result = audit_tool_result("save_meal_plan", "")
        assert is_err
        assert "empty result" in result

    def test_forbidden_detected(self):
        from src.tool_resilience import audit_tool_result

        is_err, result = audit_tool_result("get_action_items", "403 Forbidden")
        assert is_err
        assert "TOOL WARNING" in result
