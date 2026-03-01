# Research: User Preference Persistence

**Feature**: 013-user-preference-persistence
**Date**: 2026-03-01

## Decision 1: Storage Format

**Question**: How should user preferences be stored?

**Options evaluated**:
1. **Notion database** — Consistent with action items, chores, nudges
2. **JSON file in data/** — Consistent with conversations.json, usage_counters.json, budget_pending_suggestions.json
3. **SQLite** — Structured queries but new dependency

**Decision**: JSON file (`data/user_preferences.json`)

**Rationale**:
- Follows the established pattern used by conversation.py, discovery.py, amazon_sync, and email_sync
- No API rate limits or external dependencies — preferences are checked on EVERY message
- Atomic write pattern already proven reliable (write-to-tmp-then-rename)
- Preferences are simple key-value data — no relational queries needed
- Notion API calls take 200-500ms each; preferences must be near-instant since they're injected into every system prompt
- Docker volume mount already configured for `data/` directory

## Decision 2: Preference Detection Approach

**Question**: How should the bot detect when a user is expressing a lasting preference vs. a one-time request?

**Options evaluated**:
1. **NLP classifier** — Train a model to detect preference intent
2. **Claude tool calling** — Let Claude decide when to call save_preference based on system prompt instructions
3. **Keyword matching** — Pattern match "don't", "stop", "no more" etc.

**Decision**: Claude tool calling (option 2)

**Rationale**:
- Claude already handles all message interpretation in the agentic tool loop
- Adding a `save_preference` tool with clear system prompt instructions lets Claude distinguish "don't remind me about groceries" (lasting preference) from "no I don't want tacos tonight" (one-time request)
- Claude can also detect ambiguous cases and ask for clarification (FR-013)
- Same pattern as all other tools — no new infrastructure needed
- System prompt instructions tell Claude: "when a user says 'don't [X]', 'stop [X]', 'no more [X]' in a way that implies a lasting rule, call save_preference"

## Decision 3: System Prompt Injection Strategy

**Question**: How should stored preferences modify the bot's behavior?

**Options evaluated**:
1. **Pre-filter approach** — Filter messages/nudges before they reach Claude
2. **System prompt injection** — Append active preferences to the system prompt so Claude naturally honors them
3. **Hybrid** — Inject into system prompt AND filter at the nudge layer

**Decision**: Hybrid (option 3)

**Rationale**:
- System prompt injection handles conversational behavior: Claude sees "User preferences (MUST honor these): No grocery info unless asked" and naturally avoids volunteering grocery info
- Nudge layer filtering handles proactive messages: `process_pending_nudges()` checks preferences before sending, so opted-out nudges never reach the user even when Claude isn't in the loop
- This covers both interactive (WhatsApp chat) and automated (n8n cron nudges) paths
- The system prompt injection is lightweight — just appending a few bullet points to the existing system string in `handle_message()`

## Decision 4: Preference Categories

**Question**: Should categories be enforced in code or just advisory labels?

**Decision**: Advisory labels stored as strings. Categories are: `notification_optout`, `topic_filter`, `communication_style`, `quiet_hours`.

**Rationale**:
- Categories help Claude apply preferences in the right context (the system prompt can say "this is a notification opt-out, only suppress proactive messages")
- But enforcement is through Claude's judgment (system prompt) and simple keyword matching in the nudge filter — no complex category-to-behavior mapping needed
- Keeping categories as strings avoids over-engineering while still enabling future refinement

## Decision 5: Preference Cap

**Question**: What limit should be set per user?

**Decision**: 50 preferences per user (FR-014).

**Rationale**:
- Realistic usage is 5-15 preferences per user
- 50 is generous enough to never hit accidentally
- Prevents unbounded JSON growth from bugs or misuse
- Each preference is ~200 bytes JSON — 50 preferences per user is ~10KB, negligible
