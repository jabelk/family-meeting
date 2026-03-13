# Quickstart: Port AI Failover & Resilience — E2E Validation

## Prerequisites

- Both repos cloned locally:
  - `/Users/jabelk/dev/projects/client-scc-tom-construction/`
  - `/Users/jabelk/dev/projects/claude-speckit-template/`
- `OPENAI_API_KEY` set in SCC `.env`
- `ANTHROPIC_API_KEY` set in SCC `.env`
- SCC test suite passes: `uv run pytest tests/ -v`

## Scenario 1: SCC — Claude Primary Path (No Failover)

**Goal**: Verify normal operation is unchanged after refactoring.

1. Start SCC dev server: `uv run uvicorn src.main:app --reload --port 8000`
2. Send a test SMS via Twilio webhook (or use test script)
3. **Verify**: Response comes from Claude (check logs for provider="claude")
4. **Verify**: Intent classification, receipt parsing, and caption generation all work normally
5. **Verify**: No latency regression (response time within normal range)

## Scenario 2: SCC — Failover to OpenAI on Claude 529

**Goal**: Verify automatic failover when Claude is overloaded.

1. Create `test_failover_live.py` in SCC repo (mirrors family-meeting's pattern)
2. Patch `anthropic.Anthropic` to raise `APIStatusError(529)`
3. Call `ai_provider.classify_intent()` with a test message
4. **Verify**: Response comes from OpenAI (provider="openai")
5. **Verify**: Intent classification returns valid structured data
6. **Verify**: Entities are correctly extracted

## Scenario 3: SCC — Vision Failover (Receipt Parsing)

**Goal**: Verify receipt parsing works on OpenAI backup.

1. Patch Claude to fail with 529
2. Call `ai_provider.parse_receipt()` with a test receipt image
3. **Verify**: Receipt is parsed via OpenAI with vision
4. **Verify**: Response includes vendor, date, total, line_items
5. **Verify**: Image format was correctly converted (base64 → data URI)

## Scenario 4: SCC — Vision Failover (Social Caption)

**Goal**: Verify caption generation works on OpenAI backup.

1. Patch Claude to fail with 529
2. Call `ai_provider.generate_social_caption()` with a test photo
3. **Verify**: Caption is generated via OpenAI with vision
4. **Verify**: Caption includes text + hashtags

## Scenario 5: SCC — Both Providers Down

**Goal**: Verify graceful degradation when all AI is unavailable.

1. Patch both Claude and OpenAI to fail
2. Call `ai_provider.classify_intent()` — should raise `AllProvidersDownError`
3. **Verify**: `router_svc.py` catches the error and returns `_build_fallback_message()`
4. **Verify**: Fallback message lists keyword commands
5. **Verify**: Pending actions are still accessible via keywords

## Scenario 6: SCC — Tool Result Auditing

**Goal**: Verify error detection in service call results.

1. Simulate a QuickBooks API error during expense creation
2. **Verify**: Error is detected and surfaced in the response to the user
3. **Verify**: Response includes specific diagnostic context (e.g., "QuickBooks auth expired")
4. **Verify**: Error is logged with structured context

## Scenario 7: SCC — Resilience Prompt Rules

**Goal**: Verify Claude follows error reporting rules.

1. Trigger a tool failure in a conversation
2. **Verify**: Claude mentions the specific failure in its response
3. **Verify**: Claude provides actionable guidance (not vague "something went wrong")

## Scenario 8: Template — Scaffolding Verification

**Goal**: Verify template files exist and are well-structured.

1. Check `/Users/jabelk/dev/projects/claude-speckit-template/src/services/ai_provider.py` exists
2. **Verify**: Contains `{{PLACEHOLDER}}` patterns and customization comments
3. **Verify**: Contains example failover functions with format converters
4. Check `src/prompts/system/05-resilience.md` exists
5. **Verify**: Contains template resilience rules with `{{BUSINESS_NAME}}`
6. Check CLAUDE.md has resilience architecture section
7. **Verify**: Section describes the ai_provider pattern and customization steps

## Scenario 9: SCC — Full Test Suite Regression

**Goal**: Verify zero regressions.

1. Run `uv run pytest tests/ -v` in SCC repo
2. **Verify**: All existing tests pass
3. **Verify**: New `test_ai_provider.py` tests pass
4. Run `uv run ruff check src/ tests/` — clean
5. Run `uv run ruff format --check src/ tests/` — clean

## Scenario 10: SCC — Deploy and Health Check

**Goal**: Verify production deployment.

1. Set `OPENAI_API_KEY` on Railway
2. Deploy to Railway
3. **Verify**: `GET /health` returns healthy with backup provider info
4. Send a test SMS through production
5. **Verify**: Response received normally (primary path)
