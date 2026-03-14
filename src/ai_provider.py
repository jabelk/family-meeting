"""AI provider abstraction with automatic failover.

Tries Claude (primary) first. On failure (500/529/timeout/connection error),
falls back to OpenAI GPT with a core tool subset. If both fail, raises
AllProvidersDownError for the caller to handle with a static message.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import anthropic
import httpx
from openai import OpenAI

from src.config import ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

# Primary timeout: 45 seconds before failover triggers
_PRIMARY_TIMEOUT = 45.0

# Model tier constants for routing
MODEL_OPUS = "claude-opus-4-20250514"
MODEL_SONNET = "claude-sonnet-4-5-20250514"
MODEL_HAIKU = "claude-haiku-4-5-20250901"
MODEL_DEFAULT = MODEL_SONNET  # Default to Sonnet — Opus only when explicitly requested

# Core tool subset available on the backup provider (~10 most-used tools).
# Advanced integrations (YNAB, recipes, AnyList, etc.) are deferred until
# the primary recovers.
BACKUP_TOOLS: set[str] = {
    "get_daily_context",
    "get_calendar_events",
    "create_quick_event",
    "get_action_items",
    "add_action_item",
    "complete_action_item",
    "save_preference",
    "list_preferences",
    "check_system_logs",
    "get_family_profile",
}


class AllProvidersDownError(Exception):
    """Raised when both primary and backup AI providers are unavailable."""


@dataclass
class TextBlock:
    """Normalized text content block."""

    type: str = "text"
    text: str = ""


@dataclass
class ToolUseBlock:
    """Normalized tool use request block."""

    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {}


@dataclass
class ProviderResponse:
    """Normalized response from either AI provider."""

    content: list = None
    stop_reason: str = "end_turn"
    provider: str = "claude"

    def __post_init__(self):
        if self.content is None:
            self.content = []


# ---------------------------------------------------------------------------
# Tool format conversion: Anthropic → OpenAI
# ---------------------------------------------------------------------------


def _convert_tools_for_openai(anthropic_tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool definitions to OpenAI function-calling format.

    Only includes tools in BACKUP_TOOLS subset.
    """
    openai_tools = []
    for tool in anthropic_tools:
        if tool["name"] not in BACKUP_TOOLS:
            continue
        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
        )
    return openai_tools


# ---------------------------------------------------------------------------
# Message format conversion: Anthropic → OpenAI
# ---------------------------------------------------------------------------


def _convert_messages_for_openai(system: str, messages: list[dict]) -> list[dict]:
    """Convert Anthropic message format to OpenAI chat format.

    Anthropic uses:
    - system as separate param
    - tool_result blocks inside user messages
    - tool_use blocks inside assistant content

    OpenAI uses:
    - system as {"role": "system"} message
    - tool results as {"role": "tool"} messages
    - tool calls on assistant messages via tool_calls field
    """
    openai_msgs = [{"role": "system", "content": system}]

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Simple text message
        if isinstance(content, str):
            openai_msgs.append({"role": role, "content": content})
            continue

        # Content is a list of blocks (Anthropic format)
        if isinstance(content, list):
            if role == "assistant":
                # Extract text and tool_use blocks
                text_parts = []
                tool_calls = []
                for block in content:
                    if hasattr(block, "type"):
                        # Anthropic SDK objects
                        if block.type == "text":
                            text_parts.append(block.text)
                        elif block.type == "tool_use":
                            tool_calls.append(
                                {
                                    "id": block.id,
                                    "type": "function",
                                    "function": {
                                        "name": block.name,
                                        "arguments": json.dumps(block.input),
                                    },
                                }
                            )
                    elif isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            tool_calls.append(
                                {
                                    "id": block["id"],
                                    "type": "function",
                                    "function": {
                                        "name": block["name"],
                                        "arguments": json.dumps(block.get("input", {})),
                                    },
                                }
                            )

                assistant_msg: dict[str, Any] = {"role": "assistant"}
                if text_parts:
                    assistant_msg["content"] = "\n".join(text_parts)
                else:
                    assistant_msg["content"] = None
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                openai_msgs.append(assistant_msg)

            elif role == "user":
                # Check for tool_result blocks
                text_parts = []
                tool_results = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "tool_result":
                            tool_results.append(block)
                        elif block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        else:
                            text_parts.append(str(block))
                    elif hasattr(block, "type") and block.type == "tool_result":
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.tool_use_id,
                                "content": block.content,
                            }
                        )
                    else:
                        text_parts.append(str(block))

                # Add tool result messages first
                for tr in tool_results:
                    openai_msgs.append(
                        {
                            "role": "tool",
                            "tool_call_id": tr.get("tool_use_id", ""),
                            "content": str(tr.get("content", "")),
                        }
                    )

                # Add any text content as user message
                if text_parts:
                    openai_msgs.append({"role": "user", "content": "\n".join(text_parts)})
            else:
                # Other roles — pass through as text
                openai_msgs.append({"role": role, "content": str(content)})

    return openai_msgs


