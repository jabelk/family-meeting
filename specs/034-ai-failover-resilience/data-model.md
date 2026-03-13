# Data Model: AI Failover & Resilience Improvements

## Entities

### AIProviderConfig

Configuration for an AI provider (primary or backup).

| Field | Type | Description |
|-------|------|-------------|
| name | str | Provider identifier: "claude" or "openai" |
| api_key_env | str | Environment variable name for API key |
| model | str | Model identifier (e.g., "claude-opus-4-20250514", "gpt-4o-mini") |
| timeout | int | Request timeout in seconds |
| max_tokens | int | Maximum response tokens |
| is_primary | bool | Whether this is the primary provider |

### ProviderResponse

Normalized response from either AI provider, consumed by the tool loop.

| Field | Type | Description |
|-------|------|-------------|
| content | list[ContentBlock] | Text and tool_use blocks (Anthropic-style format) |
| stop_reason | str | "end_turn" or "tool_use" |
| provider | str | Which provider generated this response ("claude" or "openai") |

### ContentBlock (union type)

| Variant | Fields | Description |
|---------|--------|-------------|
| TextBlock | type="text", text: str | Text content from the AI |
| ToolUseBlock | type="tool_use", id: str, name: str, input: dict | Tool call request |

### ToolAuditResult

Result of auditing a tool's return string for hidden errors.

| Field | Type | Description |
|-------|------|-------------|
| is_error | bool | Whether the result string contains error indicators |
| original_result | str | The raw tool return string |
| audit_message | str | Warning prefix if error detected, empty otherwise |

## Relationships

- `AIProviderConfig` → used by `ai_provider.py` to initialize clients
- `ProviderResponse` → consumed by `assistant.py` tool loop (replaces raw Anthropic response)
- `ToolAuditResult` → produced by `tool_resilience.py`, consumed by tool loop in `assistant.py`

## State Transitions

### AI Provider Failover (per-request, stateless)

```
[Request arrives]
    → Try Claude (primary, 45s timeout)
        → Success → return ProviderResponse(provider="claude")
        → Failure (500/529/timeout/connection) → Try OpenAI (backup, 30s timeout)
            → Success → return ProviderResponse(provider="openai")
            → Failure → return static error message (bypass AI entirely)
```

No persistent state — each request starts fresh with the primary provider.
