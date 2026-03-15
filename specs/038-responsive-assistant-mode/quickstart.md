# Quickstart: Responsive Assistant Mode

**Feature**: 038-responsive-assistant-mode | **Date**: 2026-03-15

## What This Feature Does

Flips the assistant from proactive (suggesting things unprompted) to responsive (only suggesting when asked). Also adds structured dietary preferences that are automatically enforced during meal planning.

## Key Changes

| File | Change |
|------|--------|
| `src/prompts/system/03-daily-planner.md` | Remove Rule 12 (auto-fill free time with backlog items) |
| `src/prompts/system/05-chores-nudges.md` | Remove proactive chore suggestion behavior from Rules 23-26 |
| `src/prompts/system/08-advanced.md` | Update Rule 68 communication mode descriptions to all be responsive |
| `src/context.py` | Update mode description strings to match new responsive defaults |
| `src/preferences.py` | Add "dietary" to valid preference categories |
| `src/prompts/system/08-advanced.md` | Add dietary preference enforcement instruction near Rule 55 |

## How to Test

### 1. No Unsolicited Suggestions (US1)

Manual test via WhatsApp:
- Ask "schedule my day" when calendar has free time gaps
- Verify free time is shown as free, NOT filled with backlog suggestions
- Then ask "what should I do with my free hour?"
- Verify it THEN suggests backlog items

### 2. Dietary Preferences (US2)

Manual test via WhatsApp:
- Say "no vegetarian meals"
- Verify the bot saves it as a dietary preference
- Ask for dinner suggestions
- Verify no vegetarian-only options are suggested
- Say "Jason doesn't eat fish"
- Ask for a dinner plan for a night Jason is home
- Verify no fish dishes are suggested

### 3. Quieter Communication Modes (US3)

Manual test via WhatsApp:
- At 9 AM (morning mode), send a simple question
- Verify response is direct, no appended "you could also..." tips
- Verify departure reminders still work (create an event 30 min from now)

## Deployment Notes

- No new dependencies
- No database changes
- No environment variable changes
- No new endpoints
- Safe to deploy as a single commit — all changes are prompt edits + one preference category addition
- Rollback: revert the prompt files to restore proactive behavior
