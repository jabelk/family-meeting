# Research: AI Failover & Resilience Improvements

## R1: OpenAI Tool-Calling Format Conversion

**Decision**: Use OpenAI Chat Completions API (`client.chat.completions.create()`) with tool-calling, converting Anthropic tool definitions at call time.

**Rationale**: Chat Completions is the mature, widely-adopted API that maps most closely to Anthropic's patterns. The newer Responses API has different conventions that would add complexity.

**Alternatives considered**:
- OpenAI Responses API — newer but less documented, different ID conventions
- Google Gemini — tool-calling interface is less mature, more format differences

**Key conversion points**:
| Aspect | Anthropic | OpenAI |
|--------|-----------|--------|
| Tool schema key | `input_schema` | `parameters` (nested under `function`) |
| Tool wrapper | Flat dict | `{"type": "function", "function": {...}}` |
| System prompt | Separate `system=` param | `{"role": "system"}` in messages |
| Stop signal | `response.stop_reason == "tool_use"` | Check `message.tool_calls` is truthy |
| Tool args | `block.input` (already dict) | `tool_call.function.arguments` (JSON string, needs `json.loads()`) |
| Tool result role | `role: "user"` with `tool_result` blocks | `role: "tool"` with `tool_call_id` |

## R2: Anthropic SDK Error Classification for Failover

**Decision**: Catch specific Anthropic SDK exceptions to trigger failover: `anthropic.APIStatusError` (status 500, 529), `anthropic.APITimeoutError`, `anthropic.APIConnectionError`.

**Rationale**: These are the exact error types that indicate Claude is down vs. a client-side issue. Status 529 is Anthropic's "overloaded" code. 4xx errors (bad request, auth) should NOT trigger failover.

**Alternatives considered**:
- Catch all exceptions — too broad, would mask client bugs
- HTTP status only — misses timeout and connection errors

## R3: OpenAI Model Selection for Backup

**Decision**: Use `gpt-4o-mini` as the backup model.

**Rationale**: Cost-effective, fast, supports tool-calling well. For a backup that handles basic family assistant tasks during outages, full GPT-4o is overkill. `gpt-4o-mini` provides good tool-calling accuracy at ~10x lower cost.

**Alternatives considered**:
- `gpt-4o` — more capable but higher cost and latency for a backup
- `gpt-4.1-mini` / `gpt-4.1-nano` — newer models but gpt-4o-mini is proven and stable

## R4: Tool Result Auditing Patterns

**Decision**: Pattern-match tool return strings for known error indicators before passing to Claude.

**Rationale**: Some tools return error strings (not exceptions) that Claude may interpret as success. Examples: `"Error: currently unavailable"`, `"Failed to create event"`, `"Unauthorized"`. A simple substring check catches these.

**Error patterns to detect**:
- Starts with "Error:" or "TOOL FAILED:"
- Contains "unavailable", "failed", "unauthorized", "forbidden"
- Contains "not found" when tool was expected to create/update
- Returns empty string when non-empty expected

## R5: Lost Message Detection Approach

**Decision**: Prompt-based detection using system prompt instructions.

**Rationale**: The AI already has conversation context. Adding a system prompt rule to check for references to missing messages is simpler and more flexible than code-level pattern matching. The AI can understand nuanced phrasings better than regex.

**Alternatives considered**:
- Code-level message gap detection (track message IDs) — WhatsApp doesn't guarantee sequential delivery
- Separate classification step — adds latency for marginal benefit

## R6: Action Item Completion Intent Detection

**Decision**: Prompt-based intent vs. completion distinction.

**Rationale**: Per spec assumption, this is an AI interpretation issue best solved by clear prompt instructions. The AI processes natural language and can distinguish "I'm going to do X" from "I did X" with proper guidance.

**Key phrases**:
- Intent (do NOT complete): "I'm going to", "I'll do", "planning to", "need to", "going to", "I'm about to"
- Completion (DO complete): "done", "finished", "just did", "completed", "X is done", "took care of"
