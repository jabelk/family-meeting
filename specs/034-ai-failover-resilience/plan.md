# Implementation Plan: AI Failover & Resilience Improvements

**Branch**: `034-ai-failover-resilience` | **Date**: 2026-03-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/034-ai-failover-resilience/spec.md`

## Summary

Add OpenAI GPT as a backup AI provider when Claude is unavailable (500/529/timeout), strengthen tool failure reporting so users always know when something went wrong, add system prompt instructions for lost message detection and intent-vs-completion distinction for action items, and ensure proactive log diagnostics are integrated into all error paths. Most changes are in `src/assistant.py` (AI provider abstraction + tool result auditing) and `src/prompts/system/` (new prompt rules).

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK, openai SDK (new), httpx, PyYAML
**Storage**: JSON files in `data/` (existing pattern, unchanged)
**Testing**: pytest (`tests/`)
**Target Platform**: Linux server (Railway), macOS (local dev)
**Project Type**: Web service (FastAPI webhook)
**Performance Goals**: Failover within 5 seconds of detecting primary failure; 45-second primary timeout
**Constraints**: Single uvicorn worker (APScheduler requirement); core tool subset only on backup (~10 tools)
**Scale/Scope**: Single family (2 users), ~50 messages/day

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Uses OpenAI API (existing service) rather than building custom AI; leverages Axiom for diagnostics |
| II. Mobile-First Access | PASS | All changes are server-side; WhatsApp interface unchanged |
| III. Simplicity & Low Friction | PASS | Failover is automatic; no user action required. Prompt changes require zero user setup |
| IV. Structured Output | PASS | Error messages formatted as clear bullet points for WhatsApp |
| V. Incremental Value | PASS | Each user story is independently deployable. US2/US5 are partially done already |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/034-ai-failover-resilience/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── ai_provider.py           # NEW — AI provider abstraction (Claude primary, OpenAI backup)
├── assistant.py             # MODIFIED — use ai_provider instead of direct Anthropic client
├── tool_resilience.py       # MODIFIED — tool result string auditing for silent failures
├── log_diagnostics.py       # EXISTING — already implemented (minor enhancements)
├── integrations.py          # MODIFIED — add openai integration entry
├── config.py                # MODIFIED — add OPENAI_API_KEY, failover config
├── prompts/
│   ├── system/
│   │   ├── 02-response-rules.md  # MODIFIED — add rule for tool failure reporting
│   │   └── 11-resilience.md      # NEW — lost message detection + action item intent rules
│   └── tools/
│       └── context.md            # EXISTING — check_system_logs already there
└── app.py                   # MODIFIED — static fallback message when both AI providers down

tests/
├── test_ai_provider.py      # NEW — unit tests for failover logic
├── test_tool_resilience.py  # EXISTING — add tool result auditing tests
└── test_prompts.py          # MODIFIED — update tool/section counts
```

**Structure Decision**: Existing single-project structure. One new module (`ai_provider.py`) encapsulates the failover logic, keeping `assistant.py` focused on tool dispatch and conversation management.

## Architecture

### US1: AI Provider Failover

**New module: `src/ai_provider.py`**

Encapsulates AI provider selection and failover:

1. `create_message(system, tools, messages, max_tokens)` — main entry point
2. Attempts Claude first (45-second timeout via `anthropic` SDK `timeout` param)
3. On Claude failure (500, 529, overloaded error, timeout), catches exception and retries with OpenAI
4. OpenAI call uses `openai.OpenAI(api_key=OPENAI_API_KEY)` with `chat.completions.create()`
5. Tool definition conversion: Anthropic format → OpenAI format (rename `input_schema` → `parameters`, wrap in `{"type": "function", "function": {...}}`)
6. Response conversion: OpenAI response → Anthropic-like response object (normalize so `assistant.py` tool loop doesn't change)
7. Returns `(response, provider_used)` tuple so caller can append backup indicator

**Tool conversion for backup (core subset ~10 tools)**:
- `get_daily_context`, `get_calendar_events`, `create_quick_event`, `get_action_items`, `add_action_item`, `complete_action_item`, `save_preference`, `list_preferences`, `check_system_logs`, `get_family_profile`
- Defined as `BACKUP_TOOLS` constant in `ai_provider.py`

**Static fallback**: If both providers fail, `app.py` sends a hardcoded WhatsApp message directly (bypasses AI entirely).

### US2: Eliminate Silent Tool Failures

**Two-part fix**:

1. **Tool result string auditing** (`src/tool_resilience.py`): New function `audit_tool_result(tool_name, result_str)` that scans tool return strings for error patterns (`"error"`, `"unavailable"`, `"failed"`, `"not found"`, `"unauthorized"`) and prefixes them with a `TOOL WARNING:` instruction to Claude.

2. **Prompt reinforcement** (`src/prompts/system/02-response-rules.md`): Add explicit rule: "If ANY tool result contains an error, failure, or warning, you MUST mention it to the user. Never present a failed tool action as successful."

### US3: Lost Message Detection

**Prompt-only fix** (`src/prompts/system/11-resilience.md`): New system prompt section with instructions for detecting references to missing context. Patterns to recognize: "read my message", "did you get that", "what do you think about what I said", "so can you do that?" with no prior request. Instructions to respond with acknowledgment and resend request.

### US4: Premature Action Item Completion

**Prompt-only fix** (`src/prompts/system/11-resilience.md`): Add rules distinguishing intent from completion. Intent phrases ("I'm going to", "I'll do", "planning to", "need to") → acknowledge but do NOT call `complete_action_item`. Completion phrases ("done", "finished", "just did", "X is done") → call `complete_action_item`.

### US5: Proactive Log Diagnostics

**Already largely implemented** via `src/log_diagnostics.py` and `src/tool_resilience.py` (PRs #61, #62, #63). Remaining work:
- Ensure `check_system_logs` tool description in prompts encourages proactive use
- Verify diagnosis is included in all error paths (already done in `format_error_message` and `attempt_fallback`)
- Add prompt rule: "When any tool fails, use the diagnostic context to give specific guidance, not generic 'something went wrong'"

## Key Design Decisions

1. **Normalization approach for OpenAI responses**: Convert OpenAI responses to Anthropic-like format so the existing tool loop in `assistant.py` requires minimal changes. This avoids duplicating the 100-line tool dispatch loop.

2. **Core tool subset**: Only ~10 tools on backup. This keeps the OpenAI tool conversion simple and avoids edge cases with complex tools (YNAB, recipes, AnyList) that may not work well with a different AI model.

3. **Prompt-based fixes for US3/US4**: These are AI interpretation issues, not code bugs. System prompt instructions are the correct fix — no code-level intent classification needed.

4. **No new database/storage**: Failover state is per-request (stateless). No persistence needed for which provider is active.
