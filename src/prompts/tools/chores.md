## set_quiet_day

Suppress all proactive nudges (departure reminders, chore suggestions) for the rest of today. Use when Erin says 'quiet day', 'no nudges today', or 'leave me alone today'. She can still message the bot and get responses — only proactive nudges are paused.

## complete_chore

Mark a chore as completed. Updates the Chores database and marks the nudge as done. Use when Erin says 'done', 'finished', 'did it' after a chore suggestion.

## skip_chore

Skip a suggested chore (won't be re-suggested today). Use when Erin says 'skip', 'not now', 'pass' to a chore suggestion.

## start_laundry

Start a laundry session with timed reminders. Creates washer-done nudge and follow-up nudge. Checks calendar for conflicts with dryer timing. Use when Erin says 'started laundry', 'doing a load', etc.

## advance_laundry

Move laundry to dryer phase. Creates dryer-done nudge and cancels follow-up. Use when Erin says 'moved to dryer', 'put it in the dryer', etc.

## cancel_laundry

Cancel the active laundry session and all pending laundry reminders. Use when Erin says 'never mind', 'didn't do laundry', or 'cancel laundry'.

## set_chore_preference

Update Erin's preferences for a chore: how often, preferred days, and like/dislike. Use when Erin says things like 'I like to vacuum on Wednesdays', 'I hate cleaning bathrooms', 'vacuum weekly instead of daily'.

## get_chore_history

Show what chores Erin has completed recently. Use when she asks 'what have I done this week?', 'chore history', etc.

## check_reorder_items

Check grocery history for staple/regular items due for reorder. Returns items grouped by store with days overdue. Use when asked about grocery needs or to proactively suggest reorders.

## confirm_groceries_ordered

Mark all pending grocery orders as confirmed (updates Last Ordered date). Call when user says 'groceries ordered', 'placed the order', etc.