# ---------------------------------------------------------------------------
# Response normalization: OpenAI → Anthropic-like
# ---------------------------------------------------------------------------


def _normalize_openai_response(openai_response) -> ProviderResponse:
    """Convert OpenAI response to Anthropic-like ProviderResponse."""
    choice = openai_response.choices[0]
    message = choice.message
    content_blocks: list = []

    # Text content
    if message.content:
        content_blocks.append(TextBlock(text=message.content))

    # Tool calls
    if message.tool_calls:
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                args = {}
            content_blocks.append(
                ToolUseBlock(
                    id=tc.id,
                    name=tc.function.name,
                    input=args,
                )
            )

    # Determine stop reason
    stop_reason = "end_turn"
    if message.tool_calls:
        stop_reason = "tool_use"

    return ProviderResponse(
        content=content_blocks,
        stop_reason=stop_reason,
        provider="openai",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def create_message(
    system: str,
    tools: list[dict],
    messages: list[dict],
    max_tokens: int = 2048,
    model: str = MODEL_DEFAULT,
) -> tuple[ProviderResponse, str]:
    """Create an AI message with automatic failover.

    Tries Claude first (45s timeout). On server error, overload, timeout,
    or connection failure, retries with OpenAI GPT.

    Returns (response, provider_used) where provider_used is "claude" or "openai".
    Raises AllProvidersDownError if both providers fail.
    """
    # --- Try Claude (primary) ---
    try:
        claude_client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
            timeout=httpx.Timeout(_PRIMARY_TIMEOUT),
            default_headers={
                "anthropic-beta": "token-efficient-tools-2025-02-19",
            },
        )
        # Build system prompt with cache_control on the static portion.
        # The system text and tool definitions are identical across calls,
        # so caching them saves ~90% on input token costs for those blocks.
        system_blocks = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        # Mark the last tool with cache_control so the entire tool list
        # is included in the cached prefix.
        cached_tools = [dict(t) for t in tools]
        if cached_tools:
            cached_tools[-1] = {
                **cached_tools[-1],
                "cache_control": {"type": "ephemeral"},
            }

        logger.info("Claude request using model=%s", model)
        response = claude_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_blocks,
            tools=cached_tools,
            messages=messages,
        )
        return ProviderResponse(
            content=response.content,
            stop_reason=response.stop_reason,
            provider="claude",
        ), "claude"

    except anthropic.APIStatusError as exc:
        # Only failover on server errors (500, 529 overloaded) — not client errors (400, 401)
        if exc.status_code < 500 and exc.status_code != 429:
            raise
        logger.warning("Claude server error (HTTP %d), failing over to OpenAI: %s", exc.status_code, exc)

    except anthropic.APITimeoutError:
        logger.warning("Claude timed out after %ds, failing over to OpenAI", _PRIMARY_TIMEOUT)

    except anthropic.APIConnectionError as exc:
        logger.warning("Claude connection error, failing over to OpenAI: %s", exc)

    # --- Try OpenAI (backup) ---
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key not configured — cannot failover")
        raise AllProvidersDownError("Primary AI failed and no backup API key configured")

    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0)
        openai_tools = _convert_tools_for_openai(tools)
        openai_messages = _convert_messages_for_openai(system, messages)

        openai_response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=max_tokens,
            messages=openai_messages,
            tools=openai_tools if openai_tools else None,
        )

        normalized = _normalize_openai_response(openai_response)
        logger.info("OpenAI backup responded successfully (model=%s)", OPENAI_MODEL)
        return normalized, "openai"

    except Exception as exc:
        logger.error("OpenAI backup also failed: %s", exc)
        raise AllProvidersDownError(f"Both Claude and OpenAI failed: {exc}") from exc
