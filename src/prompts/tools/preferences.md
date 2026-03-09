## save_preference

Save a user preference that persists across conversations. Use when the user expresses a lasting rule like 'don't remind me about X', 'stop sending X', 'no more X', or 'check the time before Y'. Do NOT use for one-time requests like 'no tacos tonight'.

## list_preferences

List all stored preferences for the current user. Use when the user asks 'what are my preferences?', 'what have I set?', or 'show my preferences'.

## remove_preference

Remove a stored preference so the bot resumes default behavior. Use when the user says 'start reminding me about X again', 'remove the X preference', 'undo the X opt-out', or 'clear all my preferences'. Use search_text='ALL' to clear all preferences.
