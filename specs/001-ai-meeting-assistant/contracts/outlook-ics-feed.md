# Contract: Outlook ICS Feed (Jason's Work Calendar)

**Type**: Published ICS calendar feed (read-only, HTTP GET)

**URL**: Stored in `.env` as `OUTLOOK_CALENDAR_ICS_URL`
**Auth**: None (URL contains a secret token — treat as credential)
**Format**: iCalendar (RFC 5545)

## Fetching the Feed

```
GET {OUTLOOK_CALENDAR_ICS_URL}
Accept: text/calendar
```

**Response**: Full iCalendar file with all events (VEVENT components).

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Microsoft Corporation//Outlook 16.0//EN
BEGIN:VEVENT
DTSTART:20260223T160000Z
DTEND:20260223T170000Z
SUMMARY:Team Standup
DESCRIPTION:Weekly team sync
LOCATION:Webex
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR
END:VEVENT
BEGIN:VEVENT
DTSTART:20260224T180000Z
DTEND:20260224T190000Z
SUMMARY:1:1 with Manager
END:VEVENT
END:VCALENDAR
```

## Parsing

**Libraries**: `icalendar` (parse) + `recurring-ical-events` (expand recurring events)

```python
import icalendar
import recurring_ical_events
from datetime import date

cal = icalendar.Calendar.from_ical(response.text)
events = recurring_ical_events.of(cal).between(start_date, end_date)

for event in events:
    summary = str(event.get("SUMMARY", ""))
    start = event.get("DTSTART").dt
    end = event.get("DTEND").dt
```

## Data Extracted

| Field    | ICS Property | Used For                                  |
|----------|-------------|-------------------------------------------|
| Summary  | SUMMARY     | Event title for daily plan display         |
| Start    | DTSTART     | Determine Jason's busy windows             |
| End      | DTEND       | Calculate meeting duration                 |
| Location | LOCATION    | Optional — show if present                 |

**Not needed**: DESCRIPTION, ATTENDEES, ORGANIZER (too verbose for daily plan)

## Usage Patterns

1. **Daily plan generation** (US5): Fetch ICS → filter today's events → identify Jason's meeting blocks → determine breakfast window
2. **Weekly agenda** (US1): Fetch ICS → filter next 7 days → show Jason's notable work events (optional, only if relevant)

## Polling Strategy

- Fetch on demand (when generating daily plan or agenda)
- No caching — the ICS URL always returns current data
- Typical fetch time: <1 second (small calendar, direct HTTP)

## Setup

Jason goes to: outlook.office365.com → Settings → Calendar → Shared calendars → Publish a calendar → Select calendar → Copy ICS link

**One-time setup**: Copy the ICS URL to `.env` as `OUTLOOK_CALENDAR_ICS_URL`

## Error Handling

- `403 Forbidden` or `404 Not Found`: ICS publishing may have been disabled by Cisco IT. Fall back: "Couldn't check Jason's work calendar — you may want to ask him about morning meetings"
- Network timeout: Skip work calendar data, generate plan without it
- Parse error: Log and skip — don't crash the daily plan generation
