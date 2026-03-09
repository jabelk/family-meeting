## save_routine

Save a personal routine checklist. Overwrites if a routine with the same name already exists. Examples: morning skincare, bedtime, meal prep, school pickup.

## get_routine

Get a stored personal routine by name. Returns the ordered checklist. If name is empty or 'all', lists all saved routine names.

## delete_routine

Delete a stored personal routine by name. Use when the user says 'delete my morning routine' or 'remove my bedtime routine'.

## get_drive_times

Get all stored drive times for common locations. Returns a list of locations and their drive times from home in minutes. Call this during daily plan generation to insert travel buffers.

## save_drive_time

Save or update a drive time for a location. Use when the user says something like 'the gym is 5 minutes away' or 'school is 10 minutes from home'.

## delete_drive_time

Remove a stored drive time for a location.
