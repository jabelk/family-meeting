# Research: AI-Powered Weekly Family Meeting Assistant

**Branch**: `001-ai-meeting-assistant` | **Date**: 2026-02-22 (v2 — expanded scope)

## Decision 1: WhatsApp Integration Approach

**Decision**: Meta WhatsApp Cloud API (direct, no third-party middleware)

**Rationale**: For a low-volume family bot (~20-50 messages/week), the direct
Meta Cloud API is simpler and cheaper than Twilio or other providers. All
user-initiated (service) conversations are free since November 2024.

**Estimated cost**: $0/month

## Decision 2: AI Orchestration

**Decision**: Anthropic Claude API with Python SDK tool runner

**Model**: Claude Haiku 4.5 — 90% of Sonnet's performance on tool use, 3x
cheaper, 3-4x faster. Can upgrade to Sonnet by changing one string.

**Estimated cost**: ~$0.05-0.10/month

## Decision 3: Data Persistence

**Decision**: Notion API (free plan) — decision may be revisited

**Rationale**: Good programmatic API, zero cost, browsable UI. However, Erin
will never open Notion — her only interface is WhatsApp. Jason could browse
in Notion but is also comfortable with CLI/GitHub. The code is already written
for Notion, so keeping it avoids rework. If maintenance becomes an issue, can
migrate to SQLite on the NUC with minimal tool function changes.

**Alternatives evaluated and deferred**:
- SQLite on NUC: Simplest, zero dependency, but no browse UI without building one
- Postgres on NUC: Overkill for 2 users
- Obsidian: Nice mobile app but no query capability
- Graphiti knowledge graph: Evaluated and rejected — overkill (LLM calls per write, graph DB overhead for 4 entities / 2 users)
- JSON in GitHub repo: Simple but awkward for queries

**Estimated cost**: $0/month

## Decision 4: Google Calendar API — Expanded

**Decision**: Google Calendar API v3 with read AND write access

**Change from v1**: Upgraded from `calendar.readonly` to `calendar.events` scope. The assistant now writes time blocks (chores, rest, development, exercise) to Erin's Google Calendar. These appear in her Apple Calendar app with push notifications.

**Key details**:
- Scope: `https://www.googleapis.com/auth/calendar.events` (read + write events)
- Requires re-running OAuth flow (delete token.json, re-authorize)
- 3 Google Calendars: Jason's personal, Erin's personal, shared family calendar
- Batch API for creating 25-40 events/week (one HTTP request)
- `extendedProperties.private.createdBy = "family-meeting-assistant"` to tag our events
- Delete-and-recreate pattern for weekly schedule refresh (simpler than diffing)
- Color coding: use consistent `colorId` so Erin can visually distinguish auto-created blocks

**Estimated cost**: $0/month

## Decision 5: YNAB API

**Decision**: YNAB API v1 with Personal Access Token (unchanged from v1)

**Estimated cost**: $0 (with existing YNAB subscription)

## Decision 6: Jason's Work Calendar (Outlook/Cisco)

**Decision**: Published ICS feed, polled directly from Python

**Rationale**: Microsoft Graph API requires Cisco admin consent (since Oct 2025 policy change) — impractical for a personal family project. Syncing Outlook to Google Calendar has 24-48 hour delay — too stale for breakfast planning. The ICS feed approach is the simplest: Jason publishes his calendar once (2-minute setup), Python fetches the ICS URL on demand for always-fresh data.

**Setup**: Jason goes to outlook.office365.com → Settings → Calendar → Shared calendars → Publish → copy ICS link → add to `.env` as `OUTLOOK_CALENDAR_ICS_URL`

**Fallback**: If Cisco blocks calendar publishing, fall back to syncing Outlook → Google Calendar (accept stale data) or reading Apple Calendar via EventKit on Mac.

**Dependencies**: `icalendar` + `recurring-ical-events` (pip)

**Estimated cost**: $0

## Decision 7: AnyList Grocery Integration

**Decision**: Node.js sidecar wrapping the `codetheweb/anylist` npm package

**Rationale**: AnyList has no official public API. The `codetheweb/anylist` package reverse-engineers their protobuf-based API and is battle-tested in the Home Assistant ecosystem. Running it as a small Express/Docker sidecar gives our Python app a clean REST interface via `localhost`.

**Architecture**:
```
Python (FastAPI) → HTTP localhost → Node.js sidecar → AnyList servers
```

**Key operations**:
- `GET /items?list=Grocery` — get current items
- `POST /add` — add item to list
- `POST /remove` — remove item
- Clear-and-repopulate pattern for weekly meal plan refresh

**Risks**: Unofficial API — could break if AnyList changes their backend. Build so grocery push is a nice-to-have, not a hard dependency.

**Estimated cost**: AnyList $12/year

## Decision 8: Hosting Architecture

**Decision**: All services on the NUC via Docker Compose + Cloudflare Tunnel

**Rationale**: Jason already has a NUC running Docker with n8n. Adding FastAPI, the AnyList sidecar, and a Cloudflare Tunnel container gives a complete self-hosted setup with zero ongoing hosting costs. Cloudflare Tunnel provides the public HTTPS URL that WhatsApp webhooks require — no port forwarding needed.

**Architecture**:
```
Internet → Cloudflare Tunnel → NUC Docker network
                                  ├── FastAPI (:8000)
                                  ├── n8n (:5678)
                                  └── AnyList sidecar (:3000)
```

**Fallback**: If home internet reliability is a problem, move FastAPI to Railway (~$5-7/mo). n8n stays on NUC (only makes outbound calls).

**Requirements**: Domain managed by Cloudflare DNS (~$10/year)

**Estimated cost**: $0/month (domain ~$10/year one-time)

## Decision 9: Scheduled Automations (n8n)

**Decision**: n8n on NUC with cron-triggered HTTP Request workflows

**Workflows**:
1. **Daily morning briefing** — 7am daily, `POST /api/v1/briefing/daily` → generates Erin's plan, sends to WhatsApp automatically
2. **Weekly calendar population** — Sunday evening, `POST /api/v1/calendar/populate-week` → writes time blocks to Erin's Google Calendar
3. **Grandma schedule prompt** — Monday 9am, sends WhatsApp asking which days grandma has Zoey

**Key**: Set `GENERIC_TIMEZONE=America/Los_Angeles` in n8n Docker config.

## Cost Summary (v2)

| Service                | Monthly Cost |
|------------------------|-------------|
| WhatsApp Cloud API     | $0          |
| Claude API (Haiku 4.5) | ~$0.10      |
| Notion                 | $0          |
| Google Calendar API    | $0          |
| YNAB API               | $0 (with sub) |
| Hosting (NUC)          | $0          |
| Cloudflare Tunnel      | $0          |
| AnyList                | ~$1/month   |
| Domain                 | ~$1/month   |
| **Total**              | **~$2/month** |

Well under the $30-50/month budget.
