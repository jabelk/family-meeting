# Contract: Railway Project Configuration

**Feature**: 020-railway-cloud-deploy
**Type**: Infrastructure configuration

## railway.toml (FastAPI Service)

```toml
[build]
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 60
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

## Railway Project Structure

```
Railway Project: "mombot" (or family-specific name)
├── Service: fastapi
│   ├── Source: GitHub repo (root directory: /)
│   ├── Dockerfile: /Dockerfile
│   ├── Volume: /app/data (persistent storage)
│   ├── Public domain: <auto>.up.railway.app (or custom domain)
│   └── Environment variables: (see .env.example)
│
├── Service: anylist-sidecar (OPTIONAL)
│   ├── Source: Same GitHub repo (root directory: /anylist-sidecar)
│   ├── Dockerfile: /anylist-sidecar/Dockerfile
│   ├── No volume needed
│   ├── No public domain (private networking only)
│   └── Environment variables: ANYLIST_EMAIL, ANYLIST_PASSWORD
│
└── No database services needed
```

## Environment Variables

### Required (all instances)

```
ANTHROPIC_API_KEY=<claude-api-key>
WHATSAPP_PHONE_NUMBER_ID=<from-meta-dashboard>
WHATSAPP_ACCESS_TOKEN=<from-meta-dashboard>
WHATSAPP_VERIFY_TOKEN=<chosen-by-user>
WHATSAPP_APP_SECRET=<from-meta-dashboard>
N8N_WEBHOOK_SECRET=<generated-shared-secret>
```

### Optional (per integration)

```
# Google Calendar
GOOGLE_TOKEN_JSON=<contents-of-token.json>
GOOGLE_CREDENTIALS_JSON=<contents-of-credentials.json>
GOOGLE_CALENDAR_JASON_ID=<calendar-email>
GOOGLE_CALENDAR_ERIN_ID=<calendar-email>
GOOGLE_CALENDAR_FAMILY_ID=<calendar-id>

# Notion
NOTION_TOKEN=<notion-integration-token>
NOTION_ACTION_ITEMS_DB=<database-id>
NOTION_MEAL_PLANS_DB=<database-id>
NOTION_MEETINGS_DB=<database-id>
NOTION_FAMILY_PROFILE_PAGE=<page-id>
NOTION_BACKLOG_DB=<database-id>
NOTION_GROCERY_HISTORY_DB=<database-id>

# YNAB
YNAB_ACCESS_TOKEN=<ynab-token>
YNAB_BUDGET_ID=<budget-id>

# AnyList (requires sidecar service)
ANYLIST_SIDECAR_URL=http://anylist-sidecar.railway.internal:3000
ANYLIST_EMAIL=<anylist-email>
ANYLIST_PASSWORD=<anylist-password>

# Outlook/Work Calendar
OUTLOOK_CALENDAR_ICS_URL=<ics-url>
```

### Railway-specific

```
RAILWAY_RUN_UID=0
SCHEDULER_ENABLED=true
PORT=8000
```

## WhatsApp Webhook URL

Each Railway instance gets a public URL. Configure in Meta's WhatsApp dashboard:
- Webhook URL: `https://<railway-domain>/webhook`
- Verify token: value of `WHATSAPP_VERIFY_TOKEN`
