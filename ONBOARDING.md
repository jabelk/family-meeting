# MomBot Onboarding Guide

Welcome! This guide walks you through setting up your own MomBot instance — a family assistant that lives in your WhatsApp group chat. It manages calendars, meal plans, budgets, grocery lists, and more.

**You'll need**: A computer with Claude Code installed. Claude Code will guide you through each step interactively.

---

## Quick Start (~30 minutes)

Want to get up and running fast? You only need **WhatsApp + Claude AI** for a working assistant. All other integrations (calendar, budget, meal planning, grocery lists) are optional add-ons you can enable later.

### What you get with minimal setup

- AI-powered family chat assistant in WhatsApp
- Natural language conversations with Claude
- Preference tracking and daily context
- Drive time lookups and routine management

### Minimal setup steps

1. **Clone the repo** and configure `config/family.yaml` with your family info
2. **Set up Railway** (Step 2 below) with only the required env vars
3. **Set up WhatsApp Business** (Step 3 below)
4. **Deploy** (Step 4 below)

### Validate your setup

Before deploying, run the validation script to catch configuration errors:

```bash
python scripts/validate_setup.py --env-file .env --config-file config/family.yaml
```

This checks:
- Family config completeness (names, timezone, partners)
- Required environment variables (API key format, WhatsApp credentials)
- Integration completeness (flags partially-configured integrations)

A minimal deployment needs only `ANTHROPIC_API_KEY` and `WHATSAPP_*` variables. The bot automatically adapts — tools and prompt sections for unconfigured integrations are excluded, so the bot never references features that aren't set up.

### Adding integrations later

Once your minimal bot is working, add integrations one at a time (Steps 5-8). Re-run the validation script after each to confirm. The bot picks up new integrations on restart — no code changes needed.

---

## Full Setup (~1-2 hours)

Follow all steps below for the complete experience with calendar, Notion, budget, and grocery list integrations.

---

## Step 1: Create Your GitHub Repository

1. Go to the MomBot template repository on GitHub
2. Click **"Use this template"** → **"Create a new repository"**
3. Name it something like `family-assistant` or `mombot`
4. Make it **Private** (it will contain your configuration)
5. Clone it to your computer:
   ```bash
   git clone https://github.com/YOUR_USERNAME/family-assistant.git
   cd family-assistant
   ```

---

## Step 2: Set Up Railway

1. Go to [railway.app](https://railway.app) and create an account (Hobby plan, ~$5/month)
2. Install the Railway CLI:
   ```bash
   npm install -g @railway/cli
   railway login
   ```
3. Create a new Railway project:
   ```bash
   railway init --name mombot
   railway link
   ```
4. Add a persistent volume (in Railway dashboard):
   - Go to your service → **Settings** → **Volumes**
   - Click **"Add Volume"**
   - Mount path: `/app/data`
5. Set the required environment variables:
   ```bash
   railway variables set ANTHROPIC_API_KEY=sk-ant-...
   railway variables set N8N_WEBHOOK_SECRET=$(openssl rand -hex 16)
   railway variables set PORT=8000
   railway variables set RAILWAY_RUN_UID=0
   ```

---

## Step 3: Set Up WhatsApp Business

Each family needs their own WhatsApp Business app. This ensures your messages, phone number, and data are completely yours.

1. Go to [developers.facebook.com](https://developers.facebook.com) and create a Meta developer account
2. Create a new app → Select **"Business"** type
3. Add the **WhatsApp** product to your app
4. In WhatsApp → **Getting Started**:
   - Note your **Phone Number ID**
   - Note your **WhatsApp Business Account ID**
5. Generate a permanent access token:
   - Go to **Business Settings** → **System Users**
   - Create a system user with admin access
   - Generate a token with `whatsapp_business_messaging` permission
6. Set the WhatsApp environment variables:
   ```bash
   railway variables set WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
   railway variables set WHATSAPP_ACCESS_TOKEN=your-permanent-token
   railway variables set WHATSAPP_VERIFY_TOKEN=$(openssl rand -hex 8)
   railway variables set WHATSAPP_APP_SECRET=your-app-secret
   ```
7. Set your family's phone numbers (without `+` prefix):
   ```bash
   railway variables set JASON_PHONE=15551234567
   railway variables set ERIN_PHONE=15559876543
   ```

---

## Step 4: Deploy

```bash
railway up
```

Once deployed, get your public URL:
```bash
railway domain
```

Then configure the WhatsApp webhook:
1. In Meta developer dashboard → WhatsApp → **Configuration**
2. Set Webhook URL: `https://YOUR-RAILWAY-URL/webhook`
3. Set Verify Token: (the value you set for `WHATSAPP_VERIFY_TOKEN`)
4. Subscribe to: `messages`

**Test it**: Send a WhatsApp message to your bot. You should get a response!

---

## Step 5 (Optional): Google Calendar

Adds calendar awareness to daily briefings and scheduling.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g., "Family Assistant")
3. Enable the **Google Calendar API** and **Gmail API**
4. Create OAuth credentials:
   - Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth Client ID**
   - Application type: **Desktop app**
   - Download the `credentials.json` file
5. **Publish your OAuth app** (important — prevents token expiry):
   - Go to **OAuth consent screen**
   - Add your family Gmail addresses as test users first
   - Click **"Publish App"** (no Google verification needed for <100 users)
6. Generate your token locally:
   ```bash
   python scripts/setup_calendar.py
   ```
   This opens a browser — authorize with your Gmail account.
7. Upload credentials to Railway:
   ```bash
   railway variables set GOOGLE_TOKEN_JSON="$(cat token.json)"
   railway variables set GOOGLE_CREDENTIALS_JSON="$(cat credentials.json)"
   railway variables set GOOGLE_CALENDAR_JASON_ID=your-email@gmail.com
   railway variables set GOOGLE_CALENDAR_ERIN_ID=partner-email@gmail.com
   railway variables set GOOGLE_CALENDAR_FAMILY_ID=your-shared-calendar-id@group.calendar.google.com
   ```

---

## Step 6 (Optional): Notion

Adds task management, meal planning, meeting agendas, and grocery tracking.

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) and create an integration
2. Set the required database IDs (see Notion setup docs in the repo for database templates):
   ```bash
   railway variables set NOTION_TOKEN=ntn_...
   railway variables set NOTION_ACTION_ITEMS_DB=...
   railway variables set NOTION_MEAL_PLANS_DB=...
   railway variables set NOTION_MEETINGS_DB=...
   railway variables set NOTION_FAMILY_PROFILE_PAGE=...
   ```

