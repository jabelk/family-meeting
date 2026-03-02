# Quickstart: iOS Work Calendar Sync

**Feature**: 015-ios-work-calendar | **Date**: 2026-03-02

## Prerequisites

- Running FastAPI server (local or Docker)
- `N8N_WEBHOOK_SECRET` set in `.env`

## Integration Test Scenarios

### Scenario 1: Push Work Events

Push sample events for tomorrow and verify storage.

```bash
# Set your secret
export N8N_SECRET="your-n8n-webhook-secret"

# Push 2 events for tomorrow
TOMORROW=$(date -v+1d +%Y-%m-%d)
curl -X POST http://localhost:8000/api/v1/calendar/work-events \
  -H "Content-Type: application/json" \
  -H "X-N8N-Auth: $N8N_SECRET" \
  -d "{
    \"events\": [
      {\"title\": \"Standup\", \"start\": \"${TOMORROW}T09:00:00\", \"end\": \"${TOMORROW}T09:30:00\"},
      {\"title\": \"Project sync\", \"start\": \"${TOMORROW}T14:00:00\", \"end\": \"${TOMORROW}T15:00:00\"}
    ]
  }"

# Expected response:
# {"status":"ok","events_received":2,"dates_covered":["2026-03-03"],"message":"Stored 2 events covering 1 day"}
```

### Scenario 2: Verify get_outlook_events Uses Pushed Data

After pushing events, verify the tool reads from the file.

```bash
# With OUTLOOK_CALENDAR_ICS_URL unset (empty), the tool should read from work_calendar.json
python3 -c "
from src.tools.outlook import get_outlook_events
result = get_outlook_events('$(date -v+1d +%Y-%m-%d)')
print(result)
"

# Expected: "Jason's work meetings on [Day], [Date]:\n- 9:00 AM-9:30 AM: Standup\n- 2:00 PM-3:00 PM: Project sync"
```

### Scenario 3: Push Empty Day (Jason is free)

```bash
TOMORROW=$(date -v+1d +%Y-%m-%d)
curl -X POST http://localhost:8000/api/v1/calendar/work-events \
  -H "Content-Type: application/json" \
  -H "X-N8N-Auth: $N8N_SECRET" \
  -d '{"events": []}'

# Expected: {"status":"ok","events_received":0,"dates_covered":[],"message":"Stored 0 events covering 0 days"}

# Then verify:
python3 -c "
from src.tools.outlook import get_outlook_events
print(get_outlook_events('${TOMORROW}'))
"
# If day was previously pushed with events and now pushed empty → should show no meetings
```

### Scenario 4: Verify Auth Rejection

```bash
curl -X POST http://localhost:8000/api/v1/calendar/work-events \
  -H "Content-Type: application/json" \
  -H "X-N8N-Auth: wrong-secret" \
  -d '{"events": []}'

# Expected: 401 {"detail":"Invalid or missing X-N8N-Auth header"}
```

### Scenario 5: Verify 7-Day Expiration

```python
# Simulate stale data by manually editing work_calendar.json
import json
from pathlib import Path

data_file = Path("data/work_calendar.json")
data = json.loads(data_file.read_text()) if data_file.exists() else {}

# Add a stale entry (8 days ago)
data["2026-02-22"] = {
    "events": [{"title": "Old meeting", "start": "2026-02-22T10:00:00", "end": "2026-02-22T11:00:00"}],
    "received_at": "2026-02-22T19:00:00"
}
data_file.write_text(json.dumps(data, indent=2))

# Now call get_outlook_events for that date — should return "unavailable"
from src.tools.outlook import get_outlook_events
result = get_outlook_events("2026-02-22")
print(result)  # Should say "work schedule unavailable" or similar
```

### Scenario 6: Full Weekly Push (Simulates iOS Shortcut)

```bash
# Simulate what the iOS Shortcut sends — a full week Mon-Fri
curl -X POST http://localhost:8000/api/v1/calendar/work-events \
  -H "Content-Type: application/json" \
  -H "X-N8N-Auth: $N8N_SECRET" \
  -d '{
    "events": [
      {"title": "Standup", "start": "2026-03-03T09:00:00", "end": "2026-03-03T09:30:00"},
      {"title": "Sprint planning", "start": "2026-03-03T10:00:00", "end": "2026-03-03T11:00:00"},
      {"title": "Standup", "start": "2026-03-04T09:00:00", "end": "2026-03-04T09:30:00"},
      {"title": "1:1 with manager", "start": "2026-03-04T14:00:00", "end": "2026-03-04T14:30:00"},
      {"title": "Standup", "start": "2026-03-05T09:00:00", "end": "2026-03-05T09:30:00"},
      {"title": "Team retro", "start": "2026-03-05T15:00:00", "end": "2026-03-05T16:00:00"},
      {"title": "Standup", "start": "2026-03-06T09:00:00", "end": "2026-03-06T09:30:00"},
      {"title": "Standup", "start": "2026-03-07T09:00:00", "end": "2026-03-07T09:30:00"},
      {"title": "All hands", "start": "2026-03-07T11:00:00", "end": "2026-03-07T12:00:00"}
    ]
  }'

# Expected: {"status":"ok","events_received":9,"dates_covered":["2026-03-03","2026-03-04","2026-03-05","2026-03-06","2026-03-07"],"message":"Stored 9 events covering 5 days"}
```
