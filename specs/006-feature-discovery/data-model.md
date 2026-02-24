# Data Model: Feature Discovery & Onboarding

## Help Category (in-code constant, not a database)

Defines the structure for each help category displayed to the user.

| Field | Type | Notes |
|-------|------|-------|
| icon | String | Emoji icon for WhatsApp display (e.g., "🍳") |
| name | String | Category display name (e.g., "Recipes & Cooking") |
| capabilities | List[String] | 1-3 sentence descriptions of what the bot can do |
| static_examples | List[String] | Pre-written example phrases using known family data |
| personalize_from | String | Which tool to call for live examples (optional) |

### Help Categories

| Icon | Name | Capabilities | Static Examples |
|------|------|-------------|-----------------|
| 🍳 | Recipes & Cooking | Search Downshiftology recipes, browse saved recipes, import recipes to catalogue | "find me a chicken dinner recipe", "search for keto breakfast ideas" |
| 💰 | Budget & Spending | Check budget, search transactions, recategorize, move money between categories | "what did we spend at Costco?", "move $50 from Restaurants to Groceries" |
| 📅 | Calendar & Reminders | View calendar events, create reminders on family calendar, daily plan | "what's on our calendar this week?", "remind Jason to pick up dog at 12:30" |
| 🛒 | Groceries & Meal Planning | Generate meal plans, grocery lists, push to AnyList for delivery | "what's for dinner this week?", "order groceries" |
| 🏠 | Chores & Home | Track chores, laundry timer, set preferences, view history | "started laundry", "what chores have I done this week?" |
| 📋 | Family Management | Action items, backlog tasks, meeting agenda, family profile updates | "what's my day look like?", "add to backlog: organize garage" |

## Tip (in-code constant, not a database)

Contextual tips shown after normal responses to surface related features.

| Field | Type | Notes |
|-------|------|-------|
| id | String | Unique identifier (e.g., "tip_recipe_after_meal") |
| trigger_tools | List[String] | Tool names that trigger this tip when used |
| text | String | The "Did you know?" tip text |
| related_category | String | Which help category this tip relates to |

### Tip Definitions

| ID | Trigger Context | Tip Text |
|----|----------------|----------|
| tip_recipe_search | After meal plan generation | "You can say 'find me a keto dinner recipe' to search Downshiftology for new ideas!" |
| tip_grocery_push | After recipe details or meal plan | "Say 'order groceries' to push your meal plan ingredients to AnyList for delivery." |
| tip_budget_search | After grocery order | "Wondering where the money went? Say 'what did we spend at Costco?' to search transactions." |
| tip_reminder | After calendar view | "You can say 'remind Jason to pick up dog at 12:30' to create a shared calendar reminder." |
| tip_chore_timer | After chore completion | "Starting laundry? Say 'started laundry' and I'll remind you when it's time to move it to the dryer." |
| tip_recipe_import | After Downshiftology search | "Found a recipe you love? Say 'save number 2' to import it to your recipe catalogue." |
| tip_backlog | After daily plan | "Got a project in mind? Say 'add to backlog: organize garage' and I'll track it for you." |
| tip_meal_swap | After meal plan | "Don't feel like what's planned? Say 'swap Wednesday for tacos' to change the meal plan." |
| tip_chore_pref | After chore suggestion | "Want to customize? Say 'I like to vacuum on Wednesdays' and I'll remember your preferences." |
| tip_quiet_day | After multiple nudges | "Need a break? Say 'quiet day' to pause all proactive reminders for today." |

## Usage Counter (persistent JSON file, not a database)

Tracks per-user feature category interactions and last-shown tip for smart suggestions and tip rotation.

**File**: `data/usage_counters.json` (Docker: `/app/data/usage_counters.json`)

**Schema**:
```json
{
  "+15551234567": {
    "recipes": 12,
    "budget": 5,
    "calendar": 8,
    "groceries": 0,
    "chores": 3,
    "family_management": 2,
    "_last_tip": "tip_recipe_search"
  }
}
```

| Field | Type | Notes |
|-------|------|-------|
| phone (key) | String | Phone number as top-level key |
| {category} | Integer | Count of tool calls in this category. Categories: recipes, budget, calendar, groceries, chores, family_management |
| _last_tip | String | ID of last tip shown to this user — used to avoid consecutive repeats |

### Tool-to-Category Mapping

Maps each of the ~40 tool names to one of 6 category keys:

| Category Key | Tools |
|-------------|-------|
| recipes | search_downshiftology, get_downshiftology_details, import_downshiftology_recipe, extract_and_save_recipe, search_recipes, get_recipe_details, recipe_to_grocery_list, list_cookbooks |
| budget | get_budget_summary, search_transactions, recategorize_transaction, create_transaction, update_category_budget, move_money |
| calendar | get_calendar_events, get_outlook_events, write_calendar_blocks, create_quick_event |
| groceries | get_grocery_history, get_staple_items, push_grocery_list, generate_meal_plan, handle_meal_swap, save_meal_plan, get_meal_plan, check_reorder_items, confirm_groceries_ordered |
| chores | complete_chore, skip_chore, start_laundry, advance_laundry, cancel_laundry, set_chore_preference, get_chore_history, set_quiet_day |
| family_management | get_action_items, add_action_item, complete_action_item, add_topic, get_family_profile, update_family_profile, create_meeting, rollover_incomplete_items, get_backlog_items, add_backlog_item, complete_backlog_item, get_routine_templates |

## Session State (in-memory, module-level)

| Field | Type | Notes |
|-------|------|-------|
| _welcomed_phones | Set[String] | Phone numbers that have received the welcome message. Resets on container restart. |

No new Notion databases or properties needed for this feature.
