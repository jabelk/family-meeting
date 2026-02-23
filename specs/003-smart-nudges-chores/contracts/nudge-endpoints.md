# API Contracts: Smart Nudges & Chore Scheduling

## POST /api/v1/nudges/scan

**Purpose**: Called by n8n every 15 minutes to scan for new departure events, identify free windows for chore suggestions, and deliver pending nudges.

**Authentication**: `X-N8N-Auth` header matching `N8N_WEBHOOK_SECRET`.

**Request Body**: None (empty POST).

**Response** (200 OK):

```json
{
  "departures_created": 2,
  "chores_suggested": 1,
  "nudges_sent": 3,
  "nudges_batched": 1,
  "daily_count": 5,
  "daily_cap": 8,
  "quiet_day": false,
  "errors": []
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| departures_created | int | New departure nudges added to Nudge Queue |
| chores_suggested | int | New chore suggestion nudges created |
| nudges_sent | int | Pending nudges delivered via WhatsApp |
| nudges_batched | int | Number of batch groups sent (multiple nudges → single message) |
| daily_count | int | Total proactive messages sent today (after this scan) |
| daily_cap | int | Maximum allowed proactive messages per day (8) |
| quiet_day | bool | Whether quiet day is active (all nudges suppressed) |
| errors | string[] | Non-fatal errors encountered during scan |

**Error Responses**:

| Status | Condition |
|--------|-----------|
| 401 | Missing or invalid `X-N8N-Auth` header |
| 503 | `N8N_WEBHOOK_SECRET` not configured |
| 500 | Unhandled exception (logged, non-fatal errors returned in `errors` array) |

**Behavior**:
1. Skip all processing if `quiet_day` is active
2. Scan Google Calendar for upcoming events (next 2 hours) → create departure nudges for non-virtual events not already in Nudge Queue
3. Compare calendar + routine templates → find free windows ≥ 15 min → create chore suggestion nudges
4. Query Nudge Queue for `Status = Pending AND Scheduled Time <= now`
5. Batch nudges within 5-minute window into single messages
6. Check daily cap before each send; stop sending if cap reached
7. Send via WhatsApp with template fallback for outside 24h window

---

## Claude Agent Tools (called via tool_use in assistant.py)

### start_laundry

**Purpose**: Erin tells the bot she started a load of laundry. Creates a laundry session with timed nudges.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| washer_minutes | int | No | Washer cycle duration (default: 45) |
| dryer_minutes | int | No | Dryer cycle duration (default: 60) |

**Returns** (string): Confirmation message with scheduled times and any calendar conflict warnings.

**Side Effects**:
- Creates 2 Nudge Queue entries: `laundry_washer` (now + washer_minutes), `laundry_followup` (now + 2h45m)
- Checks calendar for conflicts with dryer timing
- Cancels any existing active laundry session

---

### advance_laundry

**Purpose**: Erin confirms she moved clothes to the dryer. Advances the laundry session.

**Parameters**: None.

**Returns** (string): Confirmation with dryer completion time and any calendar conflict warnings.

**Side Effects**:
- Creates 1 Nudge Queue entry: `laundry_dryer` (now + dryer_minutes)
- Cancels pending `laundry_followup` nudge
- Updates session context to phase "drying"

---

### complete_chore

**Purpose**: Erin confirms she completed a suggested chore.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| chore_name | string | Yes | Name of the completed chore (matched against Chores DB) |

**Returns** (string): Confirmation with encouragement.

**Side Effects**:
- Updates Chore record: `Last Completed = today`, `Times Completed += 1`
- Marks the associated nudge as `Done`

---

### skip_chore

**Purpose**: Erin declines a chore suggestion.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| chore_name | string | Yes | Name of the skipped chore |

**Returns** (string): Acknowledgment (no guilt).

**Side Effects**:
- Marks the associated nudge as `Dismissed`
- Adds chore to today's skip list (won't re-suggest today)

---

### set_quiet_day

**Purpose**: Erin requests no proactive nudges for the rest of the day.

**Parameters**: None.

**Returns** (string): Confirmation that nudges are paused until tomorrow.

**Side Effects**:
- Creates a `quiet_day` Nudge Queue entry with `Status = Pending` and `Scheduled Time = today`
- Cancels all other `Pending` nudges for today (except active laundry session nudges which are user-initiated)

---

### set_chore_preference

**Purpose**: Erin tells the bot her preferences for a chore (frequency, preferred days, like/dislike).

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| chore_name | string | Yes | Chore to update |
| preference | string | No | `like`, `neutral`, or `dislike` |
| preferred_days | string[] | No | Days of week (e.g., `["Monday", "Wednesday"]`) |
| frequency | string | No | `daily`, `every_other_day`, `weekly`, `biweekly`, `monthly` |

**Returns** (string): Confirmation of updated preference.

**Side Effects**:
- Updates matching Chore record fields

---

### get_chore_history

**Purpose**: Erin asks what chores she's done recently.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| days | int | No | Number of days to look back (default: 7) |

**Returns** (string): Formatted summary of completed chores with dates.

**Side Effects**: None (read-only).
