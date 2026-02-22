# Contract: AnyList Node.js Sidecar

**Type**: Local REST API (Python FastAPI → Node.js sidecar on localhost)

**Base URL**: `http://anylist-sidecar:3000` (Docker network) or `http://localhost:3000` (dev)
**Auth**: None (internal network only — not exposed to internet)

## Overview

AnyList has no official public API. The `codetheweb/anylist` npm package
reverse-engineers their protobuf-based API. We wrap it in a small Express
server to give our Python app a clean REST interface.

## Authentication

The sidecar authenticates to AnyList servers on startup using credentials
from environment variables:

```
ANYLIST_EMAIL=jason@example.com
ANYLIST_PASSWORD=...
```

## Endpoints

### GET /health

Health check for Docker Compose.

**Response**: `200 OK` with `{"status": "ok"}`

### GET /items

Get all items from a specific list.

**Query params**: `?list=Grocery` (list name, default: "Grocery")

**Response**:
```json
{
  "items": [
    { "name": "Chicken breast", "checked": false },
    { "name": "Rice", "checked": true },
    { "name": "Stir-fry veggies", "checked": false }
  ]
}
```

### POST /add

Add an item to a list.

**Body**:
```json
{
  "list": "Grocery",
  "item": "Chicken breast"
}
```

**Response**: `201 Created` with `{"added": "Chicken breast"}`

### POST /add-bulk

Add multiple items at once (used after meal plan generation).

**Body**:
```json
{
  "list": "Grocery",
  "items": ["Chicken breast", "Rice", "Stir-fry veggies", "Ground turkey"]
}
```

**Response**: `201 Created` with `{"added": 4}`

### POST /remove

Remove an item from a list.

**Body**:
```json
{
  "list": "Grocery",
  "item": "Chicken breast"
}
```

**Response**: `200 OK` with `{"removed": "Chicken breast"}`

### POST /clear

Clear all unchecked items from a list (used before weekly meal plan refresh).

**Body**:
```json
{
  "list": "Grocery"
}
```

**Response**: `200 OK` with `{"cleared": 12}`

## Usage Pattern (Weekly Meal Plan → Grocery)

1. `POST /clear` — remove previous week's unchecked items
2. `POST /add-bulk` — add new grocery list from meal plan
3. Erin opens AnyList app → taps "Order Pickup or Delivery" → selects Whole Foods → reviews → checks out

## Docker Configuration

```yaml
anylist-sidecar:
  build: ./anylist-sidecar
  ports:
    - "3000:3000"
  environment:
    - ANYLIST_EMAIL=${ANYLIST_EMAIL}
    - ANYLIST_PASSWORD=${ANYLIST_PASSWORD}
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
    interval: 30s
    timeout: 5s
    retries: 3
```

## Risks & Mitigations

- **Unofficial API**: Could break if AnyList changes their backend. The
  `codetheweb/anylist` package is actively maintained (last update: 2025).
  If it breaks, grocery push degrades gracefully — assistant sends a
  formatted list in WhatsApp as fallback.
- **Authentication expiry**: AnyList session may expire. Sidecar should
  re-authenticate on 401 errors.
- **Rate limits**: Unknown (unofficial). Keep requests minimal — only
  push after meal plan generation (~1/week).

## Error Handling

- Sidecar unreachable: Skip grocery push, send formatted list via WhatsApp
- AnyList auth failure: Log error, return 503, assistant falls back
- Item not found on remove: Return 200 OK (idempotent)
