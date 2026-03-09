# Contract: Enhanced Health Check Endpoint

## Endpoint

`GET /health`

## Authentication

None required (public endpoint for monitoring).

## Response

### 200 OK — Healthy or Degraded

All required integrations are configured and connected. Optional integrations may be missing or disconnected.

```json
{
  "status": "healthy",
  "family": "The Belk Family",
  "bot_name": "Mom Bot",
  "uptime_seconds": 3847,
  "integrations": {
    "whatsapp": {
      "required": true,
      "configured": true,
      "connected": true,
      "error": null
    },
    "ai_api": {
      "required": true,
      "configured": true,
      "connected": true,
      "error": null
    },
    "notion": {
      "required": false,
      "configured": true,
      "connected": true,
      "error": null
    },
    "google_calendar": {
      "required": false,
      "configured": true,
      "connected": true,
      "error": null
    },
    "ynab": {
      "required": false,
      "configured": false,
      "connected": false,
      "error": null
    },
    "anylist": {
      "required": false,
      "configured": true,
      "connected": false,
      "error": "Connection refused: anylist-sidecar:3000"
    },
    "outlook": {
      "required": false,
      "configured": true,
      "connected": true,
      "error": null
    }
  }
}
```

### Degraded status

When optional integrations fail but all required pass:

```json
{
  "status": "degraded",
  "family": "The Belk Family",
  "bot_name": "Mom Bot",
  "uptime_seconds": 3847,
  "integrations": { "..." }
}
```

### 503 Service Unavailable — Unhealthy

When one or more required integrations are not configured or not connected:

```json
{
  "status": "unhealthy",
  "family": "The Belk Family",
  "bot_name": "Mom Bot",
  "uptime_seconds": 12,
  "integrations": {
    "whatsapp": {
      "required": true,
      "configured": false,
      "connected": false,
      "error": "WHATSAPP_ACCESS_TOKEN not set"
    },
    "ai_api": {
      "required": true,
      "configured": true,
      "connected": true,
      "error": null
    }
  }
}
```

## Status Logic

- `"healthy"`: All required integrations configured + connected, all optional configured ones connected
- `"degraded"`: All required pass, but one or more configured optional integrations are disconnected
- `"unhealthy"`: One or more required integrations are not configured or not connected

## Integration Checks

| Integration | Required | Config Check | Connectivity Check |
|-------------|----------|-------------|-------------------|
| `whatsapp` | Yes | WHATSAPP_ACCESS_TOKEN + WHATSAPP_PHONE_NUMBER_ID exist | Env vars non-empty |
| `ai_api` | Yes | ANTHROPIC_API_KEY exists | Env var non-empty |
| `notion` | No | NOTION_TOKEN exists | `notion.users.me()` succeeds |
| `google_calendar` | No | GOOGLE_TOKEN_JSON or GOOGLE_CREDENTIALS_JSON exists | Calendar list API call succeeds |
| `ynab` | No | YNAB_ACCESS_TOKEN exists | HTTP HEAD to api.ynab.com with auth |
| `anylist` | No | ANYLIST_SIDECAR_URL exists | HTTP GET to sidecar /health |
| `outlook` | No | OUTLOOK_CALENDAR_ICS_URL exists | Env var non-empty (no live check) |

## Timeout

Each integration connectivity check has a 5-second timeout. Total endpoint response time should not exceed 10 seconds.

## Backward Compatibility

The endpoint path (`/health`) and success HTTP status code (200) remain the same. Railway health checks continue to work. The response body changes from `{"status": "ok"}` to the enhanced format — no external systems depend on the old response body.
