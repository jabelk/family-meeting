# Contract: Google Calendar API v3

**Type**: REST API (our server → Google Calendar API)

**Base URL**: `https://www.googleapis.com/calendar/v3`
**Auth**: OAuth2 Bearer token (offline access, auto-refresh)
**Scope**: `https://www.googleapis.com/auth/calendar.events` (read + write events)

## Calendars

| Calendar | ID (from .env) | Access |
|----------|----------------|--------|
| Jason personal | `GOOGLE_CALENDAR_JASON_ID` | Read only |
| Erin personal | `GOOGLE_CALENDAR_ERIN_ID` | Read + Write |
| Shared family | `GOOGLE_CALENDAR_FAMILY_ID` | Read only |

## Read: List Events

**Used by**: Agenda generation (US1), Daily plan (US5)

```
GET /calendars/{calendarId}/events
  ?timeMin=2026-02-22T00:00:00-08:00
  &timeMax=2026-03-01T00:00:00-08:00
  &singleEvents=true
  &orderBy=startTime
```

**Response** (relevant fields):
```json
{
  "items": [
    {
      "id": "abc123",
      "summary": "Vienna school pickup",
      "start": { "dateTime": "2026-02-23T15:00:00-08:00" },
      "end": { "dateTime": "2026-02-23T15:30:00-08:00" },
      "extendedProperties": {
        "private": { "createdBy": "family-meeting-assistant" }
      }
    }
  ]
}
```

## Write: Create Event (single)

**Used by**: On-demand calendar adjustments

```
POST /calendars/{GOOGLE_CALENDAR_ERIN_ID}/events

{
  "summary": "Chore block",
  "start": { "dateTime": "2026-02-23T09:30:00-08:00", "timeZone": "America/Los_Angeles" },
  "end": { "dateTime": "2026-02-23T11:00:00-08:00", "timeZone": "America/Los_Angeles" },
  "colorId": "6",
  "extendedProperties": {
    "private": { "createdBy": "family-meeting-assistant" }
  }
}
```

## Write: Batch Create Events (weekly population)

**Used by**: Weekly calendar population (n8n Sunday cron → US5)

Uses Google Batch API to create 25-40 events in a single HTTP request.

```
POST https://www.googleapis.com/batch/calendar/v3
Content-Type: multipart/mixed; boundary=batch_boundary

--batch_boundary
Content-Type: application/http
Content-ID: <item1>

POST /calendar/v3/calendars/{calendarId}/events
Content-Type: application/json

{"summary": "Chore block", "start": {...}, "end": {...}, "colorId": "6", "extendedProperties": {...}}

--batch_boundary
Content-Type: application/http
Content-ID: <item2>

POST /calendar/v3/calendars/{calendarId}/events
...
--batch_boundary--
```

## Delete: Clear Assistant Events (before weekly refresh)

**Pattern**: Delete-and-recreate (simpler than diffing existing events)

```
# Step 1: Find all assistant-created events for the week
GET /calendars/{calendarId}/events
  ?timeMin=...&timeMax=...
  &privateExtendedProperty=createdBy%3Dfamily-meeting-assistant

# Step 2: Delete each one
DELETE /calendars/{calendarId}/events/{eventId}
```

## Color Coding

| colorId | Color   | Usage                        |
|---------|---------|------------------------------|
| 6       | Tangerine | Chore blocks               |
| 2       | Sage    | Rest / out-of-house time     |
| 10      | Basil   | Personal development         |
| 3       | Grape   | Exercise                     |
| 5       | Banana  | Side work (dad's real estate)|
| 1       | Lavender| Backlog item                 |

## Rate Limits

- 1,000,000 queries/day (free quota)
- Batch requests count as N individual requests
- No practical limit for this use case (~200 API calls/week max)

## Error Handling

- `401 Unauthorized`: Token expired — refresh via `google.auth.transport.requests.Request()`
- `403 Rate Limit`: Back off and retry (unlikely at our volume)
- `404 Not Found`: Calendar ID misconfigured — log error, skip calendar
- `409 Conflict`: Event already exists — safe to ignore on batch create
