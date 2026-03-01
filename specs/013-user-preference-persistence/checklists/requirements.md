# Requirements Checklist: User Preference Persistence (013)

## Functional Requirements Validation

### FR-001: Preference Detection
- [ ] Bot correctly identifies "don't remind me about groceries unless I ask" as a lasting preference
- [ ] Bot correctly identifies "no Jason appointment reminders" as a lasting preference
- [ ] Bot correctly identifies "check the time before making recommendations" as a lasting preference
- [ ] Bot does NOT treat "okay, I'll check groceries later" as a preference (conversational, not a rule)
- [ ] Bot does NOT treat "quiet day" as a persistent preference (already handled by Feature 003 as a temporary toggle)
- [ ] Bot asks for clarification on ambiguous statements like "leave me alone"

### FR-002: Persistent Storage
- [ ] Preferences are written to `data/user_preferences.json` (local) or `/app/data/user_preferences.json` (Docker)
- [ ] File follows `_DATA_DIR` pattern from `conversation.py` and `discovery.py`
- [ ] Preferences survive Docker container restart (verified with `docker compose restart fastapi`)
- [ ] Preferences survive full redeployment (`docker compose down && docker compose up`)
- [ ] File is valid JSON after every write operation

### FR-003: Per-User Isolation
- [ ] Erin's preferences are stored under Erin's phone number
- [ ] Jason's preferences are stored under Jason's phone number
- [ ] Setting a preference for Erin does not affect Jason's experience
- [ ] Listing preferences for Erin does not show Jason's preferences

### FR-004: System Prompt Injection
- [ ] Active preferences for the current user are appended to the system prompt before each message
- [ ] Preferences are formatted clearly so Claude understands and respects them
- [ ] System prompt injection does not break existing system prompt rules
- [ ] Performance: adding preferences does not significantly increase response latency

### FR-005: Nudge Filtering
- [ ] Grocery opt-out suppresses grocery-related proactive nudges for that user
- [ ] Departure opt-out suppresses departure reminder nudges for that user
- [ ] Budget opt-out suppresses budget-related proactive nudges for that user
- [ ] Chore opt-out suppresses chore suggestion nudges for that user
- [ ] Nudges for non-opted-out topics are still delivered normally
- [ ] Filtered nudges are logged (not silently dropped) for debugging

### FR-006: List Preferences
- [ ] "What are my preferences?" returns a formatted list of all active preferences
- [ ] Each preference shows: description, category, and when it was set
- [ ] Response uses WhatsApp formatting (bold headers, bullet lists)
- [ ] Empty preference set returns a helpful message with examples

### FR-007: Remove Preferences
- [ ] "Start reminding me about groceries again" removes the grocery opt-out
- [ ] "Remove preference about groceries" removes the grocery opt-out
- [ ] "I want Jason's appointments back" removes the Jason calendar filter
- [ ] "Clear all my preferences" removes all preferences for that user
- [ ] Removal confirmation includes what was removed and that it takes effect immediately

### FR-008: Conflicting Preferences
- [ ] Newer preference for the same topic replaces the older one
- [ ] Bot confirms the update, not a duplicate creation
- [ ] If a user opts out then opts back in for the same topic, only the opt-in is active

### FR-009: Confirmation Messages
- [ ] Preference creation is confirmed with a human-readable message
- [ ] Confirmation includes how to reverse the preference
- [ ] Preference removal is confirmed with what was removed
- [ ] Removal confirmation mentions the preference is no longer active

### FR-010: Startup Loading
- [ ] Preferences are loaded from disk when the module is imported (same as `conversation.py`)
- [ ] If the file does not exist on startup, an empty preference set is used (no crash)
- [ ] If the file is corrupted, a warning is logged and an empty preference set is used

### FR-011: Atomic Writes
- [ ] Writes go to a `.tmp` file first, then `rename()` to the final path
- [ ] Pattern matches `_save_conversations()` in `conversation.py`
- [ ] Concurrent reads during a write do not see partial data

### FR-012: Explicit Requests Override Opt-Outs
- [ ] Erin can ask "what's the meal plan?" even with a grocery opt-out and gets a full answer
- [ ] Erin can ask "what's on Jason's calendar?" even with a Jason filter and gets the data
- [ ] Opt-outs only suppress proactive/unsolicited messages, not direct requests

### FR-013: Ambiguity Handling
- [ ] "Leave me alone" prompts clarification (quiet day vs. permanent)
- [ ] "Stop everything" prompts clarification (all nudges vs. all communication)
- [ ] If no clarification is given, the less destructive option is chosen

### FR-014: Preference Cap
- [ ] Users cannot store more than 50 preferences
- [ ] A warning is shown when approaching the limit (e.g., 45+)
- [ ] Attempting to add a 51st preference returns an error with guidance to remove old ones

## Integration Points

### Nudge System (Feature 003)
- [ ] `process_pending_nudges()` in `src/tools/nudges.py` checks preferences before sending
- [ ] `scan_upcoming_departures()` respects departure nudge opt-outs
- [ ] Quiet day (Feature 003) and preference opt-outs work independently and do not conflict

### System Prompt (`src/assistant.py`)
- [ ] Preferences are injected into the system prompt dynamically
- [ ] Injection happens in `handle_message()` before the Claude API call
- [ ] Existing hardcoded preferences (Rule 67: budget quiet hours) are not broken

### Conversation Memory (Feature 007)
- [ ] Preferences are NOT stored in conversation memory (they have their own file)
- [ ] Preferences persist beyond the 24h conversation timeout
- [ ] Preference operations (set, list, remove) are reflected in conversation context

### Daily Planner / Meeting Prep
- [ ] Topic filters (e.g., exclude Jason calendar) modify what data is fetched for briefings
- [ ] Notification opt-outs (e.g., no groceries) suppress those sections in daily plans
- [ ] Communication style preferences (e.g., time-awareness) shape recommendation timing

## Data Integrity

- [ ] JSON schema includes: id, phone, label, category, topic, original_text, created_at, active
- [ ] Phone numbers are stored in E.164 format (matching WhatsApp webhook format)
- [ ] Timestamps use ISO 8601 format
- [ ] No sensitive data beyond phone numbers (already present in conversations.json)

## Erin's Three Specific Preferences (Day-One Validation)

- [ ] "Don't send grocery info unless I ask" -> Stored as notification opt-out, topic: groceries
- [ ] "Don't remind me of Jason's appointments" -> Stored as topic filter, scope: jason_personal_calendar
- [ ] "Check the time before making recommendations" -> Stored as communication style, scope: time_awareness
- [ ] All three are honored in the daily briefing
- [ ] All three persist across container restart
- [ ] All three can be listed and removed
