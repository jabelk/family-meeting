# Implementation Plan: Chat Memory & Conversation Persistence

**Branch**: `007-chat-memory` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-chat-memory/spec.md`

## Summary

Mom Bot currently treats every WhatsApp message as independent — each `handle_message()` call creates a fresh `messages = [{"role": "user", "content": ...}]` with no history. This means follow-up questions like "tell me more about number 2" or "swap Wednesday for tacos" fail because Claude has no context from the previous exchange.

The fix: store conversation history per phone number in a JSON file (`data/conversations.json`), load it before each API call, and save it after. History expires after 30 minutes of inactivity and is capped at 10 conversation turns. Anthropic SDK content blocks are serialized via `model_dump()` for JSON storage. Image data is replaced with text placeholders to manage file size.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK (Claude Opus), Pydantic (via anthropic SDK)
**Storage**: JSON file in `data/` directory (same pattern as `data/usage_counters.json`), Docker volume mount already configured
**Testing**: Manual validation via SSH + docker compose exec (no automated tests)
**Target Platform**: Linux server (NUC), Docker Compose
**Project Type**: Web service (WhatsApp bot backend)
**Performance Goals**: Bot response time increase ≤2 seconds with 5 prior messages in history
**Constraints**: Context window budget: ~15K tokens (system prompt + tools) + ~30K tokens (10 turns of history) = ~45K of 200K available
**Scale/Scope**: 2 users (Jason and Erin), minimal storage, ~50K tokens max per API call

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Uses existing Claude API conversation format — no new services |
| II. Mobile-First Access | PASS | Enhances existing WhatsApp interface, transparent to users |
| III. Simplicity & Low Friction | PASS | Zero user setup, conversation memory works automatically |
| IV. Structured Output | N/A | Feature is about context passing, not output format |
| V. Incremental Value | PASS | US1 (follow-ups) delivers standalone value; US2/US3 layer on |

No violations. Complexity tracking not needed.

## Key Decisions

### 1. Storage Mechanism
- **Decision**: JSON file in `data/` directory with in-memory cache
- **Rationale**: Proven pattern from `discovery.py` usage counters, Docker volume mount already exists, 2 users means minimal data
- **Alternatives rejected**: SQLite (overkill, adds dependency), Redis (new service), pure in-memory (no restart persistence)

### 2. History Format
- **Decision**: Store full Claude API message format (user/assistant/tool_use/tool_result)
- **Rationale**: Claude sees exact same context it had — no information loss for follow-ups like "number 2" or "save that one". Serialized via Pydantic's `model_dump(mode="json")`
- **Alternatives rejected**: Text-only summaries (loses tool context, breaks "number 2" references), structured summaries (complex to build, still lossy)

### 3. History Size Limit
- **Decision**: Cap at 10 conversation turns (1 turn = user message → complete bot response including all tool loops)
- **Rationale**: 10 turns × ~3K tokens avg = ~30K tokens. Combined with system prompt + tools (~15K), total ~45K is well within 200K context. Covers complex multi-step workflows.
- **Alternatives rejected**: Token counting (complex, adds dependency for tokenizer), unlimited (expensive, could hit limits), 5 turns (too few for recipe→details→save→grocery workflows)

### 4. Image Handling in History
- **Decision**: Replace base64 image data with text placeholder `"[Image sent: photo]"` when storing
- **Rationale**: Images are 100K+ bytes each, already processed by Claude in the original turn, follow-ups reference the text output not the raw image
- **Alternatives rejected**: Store full images (huge storage), omit entirely (loses context about what was sent)

### 5. Conversation Expiry
- **Decision**: 30-minute inactivity timeout, configurable constant
- **Rationale**: Most WhatsApp follow-ups happen within minutes; 30 min covers extended sessions without stale context
- **Alternatives rejected**: 1 hour (stale context risk), 15 min (too short for distracted parents), no expiry (old topics leak into new ones)

### 6. Module Architecture
- **Decision**: New `src/conversation.py` module (not in `tools/` — it's infrastructure, not a tool)
- **Rationale**: Keeps conversation storage concerns (serialization, expiry, file I/O) separate from assistant.py. Constitution says "fewer files" but assistant.py is already 1118 lines and conversation storage is a distinct concern (~80-100 lines).
- **Alternatives rejected**: All in assistant.py (would grow assistant.py to 1200+ lines, mixing concerns)

## Project Structure

### Documentation (this feature)

```text
specs/007-chat-memory/
├── plan.md              # This file
├── research.md          # Phase 0: research decisions
├── data-model.md        # Phase 1: conversation/message entities
├── quickstart.md        # Phase 1: manual test scenarios
├── contracts/
│   └── conversation-module.md  # Internal module contract
└── tasks.md             # Phase 2: task breakdown (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── assistant.py         # MODIFIED: load/save history in handle_message()
├── conversation.py      # NEW: conversation history storage & management
└── tools/
    └── discovery.py     # (unchanged — existing persistence pattern reference)

data/
├── .gitkeep             # (existing)
├── usage_counters.json  # (existing — feature discovery)
└── conversations.json   # NEW: per-phone conversation history
```

**Structure Decision**: Single new file (`src/conversation.py`) plus modifications to `src/assistant.py`. The `data/` directory and Docker volume mount already exist from feature 006. No new infrastructure needed.

## Implementation Phases

### Phase 1: Conversation Storage Module
- Create `src/conversation.py` with in-memory dict + JSON file persistence
- Functions: `get_history()`, `save_turn()`, `_is_expired()`, `_serialize_content()`, `_strip_images()`, `_trim_history()`
- Follow atomic write pattern from `discovery.py`

### Phase 2: History Integration in handle_message()
- Modify `src/assistant.py` to import conversation module
- Before API call: load history, check expiry, prepend to messages
- After API call: serialize and save the new turn
- Skip history for `sender_phone == "system"` (automated messages)

### Phase 3: Polish & Validation
- Test follow-up scenarios on NUC
- Verify expiry works correctly
- Verify restart persistence
- Tune conversation turn limit if needed
