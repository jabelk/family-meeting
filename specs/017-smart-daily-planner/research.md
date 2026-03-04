# Research: Smart Daily Planner

**Feature**: 017-smart-daily-planner | **Date**: 2026-03-03

## R1: How to make Claude treat existing calendar events as immovable blocks

**Decision**: System prompt rules only — no code changes needed for calendar reading.

**Rationale**: `get_daily_context()` in `src/context.py` already reads all 3 Google Calendars (Jason personal, Erin personal, Family shared) via `get_events_for_date()` and returns structured text with event times and descriptions. The function also handles recurring events (they appear on the calendar like any other event). The issue is that Claude's current system prompt (rules 9-15b) doesn't explicitly instruct it to treat these events as fixed/immovable when generating a plan. Adding explicit rules ("treat existing calendar events as fixed blocks that cannot be moved or overlapped") will fix this without any code changes.

**Alternatives considered**:
- Modify `get_daily_context()` to return events with a `[FIXED]` tag — rejected because the problem is prompt behavior, not data formatting. Adding tags is unnecessary complexity.
- Pre-process calendar events into a structured plan template before Claude sees them — rejected because Claude is already good at working with structured text when given clear instructions.

## R2: Confirm-before-write pattern

**Decision**: Modify system prompt rule 14 to present draft → wait for confirmation → only then call `write_calendar_blocks`.

**Rationale**: The `write_calendar_blocks` tool is already a separate tool call that Claude decides to invoke. Currently rule 14 instructs Claude to call it immediately after generating the plan. Changing the rule to "present as draft, ask for confirmation" means Claude will hold off on the tool call until the user says "yes" / "looks good" / "add it." This is pure prompt engineering — no code changes to the tool or the message handler. The morning briefing (n8n trigger) uses the same flow, so the rule also needs to specify: never auto-write from the briefing, always wait for WhatsApp confirmation.

**Alternatives considered**:
- Add a `draft_plan` intermediate storage mechanism — rejected because the plan exists in chat context. Claude can reference it when the user confirms and then call `write_calendar_blocks`.
- Add a confirmation modal/UI — rejected because WhatsApp is the interface and natural conversation ("looks good") is simpler.

## R3: Drive time storage approach

**Decision**: New `src/drive_times.py` module with atomic JSON file at `data/drive_times.json`.

**Rationale**: The project has an established pattern for small persistent data: in-memory dict + atomic JSON writes (see `preferences.py`, `routines.py`, `conversation.py`). Drive times are a simple key-value mapping (location name → minutes from home). Maximum ~10 entries. The pattern works perfectly:
- `get_drive_times()` → returns all stored drive times
- `save_drive_time(location, minutes)` → add or update
- `delete_drive_time(location)` → remove

Two new tools registered in `assistant.py` so Claude can read/write drive times.

**Alternatives considered**:
- Store in Notion Family Profile page — rejected because it requires API calls for simple key-value data, adds latency, and the page structure is complex. Local JSON is faster and simpler.
- Store in user preferences (`preferences.py`) — rejected because drive times are family-level data (not per-phone-number) and the preferences module is structured around categories/descriptions, not simple key-value pairs.
- Store in a dedicated Notion database — rejected per Constitution I (Integration Over Building) and III (Simplicity). A JSON file for <10 entries is the right tool.

## R4: How to include drive times in daily context

**Decision**: Add `get_drive_times` call to `get_daily_context()` output and reference it in system prompt rules.

**Rationale**: When Claude generates a plan, it calls `get_daily_context` which returns calendar events, childcare status, etc. Including drive times in this output means Claude sees them at plan time without needing a separate tool call. However, Claude also needs a separate `save_drive_time` tool for when Erin says "the gym is 5 minutes away" in normal conversation. So: drive times appear in context output (for automatic use during planning) AND as dedicated tools (for add/update/delete).

## R5: Morning briefing behavior

**Decision**: System prompt rule covers this — the morning briefing (n8n trigger) generates a plan but does NOT auto-write to calendar.

**Rationale**: The morning briefing comes through the same `handle_message` endpoint as regular WhatsApp messages. The system prompt will instruct Claude: "When generating a daily plan from the morning briefing or any automated trigger, present the plan as a draft and wait for the user to confirm before writing to calendar." This matches the confirm-before-write pattern from US2 and requires no code changes to n8n or the webhook handler.
