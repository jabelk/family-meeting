## get_daily_context

Get today's family context: calendar events grouped by person, who has {child2_name}, communication mode (time-of-day tone), active preferences, and pending backlog count. Call this at the start of any planning, scheduling, daily plan, or recommendation interaction. Do NOT call for simple factual questions.

## check_system_logs

Check recent system logs to diagnose issues. Call this when something isn't working, a user reports a problem, a tool just failed, or someone asks about system status. Also call proactively after any tool error to include specific diagnostic context in your response — don't wait for the user to ask. Returns a summary of recent errors, warnings, and known issues with specific diagnoses (e.g., "Google Calendar auth expired" or "Notion API errors"). Use the results to give the user a clear, specific explanation of what's wrong instead of a vague "something went wrong." Provide actionable guidance when possible (e.g., "{partner1_name} needs to refresh the calendar token" rather than "calendar is down").
