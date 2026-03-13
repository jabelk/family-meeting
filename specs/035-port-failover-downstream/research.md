# Research: Port AI Failover & Resilience to Downstream Repos

## 1. OpenAI Vision API Format

**Decision**: Use OpenAI's `image_url` format with data URI for base64 images.

**Rationale**: GPT-4o-mini fully supports vision input. The conversion from Anthropic's `source.data` base64 to OpenAI's data URI is straightforward — wrap the base64 data in `data:{mime_type};base64,{data}`.

**Conversion**:
- Anthropic: `{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}`
- OpenAI: `{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{b64}"}}`

**Alternatives considered**:
- Upload images to a URL first → unnecessary complexity, adds storage dependency
- Skip vision on backup → rejected per clarification (always attempt vision)

## 2. OpenAI Forced tool_choice

**Decision**: Convert Anthropic's `{"type": "tool", "name": "..."}` to OpenAI's `{"type": "function", "function": {"name": "..."}}`.

**Rationale**: OpenAI GPT-4o-mini fully supports forced function calling. All three SCC forced-tool patterns (classify_message, extract_receipt, generate_caption) will work identically on OpenAI.

**Conversion mapping**:
- `{"type": "tool", "name": "X"}` → `{"type": "function", "function": {"name": "X"}}`
- `{"type": "any"}` → `"required"`
- `{"type": "auto"}` → `"auto"`
- `None` → `None` (omit parameter)

**Alternatives considered**:
- Use `response_format` for structured output → doesn't support function calling semantics
- Prompt-only approach without tool_choice → lower reliability for entity extraction

## 3. SCC Architecture Analysis

**Decision**: New centralized `src/services/ai_provider.py` with 5 public functions mirroring `claude_svc.py`.

**Rationale**: Per clarification, Option A (centralized module) chosen for multi-client reuse. The module exposes the same function signatures as `claude_svc.py` so callers don't change. Internally, each function implements the try-Claude/catch/try-OpenAI/catch/raise pattern with appropriate format conversions.

**Current SCC architecture**:
- `claude_svc.py`: 5 functions, each creates messages directly via `anthropic.Anthropic` singleton
- `router_svc.py`: Calls `claude_svc.classify_intent()` with try/except, falls back to `_build_fallback_message()`
- Error handling: QBO uses tenacity retries; Claude calls have no retry/failover
- Health check: Claude only checks env var (no API ping)

**Integration approach**:
1. `ai_provider.py` contains all provider logic + format converters
2. `claude_svc.py` becomes thin wrappers that call `ai_provider.py`
3. `router_svc.py` catches `AllProvidersDownError` → `_build_fallback_message()`
4. No changes to `twilio.py` or `main.py` (error handling already propagates)

**Alternatives considered**:
- Inline failover in each claude_svc function (Option B) → code duplication across 5 functions, compounds across client projects
- Client factory (Option C) → doesn't work because Anthropic and OpenAI have fundamentally different APIs

## 4. GPT-4o-mini Vision Capability

**Decision**: Use `gpt-4o-mini` as the backup model for all functions including vision.

**Rationale**: GPT-4o-mini supports vision input at $0.15/1M input tokens — cheapest vision-capable OpenAI model. Receipt parsing and caption generation will work on the backup provider without model switching.

**Alternatives considered**:
- `gpt-4.1-nano` ($0.10/1M) — slightly cheaper, newer (April 2025), but less battle-tested
- `gpt-4o` ($2.50/1M) — overkill for failover backup at 16x the cost
- Separate models for vision vs text — unnecessary complexity since gpt-4o-mini handles both

## 5. Template Repo Approach

**Decision**: Add opt-in scaffolding files with `{{PLACEHOLDER}}` patterns and detailed comments.

**Rationale**: Template repo has no production code. Adding real Python files with placeholder patterns lets new projects customize rather than implement from scratch. Files are clearly marked as templates with customization instructions.

**Files to add**:
- `src/services/ai_provider.py` — template with 2 example functions, all conversion logic, placeholder model names
- `src/prompts/system/05-resilience.md` — template resilience rules with `{{BUSINESS_NAME}}` / `{{OWNER_NAME}}` placeholders
- CLAUDE.md update — resilience architecture section

**Alternatives considered**:
- Documentation only (no template files) → developers would rewrite from scratch each time
- Full working code → impossible in a language-agnostic template
