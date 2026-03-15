# Data Model: Responsive Assistant Mode

**Feature**: 038-responsive-assistant-mode | **Date**: 2026-03-15

## Entities

### Dietary Preference (extends existing Preference)

Stored in the existing `user_preferences.json` using the preference system's standard format. The new `dietary` category is added to the valid categories list.

| Field | Type | Description |
|-------|------|-------------|
| id | str (UUID) | Auto-generated unique identifier |
| phone | str | Phone number of the user who set the preference |
| category | str | `"dietary"` (new category added alongside existing: notification_optout, topic_filter, communication_style, quiet_hours) |
| description | str | Human-readable constraint (e.g., "No vegetarian meals — family preference") |
| raw_text | str | Original user message that triggered the preference |
| created_at | str (ISO datetime) | When the preference was saved |

### Communication Mode (modified)

Existing entity in `src/context.py`. Mode descriptions updated to remove proactive language.

| Mode | Hours | Current Description | New Description |
|------|-------|---------------------|-----------------|
| morning | 7am-12pm | "energetic, proactive suggestions welcome" | "responsive, answer questions directly" |
| afternoon | 12pm-5pm | "normal, responsive to requests" | "responsive, answer questions directly" |
| evening | 5pm-9pm | "winding down, respond to questions but limit proactive content" | "responsive, answer questions directly, no unsolicited content" |
| late_night | 9pm-7am | "direct answers only, no proactive suggestions" | "direct answers only, no follow-up prompts" (unchanged intent) |

## No New Entities

This feature modifies existing entities and prompt rules. No new data structures, tables, or files are created.

## Relationships

- Dietary Preference → User (via phone number, same as all preferences)
- Dietary Preference → Meal Planning (checked by LLM before suggesting recipes, via system prompt injection)
- Communication Mode → System Prompt (mode description included in daily context output, influences LLM behavior)
