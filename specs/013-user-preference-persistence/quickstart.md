# Quickstart: User Preference Persistence

**Feature**: 013-user-preference-persistence
**Date**: 2026-03-01

## Scenario 1: Erin Sets a Grocery Opt-Out

**WhatsApp input**: "don't send grocery info unless I ask"

**Expected behavior**:
1. Claude detects this as a lasting preference (not a one-time request)
2. Claude calls `save_preference(category="notification_optout", description="No grocery reminders unless asked", raw_text="don't send grocery info unless I ask")`
3. Preference stored in `data/user_preferences.json` under Erin's phone number
4. Bot confirms: "Got it -- I won't bring up grocery info unless you ask. You can change this anytime by saying 'start reminding me about groceries again'."

## Scenario 2: Preference Honored in Daily Briefing

**Precondition**: Erin has stored "No grocery reminders unless asked"

**WhatsApp input**: (automated daily briefing via n8n)

**Expected behavior**:
1. `handle_message("system", ...)` is called
2. System prompt includes: "**User preferences (MUST honor these):** - No grocery reminders unless asked"
3. Claude generates daily briefing WITHOUT unsolicited grocery or meal plan information
4. If Erin later asks "what's the meal plan?", Claude answers normally (explicit requests override opt-outs)

## Scenario 3: Nudge Filtered by Preference

**Precondition**: Erin has stored a grocery notification opt-out

**Trigger**: n8n calls `/api/v1/nudges/scan`, which creates a grocery-related nudge

**Expected behavior**:
1. `process_pending_nudges()` is called
2. Before sending each nudge, preferences for the target phone are loaded
3. Grocery-related nudge matches the `notification_optout` category
4. Nudge is suppressed (not sent to WhatsApp)
5. Other nudges (departure, chore) are sent normally

## Scenario 4: List Preferences

**WhatsApp input**: "what are my preferences?"

**Expected behavior**:
1. Claude calls `list_preferences()`
2. Tool returns formatted list:
   ```
   *Your stored preferences:*
   1. No grocery reminders unless asked (notification opt-out, set Feb 25)
   2. Exclude Jason's calendar from daily briefing (topic filter, set Feb 26)
   3. Check the time before making recommendations (communication style, set Feb 27)
   ```

## Scenario 5: Remove a Preference

**WhatsApp input**: "start reminding me about groceries again"

**Expected behavior**:
1. Claude calls `remove_preference(search_text="groceries")`
2. Fuzzy match finds "No grocery reminders unless asked"
3. Preference removed from storage
4. Bot confirms: "Done -- I've removed your grocery opt-out. I'll include grocery info in proactive messages again."
5. Next daily briefing includes grocery information

## Scenario 6: Preference Survives Container Restart

**Steps**:
1. Erin sets a preference via WhatsApp
2. Docker container restarts (`docker compose restart fastapi`)
3. Module import triggers `_load_preferences()` from JSON file
4. Erin sends "what are my preferences?" -- preference is still listed
5. Daily briefing honors the preference -- opt-out still active

## Scenario 7: Clear All Preferences

**WhatsApp input**: "clear all my preferences"

**Expected behavior**:
1. Claude calls `remove_preference(search_text="ALL")`
2. All of Erin's preferences are removed
3. Bot confirms: "Done -- I've cleared all 3 of your preferences. I'll go back to default behavior for everything."

## Verification Commands

```bash
# Test module import
python3 -c "import src.preferences; print('OK')"

# Test tool count (should be 3 more than before)
python3 -c "from src.assistant import TOOLS; print(f'{len(TOOLS)} tools')"

# Test preference CRUD
python3 -c "
from src.preferences import get_preferences, add_preference, remove_preference_by_description, clear_preferences
p = add_preference('test123', 'notification_optout', 'Test pref', 'test')
print('Added:', p)
print('List:', get_preferences('test123'))
remove_preference_by_description('test123', 'test')
print('After remove:', get_preferences('test123'))
"
```
