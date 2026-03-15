# Tool Contracts: Calendar Reliability

**Feature**: 037-calendar-reliability | **Date**: 2026-03-15

## Modified Tool: `write_calendar_blocks`

No schema changes. Behavior change: times are now validated before submission.

### Response Format Changes

**Before** (current):
```
Created 15 calendar blocks on Erin's calendar.
```

**After** (with corrections):
```
Created 15 calendar blocks on Erin's calendar.
⚠️ Time corrections applied:
  - "School pickup: Vienna" corrected: 2:30 AM → 2:30 PM
  - "Swim lessons" corrected: 4:00 AM → 4:00 PM
  - "Return home & dinner prep" corrected: 5:00 AM → 5:00 PM
```

**After** (no corrections needed):
```
Created 15 calendar blocks on Erin's calendar.
```

## Modified Tool: `create_quick_event`

No schema changes. Behavior change: time validated before submission.

### Response Format Changes

**Before**:
```
Created reminder on family calendar: Cleaners (abc123)
```

**After** (with correction):
```
Created reminder on family calendar: Cleaners (abc123)
⚠️ Time corrected: 2:00 AM → 2:00 PM
```

## Modified Tool: `get_daily_context`

No schema changes. Output format changes to separate completed vs upcoming events.

### Output Format Changes

**Before** (all events in one list per calendar):
```
👤 Erin's events today:
- 7:00 AM – 8:00 AM: Morning routine & breakfast
- 9:00 AM – 10:00 AM: Gym
- 1:00 PM – 1:30 PM: Zoey quiet time
- 2:30 PM – 3:00 PM: School pickup: Vienna
- 4:00 PM – 5:00 PM: Swim lessons
```

**After** (split by current time — example at 2 PM):
```
👤 Erin's events today:
  ✅ Completed:
  - 7:00 AM – 8:00 AM: Morning routine & breakfast
  - 9:00 AM – 10:00 AM: Gym
  - 1:00 PM – 1:30 PM: Zoey quiet time
  📋 Upcoming:
  - 2:30 PM – 3:00 PM: School pickup: Vienna
  - 4:00 PM – 5:00 PM: Swim lessons
```

**After** (early morning — no filtering applied):
```
👤 Erin's events today:
  📋 Upcoming:
  - 7:00 AM – 8:00 AM: Morning routine & breakfast
  - 9:00 AM – 10:00 AM: Gym
  ...
```

## New Internal Function: `_validate_event_time()`

Not a tool — internal utility in `src/tools/calendar.py`.

### Contract

```
Input:
  start_time: str (ISO 8601 or informal time string)
  end_time: str (ISO 8601 or informal time string)
  summary: str (event title, used for allowlist matching)

Output:
  tuple[str, str, list[str]]
  - corrected_start_time: str (ISO 8601)
  - corrected_end_time: str (ISO 8601)
  - corrections: list[str] (human-readable correction messages, empty if none)

Behavior:
  1. Parse start_time and end_time to datetime objects
  2. If either time falls between 00:00 and 07:59:
     a. Check summary against early-morning allowlist (case-insensitive substring match)
     b. If NO match: shift +12 hours, add correction message
     c. If match: preserve original time
  3. Return corrected times and list of correction messages
```

## New Endpoint: Cleanup Scan (Admin)

### `POST /api/v1/admin/calendar-cleanup`

Triggers one-time scan of future-dated assistant-created events for AM/PM errors. Sends results to user via WhatsApp for confirmation.

**Auth**: Bearer token (reuses `N8N_WEBHOOK_SECRET`)

**Request**: No body required.

**Response**:
```json
{
  "status": "started",
  "events_scanned": 45,
  "suspects_found": 8,
  "batches_queued": 2
}
```

**WhatsApp Message to User** (per batch):
```
🔧 Calendar Cleanup (Batch 1/2)

I found 5 events that might have wrong times:

1. "School pickup: Vienna" — 2:30 AM → 2:30 PM (Mar 17)
2. "Swim lessons" — 4:00 AM → 4:00 PM (Mar 17)
3. "Dinner prep" — 5:00 AM → 5:00 PM (Mar 17)
4. "Zoey quiet time" — 1:30 AM → 1:30 PM (Mar 18)
5. "Pickup Vienna" — 2:30 AM → 2:30 PM (Mar 18)

A: Fix all 5
B: Skip these
C: Let me review each one
```
