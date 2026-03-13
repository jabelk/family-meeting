"""Unit tests for AI provider failover logic."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.ai_provider import (
    BACKUP_TOOLS,
    AllProvidersDownError,
    ProviderResponse,
    TextBlock,
    ToolUseBlock,
    _convert_messages_for_openai,
    _convert_tools_for_openai,
    _normalize_openai_response,
    create_message,
)


# ---------------------------------------------------------------------------
# Tool format conversion tests
# ---------------------------------------------------------------------------


class TestConvertToolsForOpenai:
    def test_converts_backup_tool(self):
        anthropic_tools = [
            {
                "name": "get_daily_context",
                "description": "Get daily context",
                "input_schema": {
                    "type": "object",
                    "properties": {"date": {"type": "string"}},
                    "required": [],
                },
            }
        ]
        result = _convert_tools_for_openai(anthropic_tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "get_daily_context"
        assert result[0]["function"]["parameters"]["type"] == "object"
        assert "input_schema" not in result[0]["function"]

    def test_filters_non_backup_tools(self):
        anthropic_tools = [
            {"name": "get_daily_context", "description": "...", "input_schema": {"type": "object", "properties": {}}},
            {
                "name": "push_grocery_list",
                "description": "...",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]
        result = _convert_tools_for_openai(anthropic_tools)
        assert len(result) == 1
        assert result[0]["function"]["name"] == "get_daily_context"

    def test_empty_tools(self):
        assert _convert_tools_for_openai([]) == []


# ---------------------------------------------------------------------------
# Message format conversion tests
# ---------------------------------------------------------------------------


class TestConvertMessagesForOpenai:
    def test_simple_text_messages(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result = _convert_messages_for_openai("You are helpful.", messages)
        assert result[0] == {"role": "system", "content": "You are helpful."}
        assert result[1] == {"role": "user", "content": "Hello"}
        assert result[2] == {"role": "assistant", "content": "Hi there"}

    def test_tool_result_conversion(self):
        messages = [
            {"role": "user", "content": "What's today?"},
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "call_123", "content": "Monday"},
                ],
            },
        ]
        result = _convert_messages_for_openai("system", messages)
        # System + user text + tool result
        assert len(result) == 3
        assert result[2]["role"] == "tool"
        assert result[2]["tool_call_id"] == "call_123"
        assert result[2]["content"] == "Monday"


# ---------------------------------------------------------------------------
# Response normalization tests
# ---------------------------------------------------------------------------


class TestNormalizeOpenaiResponse:
    def test_text_response(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello!"
        mock_response.choices[0].message.tool_calls = None
        result = _normalize_openai_response(mock_response)
        assert isinstance(result, ProviderResponse)
        assert result.provider == "openai"
        assert result.stop_reason == "end_turn"
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextBlock)
        assert result.content[0].text == "Hello!"

    def test_tool_call_response(self):
        mock_tc = MagicMock()
        mock_tc.id = "call_abc"
        mock_tc.function.name = "get_daily_context"
        mock_tc.function.arguments = '{"date": "2026-03-13"}'

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.choices[0].message.tool_calls = [mock_tc]

        result = _normalize_openai_response(mock_response)
        assert result.stop_reason == "tool_use"
        assert len(result.content) == 1
        assert isinstance(result.content[0], ToolUseBlock)
        assert result.content[0].name == "get_daily_context"
        assert result.content[0].input == {"date": "2026-03-13"}


# ---------------------------------------------------------------------------
# Failover logic tests
# ---------------------------------------------------------------------------


class TestCreateMessage:
    @patch("src.ai_provider.anthropic.Anthropic")
    def test_claude_success(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Hello")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        response, provider = create_message(
            system="test", tools=[], messages=[{"role": "user", "content": "hi"}]
        )
        assert provider == "claude"

    @patch("src.ai_provider.OpenAI")
    @patch("src.ai_provider.anthropic.Anthropic")
    def test_failover_to_openai_on_529(self, mock_anthropic_cls, mock_openai_cls):
        import anthropic

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # Simulate 529 overloaded
        mock_resp = MagicMock()
        mock_resp.status_code = 529
        mock_client.messages.create.side_effect = anthropic.APIStatusError(
            message="overloaded", response=mock_resp, body=None
        )

        # OpenAI succeeds
        mock_openai = MagicMock()
        mock_openai_cls.return_value = mock_openai
        mock_oai_response = MagicMock()
        mock_oai_response.choices = [MagicMock()]
        mock_oai_response.choices[0].message.content = "Backup response"
        mock_oai_response.choices[0].message.tool_calls = None
        mock_openai.chat.completions.create.return_value = mock_oai_response

        response, provider = create_message(
            system="test", tools=[], messages=[{"role": "user", "content": "hi"}]
        )
        assert provider == "openai"
        assert response.content[0].text == "Backup response"

    @patch("src.ai_provider.OpenAI")
    @patch("src.ai_provider.anthropic.Anthropic")
    def test_both_down_raises(self, mock_anthropic_cls, mock_openai_cls):
        import anthropic

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.messages.create.side_effect = anthropic.APIStatusError(
            message="server error", response=mock_resp, body=None
        )

        mock_openai = MagicMock()
        mock_openai_cls.return_value = mock_openai
        mock_openai.chat.completions.create.side_effect = Exception("OpenAI also down")

        with pytest.raises(AllProvidersDownError):
            create_message(system="test", tools=[], messages=[{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# BACKUP_TOOLS constant test
# ---------------------------------------------------------------------------


def test_backup_tools_is_subset():
    """Verify BACKUP_TOOLS contains expected core tools."""
    assert "get_daily_context" in BACKUP_TOOLS
    assert "get_calendar_events" in BACKUP_TOOLS
    assert "add_action_item" in BACKUP_TOOLS
    assert "check_system_logs" in BACKUP_TOOLS
    assert "get_family_profile" in BACKUP_TOOLS
    # Should NOT contain advanced tools
    assert "push_grocery_list" not in BACKUP_TOOLS
    assert "get_budget_summary" not in BACKUP_TOOLS
    assert "search_recipes" not in BACKUP_TOOLS
