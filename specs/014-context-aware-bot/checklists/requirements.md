# Requirements Checklist: Context-Aware Bot (014)

## Functional Requirements Validation

### FR-001: Dynamic Context Tool (`get_daily_context`)
- [ ] Tool returns current Pacific timestamp in ISO 8601 format
- [ ] Tool returns today's calendar events from Jason's personal calendar, labeled as jason
- [ ] Tool returns today's calendar events from Erin's personal calendar, labeled as erin
- [ ] Tool returns today's calendar events from the family shared calendar, labeled as family
- [ ] Events are grouped by person (jason_events, erin_events, family_events) in the output
- [ ] Tool returns childcare status: who has Zoey right now and until when
- [ ] Tool returns active user preferences for the requesting phone number
- [ ] Tool returns pending backlog item count
- [ ] Tool returns communication_mode based on current time and user preferences
- [ ] Tool returns a calendar_available boolean flag
- [ ] Tool completes in under 5 seconds (2-4 API calls)
- [ ] Tool is registered in the TOOLS list in `src/assistant.py` with proper input_schema

### FR-002: Hardcoded Schedule Removal
- [ ] Lines 46-58 (weekly schedule Mon-Sun) are removed from the system prompt
- [ ] Lines 43-44 (childcare schedule — Sandy takes Zoey) are removed from the system prompt
- [ ] System prompt instructions that reference "check who has Zoey today" now say "call get_daily_context"
- [ ] Rules 9-15 (daily planner rules) no longer reference specific days or hardcoded activities
- [ ] No remaining references to "Sandy has Zoey Mon 9-12, Tue 10-1" in any source file
- [ ] Bot correctly generates daily plans using only live calendar data from `get_daily_context`

### FR-003: Childcare Inference
- [ ] If Sandy's calendar event overlaps with current time, Zoey is reported as "with Sandy"
- [ ] If a preschool/Milestones event overlaps with current time, Zoey is reported as "at preschool"
- [ ] If grandparents have Zoey (family calendar event), this is reported correctly
- [ ] If no childcare event is found, Zoey is reported as "with Erin" (default)
- [ ] Childcare inference uses calendar event keywords: Sandy, preschool, Milestones, grandma, grandparents
- [ ] Childcare transitions within a day are handled (e.g., Sandy 9-12, then Erin 12+)

### FR-004: Communication Mode
- [ ] "morning" mode is returned between 7:00 AM and 11:59 AM Pacific
- [ ] "afternoon" mode is returned between 12:00 PM and 4:59 PM Pacific
- [ ] "evening" mode is returned between 5:00 PM and 8:59 PM Pacific
- [ ] "late_night" mode is returned between 9:00 PM and 6:59 AM Pacific
- [ ] Mode boundaries are exactly on the hour (9:00 PM is "late_night", 8:59 PM is "evening")
- [ ] Mode is derived from Pacific time regardless of server timezone

### FR-005: Late Night Suppression
- [ ] Bot does NOT proactively suggest tasks when communication_mode is "late_night"
- [ ] Bot does NOT append discovery tips when communication_mode is "late_night"
- [ ] Bot does NOT suggest chores or backlog items when communication_mode is "late_night"
- [ ] Bot still answers direct questions fully when communication_mode is "late_night"
- [ ] Nudge system checks communication mode before delivering proactive nudges
- [ ] n8n-triggered briefings are suppressed during late_night hours

### FR-006: Custom Quiet Hours via Preferences
- [ ] Erin can say "quiet after 8pm" and the late_night boundary moves to 8:00 PM
- [ ] Custom quiet hours are stored via the existing preference system (Feature 013)
- [ ] Custom quiet hours are loaded by `get_daily_context` when computing communication_mode
- [ ] Removing the quiet hours preference restores default boundaries (9pm)
- [ ] Jason and Erin can have different quiet hours boundaries

