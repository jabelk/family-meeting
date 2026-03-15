# Feature Specification: Responsive Assistant Mode

**Feature Branch**: `038-responsive-assistant-mode`
**Created**: 2026-03-15
**Status**: Draft
**Input**: User description: "Stop proactive nagging, structured dietary preferences, flip default behavior from push to pull — driven by Erin's explicit feedback."

## Context: The Push vs Pull Problem

The assistant was designed as a **proactive family coach** — filling free time windows with backlog items, suggesting chores during gaps, and nudging about departures. But Erin uses it as an **on-demand executive assistant**. She wants help when she asks for it, not unsolicited suggestions.

### Evidence from Erin's Chats

**Explicit feedback about proactive suggestions:**
> Turn 44 (Thursday 10:54 PM): "Stop suggesting things to do when I have a free window unless I ask you."

**Explicit feedback about chore nudges:**
> Turn 59 (Friday 9:20 PM): "Oooo I don't want you to tell me that I need to wipe my kitchen."

**Dietary preferences stated but not persistently enforced:**
> Image caption (March 14): "No recommending vegetarian meals."
> Turn 27 (Tuesday 6:35 PM): "That all looks good but I forgot to tell you Jason doesn't eat fish."
> Turn 26 (Tuesday 6:32 PM): "...make sure that it's not vegetarian."

### Current Behavior (What Needs to Change)

The system has several rules that drive proactive behavior Erin has asked to stop:

1. **Rule 12** (Daily Planner): "For ANY free time slots in the daily plan (even 10-15 minutes), call get_backlog_items and suggest a specific backlog task that fits the window." — This directly contradicts Erin's feedback.

2. **Rule 68** (Communication Modes): Morning mode is described as "energetic, proactive suggestions welcome" — Erin didn't agree to this.

3. **Rules 23-26** (Chores & Nudges): Drive proactive chore suggestions, departure reminders, and chore preference tracking. Erin wants to opt out of unsolicited chore suggestions.

4. **Dietary preferences** are stored as free-text notes in the Family Profile, not as structured constraints that meal planning tools check before suggesting.

The system already has a preference mechanism (Rule 55, `save_preference` tool) and a `set_quiet_day` tool, but the default is still proactive — the user has to opt out. The fix is to **flip the default**: quiet by default, proactive only when asked.

## User Scenarios & Testing

### User Story 1 - No Unsolicited Activity Suggestions (Priority: P1)

When the assistant generates a daily plan or responds to a schedule question, it must NOT fill free time windows with backlog items or chore suggestions unless the user explicitly asks "what should I do?" or "what's on my backlog?" The default behavior is to respect free time as free time.

**Why this priority**: This is Erin's most direct complaint — she told the bot to stop twice. Every unsolicited suggestion erodes trust and makes her feel nagged rather than helped.

**Independent Test**: Ask the bot to "schedule my day" and verify that free time windows are shown as free, not filled with backlog suggestions. Then ask "what should I do with my free hour?" and verify it THEN suggests backlog items.

**Acceptance Scenarios**:

1. **Given** Erin asks "schedule my day" and her calendar has a 2-hour gap from 10 AM to noon, **When** the assistant generates the plan, **Then** the gap is shown as "Free time" without any backlog or chore suggestions.
2. **Given** Erin asks "I have an hour, what should I do?", **When** the assistant responds, **Then** it calls get_backlog_items and suggests appropriate tasks for the time window — because she explicitly asked.
3. **Given** Erin asks "what's on my schedule today?" at 2 PM, **When** the assistant responds, **Then** it shows her remaining events without appending "you could also..." suggestions.
4. **Given** Erin has a preference saved that says "no unsolicited suggestions", **When** the assistant generates any response, **Then** it does not proactively suggest activities, chores, or backlog items unless explicitly asked.

---

### User Story 2 - Structured Dietary Preferences (Priority: P2)

When dietary constraints are expressed ("no vegetarian meals", "Jason doesn't eat fish"), they must be saved as structured, persistent rules that are automatically checked before any meal plan, recipe suggestion, or grocery list is generated. The user should never have to repeat a dietary preference.

**Why this priority**: Erin has stated dietary preferences at least 3 times in different conversations. The current system stores them as free-text profile notes, but the meal planning tools don't check them before suggesting recipes.

**Independent Test**: Save "no vegetarian meals" as a dietary preference, then ask for dinner suggestions and verify no vegetarian options are included.

**Acceptance Scenarios**:

1. **Given** Erin says "no vegetarian meals" or "don't recommend vegetarian", **When** the assistant processes the request, **Then** it saves a structured dietary preference that persists across conversations.
2. **Given** a "no vegetarian" dietary preference is saved, **When** Erin asks for meal suggestions or a weekly meal plan, **Then** all suggested meals include a protein source (meat, fish, poultry) and no vegetarian-only options are presented.
3. **Given** Erin says "Jason doesn't eat fish", **When** the assistant generates a dinner plan for a night Jason will be home, **Then** no fish-based meals are suggested for that dinner.
4. **Given** dietary preferences exist, **When** Erin asks "what are my dietary preferences?", **Then** the assistant lists all saved dietary constraints clearly.
5. **Given** Erin says "actually, Jason is okay with salmon now", **When** the assistant processes this, **Then** the "no fish" constraint is updated or removed appropriately.

---

### User Story 3 - Quieter Communication Modes (Priority: P3)

