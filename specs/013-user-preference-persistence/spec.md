# Feature Specification: User Preference Persistence

**Feature Branch**: `013-user-preference-persistence`
**Created**: 2026-03-01
**Status**: Draft
**Input**: User description: "User preference persistence — bot remembers Erin and Jason's explicit opt-outs and communication preferences across conversations. When Erin says 'don't remind me about groceries unless I ask' or 'no Jason appointment reminders' or 'check the time before making recommendations', these preferences are stored persistently and honored in all future interactions. Preferences survive container restarts, can be listed ('what are my preferences?'), and removed ('start reminding me about groceries again'). Integrates with the existing nudge system (Feature 003) to filter proactive messages, and with the system prompt to shape response behavior. Preferences are per-user (per phone number). Same WhatsApp interface."

## Context

Erin has explicitly stated three preferences that the bot currently ignores because there is no persistence mechanism:

1. **"Don't send grocery info unless I ask"** — Erin does not want proactive grocery reminders, meal plan nudges, or unsolicited grocery lists. She wants grocery information only when she explicitly asks for it.
2. **"Don't remind me of Jason's appointments"** — Erin does not want to see Jason's calendar events in her daily briefing or proactive nudges. She only wants her own and the family calendar.
3. **"Check the time before making recommendations"** — The bot should be time-aware when making suggestions. No dinner recommendations at 8 AM, no morning routine suggestions at 3 PM, no bedtime-related nudges at noon.

Today, the bot has a 24-hour conversation window (Feature 007) and a "quiet day" toggle (Feature 003), but no mechanism to store lasting per-user preferences that survive beyond a single conversation session or container restart. The budget quiet hours rule (Rule 67 — no budget talk before 8 PM) is hardcoded in the system prompt rather than being a user-configurable preference.

This feature adds a persistent, per-user preference store that is checked on every message and before every proactive nudge, allowing the bot to honor what users have explicitly asked for.

## Assumptions

- Storage follows the established JSON file pattern: `data/user_preferences.json` (local) or `/app/data/user_preferences.json` (Docker), using the same `_DATA_DIR` pattern as `conversations.json`, `usage_counters.json`, and `budget_pending_suggestions.json`
- Preferences are keyed by phone number (same identifier used throughout the codebase via `PHONE_TO_NAME`)
- Preferences are injected into the system prompt dynamically on each incoming message so Claude respects them naturally during response generation
- The nudge system (Feature 003, `src/tools/nudges.py`) checks stored preferences before sending any proactive message
- The daily planner and meeting prep logic in the system prompt respects preference filters (e.g., excluding Jason's calendar from Erin's briefing if she opted out)
- No new Notion databases are needed — this is a lightweight JSON file feature
- No new external APIs — this is purely internal state management
- The existing WhatsApp interface is the only interaction surface
- Atomic file writes (write-to-tmp-then-rename) are used for crash safety, following the established pattern in `conversation.py`
- The existing hardcoded budget quiet hours (Rule 67) is a candidate for migration into user preferences in a future iteration, but is not required for this feature

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture & Store Preferences (Priority: P1)

When Erin or Jason states a preference in natural language — such as "don't remind me about groceries unless I ask", "stop sending me Jason's appointments", or "check the time before making suggestions" — the bot recognizes this as a lasting preference (not a one-time request), stores it persistently with a human-readable label, and confirms that it has been saved. The preference survives conversation expiry, container restarts, and redeployment.

**Why this priority**: Without capture and storage, no other preference functionality can work. This is the foundational building block. Erin has already stated preferences three times and been ignored — this directly addresses that frustration.

**Independent Test**: Send "don't remind me about groceries unless I ask" in WhatsApp. Restart the Docker container. Send a new message. Verify that the preference is still stored by asking "what are my preferences?" and seeing the grocery opt-out listed.

**Acceptance Scenarios**:

