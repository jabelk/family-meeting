# Research: Chat Memory & Conversation Persistence

## R1: Conversation History Storage Strategy

**Decision**: JSON file in `data/conversations.json` with in-memory cache, following the atomic write pattern from `discovery.py`.

**Rationale**: The project already uses this pattern for `data/usage_counters.json` — in-memory dict loaded at module import, saved atomically (write to `.tmp` then `rename()`) after each update. The `data/` directory already has a Docker volume mount (`./data:/app/data` in `docker-compose.yml`), so persistence across container restarts is already solved. For 2 users with ~10 turns of history each, the file will be <100KB.

**Alternatives considered**:
1. SQLite — Adds a new dependency, overkill for 2 users and ephemeral (30-min expiry) data. Would be appropriate at 10+ users or if we needed query capabilities.
2. Redis — Adds a new Docker service. Great for TTL-based expiry but massive overkill for 2 users.
3. Pure in-memory (no file) — Simple but violates FR-009 (must persist across restarts). A mid-conversation deploy would break Erin's flow.
4. Per-phone files (`conversations_{phone}.json`) — More isolated but adds file management complexity. A single file is fine at this scale.

## R2: Anthropic SDK Content Block Serialization

**Decision**: Use Pydantic's `model_dump(mode="json", exclude_unset=True)` to serialize `response.content` blocks (TextBlock, ToolUseBlock) for JSON storage. When loading history, the plain dicts are passed directly to `client.messages.create()` — the Anthropic SDK accepts both object instances and dict representations.

**Rationale**: The Anthropic Python SDK (>=0.42.0) uses Pydantic v2 BaseModel for all content block types. `model_dump(mode="json")` produces clean, JSON-serializable dicts with proper type discriminators:
- TextBlock → `{"type": "text", "text": "..."}`
- ToolUseBlock → `{"type": "tool_use", "id": "...", "name": "...", "input": {...}}`

Tool result messages are already plain dicts in the current code (`{"type": "tool_result", "tool_use_id": "...", "content": "..."}`), so they need no special serialization.

**Key finding**: Line 1096 in assistant.py appends `response.content` (Pydantic objects) directly. For storage, we serialize with `model_dump()`. For loading, the Anthropic API accepts dicts matching the content block schema — no deserialization back to Pydantic objects needed.

## R3: History Size Management

**Decision**: Cap at 10 conversation turns. One "turn" = one user message through to the complete bot response (including all tool call loops within that response). This means the `messages` array might have 4-6 entries per turn (user → assistant-with-tools → tool-results → assistant-with-tools → tool-results → final-assistant), but we count by logical turns, not raw message entries.

**Rationale**: Token budget analysis:
- System prompt: ~5K tokens
- Tool definitions (40+ tools): ~10K tokens
- Per turn (avg): ~3K tokens (user message ~200, tool calls ~1K, tool results ~1K, bot response ~800)
- 10 turns: ~30K tokens
- **Total per API call: ~45K tokens** — well within Claude Opus's 200K context window
- Cost impact: ~3x increase per message (from ~15K to ~45K input tokens). Acceptable for 2 users with moderate usage.

**Alternatives considered**:
1. Token-based limit (e.g., 50K tokens for history) — More precise but requires a tokenizer dependency or estimation logic. Unnecessary complexity for 2 users.
2. 5 turns — Too few. A recipe workflow (search → details → save → grocery list → push to AnyList) is 5 turns by itself.
3. 20 turns — Wastes tokens on stale context. Most useful conversations are 3-8 turns.

## R4: Image Handling in Stored History

**Decision**: When saving a conversation turn to history, replace any base64 image content blocks with a text placeholder: `"[Image sent: photo]"`. The image's visual content is already captured in Claude's text response from that turn, which IS stored.

**Rationale**: Recipe photos are typically 100-500KB base64 each. Storing even 2 images would make the conversations file 1MB+, and loading that into every subsequent API call would waste tokens on data Claude already processed. The module-level `_buffered_images` variable in assistant.py handles within-session image accumulation; conversation history doesn't need the raw data.

**Edge case**: If Erin sends a photo, then a follow-up text message in the same conversation, Claude will see its own previous text description of the photo in history — sufficient for follow-ups like "save that recipe" or "what cookbook is that from?".

## R5: Interaction with Existing Module-Level State

**Decision**: Conversation history replaces the need for module-level state like `_last_search_results` in downshiftology.py. However, we will NOT modify the existing module-level state in this feature — both mechanisms will coexist. The conversation history provides Claude with the context to understand follow-ups, while module-level state provides the actual data for tool execution.

**Rationale**: The existing `_last_search_results` in downshiftology.py stores the actual recipe data needed by `get_downshiftology_details(result_number)`. When Erin says "tell me more about number 2", Claude needs to call this tool with `result_number=2`. The tool itself looks up `_last_search_results[1]`. Conversation history gives Claude the context to know that "number 2" refers to a Downshiftology search, but the tool still needs the cached data. Both systems serve different purposes:
- **Conversation history**: Gives Claude conversational context (what was discussed)
- **Module-level state**: Gives tool functions operational data (what to look up)

This avoids a risky refactor of the tool modules while delivering the conversation memory feature.

## R6: Conversation Turn Boundaries

**Decision**: A "conversation turn" starts when `handle_message()` receives a new user message and ends when the final bot response is returned. All intermediate tool-use loop iterations (which may involve multiple assistant/tool_result message pairs) are part of the same turn.

**Rationale**: The tool-use loop in handle_message() (lines 1049-1102) already builds up the `messages` list with multiple entries per turn:
```
Turn 1: user → assistant(tool_use) → user(tool_result) → assistant(tool_use) → user(tool_result) → assistant(text)
```
After the loop, we save all of these as a single turn. On the next message, we prepend all of them as history. This ensures Claude sees the full tool call chain — critical for follow-ups that reference tool results.
