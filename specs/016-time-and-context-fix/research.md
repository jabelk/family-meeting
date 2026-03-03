# Research: Time Awareness & Extended Conversation Context

**Feature**: 016-time-and-context-fix | **Date**: 2026-03-03

## R1: Why Claude Ignores the Current Time in System Prompt

**Decision**: Inject timestamp into the user message content AND add explicit time-checking rules to the system prompt.

**Rationale**: The current approach places `**Right now:** Monday, March 03, 2026 at 12:30 PM Pacific.` at the top and bottom of the system prompt. This was a P1 fix (GitHub issue #2) but it's insufficient because:
1. The system prompt is long (~200 lines). By the time Claude processes the user's request ("plan my day"), the timestamp at the top is far away in context.
2. Claude tends to attend more to information near the user message than at the edges of the system prompt.
3. There's no explicit instruction telling Claude to check the time before generating schedules.

**Solution — three-pronged approach**:
1. **Keep existing**: timestamp at top and bottom of system prompt (already done)
2. **Add to user message**: Prepend `[Current time: Monday, March 3, 2026 at 12:30 PM Pacific]` before the user's message content so it's directly adjacent to the request
3. **Add explicit rules**: Add rules to SYSTEM_PROMPT saying "ALWAYS check the current time before generating any schedule or plan. Never suggest activities for times that have already passed."

**Alternatives considered**:
- Removing time from system prompt entirely (bad — Claude needs it for non-schedule questions too)
- Using a tool call for time (unnecessary overhead — time is known at message receipt)
- Adding time as a separate system message (Anthropic API only supports one system block)

## R2: Optimal Conversation Retention Window

**Decision**: 7-day timeout + 100-turn limit.

**Rationale**: The family sends roughly 10-20 turns per person per day on active days, and many days have zero messages. A 7-day window at 100 turns provides ample coverage for a typical week while bounding storage and API token costs.

**Token budget check**: At ~500 tokens per serialized turn (user message + assistant response + tool calls), 100 turns = ~50K tokens. Claude Haiku 4.5's context window is 200K tokens, and the system prompt is ~5K tokens. This leaves ~145K tokens of headroom — more than sufficient.

**Alternatives considered**:
- 30-day retention (too much history — stale context would confuse Claude)
- Unlimited turns (unbounded storage and token growth)
- Summarization of old turns (out of scope per spec; adds complexity for minimal gain)

## R3: Conversation Timeout Behavior Change

**Decision**: Change timeout from "inactivity" (24h since last message) to "age-based" (7 days since oldest turn).

**Rationale**: The current 24-hour inactivity timeout means if Erin doesn't message for 25 hours, ALL history is wiped. With a 7-day window, we should keep all turns from the last 7 days regardless of gaps. This better serves the use case of "Erin discussed something Monday, asks about it Thursday."

**Implementation**: Instead of checking `last_active + timeout > now`, prune individual turns older than 7 days on each `get_history()` call. Keep the `last_active` field for backwards compatibility but use per-turn timestamps for retention decisions.

**Change required**: Each turn needs a `timestamp` field. Currently turns are just `{"messages": [...]}`. Add `{"messages": [...], "timestamp": "ISO8601"}` on save. Old turns without timestamps are treated as "keep" (won't be pruned until they naturally fall off the 100-turn limit).

## R4: Date Format Consistency

**Decision**: Use `%-d` (unpadded day) and `%-I` (unpadded hour) consistently across both `assistant.py` and `context.py`.

**Rationale**: `assistant.py` currently uses `%d` (zero-padded: "March 03") while `context.py` uses `%-d` (unpadded: "March 3"). The unpadded format is more natural for human reading and matches how people say dates. Using consistent formatting across all time injections reduces confusion.

**Change**: `assistant.py:1617` — change `%d` to `%-d` and `%I` to `%-I`.