### FR-007: Save Routine Tool
- [ ] `save_routine` accepts a routine name and ordered list of steps
- [ ] Routine is stored in `data/routines.json` (local) or `/app/data/routines.json` (Docker)
- [ ] Storage follows the `_DATA_DIR` pattern from `preferences.py`
- [ ] Atomic writes: write to `.tmp` then rename (matches `_save_preferences()` pattern)
- [ ] In-memory cache is kept synchronized with the on-disk file
- [ ] Routines are loaded from disk on module import
- [ ] Routine names are normalized (lowercased, trimmed) for matching
- [ ] Saving a routine with an existing name overwrites it (upsert behavior)
- [ ] Bot confirms creation with step count: "Saved your morning routine (5 steps)"

### FR-008: Get Routine Tool
- [ ] `get_routine` accepts a routine name and returns the ordered steps
- [ ] Steps are returned as a numbered list suitable for WhatsApp formatting
- [ ] If the routine does not exist, a helpful message is returned suggesting creation
- [ ] Routine lookup is case-insensitive ("Morning" matches "morning")

### FR-009: Routine Modification
- [ ] "Add X after Y" inserts a step at the correct position
- [ ] "Remove X from my morning routine" removes the matching step
- [ ] "Move X before Y" reorders steps
- [ ] After modification, the updated routine is saved and the bot shows the new order
- [ ] Modification of a non-existent routine suggests creating one first

### FR-010: Routine References in Daily Plans
- [ ] When a morning time block aligns with a stored "morning" routine, the plan references it
- [ ] Reference includes step count and estimated duration
- [ ] Reference includes a prompt: "Say 'show morning routine' for the full list"
- [ ] If no matching routine exists, the time block is generated normally without a routine reference

### FR-011: System Prompt Line Count
- [ ] System prompt is 280 lines or fewer after cleanup
- [ ] Reduction is at least 30% from the original ~413 lines
- [ ] Line count is measured from the opening triple-quote to the closing triple-quote of SYSTEM_PROMPT

### FR-012: Behavioral Rules Retained
- [ ] Rule 1 (WhatsApp formatting) is retained
- [ ] Rule 3 (weekly agenda sections) is retained
- [ ] Rules 18-22 (grocery and recipe integration) are retained
- [ ] Rules 23-27 (nudge interactions) are retained
- [ ] Rules 28-31 (Downshiftology) are retained
- [ ] Rules 32-36 (budget management) are retained
- [ ] Rules 37 (quick reminders) is retained
- [ ] Rules 38-39 (feature discovery) are retained
- [ ] Rules 40-50 (cross-domain thinking) are retained
- [ ] Rules 51-66 (Amazon/email sync, budget goals) are retained
- [ ] Rules 69-71 (user preferences) are retained and updated to reference routines

### FR-013: Calendar Event Attribution
- [ ] Events from Jason's calendar (`_calendar_source: "jason"`) are grouped under Jason
- [ ] Events from Erin's calendar (`_calendar_source: "erin"`) are grouped under Erin
- [ ] Events from the family calendar (`_calendar_source: "family"`) are grouped under Family
- [ ] The context tool output makes attribution explicit so the model does not have to infer it

### FR-014: Calendar API Failure Handling
- [ ] If Google Calendar returns an error, the context tool catches the exception
- [ ] `calendar_available` is set to `false` in the response
- [ ] A human-readable error message is included in the response
- [ ] The bot does NOT crash — it tells the user calendar data is temporarily unavailable
- [ ] Other context fields (time, preferences, communication mode) are still populated

### FR-015: Per-User Routines
- [ ] Routines are keyed by phone number in the JSON file
- [ ] Erin's routines are separate from Jason's routines
- [ ] "Show me my morning routine" shows only the requesting user's routine
- [ ] "Save my evening routine" saves under the requesting user's phone number

### FR-016: Routine File I/O
- [ ] Routines are loaded from `data/routines.json` on module import
- [ ] If the file does not exist, an empty routine set is used (no crash)
- [ ] If the file is corrupted, a warning is logged and an empty set is used
- [ ] Every write operation updates both the in-memory cache and the on-disk file
- [ ] Atomic writes: `.tmp` file then rename

## Integration Points

