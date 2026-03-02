# Research: iOS Work Calendar Sync

**Feature**: 015-ios-work-calendar | **Date**: 2026-03-02

## R1: iOS Shortcut Calendar Access

**Decision**: Use "Find Calendar Events" action in iOS Shortcuts to read Cisco/Exchange calendar events.

**Rationale**: iOS Shortcuts has native access to all calendars configured on the phone via the EventKit framework. This includes Exchange/Outlook accounts added through iOS Settings → Mail → Accounts. The "Find Calendar Events" action supports filtering by calendar name, date range, and returns title, start date, and end date for each event.

**Alternatives considered**:
- **CalDAV direct access**: Cisco IT blocks external CalDAV connections — not viable.
- **Outlook REST API**: Requires Azure AD app registration and admin consent — Cisco IT won't approve.
- **Google Calendar subscribe to Outlook**: Cisco blocks ICS feed publishing — not viable (confirmed by user).
- **Manual entry**: Too much friction — violates Constitution Principle III.

## R2: Data Transport Format

**Decision**: iOS Shortcut will POST a JSON array of events with title, start (ISO 8601), and end (ISO 8601) to the bot's endpoint.

**Rationale**: iOS Shortcuts' "Get Contents of URL" action supports POST with JSON body. The shortcut builds the JSON array using "Repeat with Each" over found calendar events, extracting title and dates formatted as ISO 8601 strings. The `X-N8N-Auth` header provides authentication using the same shared secret as all other n8n-triggered endpoints.

**Alternatives considered**:
- **Form-encoded data**: Harder to represent arrays; JSON is standard for this codebase.
- **Multipart upload**: Unnecessary complexity for a small payload.
- **Base64-encoded ICS blob**: Extra parsing step; we only need title + time blocks.

## R3: Storage Strategy

**Decision**: Atomic JSON file at `data/work_calendar.json`, keyed by ISO date string. Full date replacement on write. Auto-prune entries older than 7 days.

**Rationale**: Follows the exact same pattern as `preferences.py` (atomic write via temp file + rename), `conversation.py`, and `routines.py`. The file is small (~1-3KB for a full week of meetings). Docker volume mount at `/app/data` already handles persistence across container restarts.

**Alternatives considered**:
- **Notion database**: Adds API call latency to daily plan generation; overkill for a single user's ephemeral schedule data.
- **SQLite**: Adds a dependency; JSON file is simpler and sufficient for this scale.
- **In-memory only**: Doesn't survive container restarts — unacceptable since shortcut runs weekly.

## R4: Fallback Behavior in outlook.py

**Decision**: Modify `get_outlook_events()` and `get_outlook_busy_windows()` to check `data/work_calendar.json` first. If today's data exists and is fresh (≤7 days old), use it. If ICS URL is configured, prefer ICS feed. If neither, return graceful "unavailable" message.

**Rationale**: The spec (FR-010) says to fall back to ICS if configured, using pushed data only when ICS is unavailable. In practice, Jason's Cisco IT blocks ICS, so `OUTLOOK_CALENDAR_ICS_URL` will be empty. The priority order is: ICS URL (if configured) → pushed data (if fresh) → "unavailable" message.

**Alternatives considered**:
- **New separate tool**: Adds complexity to assistant.py tool definitions; modifying the existing tool is simpler and transparent to the Claude agent.
- **Merge ICS + pushed data**: Over-engineering — they're mutually exclusive in practice.

## R5: iOS Shortcut Automation Trigger

**Decision**: Weekly automation trigger on Sunday at 7:00 PM Pacific. Pushes Monday–Friday events for the upcoming week.

**Rationale**: Runs before the Monday 7 AM daily briefing. Sunday evening is reliable — phone is typically on WiFi, charged, and Jason doesn't need to interact. iOS 16+ supports time-based automations that run without confirmation (if the user enables "Run Immediately" in Shortcuts settings). A single weekly push minimizes battery/network impact.

**Alternatives considered**:
- **Daily push**: More frequent than needed; most meeting schedules don't change daily.
- **Push notification trigger**: Requires a push notification service — adds complexity.
- **Manual trigger only**: Violates Constitution Principle III (zero friction). Automation is essential.

## R6: Empty Day vs No Data Distinction (FR-009)

**Decision**: Store an explicit entry for each day in the pushed range. Days with no meetings get `"events": []`. Days not in the file (or expired) mean "no data received."

**Rationale**: The spec requires distinguishing "Jason is free all day" from "we don't know Jason's schedule." An empty array explicitly means "no meetings." Absence of the date key means no data was pushed. The `received_at` timestamp enables 7-day expiration.

**Alternatives considered**:
- **Sentinel value**: e.g., `"events": "none"` — type inconsistency, harder to parse.
- **Separate "coverage" field**: Over-engineering for this simple case.
