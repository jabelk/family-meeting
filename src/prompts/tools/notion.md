## get_action_items

Query action items from Notion. Can filter by assignee and/or status. Use status='open' to get all non-completed items.

## add_action_item

Create a new action item assigned to a family member.

## complete_action_item

Mark an action item as Done. Accepts either a Notion page UUID or the task description text (will fuzzy-match against open items). Prefer using the page_id from get_action_items when available.

## add_topic

Add a custom topic to the next meeting agenda.

## get_family_profile

Read the family profile including member info, dietary preferences, routine templates, childcare schedule, recurring agenda topics, and configuration.

## update_family_profile

Update the family profile with new persistent information. Use when a partner mentions a lasting preference, dietary restriction, schedule change, childcare update, or recurring topic.

## create_meeting

Create a new meeting record in Notion for today (or a specific date). Returns the meeting page ID.

## rollover_incomplete_items

Mark all incomplete 'This Week' action items as rolled over. Call this when generating a new weekly agenda.

## save_meal_plan

Save a weekly meal plan to Notion with daily meals and a grocery list.

## get_meal_plan

Get the current or most recent meal plan from Notion.

## get_backlog_items

Query {partner2_name}'s personal backlog of one-off tasks (home improvement, personal growth, side work). These are not weekly action items — they persist until done.

## add_backlog_item

Add a one-off task to the backlog (e.g., 'reorganize tupperware', 'clean garage', 'knitting project'). These are personal growth / home improvement tasks worked through at {partner2_name}'s pace.

## complete_backlog_item

Mark a backlog item as Done. Accepts either a Notion page UUID or the task description text (will fuzzy-match against open items). Prefer using the page_id from get_backlog_items when available.

## get_routine_templates

Read {partner2_name}'s daily routine templates from the family profile. Templates define time blocks for different scenarios (e.g., 'Weekday with {child2_name}', 'Weekday with Grandma'). Used for daily plan generation.
