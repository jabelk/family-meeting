# Quickstart: AI Failover & Resilience Improvements

## Prerequisites

- Python 3.12
- Existing family-meeting codebase running
- `ANTHROPIC_API_KEY` set (existing)
- `OPENAI_API_KEY` set (new — required for US1)
- `AXIOM_QUERY_TOKEN` set (existing — for US5)

## Test Scenarios

### US1: AI Provider Failover

**Unit test** (mock-based):
1. Mock `anthropic.Anthropic.messages.create` to raise `anthropic.APIStatusError(status_code=529)`
2. Verify `ai_provider.create_message()` calls OpenAI as fallback
3. Verify response is normalized to Anthropic-like format
4. Verify `provider_used` is "openai"

**Unit test — both providers down**:
1. Mock both providers to raise errors
2. Verify static error message is returned

**Integration test** (live, manual):
1. Temporarily set `ANTHROPIC_API_KEY` to an invalid value
2. Send a WhatsApp message
3. Verify response arrives (via OpenAI backup)
4. Verify response includes "Note: using backup assistant"

### US2: Silent Tool Failures

**Unit test**:
1. Call `audit_tool_result("create_quick_event", "Error: currently unavailable")`
2. Verify returns `is_error=True` with warning prefix

**Unit test — normal result**:
1. Call `audit_tool_result("get_calendar_events", "[{event data}]")`
2. Verify returns `is_error=False`

**Integration test** (live):
1. Trigger a calendar failure (e.g., expired token)
2. Verify bot response explicitly mentions the failure

### US3: Lost Message Detection

**Integration test** (live):
1. Send "read the message I just sent" as first message of the day
2. Verify bot acknowledges it may have missed a message and asks to resend
3. Send "what do you think about what I said?" with no prior context
4. Verify similar acknowledgment

**Negative test**:
1. Send "what's for dinner tonight?" then "what do you think about that?"
2. Verify bot responds normally (no false positive)

### US4: Premature Action Item Completion

**Integration test** (live):
1. Ensure a "blood draw" action item exists in Notion
2. Send "I'm getting my blood draw this afternoon"
3. Verify action item is NOT marked complete
4. Send "done with the blood draw"
5. Verify action item IS marked complete

### US5: Proactive Diagnostics

**Integration test** (live):
1. Trigger a tool failure
2. Verify bot response includes specific diagnostic info (not generic)
3. Ask "can you check the system logs?"
4. Verify bot calls `check_system_logs` and reports findings

## Environment Setup

```bash
# Add to .env
OPENAI_API_KEY=sk-...  # OpenAI API key for backup provider

# Existing (should already be set)
ANTHROPIC_API_KEY=sk-ant-...
AXIOM_QUERY_TOKEN=xaat-...
AXIOM_DATASET=railway-logs
```

## Validation Checklist

- [ ] Claude outage → OpenAI responds with core tools
- [ ] Both providers down → static "try again later" message
- [ ] Tool error string → bot tells user what failed
- [ ] "Read my last message" → bot asks to resend
- [ ] "I'm going to do X" → action item stays open
- [ ] "Done with X" → action item marked complete
- [ ] Tool failure → response includes specific diagnosis
