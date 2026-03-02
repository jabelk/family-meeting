# Data Model: iOS Work Calendar Sync

**Feature**: 015-ios-work-calendar | **Date**: 2026-03-02

## Entities

### WorkCalendarStore

The top-level JSON file containing all pushed work calendar data.

**File**: `data/work_calendar.json`

```json
{
  "2026-03-03": {
    "events": [
      {
        "title": "Standup",
        "start": "2026-03-03T09:00:00",
        "end": "2026-03-03T09:30:00"
      },
      {
        "title": "Project sync",
        "start": "2026-03-03T14:00:00",
        "end": "2026-03-03T15:00:00"
      }
    ],
    "received_at": "2026-03-02T19:00:15"
  },
  "2026-03-04": {
    "events": [],
    "received_at": "2026-03-02T19:00:15"
  }
}
```

**Schema**:
- **Top-level**: `dict[str, WorkCalendarDay]` — keys are ISO date strings (`YYYY-MM-DD`)
- Auto-pruned: entries with `received_at` older than 7 days are removed on every write

### WorkCalendarDay

A single date's worth of work events.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `events` | `list[WorkEvent]` | Yes | List of events for this date. Empty list = "no meetings" (Jason is free). |
| `received_at` | `str` (ISO 8601) | Yes | Timestamp when this data was received. Used for 7-day expiration. |

### WorkEvent

A single calendar event (time block).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `str` | Yes | Event title (e.g., "Standup", "1:1 with manager"). Displayed for context but content isn't critical. |
| `start` | `str` (ISO 8601) | Yes | Event start time. Can be datetime or date-only for all-day events. |
| `end` | `str` (ISO 8601) | Yes | Event end time. |

## Relationships

- **WorkCalendarStore** contains 0–7 **WorkCalendarDay** entries (one week's worth)
- Each **WorkCalendarDay** contains 0–N **WorkEvent** entries
- `get_outlook_events()` reads the **WorkCalendarDay** for the requested date
- `get_outlook_busy_windows()` reads the same data and returns structured tuples

## Validation Rules

- Date keys must be valid ISO date format (`YYYY-MM-DD`)
- `received_at` must be valid ISO 8601 datetime
- `start` and `end` must be valid ISO 8601 datetime strings
- `title` must be a non-empty string
- Events are stored as-is (no deduplication) — reflects actual calendar state
- Entries older than 7 days are treated as expired and auto-pruned

## State Transitions

```
No Data → Data Pushed → Data Fresh (≤7 days) → Data Expired (>7 days) → Pruned
                ↑                                                          |
                └──────────────── Next weekly push ────────────────────────┘
```

- **No Data**: Date key absent from file. Bot says "work schedule unavailable."
- **Data Fresh**: Date key present, `received_at` ≤ 7 days ago. Bot uses events.
- **Data Expired**: Date key present but `received_at` > 7 days ago. Treated as "no data."
- **Pruned**: Expired entries removed from file on next write operation.
