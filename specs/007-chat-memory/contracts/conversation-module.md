# Contract: Conversation Module (`src/conversation.py`)

## Purpose

Internal module providing conversation history storage and retrieval for the assistant. Not a tool — infrastructure consumed by `handle_message()` in `src/assistant.py`.

## Public Functions

### `get_history(phone: str) -> list[dict]`

Returns the conversation history for a phone number as a flat list of Claude API messages. Returns an empty list if no conversation exists or the conversation has expired.

**Behavior**:
- If `phone` has no stored conversation → return `[]`
- If `phone`'s conversation has `last_active` older than `CONVERSATION_TIMEOUT` seconds → clear it, return `[]`
- Otherwise → return flattened messages from all stored turns (in order, oldest first)

**Returns**: List of message dicts ready to prepend to the `messages` array in `handle_message()`. Each dict has `role` ("user" or "assistant") and `content` (string or list of content block dicts).

### `save_turn(phone: str, turn_messages: list[dict]) -> None`

Saves a completed conversation turn for a phone number. A turn includes all messages from the user's input through the final bot response (including all tool-use loop iterations).

**Behavior**:
- Updates `last_active` to current timestamp
- Appends the turn to the conversation's `turns` list
- If `turns` count exceeds `MAX_CONVERSATION_TURNS` → drop the oldest turn
- Serializes assistant content blocks via `model_dump(mode="json", exclude_unset=True)`
- Replaces any base64 image content with text placeholder `"[Image sent: photo]"`
- Atomically writes to `data/conversations.json`

**Parameters**:
- `phone`: Phone number string (e.g., "+14155551234")
- `turn_messages`: The `messages` list from `handle_message()` for the current turn. May contain Anthropic SDK content block objects (TextBlock, ToolUseBlock) in assistant messages — these will be serialized.

### `clear_history(phone: str) -> None`

Explicitly clears conversation history for a phone number. Used if needed for testing or reset.

## Constants

| Name                   | Type | Default | Description                              |
|------------------------|------|---------|------------------------------------------|
| CONVERSATION_TIMEOUT   | int  | 1800    | Seconds before conversation expires      |
| MAX_CONVERSATION_TURNS | int  | 10      | Max turns stored per conversation        |

## Integration Point

In `src/assistant.py` `handle_message()`:

```python
# Before API call:
history = conversation.get_history(sender_phone)
messages = history + [{"role": "user", "content": user_content}]

# After tool loop completes:
# turn_messages = messages[len(history):]  # just this turn's messages
conversation.save_turn(sender_phone, turn_messages)
```

## Constraints

- Skip history for `sender_phone == "system"` (automated messages per FR-007)
- File path: `data/conversations.json` (local) or `/app/data/conversations.json` (Docker)
- Thread safety: Not required — FastAPI processes one message at a time per the existing architecture (WhatsApp webhook is sequential per phone)
