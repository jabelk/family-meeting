# Data Model: Context-Aware Bot

**Feature**: 014-context-aware-bot | **Date**: 2026-03-01

## Entities

### 1. Daily Context (transient — computed per call, not stored)

The output of `get_daily_context()`. Not persisted — computed fresh each invocation.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| current_time | str | `datetime.now(PACIFIC)` | Formatted Pacific time |
| communication_mode | str | Time + preferences | One of: "morning", "afternoon", "evening", "late_night" |
| jason_events | list[dict] | Google Calendar API | Today's events from Jason's calendar |
| erin_events | list[dict] | Google Calendar API | Today's events from Erin's calendar |
| family_events | list[dict] | Google Calendar API | Today's events from family calendar |
| childcare_status | str | Inferred from events | Who has Zoey and until when |
| active_preferences | list[dict] | `preferences.get_preferences()` | User's stored preferences |
| pending_backlog_count | int | `notion.get_backlog_items()` | Number of open backlog items |
| calendar_available | bool | API success/failure | False if Google Calendar unreachable |

### 2. Communication Mode (derived — not stored separately)

| Mode | Default Hours (Pacific) | Proactive Content | Tone |
|------|------------------------|-------------------|------|
| morning | 7:00 AM – 12:00 PM | Yes — suggest tasks, chores, plans | Energetic, encouraging |
| afternoon | 12:00 PM – 5:00 PM | Limited — respond normally | Normal, helpful |
| evening | 5:00 PM – 9:00 PM | No — only respond to direct questions | Calm, brief |
| late_night | 9:00 PM – 7:00 AM | No — minimal direct answers only | Minimal, no follow-ups |

Boundaries are customizable via preferences (e.g., `quiet_hours` preference "quiet after 8pm" shifts late_night start to 8:00 PM).

### 3. Routine (persisted in `data/routines.json`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | str | `rtn_` + 8 hex chars | Unique identifier |
| name | str | Required, unique per phone | Routine name (e.g., "morning skincare") |
| steps | list[RoutineStep] | 1-30 steps | Ordered list of steps |
| created | str | ISO 8601 | Creation timestamp |
| modified | str | ISO 8601 | Last modification timestamp |

**Validation rules**:
- Name: required, max 50 chars, normalized to lowercase for matching
- Steps: at least 1, max 30 per routine
- Max 20 routines per user
- Duplicate name detection (case-insensitive): overwrites existing

### 4. Routine Step (embedded in Routine)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| position | int | 1-based, sequential | Order within routine |
| description | str | Required, max 200 chars | Step description |

**Modification operations**:
- Insert after: Shifts subsequent positions +1
- Remove: Shifts subsequent positions -1
- Reorder: Accepts new position, adjusts others accordingly

## Relationships

```text
Phone Number (user)
├── has many → Routines (data/routines.json)
├── has many → Preferences (data/user_preferences.json, existing)
└── triggers → Daily Context (computed per get_daily_context call)
                ├── reads → Google Calendar events (3 calendars)
                ├── reads → User preferences
                ├── reads → Backlog items (Notion)
                └── derives → Communication mode + Childcare status
```

## Storage Files

| File | Pattern | Module |
|------|---------|--------|
| `data/routines.json` | NEW — same as preferences.py | `src/routines.py` |
| `data/user_preferences.json` | EXISTING — read by context tool | `src/preferences.py` |
| `data/conversations.json` | EXISTING — unchanged | `src/conversation.py` |

All JSON files use the established pattern: `_DATA_DIR` detection, in-memory dict cache, atomic writes (write .tmp → rename), auto-load on module import.
