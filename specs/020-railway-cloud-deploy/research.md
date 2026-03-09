# Research: Railway Cloud Deployment

**Feature**: 020-railway-cloud-deploy
**Date**: 2026-03-08

## Decision 1: Persistent Storage

**Decision**: Railway Volumes mounted at `/app/data`

**Rationale**: Zero code changes. The app already checks `Path("/app/data")` and uses atomic writes (`.tmp` → rename). A Railway Volume at `/app/data` preserves all JSON files across redeploys. Cost is ~$0/month for <1MB of data. The `RAILWAY_RUN_UID=0` env var may be needed if the container runs as non-root.

**Alternatives considered**:
- Railway Postgres (~$0.55/month): Would require rewriting all 10+ JSON read/write patterns to SQL. Massive overkill for <1MB of data. Only worthwhile if scaling to multi-replica, which isn't planned.
- Cloudflare R2/S3: Adds latency on every read/write, requires new SDK dependency. Overkill for simple key-value JSON files.

**Key constraints**:
- One volume per service (sufficient — only fastapi needs it)
- Cannot use replicas with a volume (not needed — single instance per family)
- Brief downtime on redeploy (seconds, acceptable for a family assistant)

---

## Decision 2: Scheduled Jobs (n8n Replacement)

**Decision**: APScheduler `AsyncIOScheduler` embedded in the FastAPI process

**Rationale**: Runs in the same asyncio event loop as FastAPI. Supports any interval (including 15-minute nudge scans), full timezone support via `zoneinfo`, and calls handler functions directly (no HTTP round-trip, no auth header needed). No external service, no separate container. Schedules are defined in a JSON config file (`data/schedules.json`) so template users can customize without editing Python code.

**Alternatives considered**:
- Railway native cron: UTC-only (no timezone support), one schedule per service (would need 13 services), architectural mismatch (expects process to exit). Not viable.
- cron-job.org (external): Free, full-featured, web UI. Good fallback option but adds external dependency and requires auth header management. Could be offered as an alternative in onboarding guide.
- GitHub Actions scheduled workflows: 5-minute minimum resolution, not ideal for 15-minute nudge scans. Free but imprecise timing.

**Key constraints**:
- Single worker only (APScheduler duplicates jobs if multiple workers). Current `Procfile` runs one uvicorn worker — document this as a hard constraint.
- No built-in retry on missed jobs. If the container is down at trigger time, the job is skipped.
- Schedules loaded from config file, not hardcoded, to support per-family customization.

---

## Decision 3: Multi-Service Deployment (AnyList Sidecar)

**Decision**: Same GitHub repo, two Railway services in one project, private networking

**Rationale**: Railway supports monorepo deployments natively. The fastapi service uses root `/Dockerfile`, the anylist-sidecar uses `/anylist-sidecar/Dockerfile`. Services communicate via Railway private networking: `http://anylist-sidecar.railway.internal:3000`. The existing `ANYLIST_SIDECAR_URL` env var in `config.py` already makes this configurable — just set the Railway value.

**Alternatives considered**:
- Separate repos: Unnecessary complexity. Railway handles monorepos well.
- Merge sidecar into FastAPI: Would require porting AnyList npm package to Python. No Python equivalent exists.
- Skip AnyList entirely: Viable for new families (FR-012 makes it optional), but Jason's family uses it.

**Key facts**:
- Private networking uses WireGuard mesh — encrypted, zero config
- DNS pattern: `<service-name>.railway.internal:<port>`
- Use `http://` not `https://` (WireGuard handles encryption)
- No per-service charge — both services share the project's usage pool
- Sidecar can be "removed" (stopped) if not needed, costs nothing when not running

---

## Decision 4: Google OAuth Token Management

**Decision**: Publish OAuth app (removes 7-day testing expiry) + store token as `GOOGLE_TOKEN_JSON` env var + auto-refresh in app

**Rationale**: Publishing a Google OAuth app for <100 users requires no verification review — just click "In production" in Cloud Console. Refresh tokens then last indefinitely (as long as used within 6 months, which daily briefings ensure). The token JSON string is stored as a Railway env var and loaded via `Credentials.from_authorized_user_info()` (confirmed: this is exactly what `from_authorized_user_file()` calls internally). On Railway with a volume, refreshed tokens are also written back to `token.json` on the volume as a backup.

