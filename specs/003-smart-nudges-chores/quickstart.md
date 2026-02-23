# Quickstart: Smart Nudges & Chore Scheduling

## Prerequisites

- Existing family meeting assistant deployed (FastAPI + Docker Compose on NUC)
- Google Calendar API access configured (existing `credentials.json` + OAuth token)
- Notion API integration connected (existing `NOTION_API_KEY`)
- WhatsApp Cloud API working (existing webhook + `WHATSAPP_APP_SECRET`)
- n8n running on NUC with API access

## Setup Steps

### Step 1: Create Notion Databases

1. **Nudge Queue** — Create a new database in the family meeting Notion workspace:
   - Summary (Title)
   - Nudge Type (Select): `departure`, `laundry_washer`, `laundry_dryer`, `laundry_followup`, `chore`, `quiet_day`
   - Status (Status): Groups — `Pending`, `Sent`, `Done`, `Snoozed`, `Dismissed`, `Cancelled`
   - Scheduled Time (Date with time)
   - Event ID (Rich Text)
   - Message (Rich Text)
   - Context (Rich Text)

2. **Chores** — Create a new database:
   - Name (Title)
   - Duration (Number)
   - Frequency (Select): `daily`, `every_other_day`, `weekly`, `biweekly`, `monthly`
   - Preferred Days (Multi-select): `Monday` through `Sunday`
   - Preference (Select): `like`, `neutral`, `dislike`
   - Last Completed (Date)
   - Times Completed (Number)
   - Category (Select): `cleaning`, `kitchen`, `organizing`, `outdoor`, `laundry`, `meal_prep`

3. Copy both database IDs from the Notion URLs (32-char hex after the workspace name).

### Step 2: Add Environment Variables

Add to `.env`:

```bash
NOTION_NUDGE_QUEUE_DB=<nudge-queue-database-id>
NOTION_CHORES_DB=<chores-database-id>
```

Push to NUC: `./scripts/nuc.sh env`

### Step 3: Seed Default Chores

After deploying the code, the first run of the nudge scanner will auto-seed the Chores database if it's empty. Default chores:

| Chore | Duration | Frequency | Category |
|-------|----------|-----------|----------|
| Vacuum downstairs | 30 min | weekly | cleaning |
| Vacuum upstairs | 25 min | weekly | cleaning |
| Wipe kitchen counters | 10 min | daily | kitchen |
| Clean bathrooms | 40 min | weekly | cleaning |
| Start dishwasher | 5 min | daily | kitchen |
| Meal prep for tonight | 30 min | daily | meal_prep |
| Tidy living room | 15 min | daily | cleaning |
| Organize closet/pantry | 45 min | monthly | organizing |
| Wipe down appliances | 15 min | weekly | kitchen |
| Fold and put away laundry | 20 min | every_other_day | laundry |

### Step 4: Create n8n Workflow

Create workflow **WF-009: Nudge Scanner**:
- **Trigger**: Cron — `*/15 7-20 * * *` (every 15 min, 7am–8:45pm)
- **Action**: HTTP Request POST to `http://fastapi:8000/api/v1/nudges/scan`
- **Header**: `X-N8N-Auth: <N8N_WEBHOOK_SECRET>`
- **No request body needed**

### Step 5: Deploy

```bash
# Commit and push code changes
git add . && git commit -m "feat: smart nudges and chore scheduling" && git push

# Deploy to NUC
./scripts/nuc.sh deploy
```

## Validation

### Test 1: Departure Nudge (US1)

1. Create a Google Calendar event on Erin's calendar 25 minutes from now
2. Wait for the next n8n scan (up to 15 minutes)
3. Verify a WhatsApp nudge arrives ~15 min before the event
4. Reply "snooze" → verify a new nudge arrives 10 minutes later
5. Reply "stop" → verify no more nudges for that event

### Test 2: Virtual Event Exclusion (US1)

1. Create a Google Calendar event with a Zoom link (or "virtual" in the title)
2. Wait for the scan
3. Verify no departure nudge is sent

### Test 3: Laundry Workflow (US2)

1. Send "I started a load of laundry" to the bot
2. Verify confirmation with scheduled times
3. Wait 45 minutes (or check Nudge Queue in Notion for pending `laundry_washer` entry)
4. Verify WhatsApp reminder to move clothes to dryer
5. Reply "moved to dryer"
6. Wait 60 minutes → verify dryer-done reminder

### Test 4: Chore Suggestion (US3)

1. Ensure a free window exists in the calendar (at least 30 min gap)
2. Wait for the scan during that window
3. Verify a chore suggestion arrives with duration context
4. Reply "done" → verify chore marked as completed in Notion
5. Verify the same chore is not re-suggested the same day

### Test 5: Quiet Day (US1-US3)

1. Send "quiet day" to the bot
2. Verify confirmation
3. Wait for the next scan
4. Verify no nudges are sent for the rest of the day

### Test 6: Daily Cap (NFR-002)

1. Check Nudge Queue in Notion: count entries with `Status = Sent` and today's date
2. After 8 proactive messages, verify subsequent nudges remain `Pending` (not sent)

## Troubleshooting

- **No nudges arriving**: Check n8n workflow is active, verify `N8N_WEBHOOK_SECRET` matches between n8n and `.env`
- **Nudges for virtual events**: Check if event has `conferenceData` or virtual keywords in title/description
- **Laundry timers lost after restart**: Verify nudges exist in Notion Nudge Queue database (they persist across restarts)
- **Too many messages**: Check daily cap count in Nudge Queue; reduce n8n frequency if needed
- **Chores not suggesting**: Verify Chores DB is seeded, free windows exist, and no quiet day is active
