# Data Model: Time Awareness & Extended Conversation Context

**Feature**: 016-time-and-context-fix | **Date**: 2026-03-03

## Entities

### ConversationStore (existing — modified)

Top-level JSON object keyed by phone number. File: `data/conversations.json`.

```
{
  "<phone_number>": ConversationEntry
}
```

### ConversationEntry (existing — modified)

Per-user conversation state.

| Field       | Type            | Description                                    | Change    |
|-------------|-----------------|------------------------------------------------|-----------|
| last_active | ISO 8601 string | Timestamp of most recent message               | No change |
| turns       | list[Turn]      | Ordered list of conversation turns (oldest first) | Increased cap: 25 → 100 |

### Turn (existing — modified)

A single conversation round (user input → assistant response including tool calls).

| Field     | Type            | Description                                       | Change                        |
|-----------|-----------------|---------------------------------------------------|-------------------------------|
| messages  | list[Message]   | All messages in this turn (user, assistant, tool)  | No change                     |
| timestamp | ISO 8601 string | When this turn was saved (Pacific time)            | **NEW** — for per-turn pruning |

**Migration**: Old turns without `timestamp` are kept until they fall off the 100-turn limit. No migration script needed.

### Message (existing — no change)

Individual message within a turn. Format varies by role (user text, assistant content blocks, tool results). Already handles serialization of Anthropic SDK objects and base64 images.

## State Transitions

### Conversation Lifecycle

```
No History → First Turn Saved → Active (accumulating turns)
                                    ↓
                        Turn > 7 days old → Pruned on next access
                                    ↓
                        All turns pruned → No History (clean slate)
```

**Previous behavior**: Entire conversation wiped after 24h of inactivity.
**New behavior**: Individual turns pruned when older than 7 days. Conversation persists as long as any turn is within the 7-day window.

## Storage Estimates

- Average turn size: ~2KB serialized JSON (user message + assistant response + tool results)
- 100 turns × 2KB = ~200KB per user
- 2 users × 200KB = ~400KB total
- Well within single-file JSON performance bounds
