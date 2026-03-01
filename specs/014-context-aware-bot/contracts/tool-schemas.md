# Tool Schemas: Context-Aware Bot

**Feature**: 014-context-aware-bot | **Date**: 2026-03-01

## New Tools (3)

### 1. get_daily_context

**Purpose**: Returns structured snapshot of current family context for planning/scheduling.

```json
{
  "name": "get_daily_context",
  "description": "Get today's family context: calendar events grouped by person, who has Zoey, communication mode (time-of-day tone), active preferences, and pending backlog count. Call this at the start of any planning, scheduling, daily plan, or recommendation interaction. Do NOT call for simple factual questions.",
  "input_schema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**Output**: Plain text block (~400-600 chars). Example:
```
📅 Saturday, March 1, 2026 at 10:30 AM Pacific

🕐 Communication mode: morning (energetic, proactive suggestions welcome)

👤 Jason's events today:
- 9:00 AM: BSF at Sparks Christian Fellowship

👤 Erin's events today:
- 8:00 AM – 11:00 AM: Vienna ski lesson

👨‍👩‍👧‍👦 Family events today:
- No family events

👶 Zoey: With Erin (no childcare event detected)

📋 Pending backlog items: 7
⚙️ Active preferences: 2 (no grocery reminders, quiet after 9pm)
📅 Calendar: available
```

**Error output** (Google Calendar down):
```
📅 Saturday, March 1, 2026 at 10:30 AM Pacific

🕐 Communication mode: morning

⚠️ Calendar data unavailable — Google Calendar API error. Cannot show today's events or infer childcare status.

📋 Pending backlog items: 7
⚙️ Active preferences: 2
📅 Calendar: unavailable
```

**Handler**: Phone number injected automatically (same pattern as `save_preference`).

---

### 2. save_routine

**Purpose**: Store a named, ordered routine checklist.

```json
{
  "name": "save_routine",
  "description": "Save a personal routine checklist. Overwrites if a routine with the same name already exists. Examples: morning skincare, bedtime, meal prep, school pickup.",
  "input_schema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "Routine name (e.g., 'morning skincare', 'bedtime'). Case-insensitive."
      },
      "steps": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Ordered list of step descriptions. Example: ['Wash face', 'Toner', 'Moisturizer']"
      }
    },
    "required": ["name", "steps"]
  }
}
```

**Output**: Confirmation string. Example:
```
Saved your morning skincare routine (5 steps). Say 'show me my morning skincare routine' anytime to see it.
```

**Handler**: Phone number injected automatically.

---

### 3. get_routine

**Purpose**: Retrieve a stored routine by name, or list all routines.

```json
{
  "name": "get_routine",
  "description": "Get a stored personal routine by name. Returns the ordered checklist. If name is empty or 'all', lists all saved routine names.",
  "input_schema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "Routine name to retrieve (e.g., 'morning skincare'). Use 'all' to list all routine names."
      }
    },
    "required": ["name"]
  }
}
```

**Output (single routine)**:
```
Morning skincare routine (5 steps):
1. Wash face
2. Toner
3. Vitamin C serum
4. Moisturizer
5. Sunscreen
```

**Output (list all)**:
```
Your saved routines:
• morning skincare (5 steps)
• bedtime (4 steps)
• school pickup (3 steps)
```

**Output (not found)**:
```
No routine named 'evening' found. Want to create one? Just tell me the steps.
```

**Handler**: Phone number injected automatically.

---

### 4. delete_routine

**Purpose**: Delete a stored routine by name.

```json
{
  "name": "delete_routine",
  "description": "Delete a stored personal routine by name. Use when the user says 'delete my morning routine' or 'remove my bedtime routine'.",
  "input_schema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "Routine name to delete (e.g., 'morning skincare'). Case-insensitive."
      }
    },
    "required": ["name"]
  }
}
```

**Output (success)**:
```
Deleted your morning skincare routine.
```

**Output (not found)**:
```
No routine named 'morning skincare' found. Say 'show all routines' to see what you have saved.
```

**Handler**: Phone number injected automatically.

---

## Modified Tools (0)

No existing tool schemas change. The `get_daily_context` tool wraps existing functions internally.

## Tool Handler Integration

All 4 new tools follow the existing pattern in `assistant.py`:

1. Tool definitions added to the `TOOLS` list
2. Handler functions added to the tool dispatch `if/elif` chain in `handle_message()`
3. Phone number injected via the same mechanism as `save_preference` (line ~1678)

Routine **modification** (insert step, remove step, reorder) is handled via the read-modify-save pattern: the model calls `get_routine` to see the current steps, modifies them in-context based on the user's instruction, then calls `save_routine` with the updated list. No dedicated modify tool needed. Routine **deletion** uses the dedicated `delete_routine` tool.
