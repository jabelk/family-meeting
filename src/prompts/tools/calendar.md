## get_calendar_events

Fetch upcoming events from Google Calendars for the next N days. Reads from Jason's personal, Erin's personal, and the shared family calendar. Events are labeled by source.

## get_outlook_events

Fetch Jason's work calendar events (Outlook/Cisco) for a specific date. Shows meeting times so Erin can plan around his schedule. Use for daily plan generation and breakfast timing.

## write_calendar_blocks

Write time blocks to Erin's Google Calendar. Use after generating a daily plan to create events that appear in her Apple Calendar with push notifications. Each block needs: summary, start_time (ISO), end_time (ISO), and color_category.

## create_quick_event

Create a reminder or event on the shared family calendar. Both Jason and Erin will see it. Use when someone says 'remind me to...', 'pick up X at Y time', 'don't forget to...', or any time-specific task. Includes a 15-minute popup reminder by default.
