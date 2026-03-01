# Quickstart: Context-Aware Bot

**Feature**: 014-context-aware-bot | **Date**: 2026-03-01

## Integration Scenarios

### Scenario 1: Daily Plan with Dynamic Context

**Trigger**: Erin sends "what's my day look like?" via WhatsApp

**Flow**:
1. `handle_message()` in `assistant.py` receives the message
2. Claude decides to call `get_daily_context` (tool definition instructs this for planning interactions)
3. `get_daily_context(phone=ERIN_PHONE)` in `src/context.py`:
   - Calls `calendar.get_events_for_date(today, ["jason", "erin", "family"])` → returns event dicts with `_calendar_source`
   - Groups events by `_calendar_source`: jason_events, erin_events, family_events
   - Scans events for childcare keywords → infers "Zoey is with Sandy until 12pm"
   - Checks `datetime.now(PACIFIC)` → determines communication_mode = "morning"
   - Calls `preferences.get_preferences(ERIN_PHONE)` → returns active preferences
   - Calls `notion.get_backlog_items()` → counts pending items
   - Returns formatted text block
4. Claude uses the context to generate a daily plan (same as before, but from live data)
5. Claude calls `write_calendar_blocks` to push the plan to Erin's calendar

**Expected output**: Accurate daily plan based on today's actual calendar events, not hardcoded schedule.

### Scenario 2: Late Night Message (Communication Mode)

**Trigger**: Erin sends "what's the meal plan for tomorrow?" at 10:30 PM

**Flow**:
1. `handle_message()` receives the message
2. Claude calls `get_daily_context` → communication_mode = "late_night"
3. System prompt instruction: "When communication_mode is late_night, provide direct answers only. No proactive suggestions, follow-up prompts, or task recommendations."
4. Claude answers the meal plan question directly
5. Claude does NOT append: chore suggestions, backlog items, discovery tips, or "anything else?"

**Expected output**: Direct meal plan answer with no extras.

### Scenario 3: Routine Creation and Retrieval

**Trigger**: Erin sends "save my morning routine: wash face, toner, serum, moisturizer, sunscreen"

**Flow**:
1. Claude calls `save_routine` with name="morning", steps=["wash face", "toner", "serum", "moisturizer", "sunscreen"]
2. `src/routines.py` stores the routine in `data/routines.json`
3. Claude confirms: "Saved your morning routine (5 steps). Say 'show me my morning routine' anytime."

**Follow-up**: Erin sends "show me my morning routine"
1. Claude calls `get_routine` with name="morning"
2. Returns formatted numbered list:
   ```
   *Morning routine* (5 steps):
   1. Wash face
   2. Toner
   3. Serum
   4. Moisturizer
   5. Sunscreen
   ```

### Scenario 4: Routine Modification

**Trigger**: Erin sends "add vitamin C serum after toner in my morning routine"

**Flow**:
1. Claude calls `modify_routine` with name="morning", action="insert_after", step="Vitamin C serum", reference="toner"
2. `routines.py` finds "toner" at position 2, inserts new step at position 3, shifts remaining
3. Returns updated routine showing new order

### Scenario 5: Nudge Suppression via Communication Mode

**Trigger**: n8n cron fires `process_pending_nudges` at 9:15 PM

**Flow**:
1. `process_pending_nudges()` in `nudges.py` checks communication mode
2. Current time 9:15 PM → mode = "late_night" (or "evening" with custom preference)
3. All pending proactive nudges are held until morning
4. Only departure nudges for imminent events (within 15 min) still fire

### Scenario 6: Childcare Transition (Zero Deploy)

**Before**: Sandy takes Zoey Mon 9-12, Tue 10-1 (hardcoded in system prompt)
**After**: Zoey starts Milestones preschool Mon/Wed/Fri 8:30-12:30 (calendar events added)

**Flow**:
1. Someone adds "Zoey - Milestones Preschool" recurring event to family calendar
2. Next Monday, Erin asks "what's my day look like?"
3. `get_daily_context` scans events, finds "Milestones" keyword → childcare detected
4. Reports: "Zoey: At Milestones Preschool until 12:30 PM"
5. Daily plan correctly identifies 8:30 AM - 12:30 PM as Erin's free time
6. Zero code changes, zero deploys

## Module Dependencies

```text
src/assistant.py
├── imports src/context.py (get_daily_context)
├── imports src/routines.py (save_routine, get_routine, modify_routine, delete_routine, list_routines)
├── imports src/preferences.py (existing — get_preferences for injection)
└── defines tool schemas + handlers for all 3 new tools

src/context.py
├── imports src/tools/calendar.py (get_events_for_date)
├── imports src/preferences.py (get_preferences)
├── imports src/tools/notion.py (get_backlog_items)
└── imports src/config.py (PHONE_TO_NAME, CALENDAR_IDS)

src/routines.py
├── imports json, logging, secrets, datetime, pathlib (stdlib only)
└── follows same pattern as src/preferences.py

src/tools/nudges.py
├── imports src/context.py (get_communication_mode — for nudge suppression)
└── existing imports unchanged
```
