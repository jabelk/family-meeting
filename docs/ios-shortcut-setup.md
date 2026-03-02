# iOS Shortcut: Work Calendar Push

Push Jason's Cisco/Outlook work calendar events to the family assistant weekly so Erin's daily plan shows his meeting windows.

## What It Does

Every Sunday at 7 PM, this shortcut:
1. Reads Jason's Cisco work calendar for Mon-Fri
2. Builds a JSON payload with each event's title, start time, and end time
3. POSTs it to the bot's endpoint
4. Events appear in Erin's daily briefing the next morning

## Setup Instructions

### Step 1: Create the Shortcut

1. Open **Shortcuts** app on your iPhone
2. Tap **+** to create a new shortcut
3. Name it **"Push Work Calendar"**

### Step 2: Add "Find Calendar Events" Action

1. Tap **Add Action** → search for **"Find Calendar Events"**
2. Configure the filter:
   - **Calendar** is **[Your Cisco/Outlook calendar name]** (tap to select — it shows all calendars on your phone)
   - **Start Date** is **after** → select **"Adjusted Date"** → set to **Start of Next Week** (Monday)
   - **End Date** is **before** → select **"Adjusted Date"** → set to **End of Next Week** (Friday 11:59 PM)

### Step 3: Build the JSON Payload

1. Add a **"Set Variable"** action → name it `eventList` → set to empty text `[]`
2. Add a **"Repeat with Each"** action on the Calendar Events
3. Inside the repeat block:
   - Add **"Text"** action with this content:
     ```
     {"title":"[Title]","start":"[Start Date: Format: yyyy-MM-dd'T'HH:mm:ss]","end":"[End Date: Format: yyyy-MM-dd'T'HH:mm:ss]"}
     ```
     (Use the magic variables from "Repeat Item" — tap each placeholder to select Title, Start Date, End Date)
   - Set the date format to **Custom: `yyyy-MM-dd'T'HH:mm:ss`**
   - Add this text to your `eventList` variable (with commas between entries)
4. After the repeat block, add a **"Text"** action:
   ```
   {"events":[eventList]}
   ```

**Simpler alternative** (if the above is tricky):
1. After "Find Calendar Events", add a **"Repeat with Each"**
2. Inside the loop, use **"Add to Variable"** named `allEvents` with a Dictionary containing:
   - `title`: Repeat Item → Title
   - `start`: Repeat Item → Start Date (formatted as ISO 8601)
   - `end`: Repeat Item → End Date (formatted as ISO 8601)
3. After the loop, use **"Dictionary"** to create `{"events": allEvents}`

### Step 4: Send to the Bot

1. Add **"Get Contents of URL"** action
2. Set URL to: `https://mombot.sierrastoryco.com/api/v1/calendar/work-events`
3. Set Method to **POST**
4. Add Header:
   - **Key**: `X-N8N-Auth`
   - **Value**: `[your N8N_WEBHOOK_SECRET value]` (ask Jason for this — it's in the .env file)
5. Add Header:
   - **Key**: `Content-Type`
   - **Value**: `application/json`
6. Set Request Body to **File** → select the JSON text from Step 3

### Step 5: Set Up Weekly Automation

1. Go to **Shortcuts** → **Automation** tab
2. Tap **+** → **Time of Day**
3. Set to **Sunday at 7:00 PM**
4. Set **Repeat**: Weekly
5. Select **"Push Work Calendar"** shortcut
6. **Important**: Enable **"Run Immediately"** (toggle off "Ask Before Running")
   - This ensures it runs without needing Jason to tap anything

## Testing

### Manual Test

1. Open the shortcut and tap **Play** (triangle icon)
2. You should see a response like:
   ```json
   {"status":"ok","events_received":9,"dates_covered":["2026-03-03","2026-03-04","2026-03-05","2026-03-06","2026-03-07"],"message":"Stored 9 events covering 5 days"}
   ```
3. If you get a 401 error: check that the `X-N8N-Auth` header value matches `N8N_WEBHOOK_SECRET`

### Verify in Daily Plan

After pushing, ask the bot "what's my day look like?" (as Erin) — Jason's work meetings should appear in the daily plan.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Check `X-N8N-Auth` header matches the secret in .env |
| No events found | Make sure the correct calendar is selected in "Find Calendar Events" — look for the Cisco/Exchange calendar name |
| Events show wrong times | Ensure date format is `yyyy-MM-dd'T'HH:mm:ss` (ISO 8601) |
| Automation doesn't run | Check Shortcuts → Automation → verify "Run Immediately" is enabled |
| Phone was off/no internet | The shortcut will just skip that week. The bot falls back to "work schedule unavailable" after 7 days without a push |

## Notes

- Events are stored for 7 days, then auto-expire
- If the shortcut runs again mid-week (e.g., after meeting changes), new data replaces old for overlapping dates
- Only time blocks matter for the daily plan — meeting content/attendees aren't sent
