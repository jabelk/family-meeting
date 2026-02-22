# Research: AI-Powered Weekly Family Meeting Assistant

**Branch**: `001-ai-meeting-assistant` | **Date**: 2026-02-21

## Decision 1: WhatsApp Integration Approach

**Decision**: Meta WhatsApp Cloud API (direct, no third-party middleware)

**Rationale**: For a low-volume family bot (~20-50 messages/week), the direct
Meta Cloud API is simpler and cheaper than Twilio or other providers. All
user-initiated (service) conversations are free since November 2024. Proactive
template messages cost ~$0.004-0.015 each (negligible at this volume).

**Alternatives considered**:
- Twilio WhatsApp: Adds middleman markup (~$0.005/msg extra) and another
  account to manage. Sandbox is easier for prototyping but not sustainable.
- Telegram Bot API: Free and excellent API, but both partners already use
  WhatsApp — no new app install needed.
- Custom mobile web app: Most control but violates constitution principle III
  (Simplicity) — requires building a frontend.

**Key details**:
- Sandbox available for dev (5 test recipients, no business verification)
- Production requires Meta Business verification (biggest friction point)
- 24-hour reply window for free-form messages; proactive messages need
  pre-approved templates
- Dedicated phone number required (cannot use personal WhatsApp number)
- Formatting: bold (`*text*`), italic (`_text_`), lists, monospace supported
- 1,600 character limit per message
- Interactive messages supported (buttons, list menus)

**Estimated cost**: $0/month (user-initiated conversations are free)

## Decision 2: AI Orchestration

**Decision**: Anthropic Claude API with Python SDK tool runner

**Rationale**: The Claude Messages API with `@beta_tool` decorator and tool
runner provides a complete agentic loop out of the box. Define tools as Python
functions → Claude decides which to call → SDK executes them → Claude formats
response. No framework needed (LangChain, CrewAI add unnecessary complexity
for this use case).

**Alternatives considered**:
- OpenAI Assistants API: More complex (thread management, run polling, file
  storage). Heavier abstraction with more vendor lock-in.
- LangChain/CrewAI: Unnecessary abstraction for a single-agent tool-calling
  pattern. The Claude SDK already handles the agentic loop natively.
- Anthropic Agent SDK: Designed for Claude Code-like agents (file editing,
  command execution). Overkill for an API-calling assistant.
- MCP servers: YNAB MCP server exists, Google Calendar MCP servers exist.
  Promising but adds architectural complexity. Better as a Phase 2
  optimization.

**Model**: Claude Haiku 4.5 — 90% of Sonnet's performance on tool use, 3x
cheaper, 3-4x faster. Can upgrade to Sonnet by changing one string.

**Estimated cost**: ~$0.01-0.02 per 10-message session, ~$0.05-0.10/month

## Decision 3: Data Persistence

**Decision**: Notion API (free plan)

**Rationale**: Uniquely satisfies all four constraints — good programmatic API,
zero cost, family-friendly browsable UI (web + mobile app), and editable by
family members directly. Action items appear as a kanban board, meal plans as
structured pages, meetings as a timeline. No frontend development needed.

**Alternatives considered**:
- Google Sheets: Free, no new accounts, but clunky API (spreadsheet not
  database), no rich views (kanban, calendar). More boilerplate code.
- Airtable: Excellent API and UI but 1,000-record free limit would cap out
  in ~12 months. Paid plan ($20/user) exceeds budget for family use.
- Supabase/Firebase: Best API and query power but no family-facing UI without
  building a web app. Defeats the "minimal custom code" goal.
- JSON files: No UI, no concurrent access. Not viable.

**Key details**:
- Free plan: unlimited blocks, up to 10 guests
- API rate limit: 3 requests/second (fine for this volume)
- No webhooks (must poll for changes — acceptable at weekly cadence)
- Both partners install Notion app or use web on phone

**Estimated cost**: $0/month

## Decision 4: Google Calendar API

**Decision**: Google Calendar API v3 with Python client library

**Key details**:
- OAuth2 authentication (Desktop app flow)
- `calendar.readonly` scope sufficient
- Free: 1M queries/day
- Python library: `google-api-python-client` + `google-auth-oauthlib`
- Gotcha: Testing-mode tokens expire every 7 days; consider service account
  or submitting for verification to avoid re-auth

**Endpoint needed**: `GET /calendars/{calendarId}/events` with `timeMin`,
`timeMax`, `singleEvents=true`, `orderBy=startTime`

## Decision 5: YNAB API

**Decision**: YNAB API v1 with Personal Access Token

**Key details**:
- Static Personal Access Token (no expiry, no refresh needed)
- Free with YNAB subscription ($14.99/month — already paying)
- Rate limit: 200 requests/hour (irrelevant at this volume)
- Python: `ynab` package or plain `requests`
- Gotcha: All amounts in milliunits (divide by 1000)
- Key endpoint: `GET /budgets/{id}/months/{month}` returns all categories
  with budgeted, activity (spending), balance, and goal data

## Decision 6: Hosting

**Decision**: Cloud function or lightweight VPS

**Rationale**: The backend is a single webhook endpoint + AI tool runner.
A cloud function (AWS Lambda, Google Cloud Functions, or Railway) handles
this with zero infrastructure management. A $5/month VPS (Railway, Render,
Fly.io) works if persistent state or long-running connections are needed.

**Estimated cost**: $0-5/month

## Cost Summary

| Service                | Monthly Cost |
|------------------------|-------------|
| WhatsApp Cloud API     | $0          |
| Claude API (Haiku 4.5) | ~$0.10      |
| Notion                 | $0          |
| Google Calendar API    | $0          |
| YNAB API               | $0 (with subscription) |
| Hosting                | $0-5        |
| **Total**              | **~$0-6/month** |

Well under the $30-50/month budget, leaving room for upgrades (Sonnet model,
paid Notion plan, or additional services) as needed.