**Alternatives considered**:
- Google Service Account: Requires Google Workspace with domain-wide delegation. Personal Gmail accounts (which both Jason and the pastor use) can't use service accounts for calendar access.
- Keep testing mode + manual refresh: Breaks self-service requirement (US4). Pastor can't SSH to refresh tokens.
- Railway API to update env var on refresh: Overkill — access tokens refresh hourly but the refresh token itself rarely changes. Volume-backed `token.json` handles persistence.

**Token lifecycle**:
- Access token: expires every 1 hour, auto-refreshed by `creds.refresh(Request())`
- Refresh token: never expires for published apps (with regular use)
- `from_authorized_user_info()` with a stale access token triggers immediate refresh on first use
- `credentials.json` (OAuth client secret) is also stored as `GOOGLE_CREDENTIALS_JSON` env var

**Onboarding flow for new families**:
1. Create Google Cloud project
2. Enable Calendar API
3. Create OAuth consent screen, publish it
4. Create OAuth client (Desktop app type)
5. Download `credentials.json`
6. Run `setup_calendar.py` locally — opens browser, authorizes, generates `token.json`
7. Copy contents of both files into Railway env vars

---

## Decision 5: Template Repo Pattern

**Decision**: GitHub "Use this template" with upstream remote for manual updates + WhatsApp notification

**Rationale**: GitHub template repos create a clean copy (no fork relationship, no commit history). Each family gets a completely independent repo. To pull upstream updates, the onboarding guide adds the template repo as a git remote. Updates are notified via WhatsApp (FR-014) and applied via a single WhatsApp command that triggers a git merge + Railway redeploy. Data is backed up before update (FR-015) and rollback is available (FR-016).

**Alternatives considered**:
- GitHub fork: Maintains relationship but exposes commit history, and PRs/issues from the template show up in the fork. Too noisy.
- Git submodule: Complex for non-technical users. Claude Code can't easily guide submodule workflows.
- npm/pip package: Would require separating the "framework" from the "instance config." Over-engineered for <10 users.

**Update mechanism**:
1. Template repo pushes a new release/tag
2. A GitHub Action in the template repo calls each registered instance's webhook (or the instance polls on startup)
3. Instance sends WhatsApp notification: "Update available: [description]. Reply 'update' to apply or ignore."
4. On "update": backup data volume → git pull upstream → Railway auto-redeploys
5. On "undo update": restore data backup → git revert → Railway auto-redeploys

---

## Decision 6: Credential Security

**Decision**: All secrets in Railway env vars (encrypted at rest), credential scrubbing in logs, existing webhook signature verification

**Rationale**: Railway encrypts env vars at rest and in transit. The app already validates WhatsApp webhook signatures (`_verify_webhook_signature`) and n8n auth headers (`verify_n8n_auth`). Each family instance is a completely separate Railway project with its own env vars — no shared state. Log scrubbing will be added to prevent accidental credential leakage in exception tracebacks.

**Specific measures**:
- `WHATSAPP_APP_SECRET`, `N8N_WEBHOOK_SECRET`: Already validated on every request
- `ANTHROPIC_API_KEY`, `NOTION_TOKEN`, `YNAB_ACCESS_TOKEN`: Used only in API calls, never logged
- `GOOGLE_TOKEN_JSON`, `GOOGLE_CREDENTIALS_JSON`: New env vars, loaded once at startup
- Python logging: Add a filter to redact any string matching known env var patterns
- No `.env` file in the container — Railway injects vars directly into the process environment

---

## Decision 7: Railway Pricing & Tier

**Decision**: Railway Hobby plan ($5/month) per family instance

**Rationale**: The Hobby plan includes $5 of usage credit, which covers a lightweight FastAPI app + optional Node.js sidecar with very low traffic (a family sends maybe 20-50 messages/day). Volume storage for <1MB is essentially free. The plan includes 1 volume (sufficient), 500 hours of execution (24/7 = 720 hours, but Railway measures actual CPU time, not wall time), and 100GB egress.

**Cost breakdown estimate**:
- FastAPI service: ~$2-3/month (low CPU, ~200MB RAM)
- AnyList sidecar (optional): ~$0.50/month (idle most of the time)
- Volume storage: ~$0.00/month (<1MB)
- Total: ~$3-4/month, well within $5 credit
