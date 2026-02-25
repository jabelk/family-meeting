# Contract: Meeting Prep Endpoint

## Purpose

New n8n-triggerable endpoint for automated weekly meeting prep generation.

## Endpoint

### `POST /api/v1/meetings/prep-agenda`

**Authentication**: n8n auth header (same as existing endpoints)

**Request Body**: None (or optional JSON with target phone)

**Response**: JSON with meeting prep text

```json
{
  "status": "ok",
  "agenda": "📊 *Weekly Family Meeting Prep*\n\n..."
}
```

**Behavior**:
1. Calls `generate_meeting_prep()` in `src/assistant.py`
2. Sends the result to Erin's phone via `send_message()`
3. Returns the agenda text in the response

**Error Response**:
```json
{
  "status": "error",
  "message": "Failed to generate meeting prep"
}
```

## n8n Workflow

**Trigger**: Cron schedule — suggested: Saturday 5:00 PM (before Sunday family meeting)
**Method**: HTTP POST to `https://mombot.sierrastoryco.com/api/v1/meetings/prep-agenda`
**Headers**: Same n8n auth as daily briefing endpoint

## Implementation

In `src/app.py`, add alongside existing `/api/v1/briefing/daily` endpoint:

```python
@app.post("/api/v1/meetings/prep-agenda")
async def meeting_prep_agenda(request: Request):
    verify_n8n_auth(request)
    try:
        agenda = generate_meeting_prep()
        await send_message(ERIN_PHONE, agenda)
        return {"status": "ok", "agenda": agenda}
    except Exception as e:
        logger.error(f"Meeting prep failed: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500,
        )
```

## Constraints

- Follows same auth pattern as `/api/v1/briefing/daily`
- Uses `sender="system"` so meeting prep doesn't enter conversation history
- The endpoint is optional — meeting prep also works ad-hoc when Erin asks via WhatsApp
