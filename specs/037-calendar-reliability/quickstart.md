# Quickstart: Calendar Reliability

**Feature**: 037-calendar-reliability | **Date**: 2026-03-15

## What This Feature Does

Fixes three calendar reliability issues that have persisted despite three prior fix attempts:

1. **AM/PM time bug**: Events created at "2 AM" instead of "2 PM" — now caught and corrected at the code level before hitting Google Calendar
2. **Recurring events**: Bot creates 7 individual events instead of one recurring event — now reinforced with prompt rules and code-level detection
3. **Time-aware responses**: Bot shows morning events at 2 PM — now filters past events in tool output

## Key Changes

### Files Modified

| File | Change |
|------|--------|
| `src/tools/calendar.py` | Add `_validate_event_time()` utility; call from `batch_create_events()` and `create_quick_event()` |
| `src/context.py` | Split `get_daily_context()` output into completed/upcoming sections |
| `src/prompts/system/07-calendar-reminders.md` | Add explicit rule to detect recurrence language and use RRULE |
| `src/prompts/tools/calendar.md` | Strengthen recurring event instructions |
| `src/app.py` | Add `/api/v1/admin/calendar-cleanup` endpoint |

### Files Created

| File | Purpose |
|------|---------|
| None | All changes are modifications to existing files |

## How to Test

### 1. Time Validation (P1)

```bash
# Run unit tests for the new validation function
pytest tests/ -k "test_validate_event_time" -v
```

Manual test via WhatsApp:
- Ask the bot to "schedule my day" and verify all events are at correct times
- Check Google Calendar to confirm events are stored with correct ISO times

### 2. Recurring Events (P2)

Manual test via WhatsApp:
- Say "Add a weekly Monday gym class at 9am"
- Verify ONE recurring event is created (not 52 individual events)
- Check Google Calendar for RRULE on the event

### 3. Time-Aware Responses (P3)

Manual test via WhatsApp:
- At 2 PM, ask "what's on my schedule?"
- Verify morning events are shown as "Completed" and afternoon events are shown as "Upcoming"

### 4. Cleanup Scan

```bash
# Trigger the cleanup scan
curl -X POST https://mombot.sierracodeco.com/api/v1/admin/calendar-cleanup \
  -H "Authorization: Bearer $N8N_WEBHOOK_SECRET"
```

Check WhatsApp for batch cleanup messages sent to Erin.

## Deployment Notes

- No new dependencies
- No database changes
- No environment variable changes
- Safe to deploy incrementally (P1 → P2 → P3 → cleanup)
- The early-morning allowlist is defined as a module-level constant in `calendar.py` — can be updated without redeployment via config if needed later
