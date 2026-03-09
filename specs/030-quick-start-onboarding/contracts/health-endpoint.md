# Contract: Health Endpoint (Updated)

**Type**: HTTP API
**Endpoint**: `GET /health`

## Changes from Current Behavior

The only change is to the status determination logic. Unconfigured optional integrations no longer cause "degraded" status.

### Current Status Logic
```
healthy  = all required connected AND all optional connected
degraded = all required connected AND some optional failing
unhealthy = any required failing
```

### New Status Logic
```
healthy   = all required connected AND all configured-optional connected
degraded  = all required connected AND some configured-optional failing
unhealthy = any required failing
```

**Key difference**: Unconfigured optional integrations (`"configured": false`) are excluded from the status calculation entirely.

## Response Schema

No changes to the response schema. The existing fields (`status`, `family`, `bot_name`, `uptime_seconds`, `integrations`) remain the same.

## Examples

### Minimal deployment (WhatsApp + AI only)
```json
{
  "status": "healthy",
  "family": "The Garcia Family",
  "bot_name": "Home Helper",
  "uptime_seconds": 42,
  "integrations": {
    "whatsapp": {"required": true, "configured": true, "connected": true, "error": null},
    "ai_api": {"required": true, "configured": true, "connected": true, "error": null},
    "notion": {"required": false, "configured": false, "connected": false, "error": null},
    "google_calendar": {"required": false, "configured": false, "connected": false, "error": null},
    "ynab": {"required": false, "configured": false, "connected": false, "error": null},
    "anylist": {"required": false, "configured": false, "connected": false, "error": null},
    "outlook": {"required": false, "configured": false, "connected": false, "error": null}
  }
}
```

Status: **healthy** (all configured integrations are connected; unconfigured ones don't count)

### Full deployment with Notion failing
```json
{
  "status": "degraded",
  "integrations": {
    "whatsapp": {"required": true, "configured": true, "connected": true, "error": null},
    "ai_api": {"required": true, "configured": true, "connected": true, "error": null},
    "notion": {"required": false, "configured": true, "connected": false, "error": "Connection timeout"},
    "google_calendar": {"required": false, "configured": true, "connected": true, "error": null}
  }
}
```

Status: **degraded** (Notion is configured but failing)
