## get_calendar_events

Fetch upcoming events from Google Calendars for the next N days. Reads from Jason's personal, Erin's personal, and the shared family calendar. Events are labeled by source.

## get_outlook_events

Fetch Jason's work calendar events (Outlook/Cisco) for a specific date. Shows meeting times so Erin can plan around his schedule. Use for daily plan generation and breakfast timing.

## write_calendar_blocks

Write time blocks to Erin's Google Calendar. Use after generating a daily plan to create events that appear in her Apple Calendar with push notifications. Each block needs: summary, start_time (ISO), end_time (ISO), and color_category.

## create_quick_event

Create a one-time or recurring event on a Google Calendar. Defaults to the family calendar (both Jason and Erin see it). Use when someone says 'remind me to...', 'pick up X at Y time', or any time-specific task. Includes a 15-minute popup reminder by default.

For recurring events, generate an RRULE from the user's natural language and pass it in the `recurrence` parameter:
- "every Tuesday" → `["RRULE:FREQ=WEEKLY;BYDAY=TU"]`
- "every other Tuesday" → `["RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=TU"]`
- "every Monday at 4pm for 8 weeks" → `["RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=8"]`
- "first Friday of every month" → `["RRULE:FREQ=MONTHLY;BYDAY=1FR"]`
- "Tuesdays and Thursdays" → `["RRULE:FREQ=WEEKLY;BYDAY=TU,TH"]`
- "every day until June 1" → `["RRULE:FREQ=DAILY;UNTIL=20260601T235959Z"]`

Omit `recurrence` entirely for one-time events. Use `calendar_name` to target a specific calendar (family, jason, erin). After creating a recurring event, confirm the pattern and list the next 3-4 upcoming dates so the user can verify.

## delete_calendar_event

Delete a single occurrence or all future occurrences of a calendar event. Use `cancel_mode: "single"` when the user says "no swim this Monday" or "skip cleaners next week" — this cancels just one date. Use `cancel_mode: "all_following"` when the user says "cancel the cleaners" or "stop the recurring swim class" — this deletes the entire series. To find the event_id, first use `get_calendar_events` or `get_events_for_date` to locate the event. When the user asks to cancel a recurring event, ask whether they mean just this one or all future occurrences.

## list_recurring_events

List all active recurring event series on a calendar. Returns the event title, recurrence pattern, and start time for each recurring series. Use when the user asks "what recurring events do we have", "show me our regular schedule", or "what happens every week." Defaults to the family calendar.
