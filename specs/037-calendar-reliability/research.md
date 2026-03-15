# Research: Calendar Reliability

**Feature**: 037-calendar-reliability | **Date**: 2026-03-15

## Decision 1: Time Validation Strategy

**Decision**: Validate and correct times in a shared utility function called from both `batch_create_events()` and `create_quick_event()`, rather than in the assistant handler or at the prompt level.

**Rationale**:
- Three prior prompt-level fixes (Feature 016, commit 6bb0c83, Feature 024) failed because LLM compliance is not guaranteed
- All calendar event creation flows eventually pass through `batch_create_events()` (for schedule blocks) or `create_quick_event()` (for individual events) in `src/tools/calendar.py`
- Validating at the tool level catches all paths with minimal code duplication
- A shared `_validate_event_time()` function can be used by both creation paths

**Alternatives considered**:
- Prompt-only fix: Already tried 3 times, doesn't work reliably
- Validation in assistant handler (`_handle_write_calendar_blocks`): Only covers one path, misses `create_quick_event`
- Validation in Google Calendar API wrapper: Too low-level, no access to event context (summary) needed for heuristic

## Decision 2: AM/PM Correction Heuristic

**Decision**: Aggressive correction — any event between midnight and 8 AM is shifted +12 hours unless the summary matches an early-morning allowlist.

**Rationale**:
- For a family calendar with kids aged 3 and 5, events between midnight and 8 AM are extremely rare
- The only legitimate early-morning events match clear keywords: workout, gym, wake up, breakfast, morning routine, ski (for early departures)
- False positives (incorrectly shifting a real 3 AM event) are far less likely than false negatives (leaving a 3 AM "swim lessons" uncorrected)
- The allowlist is configurable for edge cases

**Alternatives considered**:
- Conservative correction (only when batch pattern detected): Misses single-event errors
- Never auto-correct (always ask user): Too disruptive for a WhatsApp bot
- ML-based classification: Over-engineered for a family calendar

**Early-morning allowlist** (initial set):
- workout, gym, exercise, run, jog, walk
- wake up, wake, alarm, morning routine
- breakfast, coffee
- ski, skiing
- flight, airport, travel, drive
- feed, nursing (baby-related)

## Decision 3: Recurring Event Enforcement

**Decision**: Strengthen system prompt rules to explicitly instruct the LLM to detect recurrence language AND add a code-level check in the tool response to detect sequential identical events.

**Rationale**:
- The `create_quick_event` tool already has full RRULE support with 6 examples in the tool schema
- The gap is in the system prompt: Rule 37 focuses on "remind me" language, not "every Tuesday" recurrence patterns
- Adding a system prompt rule is necessary but insufficient alone (same lesson as AM/PM)
- Code-level detection: if `create_quick_event` is called 3+ times in the same conversation with identical summaries and regular time intervals, the tool response should include a suggestion to use RRULE

**Alternatives considered**:
- Auto-consolidate individual events into recurring: Too invasive, might misinterpret
- Block individual event creation when recurrence detected: Too restrictive
- Only prompt-level fix: Insufficient based on prior experience

## Decision 4: Daily Context Time Filtering

**Decision**: Hybrid approach — filter past events in the tool output (`get_daily_context()`) AND reinforce with prompt rules.

**Rationale**:
- Rules 11b and 11e already exist in `03-daily-planner.md` but are prompt-only, so the LLM sometimes ignores them
- The `get_daily_context()` function returns ALL events for the day regardless of time
- Splitting output into "completed" and "upcoming" sections makes it structurally impossible for the LLM to present past events as current
- Feature 016 spec (FR-002) explicitly called for this but it was never implemented in the tool output

**Implementation**:
- `get_daily_context()` will split events into two groups:
  - "✅ Completed" — events with end time before now (dimmed/summarized)
  - "📋 Upcoming" — events with start time at or after now (full detail)
- Keep completed events visible (condensed) so the bot can reference "you already did X this morning" if asked

**Alternatives considered**:
- Remove past events entirely: Loses context the bot might need
- Prompt-only filtering: Already failed (Rules 11b, 11e exist but aren't reliably followed)
- Client-side filtering: No client — it's a WhatsApp bot

## Decision 5: One-Time Cleanup Scan

**Decision**: Implement as a triggered admin endpoint (not automatic on deploy) that scans future events, groups suspected corruptions into batches of 5, and sends to Erin via WhatsApp for confirmation.

**Rationale**:
- Auto-running on deploy is risky — could fire during a redeploy/rollback
- A manual trigger (e.g., admin API endpoint or scheduled job) is safer
- Batching into groups of 5 with simple A/B/C options keeps WhatsApp messages manageable
- Only future-dated events are scanned; past events are left untouched

**Cleanup flow**:
1. Scan all calendars for assistant-created events (`createdBy: mombot` tag) dated in the future
2. Filter events with start time between midnight and 8 AM that don't match the early-morning allowlist
3. Group into batches of 5
4. Send each batch to Erin: "I found these events that might have wrong times: [list]. A: Fix all, B: Skip, C: Review each"
5. Process responses and apply corrections

## Code Path Analysis

### Event Creation Paths (all need validation)

| Path | File | Lines | Entry Point |
|------|------|-------|-------------|
| `batch_create_events()` | `src/tools/calendar.py` | 400-438 | `_handle_write_calendar_blocks()` in assistant.py:1328 |
| `create_quick_event()` | `src/tools/calendar.py` | 334-397 | Lambda handler in assistant.py:1527 |
| `create_event()` | `src/tools/calendar.py` | 299-328 | Internal use only (not exposed as tool) |

### Event Reading Paths (need time filtering)

| Path | File | Lines | Purpose |
|------|------|-------|---------|
| `get_daily_context()` | `src/context.py` | 118-235 | Daily schedule snapshot |
| `_format_event()` | `src/context.py` | 243-267 | Time display formatting |
| `get_events_for_date()` | `src/tools/calendar.py` | 202-241 | Raw event fetch from Google |

### Timezone Configuration

- `TIMEZONE_STR = "America/Los_Angeles"` — `src/config.py:117`
- `TIMEZONE = ZoneInfo(TIMEZONE_STR)` — `src/config.py:118`
- Used consistently across context.py, calendar.py, chores.py, assistant.py
