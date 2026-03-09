# Contract: In-App Scheduler Configuration

**Feature**: 020-railway-cloud-deploy
**Type**: Internal configuration

## Schedule Config File

**Path**: `data/schedules.json`
**Loaded by**: `src/scheduler.py` (new module)
**Persistence**: Railway Volume at `/app/data/`

### Schema

```json
{
  "timezone": "<IANA timezone string>",
  "jobs": [
    {
      "id": "<unique job identifier>",
      "endpoint": "<relative path under /api/v1/>",
      "schedule": {
        "minute": "<cron minute or int>",
        "hour": "<cron hour or int>",
        "day": "<day of month (optional)>",
        "day_of_week": "<cron day_of_week (optional)>"
      },
      "enabled": true
    }
  ]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timezone` | string | Yes | IANA timezone (e.g., `America/Los_Angeles`) |
| `jobs[].id` | string | Yes | Unique identifier for the job |
| `jobs[].endpoint` | string | Yes | Path relative to `/api/v1/` (e.g., `briefing/daily`) |
| `jobs[].schedule` | object | Yes | APScheduler CronTrigger kwargs |
| `jobs[].enabled` | boolean | Yes | Whether the job is active |

### Behavior

- Scheduler starts on FastAPI lifespan startup if `SCHEDULER_ENABLED` != `false`
- Jobs call the endpoint handler functions directly (not via HTTP)
- If `data/schedules.json` doesn't exist, a default is created from the template
- Changes to `schedules.json` require an app restart to take effect
- Each job logs its execution start/end to the standard logger
