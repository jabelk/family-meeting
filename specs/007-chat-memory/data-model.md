# Data Model: Chat Memory & Conversation Persistence

## Entities

### Conversation Store

The top-level structure stored in `data/conversations.json`. Maps phone numbers to their conversation state.

```json
{
  "+14155551234": {
    "last_active": "2026-02-24T10:35:00",
    "turns": [
      { "/* Turn 1 — see Turn structure below */" : "..." },
      { "/* Turn 2 */" : "..." }
    ]
  },
  "+14155555678": {
    "last_active": "2026-02-24T09:15:00",
    "turns": []
  }
}
```

| Field        | Type              | Description                                                        |
|--------------|-------------------|--------------------------------------------------------------------|
| (phone key)  | string            | Phone number as dict key (e.g., "+14155551234")                    |
| last_active  | ISO 8601 string   | Timestamp of the most recent message in this conversation          |
| turns        | list[Turn]        | Ordered list of conversation turns, oldest first, max 10           |

### Turn

One logical exchange: a user message through to the complete bot response (including all tool call iterations).

```json
{
  "messages": [
    {"role": "user", "content": "[From Erin]: find me a chicken dinner recipe"},
    {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_01...", "name": "search_downshiftology", "input": {"query": "chicken", "course": "dinner"}}]},
    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_01...", "content": "Found 5 recipes: ..."}]},
    {"role": "assistant", "content": [{"type": "text", "text": "Here are 5 chicken dinner recipes from Downshiftology:\n1. ..."}]}
  ]
}
```

| Field    | Type         | Description                                                                           |
|----------|--------------|---------------------------------------------------------------------------------------|
| messages | list[dict]   | Claude API message format: alternating user/assistant, including tool_use/tool_result  |

**Message format**: Each entry in `messages` follows the Anthropic Messages API schema:
- `role`: "user" or "assistant"
- `content`: string (for simple text) or list of content blocks:
  - `{"type": "text", "text": "..."}` — text content
  - `{"type": "tool_use", "id": "...", "name": "...", "input": {...}}` — tool call from assistant
  - `{"type": "tool_result", "tool_use_id": "...", "content": "..."}` — tool execution result
  - `"[Image sent: photo]"` — placeholder replacing base64 image data

### Constants

| Constant               | Value | Description                                          |
|------------------------|-------|------------------------------------------------------|
| CONVERSATION_TIMEOUT   | 1800  | Seconds of inactivity before conversation expires    |
| MAX_CONVERSATION_TURNS | 10    | Maximum turns retained per conversation              |

## Lifecycle

```
New message arrives for phone P
  │
  ├─ No conversation for P exists → Start new conversation
  │
  ├─ Conversation exists, last_active > 30 min ago → Expire old, start new
  │
  └─ Conversation exists, last_active ≤ 30 min ago → Append to existing
       │
       ├─ turns count ≤ MAX → Append turn
       │
       └─ turns count > MAX → Drop oldest turn, append new
```

## Storage Details

- **File path**: `data/conversations.json` (local) or `/app/data/conversations.json` (Docker)
- **Write strategy**: Atomic — write to `.tmp` file, then `os.replace()` to target path
- **Load strategy**: Read once at module import, then kept in memory
- **Save trigger**: After each completed conversation turn in `handle_message()`
- **Cleanup**: Expired conversations are pruned on access (lazy cleanup), not on a timer

## Relationship to Existing Data

- **Usage counters** (`data/usage_counters.json`): Independent — tracks feature category usage for discovery suggestions. Not affected by conversation history.
- **Module-level state** (`_last_search_results`, `_buffered_images`, etc.): Coexists — conversation history gives Claude conversational context, module-level state gives tools operational data. Both are needed.
- **Welcome tracking** (`_welcomed_phones` set): Independent — in-memory only, resets on restart. Not related to conversation history.
