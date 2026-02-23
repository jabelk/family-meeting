# Data Model: Smart Nudges & Chore Scheduling

## Notion Database: Nudge Queue

Stores all scheduled proactive messages — departure nudges, laundry reminders, and chore suggestions.

| Property | Type | Description |
|----------|------|-------------|
| Summary | Title | Short description (e.g., "Park playdate departure", "Washer done", "Vacuum downstairs") |
| Nudge Type | Select | `departure`, `laundry_washer`, `laundry_dryer`, `laundry_followup`, `chore`, `quiet_day` |
| Status | Status | `Pending` → `Sent` → `Done`; also `Snoozed`, `Dismissed`, `Cancelled` |
| Scheduled Time | Date (with time) | When the nudge should fire (Pacific time) |
| Event ID | Rich Text | Google Calendar event ID (for departure nudges) or session ID (for laundry) |
| Message | Rich Text | Pre-formatted WhatsApp message text |
| Context | Rich Text | JSON blob with extra data (event title, chore name, duration, etc.) |
| Created | Created Time | Auto-set |

**State Transitions**:
- `Pending` → `Sent` (nudge delivered via WhatsApp)
- `Pending` → `Snoozed` (Erin says "snooze" → new Pending nudge created +10 min)
- `Pending` → `Dismissed` (Erin says "stop" or "skip")
- `Pending` → `Cancelled` (laundry cancelled, event deleted, quiet day activated)
- `Sent` → `Done` (Erin confirms action, e.g., "moved to dryer", "done vacuuming")

**Queries**:
- Pending nudges due now: `Status = Pending AND Scheduled Time <= now`
- Daily send count: `Status = Sent AND Created = today`
- Active laundry session: `Nudge Type starts_with "laundry" AND Status in (Pending, Sent)`
- Quiet day active: `Nudge Type = "quiet_day" AND Status = Pending AND Scheduled Time = today`

## Notion Database: Chores

Tracks recurring household chores with preferences and completion history.

| Property | Type | Description |
|----------|------|-------------|
| Name | Title | Chore name (e.g., "Vacuum downstairs", "Wipe kitchen counters") |
| Duration | Number | Estimated minutes to complete |
| Frequency | Select | `daily`, `every_other_day`, `weekly`, `biweekly`, `monthly` |
| Preferred Days | Multi-select | `Monday`, `Tuesday`, ... `Sunday` (empty = any day) |
| Preference | Select | `like`, `neutral`, `dislike` |
| Last Completed | Date | Most recent completion date |
| Times Completed | Number | Running count |
| Category | Select | `cleaning`, `kitchen`, `organizing`, `outdoor`, `laundry`, `meal_prep` |

**Default Seed Data** (created during setup):

| Name | Duration | Frequency | Category |
|------|----------|-----------|----------|
| Vacuum downstairs | 30 | weekly | cleaning |
| Vacuum upstairs | 25 | weekly | cleaning |
| Wipe kitchen counters | 10 | daily | kitchen |
| Clean bathrooms | 40 | weekly | cleaning |
| Start dishwasher | 5 | daily | kitchen |
| Meal prep for tonight | 30 | daily | meal_prep |
| Tidy living room | 15 | daily | cleaning |
| Organize closet/pantry | 45 | monthly | organizing |
| Wipe down appliances | 15 | weekly | kitchen |
| Fold and put away laundry | 20 | every_other_day | laundry |

**Chore Selection Algorithm**:
1. Filter chores where `Duration <= free_window_minutes`
2. Prioritize by overdue score: `days_since_last / frequency_days` (higher = more overdue)
3. Boost if today matches a Preferred Day
4. Deprioritize if `Preference = dislike` (but still suggest if overdue score > 2x)
5. Return top 1-2 suggestions with durations

## Relationships

```
Nudge Queue
  ├── references Google Calendar event (via Event ID) for departure nudges
  ├── groups laundry nudges by session ID (via Event ID field)
  └── references Chore (via Context JSON: {"chore_id": "..."}) for chore suggestions

Chores
  └── standalone; updated when Erin completes/skips via Claude tool calls
```

## No New Databases Modified

Existing databases (Action Items, Meal Plans, Meetings, Backlog, Grocery History, Recipes, Cookbooks) are unchanged. The Family Profile page is read-only for routine template access.
