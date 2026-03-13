# Implementation Plan: Port AI Failover & Resilience to Downstream Repos

**Branch**: `035-port-failover-downstream` | **Date**: 2026-03-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/035-port-failover-downstream/spec.md`

## Summary

Port the AI failover & resilience patterns from family-meeting feature 034 to two downstream repos: **client-scc-tom-construction** (production app — new `ai_provider.py` module, tool result auditing, prompt rules) and **claude-speckit-template** (scaffolding — template files with customization comments). The SCC app adapts the pattern for its service-based architecture with 5 distinct Claude functions (classify, parse receipt, generate caption, paired caption, suggest category), including vision/image format conversion and forced tool_choice support.

## Technical Context

**Language/Version**: Python 3.11+ (SCC app), language-agnostic (template)
**Primary Dependencies**: anthropic SDK, openai SDK (new for SCC), FastAPI, python-quickbooks, twilio, tenacity
**Storage**: SQLite (SCC — conversations, pending actions, job aliases); N/A (template)
**Testing**: pytest + pytest-asyncio (SCC); N/A (template)
**Target Platform**: Railway (Linux server) for SCC; GitHub template for speckit
**Project Type**: Cross-repo refactoring — web-service (SCC) + template scaffolding
**Performance Goals**: <60s failover response, no latency change on primary path
**Constraints**: SCC has 5 vision-capable Claude functions that must all fail over; template must be opt-in (not break non-AI projects)
**Scale/Scope**: 2 repos, ~15 files modified/created across both

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Leverages existing OpenAI API — no custom AI built |
| II. Mobile-First Access | PASS | No change to user-facing interface (SMS for SCC, WhatsApp for family-meeting) |
| III. Simplicity & Low Friction | PASS | Failover is transparent — zero user action required |
| IV. Structured Output | N/A | No meeting output changes |
| V. Incremental Value | PASS | Each user story is independently deployable |

**Post-design re-check**: All gates still pass. The centralized `ai_provider.py` adds one file per repo but reduces overall complexity vs. inline failover in every function.

## Project Structure

### Documentation (this feature)

```text
specs/035-port-failover-downstream/
├── plan.md              # This file
├── research.md          # Phase 0: OpenAI vision, tool_choice, format conversion
├── data-model.md        # Phase 1: Entity descriptions for both repos
├── quickstart.md        # Phase 1: E2E validation scenarios
└── tasks.md             # Phase 2: Task breakdown (via /speckit.tasks)
```

### Source Code Changes

**Repo 1: client-scc-tom-construction** (`/Users/jabelk/dev/projects/client-scc-tom-construction/`)

```text
src/
├── services/
│   ├── ai_provider.py      # NEW — centralized failover (Claude → OpenAI)
│   ├── claude_svc.py        # MODIFIED — delegate to ai_provider.py
│   ├── router_svc.py        # MODIFIED — catch AllProvidersDownError
│   └── health_svc.py        # MODIFIED — add backup provider health check
├── config.py                # MODIFIED — add OPENAI_API_KEY, OPENAI_MODEL
├── prompts/system/
│   └── 05-resilience.md     # NEW — error reporting + diagnostic rules
├── main.py                  # UNCHANGED

tests/unit/
├── test_ai_provider.py      # NEW — failover, format conversion, both-down
├── test_graceful_degradation.py  # MODIFIED — add failover scenarios
```

**Repo 2: claude-speckit-template** (`/Users/jabelk/dev/projects/claude-speckit-template/`)

```text
src/
├── services/
│   └── ai_provider.py      # NEW — template with placeholders + comments
├── prompts/system/
│   └── 05-resilience.md     # NEW — template resilience rules

CLAUDE.md                    # MODIFIED — add resilience architecture section
```

**Structure Decision**: SCC follows its existing `src/services/` layout. The new `ai_provider.py` sits alongside `claude_svc.py` as a peer service. Template repo mirrors this structure with placeholder files.

## Architecture: SCC ai_provider.py

### Public API (5 functions matching claude_svc.py)

```python
def classify_intent(message, conversation_history, active_jobs) -> dict
def parse_receipt(image_data, media_type) -> dict
def generate_social_caption(photo_data, media_type, context) -> str
def generate_paired_caption(before_data, after_data, media_type, context) -> str
def suggest_category(vendor, line_items, available_categories) -> dict
```

Each function: tries Claude first (45s timeout) → catches 500/529/timeout/connection → retries with OpenAI GPT-4o-mini (30s timeout) → raises `AllProvidersDownError` if both fail.

### Key Conversion Patterns

**Image format** (Anthropic → OpenAI):
```
Anthropic: {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}
OpenAI:    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{b64}"}}
```

**Forced tool_choice** (Anthropic → OpenAI):
```
Anthropic: {"type": "tool", "name": "classify_message"}
OpenAI:    {"type": "function", "function": {"name": "classify_message"}}
```

**Tool definitions** (same as family-meeting):
```
Anthropic: {"name": ..., "description": ..., "input_schema": {...}}
OpenAI:    {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
```

### Failover Integration Points

| Component | Change | Why |
|-----------|--------|-----|
| `claude_svc.py` | Functions become thin delegates to `ai_provider.py` | Centralize failover logic |
| `router_svc.py` | Catch `AllProvidersDownError` → `_build_fallback_message()` | Preserve existing UX |
| `health_svc.py` | Add `check_openai_health()` | Monitor backup availability |
| `config.py` | Add `OPENAI_API_KEY`, `OPENAI_MODEL` | Configure backup provider |
| `05-resilience.md` | New system prompt section | Error transparency rules |

## Complexity Tracking

No constitution violations. The centralized module pattern adds one file but replaces what would otherwise be duplicated failover blocks in 5 functions.
