# Data Model: Smart Daily Planner

**Feature**: 017-smart-daily-planner | **Date**: 2026-03-03

## Entities

### Drive Time Entry

A stored association between a location name and its one-way drive time from home.

| Field | Type | Description |
|-------|------|-------------|
| location | string | Human-readable location name (e.g., "gym", "school", "grandma's") |
| minutes | int | One-way drive time from home in minutes |
| updated | string (ISO datetime) | When this entry was last added or modified |

**Storage**: `data/drive_times.json`

```json
{
  "gym": {"minutes": 5, "updated": "2026-03-03T10:30:00"},
  "school": {"minutes": 10, "updated": "2026-03-03T10:30:00"},
  "grandma": {"minutes": 15, "updated": "2026-03-03T10:30:00"},
  "church": {"minutes": 12, "updated": "2026-03-03T10:30:00"}
}
```

**Identity**: Location name (lowercase, normalized). Duplicate location names overwrite the existing entry.

**Lifecycle**: Created when user says "the gym is 5 minutes away." Updated when user says "gym is actually 10 minutes now." Deleted if user requests removal. No automatic expiry.

**Constraints**:
- Maximum 20 entries (family has <10 common locations, 20 provides headroom)
- Minutes must be a positive integer (1-120)
- Location names normalized to lowercase, stripped of articles ("the gym" → "gym")

### Existing Entities (unchanged)

- **Calendar Event**: Already read by `get_daily_context()` via `get_events_for_date()`. No changes needed — events are returned as structured text with times and descriptions.
- **Daily Plan Draft**: Exists only in chat conversation context. Not persisted anywhere — Claude generates it, presents it, and writes to calendar only after confirmation. No new storage needed.

## Relationships

```
Drive Time Entry --used-by--> Daily Plan Generation (via system prompt rules)
Calendar Event (existing) --read-by--> get_daily_context() --feeds--> Daily Plan Generation
Daily Plan Draft --confirmed--> write_calendar_blocks() --writes--> Google Calendar
```

## Tools (new)

| Tool Name | Parameters | Returns | Purpose |
|-----------|-----------|---------|---------|
| `get_drive_times` | none | JSON string of all drive times | Read during plan generation |
| `save_drive_time` | location (str), minutes (int) | Confirmation string | Add/update when user mentions a drive time |
| `delete_drive_time` | location (str) | Confirmation string | Remove a stored drive time |
