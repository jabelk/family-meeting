# Quickstart: Tool Failure Resilience

## Test Scenarios

### Scenario 1: Transient failure retries automatically (US1)

**Setup**: Mock `create_quick_event` to raise `httpx.TimeoutException` on first call, succeed on second.

**Steps**:
1. Call the tool execution path with a `create_quick_event` tool use
2. First attempt raises timeout
3. System waits 1 second, retries
4. Second attempt succeeds

**Expected**: User receives successful calendar event response. No error visible. Log shows 1 retry.

### Scenario 2: Permanent failure reports clearly (US2)

**Setup**: Mock `create_quick_event` to raise `httpx.HTTPStatusError(403)` (non-retryable).

**Steps**:
1. Call the tool execution path with a `create_quick_event` tool use
2. Exception classified as NON_RETRYABLE
3. Error message returned to Claude with integration name and failure reason

**Expected**: Error message contains "Google Calendar" (not "google_calendar"), states the action was NOT completed, instructs Claude to tell the user and suggest alternatives. No retry attempted.

### Scenario 3: Fallback to Notion action item (US3)

**Setup**: Mock `create_quick_event` to raise `httpx.TimeoutException` on all attempts (exhausts retries).

**Steps**:
1. Tool fails on all 3 attempts (initial + 2 retries)
2. System looks up fallback mapping: `create_quick_event` → `add_action_item`
3. System executes `add_action_item` with equivalent parameters
4. Fallback succeeds

**Expected**: Error message tells Claude that Calendar is down but an action item was created as a fallback. User is informed of the degraded path.

### Scenario 4: Fallback itself fails — WhatsApp last resort (US3)

**Setup**: Mock both `create_quick_event` and `add_action_item` to fail.

**Steps**:
1. Primary tool exhausts retries
2. Fallback tool fails
3. Error message instructs Claude to send details via WhatsApp message

**Expected**: Error message includes the full event details (title, date, time) and instructs Claude to relay them directly in the chat message as a last resort.

### Scenario 5: Input error — no retry (US1, edge case)

**Setup**: Tool raises `ValueError("Invalid date format")`.

**Steps**:
1. Exception classified as INPUT_ERROR
2. No retry attempted
3. Error message tells Claude this is an input issue

**Expected**: Error message says input was invalid, not that the service is down. No retry, no fallback.

### Scenario 6: Exception classification correctness

**Setup**: Unit test with various exception types.

**Cases**:
- `httpx.TimeoutException` → RETRYABLE
- `httpx.ConnectError` → RETRYABLE
- `httpx.HTTPStatusError(500)` → RETRYABLE
- `httpx.HTTPStatusError(429)` → RETRYABLE
- `httpx.HTTPStatusError(403)` → NON_RETRYABLE
- `googleapiclient.errors.HttpError(503)` → RETRYABLE
- `googleapiclient.errors.HttpError(404)` → NON_RETRYABLE
- `ValueError` → INPUT_ERROR
- `json.JSONDecodeError` → INPUT_ERROR
- `RuntimeError` (unknown) → NON_RETRYABLE

### Scenario 7: Reverse integration lookup

**Setup**: Unit test `get_integration_for_tool()`.

**Cases**:
- `"create_quick_event"` → `"Google Calendar"`
- `"add_action_item"` → `"Notion"`
- `"push_grocery_list"` → `"AnyList"`
- `"get_budget_summary"` → `"YNAB"`
- `"unknown_tool"` → `"Unknown"`

### Scenario 8: Retry timing

**Setup**: Mock tool to fail 3 times, measure elapsed time.

**Expected**: Total elapsed time ≥ 3 seconds (1s + 2s delays), < 5 seconds (no excessive delay).

## Integration Points

- **`src/assistant.py`**: The catch-all at lines 1853-1855 is replaced with a call to the resilience module
- **`src/integrations.py`**: New `get_integration_for_tool()` function builds reverse map from `INTEGRATION_REGISTRY`
- **`src/tool_resilience.py`**: New module containing all resilience logic — imported by `assistant.py`
