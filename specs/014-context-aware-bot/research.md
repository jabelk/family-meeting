# Research: Context-Aware Bot

**Feature**: 014-context-aware-bot | **Date**: 2026-03-01

## R1: get_daily_context Tool Design

**Decision**: Single synchronous function in `src/context.py` that returns a structured text block. Called by the model as a tool (not auto-injected into every message).

**Rationale**: The model should decide when context is needed (planning, scheduling, recommendations) rather than paying the API cost on every "what's the capital of France?" message. A text block (not JSON) is ideal because Claude consumes it directly as context — no parsing step needed.

**Design**:
```python
def get_daily_context(phone: str) -> str:
    """Build structured context snapshot for the current moment."""
```

**Output structure** (plain text, ~400-600 chars):
```
📅 Saturday, March 1, 2026 at 10:30 AM Pacific

🕐 Communication mode: morning (energetic, proactive suggestions welcome)

👤 Jason's events today:
- 9:00 AM: BSF at Sparks Christian Fellowship [jason]
- No other events

👤 Erin's events today:
- 8:00 AM: Vienna ski lesson [erin]
- No other events

👨‍👩‍👧‍👦 Family events today:
- No family events

👶 Zoey: With Erin (no childcare event detected)

📋 Pending backlog items: 7
⚙️ Active preferences: 2 (no grocery reminders, quiet after 9pm)
```

**API calls**:
1. `get_events_for_date(today, calendar_names=["jason", "erin", "family"])` — single call, returns all 3 calendars
2. `preferences.get_preferences(phone)` — in-memory lookup, zero API cost
3. `notion.get_backlog_items()` — single Notion API call for count

**Alternatives considered**:
- Auto-inject context on every message: Rejected — wastes API calls and tokens on simple questions
- Return JSON for model to parse: Rejected — Claude handles structured text natively, JSON adds unnecessary complexity
- Separate tools per domain (get_calendar_context, get_childcare_status): Rejected — adds tool call overhead, violates simplicity principle

## R2: Childcare Inference Algorithm

**Decision**: Keyword-based matching against today's calendar events with time-window check.

**Rationale**: Calendar events already contain enough information to infer who has Zoey. No need for a separate childcare database — the calendar IS the source of truth.