---

## Step 7 (Optional): YNAB Budget

Adds budget tracking, spending alerts, and financial insights.

1. Go to [app.ynab.com/settings/developer](https://app.ynab.com/settings/developer) and create a personal access token
2. Set the variables:
   ```bash
   railway variables set YNAB_ACCESS_TOKEN=your-token
   railway variables set YNAB_BUDGET_ID=last-used
   ```

---

## Step 8 (Optional): AnyList Grocery Integration

Adds grocery list management via WhatsApp. Requires a separate Railway service.

1. In Railway dashboard, add a **new service** to your project
2. Source: Same GitHub repo, root directory: `/anylist-sidecar`
3. **No public domain** needed (uses private networking)
4. Set environment variables on the sidecar service:
   ```
   ANYLIST_EMAIL=your-anylist-email
   ANYLIST_PASSWORD=your-anylist-password
   ```
5. On your main FastAPI service, set:
   ```bash
   railway variables set ANYLIST_SIDECAR_URL=http://anylist-sidecar.railway.internal:3000
   ```

---

## Customizing Your Schedule

The bot runs automated jobs (daily briefings, budget scans, etc.) on a configurable schedule. Edit `data/schedules.json` on the volume to customize timing or disable jobs you don't need.

Each job has an `enabled` flag — set to `false` to disable it. For example, if you don't use YNAB, disable the budget jobs.

---

## Updating From Upstream

When improvements are made to the original MomBot template:

```bash
# One-time setup: add the upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/family-meeting.git

# Pull updates
git fetch upstream
git merge upstream/main
```

Review the changes before merging. Your environment variables and volume data are safe — they live in Railway, not in the code.

> Automated update notifications via WhatsApp are planned for a future release (see GitHub issue #30).

---

## Troubleshooting

- **Bot not responding**: Check Railway logs (`railway logs`). Verify WhatsApp webhook URL is correct.
- **Calendar not working**: Re-run `setup_calendar.py` locally and re-upload `GOOGLE_TOKEN_JSON`.
- **Scheduled jobs not firing**: Check logs for "Scheduler started: N jobs loaded". Ensure `SCHEDULER_ENABLED` is not set to `false`.
- **Volume data lost**: Verify the volume is mounted at `/app/data` in Railway dashboard.

---

## Cost

- **Railway**: ~$5/month (Hobby plan)
- **Anthropic API**: ~$5-15/month depending on usage (Claude Haiku for most operations)
- **All other APIs**: Free tier (Google Calendar, Notion, YNAB, Meta WhatsApp)