### Calendar System (`src/tools/calendar.py`)
- [ ] `get_daily_context` calls `get_events_for_date` for today's events from all 3 calendars
- [ ] `get_daily_context` optionally calls `get_outlook_events` for Jason's work calendar
- [ ] Existing calendar tool behavior is not modified — `get_daily_context` reads from existing functions

### Preference System (Feature 013, `src/preferences.py`)
- [ ] `get_daily_context` reads active preferences for the requesting phone number
- [ ] Custom quiet hours preferences are parsed to adjust communication mode boundaries
- [ ] Existing preference tools (`save_preference`, `list_preferences`, `remove_preference`) continue working

### Nudge System (Feature 003, `src/tools/nudges.py`)
- [ ] Nudge delivery checks communication mode before sending proactive messages
- [ ] `QUIET_HOURS_START` and `QUIET_HOURS_END` constants in nudges.py may be replaced by dynamic lookup
- [ ] Existing quiet day functionality (Feature 003) is not broken

### System Prompt (`src/assistant.py`)
- [ ] New tool definitions added for `get_daily_context`, `save_routine`, `get_routine`
- [ ] System prompt references the new tools in the appropriate behavioral rules
- [ ] Dynamic preference injection (Feature 013) continues working after prompt cleanup

### Daily Planner / Meeting Prep
- [ ] Daily plan generation calls `get_daily_context` as the first step
- [ ] Meeting prep calls `get_daily_context` for current schedule context
- [ ] Removed hardcoded chore windows are now inferred from free time in calendar data

## Edge Cases

- [ ] Google Calendar API timeout does not hang the bot (timeout set on API calls)
- [ ] Empty calendar day: `get_daily_context` returns empty event lists, bot notes "no events today"
- [ ] User sends message at exactly midnight Pacific: communication_mode is "late_night"
- [ ] Both Erin and Jason ask "what's my day?" simultaneously: each gets their own context (per-phone)
- [ ] Routine with special characters in name (e.g., "morning/evening") is handled gracefully
- [ ] Routine with 50+ steps: stored correctly, no truncation
- [ ] "Show me my routine" without specifying which one: bot lists all stored routines for that user
- [ ] Zoey transitions from Sandy to Erin mid-conversation: context reflects the change on next call

## Success Criteria Validation

- [ ] **SC-001**: System prompt line count <= 280 (measured from SYSTEM_PROMPT opening to closing quote)
- [ ] **SC-002**: Bot correctly reports today's day and time when asked — no more date/time errors
- [ ] **SC-003**: Events attributed to correct person in daily plan (Jason's events under Jason, etc.)
- [ ] **SC-004**: No proactive messages sent between 9pm-7am Pacific (verified over 7-day observation)
- [ ] **SC-005**: Full routine lifecycle: create, view, modify (add step), view updated — all via WhatsApp
- [ ] **SC-006**: Change a recurring calendar event (e.g., move BSF to Wednesday), bot adapts on next interaction with zero code changes

## Issue Resolution Tracking

### Issue #7: Time-context-aware recommendations
- [ ] Bot checks current time via `get_daily_context` before making recommendations
- [ ] Bot does not suggest chores when Erin is likely engaged in an activity (calendar says she's busy)
- [ ] Morning recommendations differ from evening recommendations
- [ ] Proactive suggestions only happen during "morning" and "afternoon" communication modes

### Issue #13: General quiet hours (late night engagement)
- [ ] Bot does not proactively engage after 9pm Pacific (default)
- [ ] Users can customize quiet hours start time via preferences
- [ ] Bot still responds to direct questions during quiet hours
- [ ] "Quiet after 8pm" preference is honored immediately

### Issue #14: Calendar event attendee attribution (being fixed separately)
- [ ] `get_daily_context` groups events by calendar source, making attribution explicit
- [ ] When Issue #14's calendar naming fix is applied, attribution becomes even more reliable
- [ ] Feature works without Issue #14 fix (falls back to calendar source labels)

### Issue #15: Personal routine checklists
- [ ] Erin can create a morning skincare routine via WhatsApp
- [ ] Erin can view her routine on demand
- [ ] Erin can add, remove, and reorder steps
- [ ] Routines are referenced in daily plans when relevant
- [ ] Routines persist across container restarts
