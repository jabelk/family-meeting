# Quickstart: Railway Cloud Deployment

**Feature**: 020-railway-cloud-deploy
**Date**: 2026-03-08

## Prerequisites

- GitHub account with the MomBot repo
- Railway account (Hobby plan, $5/month)
- Anthropic API key
- WhatsApp Business account with Cloud API credentials
- (Optional) Google Cloud project with Calendar API enabled
- (Optional) Notion integration token
- (Optional) YNAB access token

---

## Scenario 1: Deploy FastAPI to Railway (US1 MVP)

**Goal**: Get the app running on Railway with WhatsApp responding.

```bash
# 1. Install Railway CLI
npm install -g @railway/cli
railway login

# 2. Create a new Railway project
railway init --name mombot

# 3. Link to the GitHub repo
railway link

# 4. Add a volume for persistent data
# (Do this in Railway dashboard: Service → Settings → Volumes → Mount at /app/data)

# 5. Set required environment variables (in Railway dashboard or CLI)
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set WHATSAPP_PHONE_NUMBER_ID=...
railway variables set WHATSAPP_ACCESS_TOKEN=...
railway variables set WHATSAPP_VERIFY_TOKEN=...
railway variables set WHATSAPP_APP_SECRET=...
railway variables set N8N_WEBHOOK_SECRET=$(openssl rand -hex 16)
railway variables set RAILWAY_RUN_UID=0
railway variables set PORT=8000

# 6. Deploy
railway up

# 7. Get the public URL
railway domain
# Output: mombot-production.up.railway.app
```

**Verify**:
```bash
curl https://mombot-production.up.railway.app/health
# Expected: {"status": "ok"}
```

Then update Meta WhatsApp dashboard webhook URL to `https://mombot-production.up.railway.app/webhook`.

---

## Scenario 2: Verify Data Persistence (US2)

**Goal**: Confirm data survives a redeploy.

```bash
# 1. Send a WhatsApp message to create conversation data
# (Send "Hello" via WhatsApp)

# 2. Push a work calendar event
curl -X POST https://mombot-production.up.railway.app/api/v1/calendar/work-events \
  -H "Content-Type: application/json" \
  -H "X-N8N-Auth: $N8N_SECRET" \
  -d '{"events":[{"title":"Test meeting","start":"2026-03-09T09:00:00","end":"2026-03-09T09:30:00"}]}'

# 3. Trigger a redeploy
git commit --allow-empty -m "test redeploy" && git push

# 4. Wait for deploy to complete, then verify
curl -X POST https://mombot-production.up.railway.app/api/v1/calendar/work-events \
  -H "Content-Type: application/json" \
  -H "X-N8N-Auth: $N8N_SECRET" \
  -d '{"events":[]}'
# Work calendar file should still exist with previous data
```

---

## Scenario 3: Verify Scheduled Jobs (US3)

**Goal**: Confirm in-app scheduler fires jobs.

```bash
# 1. Check Railway logs for scheduler startup
railway logs --tail 20
# Expected: "Scheduler started: 14 jobs loaded (timezone: America/Los_Angeles)"

# 2. Wait for the next scheduled job (or set a test job for 1 minute from now)
# Check logs for:
# "Running scheduled job: daily_briefing"
# "Scheduled job complete: daily_briefing (3.2s)"
```

---

## Scenario 4: Google Calendar via Env Var (US4)

**Goal**: Set up Google Calendar without browser-based OAuth on the server.

```bash
# 1. Locally, run the existing setup script
python scripts/setup_calendar.py
# (Opens browser, you authorize, generates token.json)

# 2. Copy token.json contents to Railway env var
railway variables set GOOGLE_TOKEN_JSON="$(cat token.json)"
railway variables set GOOGLE_CREDENTIALS_JSON="$(cat credentials.json)"

# 3. Set calendar IDs
railway variables set GOOGLE_CALENDAR_JASON_ID=jbelk122@gmail.com
railway variables set GOOGLE_CALENDAR_ERIN_ID=erin.tahoe@gmail.com
railway variables set GOOGLE_CALENDAR_FAMILY_ID=a9feuvcs29qlooh6mlippbsgek@group.calendar.google.com

# 4. Redeploy to pick up new vars
railway up

# 5. Verify
# Send WhatsApp message: "What's on my calendar today?"
# Should show Google Calendar events
```

---

## Scenario 5: AnyList Sidecar (US7)

**Goal**: Deploy the optional AnyList sidecar.

```bash
# 1. In Railway dashboard, add a new service to the same project
# Source: Same GitHub repo
# Root directory: /anylist-sidecar
# No public domain needed

# 2. Set sidecar env vars
# ANYLIST_EMAIL=...
# ANYLIST_PASSWORD=...

# 3. Set the sidecar URL on the fastapi service
railway variables set ANYLIST_SIDECAR_URL=http://anylist-sidecar.railway.internal:3000

# 4. Redeploy fastapi
railway up
```

---

## Scenario 6: A/B Testing (NUC vs Railway)

**Goal**: Run both instances and compare.

```bash
# Both instances point to the same external services (Notion, Google, YNAB)
# Only ONE instance should have the WhatsApp webhook at a time

# Switch to Railway:
# 1. Update Meta WhatsApp dashboard → Webhook URL → Railway URL
# 2. Send a test message, verify response

# Switch back to NUC:
# 1. Update Meta WhatsApp dashboard → Webhook URL → NUC URL (via Cloudflare Tunnel)
# 2. Send a test message, verify response

# Compare:
# - Response time (check logs on both)
# - Uptime (Railway dashboard vs NUC uptime)
# - Cost (Railway billing vs NUC electricity)
```

---

## Scenario 7: Template Repo Onboarding (US5)

**Goal**: New user creates their own instance.

```bash
# 1. User clicks "Use this template" on GitHub
# 2. User opens their new repo in Claude Code
# 3. Claude Code reads ONBOARDING.md and walks them through:
#    a. Create Railway account and project
#    b. Set up WhatsApp Business account with Meta
#    c. Get Anthropic API key
#    d. Set required env vars in Railway
#    e. Deploy
#    f. Configure WhatsApp webhook URL
#    g. Send first message
# 4. (Optional) Set up Google Calendar, Notion, YNAB integrations
```
