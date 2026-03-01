# Data Model: User Preference Persistence

**Feature**: 013-user-preference-persistence
**Date**: 2026-03-01

## Entities

### User Preference

A stored rule that modifies the bot's behavior for a specific user.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Unique identifier, format: `pref_{8-char-hex}` |
| category | string | yes | One of: `notification_optout`, `topic_filter`, `communication_style`, `quiet_hours` |
| description | string | yes | Human-readable label (e.g., "No grocery reminders unless asked") |
| raw_text | string | yes | Original natural language statement from the user |
| created | string (ISO datetime) | yes | When the preference was set |
| active | boolean | yes | Whether the preference is currently active (always true; inactive preferences are deleted) |

### Preference Store (JSON File)

Top-level structure of `data/user_preferences.json`:

```json
{
  "14155551234": {
    "preferences": [
      {
        "id": "pref_a1b2c3d4",
        "category": "notification_optout",
        "description": "No grocery reminders unless asked",
        "raw_text": "don't send grocery info unless I ask",
        "created": "2026-02-25T20:30:00",
        "active": true
      },
      {
        "id": "pref_e5f6g7h8",
        "category": "topic_filter",
        "description": "Exclude Jason's personal calendar from daily briefing",
        "raw_text": "don't tell me about Jason's appointments",
        "created": "2026-02-26T09:15:00",
        "active": true
      }
    ]
  },
  "14155559876": {
    "preferences": []
  }
}
```

**Key**: Phone number (string, no formatting — matches `PHONE_TO_NAME` keys)
**Value**: Object with `preferences` list

## Category Definitions

| Category | Value | Applied At | Examples |
|----------|-------|------------|----------|
| Notification opt-out | `notification_optout` | Nudge delivery layer | "No grocery nudges", "Stop departure reminders" |
| Topic filter | `topic_filter` | Content generation (briefings, agendas) | "Don't include Jason's calendar", "Skip work calendar" |
| Communication style | `communication_style` | System prompt injection | "Check the time before recommending", "Keep responses short" |
| Quiet hours | `quiet_hours` | Nudge scheduling layer | "No messages before 8am", "Quiet after 9pm" |

## Constraints

- Maximum 50 preferences per phone number (FR-014)
- Preference IDs are generated via `secrets.token_hex(4)` — 8 hex chars, collision risk negligible for <50 items
- Atomic file writes: write to `.tmp` then `os.replace()` (same as conversation.py)
- Preferences loaded into module-level `_preferences` dict on import; kept in sync on every write
- Corrupted/unreadable JSON on startup results in empty preference set + warning log (no crash)
