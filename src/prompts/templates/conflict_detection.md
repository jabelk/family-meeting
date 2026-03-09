Analyze these calendars for the next {days_ahead} day(s) starting {today}.

Google Calendar events:
{cal_events}

Outlook (Jason work) events:
{outlook_events}

Family routine templates:
{templates}

IMPORTANT: Events are pulled from multiple calendars (jason, erin, family). The SAME event often appears on more than one calendar (e.g., a shared family event shows on both Erin's calendar and the Family calendar). Two entries with the same name and time on different calendars are NOT a conflict — they are the same event. Only flag a conflict when two DIFFERENT events overlap in time.

Find:
1. Hard conflicts: two DIFFERENT events with overlapping times
2. Soft conflicts: events that overlap with routine commitments (pickup times, dropoff times, Sandy/grandma schedule)

Return ONLY a JSON array (empty if no conflicts):
[{{"day": "YYYY-MM-DD", "type": "hard|soft", "event": "event name + time", "conflict_with": "other event or routine", "suggestion": "how to resolve"}}]
