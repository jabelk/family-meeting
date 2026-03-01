# API Contracts: User Preference Persistence

**Feature**: 013-user-preference-persistence
**Date**: 2026-03-01

## Claude Tools (added to assistant.py TOOLS list)

### Tool 1: save_preference

Called by Claude when a user expresses a lasting preference.

```json
{
  "name": "save_preference",
  "description": "Save a user preference that persists across conversations. Use when the user expresses a lasting rule like 'don't remind me about X', 'stop sending X', 'no more X', or 'check the time before Y'. Do NOT use for one-time requests like 'no tacos tonight'.",
  "input_schema": {
    "type": "object",
    "properties": {
      "category": {
        "type": "string",
        "description": "Preference category: 'notification_optout' (suppress proactive nudges), 'topic_filter' (exclude content from briefings), 'communication_style' (change how bot responds), or 'quiet_hours' (time-based suppression).",
        "enum": ["notification_optout", "topic_filter", "communication_style", "quiet_hours"]
      },
      "description": {
        "type": "string",
        "description": "Human-readable summary of the preference (e.g., 'No grocery reminders unless asked')."
      },
      "raw_text": {
        "type": "string",
        "description": "The user's original words that expressed this preference."
      }
    },
    "required": ["category", "description", "raw_text"]
  }
}
```

**Response**: Confirmation message including how to reverse the preference.

### Tool 2: list_preferences

Called when the user asks "what are my preferences?" or similar.

```json
{
  "name": "list_preferences",
  "description": "List all stored preferences for the current user. Use when the user asks 'what are my preferences?', 'what have I set?', or 'show my preferences'.",
  "input_schema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**Response**: Formatted list of active preferences with descriptions, categories, and dates.

### Tool 3: remove_preference

Called when the user wants to undo a preference.

```json
{
  "name": "remove_preference",
  "description": "Remove a stored preference so the bot resumes default behavior. Use when the user says 'start reminding me about X again', 'remove the X preference', 'undo the X opt-out', or 'clear all my preferences'.",
  "input_schema": {
    "type": "object",
    "properties": {
      "search_text": {
        "type": "string",
        "description": "Text to match against stored preferences (fuzzy). Use 'ALL' to clear all preferences."
      }
    },
    "required": ["search_text"]
  }
}
```

**Response**: Confirmation of removal with the removed preference description.

## No New n8n Endpoints

This feature does not require new n8n endpoints. Preference checking is integrated into:
1. `handle_message()` — system prompt injection on every message
2. `process_pending_nudges()` — nudge filtering before delivery

## Internal Python API (src/preferences.py)

```python
def get_preferences(phone: str) -> list[dict]
def add_preference(phone: str, category: str, description: str, raw_text: str) -> dict
def remove_preference(phone: str, preference_id: str) -> bool
def remove_preference_by_description(phone: str, search_text: str) -> bool
def clear_preferences(phone: str) -> int
```

These are called by the tool handler functions in assistant.py, not directly by Claude.
