# Data Model: Calendar Reliability

**Feature**: 037-calendar-reliability | **Date**: 2026-03-15

## Entities

### TimeValidationResult

Returned by the time validation utility when an event time is checked before calendar API submission.

| Field | Type | Description |
|-------|------|-------------|
| original_time | str | ISO 8601 datetime string as provided by the LLM |
| corrected_time | str | ISO 8601 datetime string after validation (may equal original) |
| was_corrected | bool | True if the time was changed |
| correction_reason | str | Human-readable reason (e.g., "shifted +12h: 'swim lessons' at 2 AM is likely 2 PM") |
| matched_allowlist | bool | True if summary matched early-morning allowlist (no correction applied) |

### EarlyMorningAllowlist

Configurable list of keywords that indicate a legitimate early-morning event (before 8 AM). Events matching these keywords are NOT shifted +12 hours.

| Field | Type | Description |
|-------|------|-------------|
| keywords | list[str] | Lowercase keyword fragments to match against event summary |

**Default keywords**: workout, gym, exercise, run, jog, walk, wake up, wake, alarm, morning routine, breakfast, coffee, ski, skiing, flight, airport, travel, drive, feed, nursing

### DailyContextSection

Structure of the daily context output after time-aware filtering is applied.

| Field | Type | Description |
|-------|------|-------------|
| current_time | str | Formatted current time in Pacific |
| communication_mode | str | morning/afternoon/evening/late-night |
| completed_events | dict[str, list[str]] | Past events grouped by calendar source (partner1, partner2, family) |
| upcoming_events | dict[str, list[str]] | Future events grouped by calendar source |
| childcare_status | str | Current childcare inference |
| backlog_count | int | Pending backlog items |
| preferences_count | int | Active preferences |

### CleanupBatch

A batch of suspected corrupted events presented to the user for confirmation.

| Field | Type | Description |
|-------|------|-------------|
| batch_number | int | Sequence number (1-based) |
| total_batches | int | Total number of batches |
| events | list[CleanupCandidate] | Up to 5 events per batch |

### CleanupCandidate

A single event suspected of having an AM/PM error.

| Field | Type | Description |
|-------|------|-------------|
| event_id | str | Google Calendar event ID |
| calendar_name | str | Which calendar (erin, family, etc.) |
| summary | str | Event title |
| current_start | str | Current start time (wrong, e.g., "2:00 AM") |
| proposed_start | str | Proposed corrected time (e.g., "2:00 PM") |
| current_end | str | Current end time |
| proposed_end | str | Proposed corrected end time |

## State Transitions

### Cleanup Flow

```
IDLE → SCANNING → PRESENTING_BATCH → AWAITING_RESPONSE → PROCESSING → PRESENTING_BATCH (next) → COMPLETE
```

- **SCANNING**: System queries future events, filters for suspected AM/PM errors
- **PRESENTING_BATCH**: System sends batch of ≤5 events to user via WhatsApp
- **AWAITING_RESPONSE**: System waits for user reply (A/B/C)
- **PROCESSING**: System applies corrections for approved events
- **COMPLETE**: All batches processed or user opted to skip remaining

## Relationships

- `TimeValidationResult` is produced by `_validate_event_time()` for every event before calendar API submission
- `EarlyMorningAllowlist` is checked by `_validate_event_time()` to determine if correction should be skipped
- `DailyContextSection` replaces the current flat-text output of `get_daily_context()`
- `CleanupBatch` contains `CleanupCandidate` entries (max 5 per batch)