1. **Given** Erin has no stored preferences, **When** she sends "don't remind me about groceries unless I ask", **Then** the bot stores a notification opt-out preference for the "groceries" topic under Erin's phone number and confirms: "Got it — I won't bring up grocery info unless you ask. You can always change this by saying 'start reminding me about groceries again'."
2. **Given** Jason has no stored preferences, **When** he sends "no appointment reminders for me", **Then** the bot stores a notification opt-out preference for departure nudges under Jason's phone number and confirms storage.
3. **Given** Erin has stored preferences, **When** the Docker container restarts, **Then** all of Erin's preferences are loaded from the JSON file on startup and are immediately active.
4. **Given** Erin sends "check the time before making recommendations", **When** the bot processes the message, **Then** a "communication style" preference is stored indicating the bot should be time-context-aware when making suggestions.
5. **Given** Erin sends "don't tell me about Jason's appointments", **When** the bot processes the message, **Then** a topic filter preference is stored that excludes Jason's personal calendar from Erin's daily briefings and nudges.

---

### User Story 2 - Honor Stored Preferences (Priority: P1)

Once a preference is stored, the bot actively honors it in all future interactions. Notification opt-outs suppress proactive nudges on that topic. Topic filters remove excluded content from daily briefings and meeting prep. Communication style preferences shape how the bot responds (e.g., time-awareness for recommendations). Preferences are checked both at the system prompt level (injected on each message) and at the nudge delivery level (checked before sending proactive messages).

**Why this priority**: Storing preferences is useless if the bot does not act on them. This is equally critical to US1 — together they form the minimum viable feature. If Erin sets a preference and the bot ignores it, trust erodes further.

**Independent Test**: Store a grocery opt-out preference for Erin. Then trigger a daily briefing for Erin. Verify that the briefing does not include unsolicited grocery or meal plan information. Separately, trigger a nudge scan and verify that grocery-related nudges are filtered out before delivery.

**Acceptance Scenarios**:

1. **Given** Erin has a stored preference "don't remind me about groceries unless I ask", **When** the daily briefing is generated, **Then** the briefing omits unsolicited grocery and meal plan sections. If Erin explicitly asks "what's the meal plan?", the bot responds normally.
2. **Given** Erin has a stored preference "don't tell me about Jason's appointments", **When** the daily briefing fetches calendar events, **Then** Jason's personal calendar events are excluded from Erin's briefing. Family calendar and Erin's personal calendar are still included.
3. **Given** Erin has a stored preference "check the time before making recommendations", **When** the bot generates recommendations at 8 AM, **Then** it suggests breakfast/morning-appropriate activities, not dinner plans or bedtime routines.
4. **Given** Erin has a grocery opt-out preference, **When** the nudge system (`process_pending_nudges`) prepares to send a grocery-related proactive nudge, **Then** the nudge is suppressed (marked as filtered, not sent).
5. **Given** Erin has a grocery opt-out preference, **When** Erin explicitly asks "what should we have for dinner?", **Then** the bot answers the question normally — opt-outs only suppress unsolicited/proactive messages, not direct requests.
6. **Given** Jason has no grocery opt-out preference but Erin does, **When** a grocery nudge is scheduled, **Then** Jason still receives the nudge (preferences are per-user, not global).

---

### User Story 3 - List & Manage Preferences (Priority: P2)

Users can ask "what are my preferences?" to see all stored preferences in a readable list. They can remove individual preferences by describing them naturally ("start reminding me about groceries again", "remove the grocery opt-out", "I want Jason's appointments back"). The bot confirms removals and immediately stops applying the removed preference.

**Why this priority**: Users need visibility and control over their preferences. Without this, users cannot audit what preferences are active or correct mistakes. This is important but not as urgent as capture and enforcement — the P1 stories deliver value even if users cannot list preferences yet.

**Independent Test**: Store two preferences for Erin. Send "what are my preferences?" and verify both are listed with human-readable descriptions. Send "start reminding me about groceries again" and verify the grocery preference is removed. Send "what are my preferences?" again and verify only one preference remains.

**Acceptance Scenarios**:

1. **Given** Erin has three stored preferences (grocery opt-out, Jason calendar filter, time-aware recommendations), **When** she sends "what are my preferences?", **Then** the bot responds with a numbered list showing each preference with its description, category, and when it was set.
2. **Given** Erin has a grocery opt-out preference, **When** she sends "start reminding me about groceries again", **Then** the bot removes the grocery opt-out preference, confirms removal, and immediately resumes including grocery information in proactive messages.
3. **Given** Erin has a grocery opt-out preference, **When** she sends "remove preference about groceries", **Then** the bot matches "groceries" to the stored preference, removes it, and confirms.
4. **Given** Erin has no stored preferences, **When** she sends "what are my preferences?", **Then** the bot responds "You don't have any stored preferences. You can set them by telling me things like 'don't remind me about groceries unless I ask' or 'no Jason appointment reminders'."
5. **Given** Erin has a preference and sends "clear all my preferences", **When** the bot processes the message, **Then** all of Erin's preferences are removed and confirmed.

---

### User Story 4 - Preference Categories (Priority: P3)

Preferences are organized into four categories, enabling the bot to apply them correctly in different contexts:

- **Notification opt-outs**: Suppress proactive nudges for specific topics (groceries, departure reminders, budget alerts). These filter at the nudge delivery layer.
- **Topic filters**: Exclude specific content from briefings and agendas (Jason's appointments, work calendar, specific budget categories). These filter at the content generation layer.
- **Communication style**: Shape how the bot generates responses (time-awareness, verbosity, formality, emoji usage). These are injected into the system prompt.
- **Quiet hours**: Per-user time windows when specific or all proactive messages are suppressed. These filter at the nudge scheduling layer.

**Why this priority**: Categorization improves the bot's ability to apply preferences in the right context (nudge layer vs. system prompt vs. content generation). However, the P1 stories can work with a simpler flat preference list — categorization refines the architecture without adding new user-facing value.

**Independent Test**: Store one preference in each category. Verify that notification opt-outs filter nudges, topic filters modify briefing content, communication style preferences change response tone, and quiet hours suppress messages during specified windows.

**Acceptance Scenarios**:

1. **Given** Erin says "no grocery nudges", **When** the preference is stored, **Then** it is categorized as a "notification opt-out" with the topic "groceries" and is checked at the nudge delivery layer.
2. **Given** Erin says "don't include Jason's calendar in my daily plan", **When** the preference is stored, **Then** it is categorized as a "topic filter" with the scope "jason_personal_calendar" and is checked during briefing generation.
3. **Given** Erin says "keep responses short and to the point", **When** the preference is stored, **Then** it is categorized as a "communication style" preference and is injected into the system prompt on each message.
4. **Given** Erin says "no messages before 8am", **When** the preference is stored, **Then** it is categorized as "quiet hours" with a start time of 8:00 AM Pacific and is checked before any proactive nudge delivery.
5. **Given** the existing hardcoded budget quiet hours (Rule 67: no budget talk before 8 PM), **When** the preference system is active, **Then** the hardcoded rule continues to work as-is. Migration to a user preference is a future enhancement, not a requirement for this feature.

---

### Edge Cases

- **Conflicting preferences**: Erin says "don't remind me about groceries" and later says "remind me about groceries before each shopping trip." The newer preference replaces the older one for the same topic. The bot confirms: "I updated your grocery preference. I'll now remind you before shopping trips instead of staying quiet about groceries."
- **Ambiguous preferences**: Erin says "leave me alone." This could mean a temporary DND (like quiet day) or a permanent opt-out. The bot should ask for clarification: "Do you want a quiet day (just for today) or should I stop all proactive messages permanently?" If no clarification is given, default to the less destructive option (quiet day).
- **Partner-about-partner preferences**: Erin says "don't tell me about Jason's stuff." The bot stores this as a topic filter under Erin's phone number that suppresses Jason-specific content in Erin's messages. It does not affect Jason's experience.
- **Vague topic matching**: Erin says "stop the budget stuff." The bot should confirm the scope: "I can stop all budget-related proactive messages — budget summaries, spending alerts, goal checks. Should I suppress all of those, or just specific ones?"
- **Preference persistence during file corruption**: If `user_preferences.json` is corrupted or unreadable on startup, the bot logs a warning and starts with an empty preference set rather than crashing. Preferences set after recovery are saved normally.
- **Preference overflow**: A user stores an unreasonable number of preferences (50+). The system should cap at a reasonable limit (e.g., 50 per user) and warn the user when approaching the limit.
- **Implicit vs. explicit preferences**: "I hate when you mention groceries" is an explicit preference to store. "Okay, I'll check on groceries later" is a conversational acknowledgment, not a preference. The bot should only store preferences when the user's intent to set a lasting rule is clear.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect when a user's message contains a lasting preference (opt-out, filter, style, or schedule) and distinguish it from a one-time conversational request.
- **FR-002**: System MUST store preferences persistently in a JSON file that survives container restarts and redeployment.
- **FR-003**: System MUST isolate preferences per phone number so that Erin's preferences do not affect Jason's experience and vice versa.
- **FR-004**: System MUST inject the current user's active preferences into the system prompt on each incoming message so Claude naturally respects them during response generation.
- **FR-005**: System MUST check stored preferences before delivering any proactive nudge (departure reminders, chore suggestions, grocery nudges, budget alerts) and suppress nudges that match an active opt-out.
- **FR-006**: System MUST allow users to list all their active preferences via natural language ("what are my preferences?").
- **FR-007**: System MUST allow users to remove individual preferences via natural language ("start reminding me about groceries again") and immediately stop applying the removed preference.
- **FR-008**: System MUST handle conflicting preferences by treating the most recent preference for a given topic as authoritative, replacing the older one.
- **FR-009**: System MUST confirm preference creation and removal with a human-readable message that includes how to reverse the action.
- **FR-010**: System MUST load preferences from disk on startup and keep the in-memory cache synchronized with the on-disk file after every write.
- **FR-011**: System MUST use atomic file writes (write-to-tmp-then-rename) to prevent data loss during concurrent access or crashes.
- **FR-012**: System MUST NOT suppress responses to explicit user requests that match an opted-out topic. Opt-outs only affect proactive/unsolicited messages, not direct questions.
- **FR-013**: System MUST ask for clarification when a preference statement is ambiguous (e.g., "leave me alone" could mean quiet day or permanent opt-out).
- **FR-014**: System MUST cap preferences at 50 per user to prevent unbounded storage growth.

### Key Entities

- **User Preference**: A stored rule that modifies the bot's behavior for a specific user. Key attributes: unique identifier, phone number (owner), human-readable label, category (notification opt-out, topic filter, communication style, quiet hours), topic or scope (e.g., "groceries", "jason_personal_calendar"), the original natural language statement, creation timestamp, and active/inactive status.
- **Preference Category**: One of four classification buckets (notification opt-out, topic filter, communication style, quiet hours) that determines where in the processing pipeline the preference is applied.
- **Preference Store**: The persistent layer holding all user preferences. Keyed by phone number, supports CRUD operations, atomic writes, and startup loading.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Preferences persist across container restarts — a preference set before restart is active and honored after restart, verified by listing preferences and observing filtered behavior.
- **SC-002**: Bot honors a stored preference within 1 message of it being set — if Erin sets a grocery opt-out and immediately triggers a daily briefing, the briefing omits grocery content.
- **SC-003**: Zero false-positive nudges for opted-out topics — after Erin opts out of grocery nudges, no grocery-related proactive messages are sent to her, measured over a 7-day observation period.
- **SC-004**: Explicit requests override opt-outs 100% of the time — if Erin asks "what's the meal plan?" despite a grocery opt-out, she gets a full answer.
- **SC-005**: Preference listing is complete and accurate — "what are my preferences?" returns all stored preferences with no omissions and no phantom entries.
- **SC-006**: Preference removal takes effect immediately — after removing a preference, the very next interaction reflects the removal (e.g., grocery info reappears in the daily briefing).
- **SC-007**: The three specific preferences Erin has already requested are supported on day one: grocery opt-out, Jason appointment filter, and time-aware recommendations.
