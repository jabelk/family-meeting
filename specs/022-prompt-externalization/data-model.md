# Data Model: Prompt Externalization

## Entities

### Prompt Section File (System Prompt)

Represents one composable section of the system prompt.

| Attribute | Description |
|-----------|-------------|
| filename | Numbered Markdown file (e.g., `01-identity.md`) — sort order determines assembly order |
| content | Plain text prompt content, no placeholders |
| directory | `src/prompts/system/` |

**Identity**: Filename is unique within `src/prompts/system/`.
**Lifecycle**: Created once during migration, edited by developers, loaded at startup.
**Validation**: Must be non-empty UTF-8 text. Missing files cause startup failure.

### Tool Description File

Represents descriptions for a group of related tools (one file per tool module).

| Attribute | Description |
|-----------|-------------|
| filename | Named after tool module (e.g., `calendar.md`, `notion.md`) |
| content | Markdown with `## tool_name` headers delimiting per-tool descriptions |
| directory | `src/prompts/tools/` |

**Identity**: Each `## tool_name` header maps 1:1 to a tool name in the TOOLS array.
**Lifecycle**: Created during migration, edited when tool descriptions change, loaded at startup.
**Validation**: Missing tool descriptions produce a warning log + fallback to tool name. Duplicate headers are an error.

### Prompt Template File

Represents a dynamic prompt template with placeholders.

| Attribute | Description |
|-----------|-------------|
| filename | Named after its function (e.g., `amazon_classification.md`) |
| content | Text with `{placeholder}` markers for runtime substitution |
| directory | `src/prompts/templates/` |

**Identity**: Filename is unique within `src/prompts/templates/`.
**Lifecycle**: Created during migration, edited to improve prompt quality, loaded at startup.
**Validation**: Must be non-empty. Placeholder names must match the kwargs passed at runtime — mismatches raise `KeyError`.

## Relationships

```
src/prompts/
├── system/         → assembled into SYSTEM_PROMPT string (concatenated in filename order)
├── tools/          → parsed into dict[tool_name, description] → merged with schemas in Python
└── templates/      → loaded individually by name → rendered with .format(**kwargs) at runtime
```

- System prompt sections have no dependencies on each other (pure concatenation).
- Tool description files map to tool schema definitions in `src/assistant.py`.
- Template files map to specific functions in `src/tools/*.py`.

## File Inventory

### System Prompt Sections (8 files)

| File | Content | Approx Lines |
|------|---------|-------------|
| `01-identity.md` | Mom Bot identity, family members, core directive | 16 |
| `02-response-rules.md` | WhatsApp formatting, conciseness, weekly agenda rules | 28 |
| `03-daily-planner.md` | Daily planning triggers, calendar safety, confirm-before-writing, childcare, backlog | 104 |
| `04-grocery-recipes.md` | Grocery integration, recipe catalogue, Downshiftology search | 38 |
| `05-chores-nudges.md` | Chore nudges, laundry state machine, quiet days | 21 |
| `06-budget.md` | YNAB transactions, recategorization, budget moves | 13 |
| `07-calendar-reminders.md` | Quick reminders, event ownership, feature discovery, cross-domain thinking | 44 |
| `08-advanced.md` | Daily briefing, meeting prep, sync patterns, budget goals, communication modes | 87 |

### Tool Description Files (12 files, 71 tools)

| File | Tools | Count |
|------|-------|-------|
| `calendar.md` | get_calendar_events, get_outlook_events, write_calendar_blocks, create_quick_event | 4 |
| `notion.md` | get/add/complete_action_item, add_topic, family_profile, create_meeting, rollover, meal_plan, backlog, routine_templates | 14 |
| `ynab.md` | budget_summary, search/recategorize/create_transaction, update_category, move_money, budget_health, goal_suggestion, allocate/approve | 10 |
| `anylist.md` | get_grocery_history, get_staple_items, push_grocery_list | 3 |
| `recipes.md` | extract/search/details/grocery_list, list_cookbooks, downshiftology search/details/import | 8 |
| `chores.md` | quiet_day, complete/skip_chore, laundry start/advance/cancel, chore_preference, chore_history, reorder_items, confirm_groceries | 10 |
| `proactive.md` | generate_meal_plan, handle_meal_swap, get_help | 3 |
| `amazon.md` | amazon_sync_status/trigger, spending_breakdown, auto_split, undo_split | 5 |
| `email.md` | email_sync_trigger/status, auto_categorize, undo_categorize | 4 |
| `preferences.md` | save/list/remove_preference | 3 |
| `context.md` | get_daily_context | 1 |
| `routines.md` | save/get/delete_routine, get/save/delete_drive_time | 6 |

### Template Files (11 files)

| File | Source Function | Dynamic Variables |
|------|----------------|-------------------|
| `amazon_order_parsing.md` | `_parse_order_email()` | `{clean_text}` |
| `amazon_classification.md` | `classify_item()` | `{category_list}`, `{examples_text}`, `{item_title}`, `{item_price}` |
| `paypal_parsing.md` | `_parse_paypal_email()` | `{stripped_text}` |
| `venmo_parsing.md` | `_parse_venmo_email()` | `{stripped_text}` |
| `apple_parsing.md` | `_parse_apple_email()` | `{stripped_text}` |
| `meal_plan_generation.md` | `generate_meal_plan()` | `{profile}`, `{recipes_summary}`, `{recipe_count}`, `{recent_plans}` |
| `meal_swap.md` | `handle_meal_swap()` | `{new_meal}` |
| `conflict_detection.md` | `detect_conflicts()` | `{days_ahead}`, `{today}`, `{cal_events}`, `{outlook_events}`, `{templates}` |
| `budget_formatting.md` | `format_budget_summary()` | `{raw}` |
| `recipe_extraction.md` | `extract_and_save_recipe()` | `{page_suffix}`, `{multi_page_rule}` |
| `daily_briefing.md` | `generate_daily_briefing()` | `{context_data}` |
