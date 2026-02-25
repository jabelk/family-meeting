# Data Model: Holistic Family Intelligence

## Overview

This feature introduces **no new persistent entities**. All data already exists in the current systems (Notion, Google Calendar, YNAB). The "entities" below are conceptual — they represent how Claude should think about the data, not new storage.

## Conceptual Entities

### Family Context Snapshot

A mental model Claude uses when answering cross-domain questions. Not stored anywhere — assembled at query time from existing tools.

**Components**:
| Domain | Source Tool | Key Data Points |
|--------|------------|-----------------|
| Schedule | get_calendar_events | Today/this week's density, busy vs free blocks |
| Work Calendar | get_outlook_events | Jason's meeting windows, availability |
| Budget | get_budget_summary | Over/under categories, remaining amounts |
| Meal Plan | get_meal_plan | This week's plan, tonight's dinner, complexity |
| Action Items | get_action_items | Overdue count, this week's items by assignee |
| Chores | get_chore_history | Recently completed, what's due |
| Grocery | check_reorder_items | Pending orders, items due for reorder |
| Backlog | get_backlog_items | Open items, categories (home, growth, side work) |

**Not stored**: Claude gathers relevant subsets at query time. A "how's our week" question might check calendar + budget + action items. A "can we eat out" question might check budget + meal plan + calendar. Claude decides which domains are relevant based on the question.

### Meeting Agenda

The structured output of a meeting prep request. Sent as a WhatsApp message, not stored in a database.

**Sections** (in order):
1. **Budget Snapshot** — Headline insight + over/under categories
2. **Calendar Review** — Past week highlights + next week preview
3. **Action Items** — Completed vs overdue, carry-forward recommendations
4. **Meal Plan** — This week's effectiveness, next week status
5. **Priorities** — Top 3 synthesized discussion points across all domains

**Format**: WhatsApp-formatted text using *bold*, bullets, and emojis per existing formatting rules (Rule 1 in system prompt).

## Existing Entities Used (Not Modified)

- **Google Calendar Events** — Read via get_calendar_events, get_outlook_events
- **YNAB Budget/Transactions** — Read via get_budget_summary, search_transactions
- **Notion Meal Plans** — Read via get_meal_plan
- **Notion Action Items** — Read via get_action_items
- **Notion Backlog Items** — Read via get_backlog_items
- **Notion Chores** — Read via get_chore_history
- **Notion Grocery History** — Read via check_reorder_items, get_grocery_history
- **Notion Family Profile** — Read via get_family_profile