**Algorithm**:
1. Get today's events from all 3 calendars
2. Search event summaries for childcare keywords: `{"zoey", "sandy", "preschool", "childcare", "babysit", "milestones", "daycare", "nanny"}`
3. For matching events, check if the current time falls within the event's time window
4. If a match is found: report "Zoey is with [Sandy/preschool/etc.] until [end_time]"
5. If no match: default to "Zoey is with Erin" (she's the stay-at-home parent)

**Edge cases**:
- All-day childcare events (no specific time): report for the full day
- Multiple overlapping childcare events: use the most specific one (timed > all-day)
- Both parents at an event simultaneously: report "Zoey needs alternative care" (but don't alarm — just note it)

**Alternatives considered**:
- Hardcode Sandy's schedule in config: Rejected — this is exactly the problem we're fixing
- Notion database for childcare: Rejected — over-engineering, calendar events already capture this

## R3: Communication Mode Boundaries

**Decision**: Time-based mode with preference overrides parsed from the existing preference system.

**Default boundaries** (Pacific time):
| Mode | Hours | Behavior |
|------|-------|----------|
| morning | 7:00 AM – 12:00 PM | Energetic, proactive suggestions welcome |
| afternoon | 12:00 PM – 5:00 PM | Normal tone, responsive |
| evening | 5:00 PM – 9:00 PM | Winding down, respond but limit proactive content |
| late_night | 9:00 PM – 7:00 AM | Minimal, direct answers only, zero proactive content |

**Preference override parsing**:
- Look for `quiet_hours` and `communication_style` preferences
- Parse patterns: "quiet after Xpm" → set late_night start to X:00 PM
- Parse patterns: "morning mode until X" → extend morning to X:00
- If no matching preference: use defaults

**Nudge integration**: `process_pending_nudges()` in `nudges.py` already enforces quiet hours (7 AM – 8:30 PM). The communication mode replaces the hardcoded `QUIET_HOURS_*` constants with preference-aware boundaries. During `evening` and `late_night`, proactive nudges are suppressed.

**Alternatives considered**:
- Per-mode preference storage (separate from existing preferences): Rejected — unnecessary new storage, existing preference system handles it
- Gradual transitions between modes: Rejected — added complexity for marginal UX benefit, instant cutoff is simpler and predictable

## R4: Routine Storage Format

**Decision**: JSON file at `data/routines.json`, per-phone storage, same pattern as `preferences.py`.

**Schema**:
```json
{
  "15551234567": {
    "routines": [
      {
        "id": "rtn_a1b2c3d4",
        "name": "morning skincare",
        "steps": [
          {"position": 1, "description": "Wash face"},
          {"position": 2, "description": "Toner"},
          {"position": 3, "description": "Vitamin C serum"},
          {"position": 4, "description": "Moisturizer"},
          {"position": 5, "description": "Sunscreen"}
        ],
        "created": "2026-03-01T10:30:00",
        "modified": "2026-03-01T10:30:00"
      }
    ]
  }
}
```

**Module**: `src/routines.py` — mirrors `src/preferences.py` exactly:
- `_DATA_DIR` detection (Docker vs local)
- In-memory dict cache `_routines`
- Atomic file writes (write to .tmp, rename)
- Auto-load on module import
- Public API: `get_routine(phone, name)`, `save_routine(phone, name, steps)`, `modify_routine(phone, name, action, step, position)`, `delete_routine(phone, name)`, `list_routines(phone)`

**Max routines per user**: 20 (reasonable cap, matching preference cap pattern)

**Alternatives considered**:
- Notion database for routines: Rejected — over-engineering for a simple ordered list, JSON file is sufficient and faster
- Store in family profile page: Rejected — per-user routines don't belong in the shared family profile
- SQLite: Rejected — adds a new dependency, JSON files are the established pattern

## R5: System Prompt Cleanup Strategy

**Decision**: Remove all dynamic/stale data from the system prompt. Keep static identity, behavioral rules, and tool instructions.

**Lines to REMOVE** (currently lines 42-74, ~33 lines):
- Lines 42-44: Childcare schedule (Sandy's days)
- Lines 46-58: Weekly schedule (Mon-Sun breakdown)
- Lines 60-61: Jason's breakfast preference
- Lines 63-66: Erin's daily needs description
- Lines 68-74: Erin's chore needs and best chore windows

**Lines to ADD** (~5 lines, replacing removed ~33):
```
**Dynamic context:** Call `get_daily_context` at the start of any planning,
scheduling, or recommendation interaction. This returns today's calendar events
grouped by person, who has Zoey, the current communication mode, and active
preferences. Do NOT reference any hardcoded schedule — all schedule data comes
from this tool.
```

**Rules to MODIFY**:
- Rule 9: Remove "use the day-specific schedule above" → "use `get_daily_context` output"
- Rule 10: Remove hardcoded Zoey schedule references → "check childcare status from `get_daily_context`"
- Rule 16: Keep but simplify — "update the family profile" still applies

**Rules to REMOVE entirely**:
- None — rules are behavioral, not data. They stay.

**Estimated result**: ~413 - 33 + 5 = ~385, then further cleanup of rule redundancy gets to ≤280.

**Additional cleanup opportunities** (to reach ≤280):
- Consolidate Rules 40-46 (cross-domain thinking, 7 rules) into 3 rules
- Consolidate Rules 51-56 (Amazon sync, 6 rules) into 3 rules
- Consolidate Rules 57-61 (Email sync, 5 rules) into 3 rules
- Move budget quiet hours (Rule 68) into communication mode (covered by get_daily_context)
- Consolidate Rules 69-71 (preferences, 3 rules) into 1 rule

**Alternatives considered**:
- Keep some hardcoded data as fallback: Rejected — defeats the purpose, creates drift risk
- Move everything to a config file instead of tools: Rejected — still requires deploy to change, doesn't solve the core problem
