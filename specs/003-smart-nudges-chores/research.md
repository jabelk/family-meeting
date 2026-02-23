# Research: Smart Nudges & Chore Scheduling

## R1: Nudge Persistence — Notion vs. File-Based

**Decision**: Notion database for Nudge Queue
**Rationale**: Survives container restarts without Docker volume configuration. Queryable via existing notion-client. Auditable (Erin can see pending nudges in Notion UI). Follows the established pattern of 7 existing Notion databases.
**Alternatives considered**:
- JSON file in Docker volume: Simpler but requires volume mount changes, no UI visibility, risk of data loss on container rebuild
- SQLite: Adds a dependency, not queryable from outside the container
- In-memory with periodic flush: Loses state on restart (violates FR-012)

## R2: Calendar Scan Frequency

**Decision**: n8n cron every 15 minutes during quiet hours window (`*/15 7-20 * * *`)
**Rationale**: 15-minute polling balances timeliness (nudges arrive within 2 min of scheduled time per NFR-001) against API usage. Events created <15 min before start get an immediate nudge when the next scan catches them. Google Calendar API free tier supports this volume easily.
**Alternatives considered**:
- Google Calendar push notifications (webhooks): More complex setup, requires public endpoint registration, 7-day channel expiry renewal. Overkill for single-user system.
- 5-minute polling: Unnecessary granularity; nudges are 15-30 min before events
- 30-minute polling: Too coarse; could miss the nudge window entirely for events created <30 min before start

## R3: Virtual Event Detection Strategy

**Decision**: Default to departure-required; exclude if virtual indicators present
**Rationale**: Clarified in spec session — missing a real departure event is worse than an unnecessary nudge. Virtual indicators (conferenceData, keywords) are reliably detectable from Google Calendar event data.
**Indicators for virtual**:
- `conferenceData` field present (Zoom, Meet, Teams auto-populated by Google Calendar)
- Title/description keywords: "call", "virtual", "remote", "online", "zoom", "meet", "teams", "webinar"
- All-day events (no departure time)
- Assistant-created events (`createdBy=family-meeting-assistant`)

## R4: Laundry Timer Architecture

**Decision**: Store laundry sessions in Nudge Queue (as nudge type "laundry") rather than a separate database
**Rationale**: Laundry reminders are just time-delayed nudges. Using the same Nudge Queue database with a `nudge_type` field keeps the architecture simple (one database instead of two for time-based reminders). The Laundry Session entity is a logical grouping of related nudges, tracked via a shared `session_id`.
**Alternatives considered**:
- Separate Laundry Sessions database: More normalized, but adds unnecessary complexity for a single-session-at-a-time use case
- n8n delayed execution: n8n has a "Wait" node but managing dynamic timers through workflow modifications is fragile

## R5: Free Window Detection

**Decision**: Compare `get_events_for_date()` against routine templates parsed by Claude
**Rationale**: Routine templates are stored as free-text in Notion (day-specific schedules). Parsing them programmatically requires either regex (brittle) or Claude (reliable). Since the daily briefing already uses Claude to interpret templates, the same pattern applies. Free windows are gaps between calendar events and routine blocks >= 15 minutes.
**Alternatives considered**:
- Structured routine storage (Notion database): Would require migrating existing text templates. Higher effort, no clear benefit given Claude already parses them reliably
- Hardcoded time slots: Too rigid for a schedule that varies by day/week

## R6: Daily Message Cap Implementation

**Decision**: Track daily send count in Nudge Queue (count nudges with status "sent" and today's date)
**Rationale**: No additional storage needed — just query the Nudge Queue. The 8-message cap (NFR-002) is checked before each send. Excludes replies to Erin's direct messages (those go through the webhook handler, not the nudge pipeline).
**Alternatives considered**:
- In-memory counter: Resets on restart, could exceed cap after restart
- Separate counter in Family Profile: Extra write per message; Nudge Queue already has the data

## R7: WhatsApp 24-Hour Window for Nudges

**Decision**: Rely on daily briefing (7am) to open the window; nudge scanner checks window status before sending
**Rationale**: WF-001 daily briefing fires at 7am M-F, which opens the 24-hour messaging window. Weekend nudges may require template fallback. The existing `send_message_with_template_fallback()` function handles this gracefully.
**Alternatives considered**:
- Separate "window opener" message: Adds noise; daily briefing already serves this purpose
- Only send nudges on weekdays: Too restrictive; weekend events (playdates, church) also need departure nudges