The default communication mode should be responsive (answer when asked) across all time periods, not proactive in the morning. The "proactive suggestions welcome" language should be removed from morning mode. Departure reminders and imminent-event nudges can remain, but unsolicited activity suggestions should stop in all modes.

**Why this priority**: This is a supporting change that reinforces US1. The communication mode labels influence the LLM's behavior even when explicit rules exist. "Proactive suggestions welcome" in morning mode contradicts the intent of US1.

**Independent Test**: At 9 AM (morning mode), ask the bot a simple question and verify it answers directly without appending unsolicited tips, suggestions, or "you could also..." content.

**Acceptance Scenarios**:

1. **Given** it is 9 AM (morning mode) and Erin sends a simple message, **When** the assistant responds, **Then** it answers her question without adding unsolicited suggestions or tips.
2. **Given** it is any time of day and Erin has an event starting in 30 minutes, **When** the departure reminder system checks, **Then** departure reminders still fire (these are event-driven, not unsolicited suggestions).
3. **Given** it is evening (after 5 PM), **When** Erin asks a question, **Then** the assistant responds normally without "gentle nudges" about upcoming tasks.
4. **Given** Erin explicitly asks for suggestions ("give me ideas for tonight", "what should we do this weekend?"), **When** the assistant responds, **Then** it provides creative, helpful suggestions — the change only affects unsolicited content.

---

### Edge Cases

- What happens when Erin sets a quiet day via `set_quiet_day` — does it still work? Yes, it should remain as an additional layer for suppressing departure reminders too.
- What happens when a new user starts using the system — should they get the proactive experience by default? No, responsive is the new default for all users.
- What happens when Erin explicitly asks the bot to be more proactive ("remind me to do my backlog items", "nudge me about chores")? The assistant should honor this as a preference that re-enables proactive behavior for that specific topic.
- What happens to the laundry timer functionality (Rules 27)? Laundry reminders are user-initiated (Erin says "started laundry") so they are pull-based and should continue unchanged.
- What happens to the "Did you know?" tips (Rule 39)? These are contextual tips appended to tool-use responses. They should remain but be less frequent — maximum 1 per conversation, not 1 per response.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST NOT proactively suggest backlog items, chores, or activities during free time windows in daily plans. Free time windows should be labeled as "Free time" or simply left unscheduled.
- **FR-002**: The system MUST suggest backlog items and activities ONLY when the user explicitly requests them (e.g., "what should I do?", "what's on my backlog?", "I have free time, suggest something").
- **FR-003**: The system MUST support structured dietary preferences that persist across conversations. Dietary preferences must be checked automatically before any meal suggestion, recipe search, or grocery list generation.
- **FR-004**: Dietary preferences MUST support per-family-member constraints (e.g., "Jason doesn't eat fish" applies only to meals when Jason is eating, not Erin's solo dinners).
- **FR-005**: The system MUST change all communication mode descriptions to be responsive by default. No mode should include language encouraging proactive suggestions.
- **FR-006**: Departure reminders and imminent-event nudges MUST continue to function — they are event-driven, not unsolicited activity suggestions.
- **FR-007**: The "Did you know?" contextual tips MUST be limited to at most 1 per conversation (not 1 per response), and only after substantive tool interactions.
- **FR-008**: The user MUST be able to explicitly opt IN to proactive behavior for specific topics (e.g., "nudge me about my backlog every morning") via the existing preference system.

### Key Entities

- **Dietary Preference**: Family member name, constraint type (exclude ingredient, exclude cuisine, exclude category), constraint value (e.g., "vegetarian", "fish", "pork"), applies-when context (always, or only when specific family member is eating).
- **Communication Mode**: Time-of-day label, behavior description (responsive for all modes), proactive content allowed (none by default, departure reminders always).

## Success Criteria

### Measurable Outcomes

- **SC-001**: Zero unsolicited activity/chore/backlog suggestions in a 2-week observation window — the bot only suggests when the user explicitly asks.
- **SC-002**: Zero "stop suggesting" or "I didn't ask for that" complaints from the user in the 2 weeks after deployment.
- **SC-003**: When a dietary preference is saved (e.g., "no vegetarian"), 100% of subsequent meal suggestions comply with the constraint — zero violations.
- **SC-004**: When the user explicitly asks "what should I do?", the system still provides helpful backlog-based suggestions 100% of the time — responsiveness is preserved, only unsolicited suggestions are removed.
- **SC-005**: Departure reminders and laundry timers continue to function normally — zero regressions in user-initiated reminder flows.

## Assumptions

- The preference system (`save_preference`, `list_preferences`, `remove_preference`) is functioning correctly and will be the storage mechanism for dietary preferences.
- Departure reminders (Rule 23) are event-driven (triggered by upcoming calendar events) and are distinct from unsolicited activity suggestions — they should continue unchanged.
- Laundry tracking (Rule 27) is user-initiated and should continue unchanged.
- The `set_quiet_day` tool should remain available as an additional opt-out layer for departure reminders.
- "Did you know?" tips (Rule 39) are low-friction and can remain in reduced frequency (1 per conversation) without being considered proactive nagging.

## Dependencies

- Existing preference system (`src/preferences.py`, `save_preference` tool) — already deployed, will be extended for dietary preferences
- Existing communication mode system (`src/context.py`) — already deployed, mode descriptions will be updated
- Feature 037 (Calendar Reliability) — already deployed, no conflicts
