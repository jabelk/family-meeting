# API Contract: Work Calendar Events Endpoint

**Feature**: 015-ios-work-calendar | **Date**: 2026-03-02

## POST /api/v1/calendar/work-events

Receives work calendar events from Jason's iOS Shortcut and stores them for daily plan generation.

### Authentication

| Header | Value | Required |
|--------|-------|----------|
| `X-N8N-Auth` | Shared secret (`N8N_WEBHOOK_SECRET`) | Yes |

Same authentication pattern as all other `/api/v1/*` endpoints.

### Request

**Content-Type**: `application/json`

```json
{
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
    },
    {
      "title": "1:1 with manager",
      "start": "2026-03-04T10:00:00",
      "end": "2026-03-04T10:30:00"
    }
  ]
}
```

**Request Model**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `events` | `list[WorkEventInput]` | Yes | List of work calendar events. Can be empty (signals "no meetings" for covered dates). |

**WorkEventInput**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `str` | Yes | Event title |
| `start` | `str` | Yes | ISO 8601 datetime (e.g., `2026-03-03T09:00:00`) |
| `end` | `str` | Yes | ISO 8601 datetime |

### Response

**200 OK**:

```json
{
  "status": "ok",
  "events_received": 3,
  "dates_covered": ["2026-03-03", "2026-03-04"],
  "message": "Stored 3 events covering 2 days"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | Always `"ok"` on success |
| `events_received` | `int` | Total number of events received |
| `dates_covered` | `list[str]` | ISO date strings for all dates that had events stored |
| `message` | `str` | Human-readable summary |

**401 Unauthorized** (missing or invalid `X-N8N-Auth`):

```json
{
  "detail": "Invalid or missing X-N8N-Auth header"
}
```

### Behavior

1. Parse each event's `start` datetime to determine the date (`YYYY-MM-DD`).
2. Group events by date.
3. For each date, **replace** all existing events with the new ones (full replace, not merge).
4. Set `received_at` to the current server timestamp.
5. Auto-prune entries older than 7 days from the file.
6. Write atomically (temp file + rename).
7. Return summary immediately (synchronous — no background task needed).

### Edge Cases

- **Empty events list**: Logs a warning, returns success with `events_received: 0`. Does not modify stored data (nothing to group by date).
- **Events spanning multiple dates**: Each event is grouped under its start date.
- **Duplicate events**: Stored as-is. No deduplication — reflects actual calendar state.
- **Malformed datetime**: Returns 422 Validation Error (Pydantic rejects it).

### Example curl

```bash
curl -X POST https://mombot.sierrastoryco.com/api/v1/calendar/work-events \
  -H "Content-Type: application/json" \
  -H "X-N8N-Auth: $N8N_WEBHOOK_SECRET" \
  -d '{
    "events": [
      {"title": "Standup", "start": "2026-03-03T09:00:00", "end": "2026-03-03T09:30:00"},
      {"title": "Project sync", "start": "2026-03-03T14:00:00", "end": "2026-03-03T15:00:00"}
    ]
  }'
```
