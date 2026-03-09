# Client Onboarding Guide

End-to-end guide for deploying a new family assistant instance for a client. This is operator documentation -- it covers everything from initial client intake through first message verification.

**Deployment model**: Single-tenant. Each client gets their own Railway deployment, their own WhatsApp number, and their own set of credentials. Client data is never shared across instances.

**Minimum viable deployment**: WhatsApp + Anthropic API key. All other integrations (Notion, Google Calendar, YNAB, AnyList, Outlook) are optional and can be added later.

**Total time**: 2-4 hours for full setup (with all integrations). 30-60 minutes for minimum viable.

---

## Step 1: Client Intake

*Estimated time: 15-30 minutes (phone call or form)*

Collect the following information from the new family before starting any technical setup.

### Required Information

| Field | Example | Notes |
|-------|---------|-------|
| Family name | "The Garcia Family" | Used in bot greeting and Notion workspace name |
| Bot name | "Home Helper" | Display name the bot uses when introducing itself |
| Partner 1 name | "Maria" | First name only |
| Partner 1 phone | +1 555 123 4567 | Must have WhatsApp installed |
| Partner 2 name | "Carlos" | First name only (leave blank if single-parent household) |
| Partner 2 phone | +1 555 234 5678 | Must have WhatsApp installed |
| Timezone | America/Chicago | IANA format -- see [timezone list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) |
| Location | "Austin, TX" | City and state for weather context |

### Children (optional)

For each child:
| Field | Example |
|-------|---------|
| Name | "Sofia" |
| Age | 7 |
| Details | "2nd grade at Barton Hills Elementary, soccer on Tuesdays" |

### Caregivers (optional)

Non-parent caregivers (grandparents, nannies, babysitters):
| Field | Example |
|-------|---------|
| Name | "Abuela Rosa" |
| Role | "grandma" |
| Keywords | ["abuela", "rosa", "grandma"] |

### Preferences (optional)

| Field | Example | Default |
|-------|---------|---------|
| Grocery store | "H-E-B" | None (AnyList integration not configured) |
| Recipe source | "Budget Bytes" | None (no external recipe integration) |
| Dietary restrictions | ["nut-free", "vegetarian"] | None |
| Work calendars | Partner 1 has Outlook work calendar | None |

### Integration Preferences

Ask the client which integrations they want. Explain that all are optional and can be added later:

- [ ] **Notion** -- Task management, meal planning, meeting agendas, grocery history
- [ ] **Google Calendar** -- Calendar awareness, scheduling, conflict detection
- [ ] **YNAB** -- Budget tracking and spending insights
- [ ] **AnyList** -- Grocery list management and ordering
- [ ] **Outlook** -- Work calendar integration (ICS feed)

> **Privacy note:** Per-incident consent is required before an operator views any client data (conversations, calendar events, financial data). Document this in the client agreement. The system logs conversation metadata (timestamps, message counts) but not message content by default.

---

## Step 2: Create Family Configuration

*Estimated time: 10 minutes*

Create the family configuration file from the example template.

1. Clone or fork the repository for this client:
   ```bash
   git clone https://github.com/YOUR_ORG/family-meeting.git garcia-family-assistant
   cd garcia-family-assistant
   ```

2. Copy the example configuration:
   ```bash
   cp config/family.yaml.example config/family.yaml
   ```

3. Edit `config/family.yaml` with the client's details:

   ```yaml
   bot:
     name: "Home Helper"
     welcome_message: ""  # Leave empty for auto-generated, or customize

   family:
     name: "The Garcia Family"
     timezone: "America/Chicago"
     location: "Austin, TX"

     partners:
       - name: "Maria"
         role: "partner"
         work: "works from home at Dell"
         has_work_calendar: true
       - name: "Carlos"
         role: "partner"
         work: "teacher at Barton Hills Elementary"
         has_work_calendar: false

     children:
       - name: "Sofia"
         age: 7
         details: "2nd grade at Barton Hills Elementary, soccer on Tuesdays"
       - name: "Mateo"
         age: 4
         details: "pre-K at Little Acorns, M/W/F"

     caregivers:
       - name: "Abuela Rosa"
         role: "grandma"
         keywords: ["abuela", "rosa", "grandma"]

   preferences:
     grocery_store: "H-E-B"
     recipe_source: ""
     dietary_restrictions: ["nut-free"]

   calendar:
     event_mappings:
       "Soccer": "Sofia"
       "BSF": "Carlos"

   childcare:
     keywords: []          # Auto-generated from children + caregiver names if empty
     caregiver_mappings: {} # Auto-generated from caregivers if empty
   ```

> **Note:** The `childcare.keywords` and `childcare.caregiver_mappings` fields auto-populate from the `children` and `caregivers` sections if left empty. Only fill them in if you need to override the defaults.

---

## Step 3: Create Environment File

*Estimated time: 10 minutes*

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Fill in the required variables:
   ```bash
   # Required for all deployments
   ANTHROPIC_API_KEY=sk-ant-...
   N8N_WEBHOOK_SECRET=$(openssl rand -hex 16)

   # WhatsApp (see Step 5 for provisioning)
   WHATSAPP_PHONE_NUMBER_ID=pending
   WHATSAPP_ACCESS_TOKEN=pending
   WHATSAPP_VERIFY_TOKEN=$(openssl rand -hex 8)
   WHATSAPP_APP_SECRET=pending

   # Family member phone numbers (without + prefix)
   PARTNER1_PHONE=15551234567
   PARTNER2_PHONE=15552345678
   ```

3. Leave all `OPTIONAL` sections commented out for now. They will be configured in Steps 6a-6e if the client wants those integrations.

> **Warning:** Never commit the `.env` file to version control. The `.gitignore` already excludes it. If you need to transfer credentials to a collaborator, use a secure channel (encrypted email, password manager share, etc.).

---

## Step 4: Deploy to Railway

*Estimated time: 15-20 minutes*

Each client gets a separate Railway project.

### 4a. Create the Railway project

```bash
# Install Railway CLI if not already installed
npm install -g @railway/cli

# Log in (opens browser)
railway login

# Create a new project for this client
railway init --name garcia-family-assistant
railway link
```

### 4b. Add a persistent volume

In the Railway dashboard:

1. Navigate to the service
2. Go to **Settings** > **Volumes**
3. Click **"Add Volume"**
4. Set mount path: `/app/data`
5. Click **"Add"**

The volume stores conversation history, schedules, preferences, and other runtime data. It persists across deployments.

### 4c. Set environment variables

```bash
# Required
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set N8N_WEBHOOK_SECRET=$(openssl rand -hex 16)
railway variables set PORT=8000
railway variables set RAILWAY_RUN_UID=0

# WhatsApp (fill in after Step 5)
railway variables set WHATSAPP_PHONE_NUMBER_ID=pending
railway variables set WHATSAPP_ACCESS_TOKEN=pending
railway variables set WHATSAPP_VERIFY_TOKEN=$(openssl rand -hex 8)
railway variables set WHATSAPP_APP_SECRET=pending

# Family phone numbers
railway variables set PARTNER1_PHONE=15551234567
railway variables set PARTNER2_PHONE=15552345678
```

### 4d. Deploy

```bash
railway up
```

### 4e. Get the public URL

```bash
railway domain
```

This returns the public URL (e.g., `garcia-assistant.up.railway.app`). You will need this for the WhatsApp webhook configuration in Step 5.

> **Note:** Railway assigns a random subdomain by default. You can set a custom domain in the Railway dashboard under **Settings** > **Networking** > **Public Networking** if the client prefers a branded URL.

---

## Step 5: Provision WhatsApp Number

*Estimated time: 30-60 minutes (plus business verification wait time)*

Follow the detailed guide at [docs/WHATSAPP_SETUP.md](./WHATSAPP_SETUP.md).

After completing the WhatsApp setup, update the environment variables:

```bash
railway variables set WHATSAPP_PHONE_NUMBER_ID=actual-phone-number-id
railway variables set WHATSAPP_ACCESS_TOKEN=actual-permanent-token
railway variables set WHATSAPP_APP_SECRET=actual-app-secret
```

Configure the webhook URL in the Meta developer dashboard:
- **Callback URL**: `https://{railway-domain}/webhook`
- **Verify Token**: The value you set for `WHATSAPP_VERIFY_TOKEN`
- **Subscribed fields**: `messages`, `message_templates`

> **Important:** The service must be deployed and running (Step 4d) before the webhook can be verified. Meta sends a verification request to your callback URL during setup.

---

## Step 6: Optional Integration Setup

Each integration below is independent. Configure only the ones the client requested in Step 1. They can be added at any time after initial deployment.

### 6a. Notion (Task Management, Meal Planning)

*Estimated time: 30-45 minutes*

Follow the detailed guide at [docs/notion-setup.md](./notion-setup.md), adapting it for the client's family.

Summary:
1. Create a Notion workspace (client's account, or operator-managed)
2. Create an integration at [notion.so/my-integrations](https://www.notion.so/my-integrations)
3. Create the required databases (Action Items, Meal Plans, Meetings, Backlog, Grocery History)
4. Create the Family Profile page with the client's family details
5. Connect the integration to each database and page
6. Copy database IDs into environment variables

```bash
railway variables set NOTION_TOKEN=ntn_...
railway variables set NOTION_ACTION_ITEMS_DB=...
railway variables set NOTION_MEAL_PLANS_DB=...
railway variables set NOTION_MEETINGS_DB=...
railway variables set NOTION_FAMILY_PROFILE_PAGE=...
railway variables set NOTION_BACKLOG_DB=...
railway variables set NOTION_GROCERY_HISTORY_DB=...
```

Optional additional databases (for recipe and chore features):
```bash
railway variables set NOTION_RECIPES_DB=...
railway variables set NOTION_COOKBOOKS_DB=...
railway variables set NOTION_NUDGE_QUEUE_DB=...
railway variables set NOTION_CHORES_DB=...
```

> **Note:** Notion's free plan supports unlimited blocks with a single workspace member. Only the primary account holder should be a workspace member. Other family members should be invited as guests with "Full access" on shared pages.

### 6b. Google Calendar (Scheduling, Daily Briefings)

*Estimated time: 20-30 minutes*

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g., "Garcia Family Assistant")
3. Enable the **Google Calendar API** and **Gmail API**
4. Create OAuth credentials:
   - **APIs & Services** > **Credentials** > **Create Credentials** > **OAuth Client ID**
   - Application type: **Desktop app**
   - Download `credentials.json`
5. Publish the OAuth app (prevents token expiry every 7 days):
   - Go to **OAuth consent screen**
   - Add family Gmail addresses as test users
   - Click **"Publish App"** (no Google review needed for <100 users)
6. Run the setup script locally:
   ```bash
   python scripts/setup_calendar.py
   ```
   This opens a browser for OAuth authorization. Authorize with the primary family Gmail account.
7. Upload credentials to Railway:
   ```bash
   railway variables set GOOGLE_TOKEN_JSON="$(cat token.json)"
   railway variables set GOOGLE_CREDENTIALS_JSON="$(cat credentials.json)"
   railway variables set GOOGLE_CALENDAR_PARTNER1_ID=maria@gmail.com
   railway variables set GOOGLE_CALENDAR_PARTNER2_ID=carlos@gmail.com
   railway variables set GOOGLE_CALENDAR_FAMILY_ID=shared-calendar-id@group.calendar.google.com
   ```

> **Important:** If the OAuth app is left in "Testing" mode instead of published, tokens expire every 7 days and require manual re-authorization. Always publish the app.

### 6c. YNAB (Budget Tracking)

*Estimated time: 5-10 minutes*

1. The client creates a personal access token at [app.ynab.com/settings/developer](https://app.ynab.com/settings/developer)
2. Set the variables:
   ```bash
   railway variables set YNAB_ACCESS_TOKEN=the-client-token
   railway variables set YNAB_BUDGET_ID=last-used
   ```

`last-used` tells the YNAB API to use the client's most recently accessed budget. If they have multiple budgets, get the specific budget ID from the YNAB API or the URL when viewing the budget in the YNAB web app.

### 6d. AnyList (Grocery Management)

*Estimated time: 15-20 minutes*

AnyList requires a separate sidecar service (Node.js + Express) because the AnyList library only runs in Node.js.

1. In the Railway dashboard, add a **new service** to the project
2. Source: Same GitHub repo, root directory: `/anylist-sidecar`
3. **Do not add a public domain** -- the sidecar communicates via Railway private networking
4. Set environment variables on the sidecar service:
   ```
   ANYLIST_EMAIL=client-anylist-email
   ANYLIST_PASSWORD=client-anylist-password
   ```
5. On the main FastAPI service, set:
   ```bash
   railway variables set ANYLIST_SIDECAR_URL=http://anylist-sidecar.railway.internal:3000
   ```

> **Note:** The client must have an active AnyList account. AnyList does not have a public API -- the sidecar uses an unofficial library that authenticates with the client's credentials.

### 6e. Outlook Work Calendar (ICS Feed)

*Estimated time: 5-10 minutes*

For partners who use Outlook/Office 365 for work:

1. In Outlook Web (outlook.office365.com), go to **Settings** > **Calendar** > **Shared calendars**
2. Under **"Publish a calendar"**, select the work calendar and click **"Publish"**
3. Copy the **ICS** link (not the HTML link)
4. Set the environment variable:
   ```bash
   railway variables set OUTLOOK_CALENDAR_ICS_URL=https://outlook.office365.com/owa/calendar/...
   ```

Alternatively, use the iOS Shortcut method documented in [docs/ios-shortcut-setup.md](./ios-shortcut-setup.md) for work calendars that cannot be published via ICS.

---

## Step 7: Health Check Verification

*Estimated time: 2 minutes*

After deploying and configuring environment variables, verify the service is running:

```bash
curl https://{railway-domain}/health
```

**Expected responses:**

```json
{"status": "ok"}
```

The `"ok"` status indicates the core service is running. Optional integrations that are not configured will simply be unavailable (the assistant gracefully tells users when a feature requires an integration that is not set up).

If the health check fails:
- Check Railway logs: `railway logs`
- Verify all required environment variables are set: `railway variables`
- Confirm the volume is mounted at `/app/data`

---

## Step 8: First Test Message

*Estimated time: 5 minutes*

1. From one of the configured family phone numbers, open WhatsApp
2. Start a new chat with the business number provisioned in Step 5
3. Send:
   ```
   help
   ```
4. The assistant should respond with a welcome message and a list of available features

If no response:
- Check Railway logs for errors: `railway logs`
- Verify the webhook is receiving messages (check Meta developer dashboard > WhatsApp > Configuration > Webhook > recent deliveries)
- Confirm the sending phone number matches one of the configured family phone numbers in the environment variables

5. Test a follow-up message to verify conversation flow:
   ```
   What can you help with?
   ```

6. If integrations were configured, test one:
   ```
   What's on the calendar this week?
   ```
   (Should work if Google Calendar is configured; should respond gracefully if not)

---

## Step 9: Client Handoff

*Estimated time: 15-30 minutes (call or meeting with client)*

### What to tell the client

1. **How to interact**: "Just send a WhatsApp message to this number like you would text a friend. Ask it questions, give it tasks, or say 'help' anytime."

2. **What it can do** (tailor to their configured integrations):
   - "Ask about your schedule for the week"
   - "Add items to your grocery list"
   - "Plan meals for the week"
   - "Check your budget"
   - "Create action items and to-dos"
   - "Get a daily morning briefing"

3. **What it cannot do**:
   - It cannot make phone calls or send emails on your behalf
   - It cannot access anything outside the configured integrations
   - It does not learn from other families -- your data is completely isolated

4. **Response time**: Responses typically arrive within 5-15 seconds. Complex requests (meal planning, calendar analysis) may take up to 30 seconds.

5. **Privacy**:
   - Conversations are stored on the service's private infrastructure
   - The operator does not routinely access conversation data
   - Per-incident consent will be requested if the operator needs to review data for troubleshooting

6. **Automated messages**: If scheduled workflows are enabled, explain the schedule:
   - Daily morning briefing (weekdays at 7 AM)
   - Weekly meal plan suggestion (Saturday at 9 AM)
   - Budget summary (Sunday at 5 PM)
   - The client can ask the assistant to adjust or disable these

### Set expectations

- The assistant works best with natural language. No special commands or syntax required.
- It may occasionally misunderstand requests. Simply rephrase or say "that's not what I meant."
- New features and improvements are deployed automatically -- no action required from the client.

---

## Step 10: Post-Deployment Checklist

Review this checklist to confirm everything is complete:

### Core (required)

- [ ] `config/family.yaml` populated with client details
- [ ] Railway project created and linked
- [ ] Railway volume mounted at `/app/data`
- [ ] `ANTHROPIC_API_KEY` set
- [ ] `N8N_WEBHOOK_SECRET` set
- [ ] `WHATSAPP_PHONE_NUMBER_ID` set (not "pending")
- [ ] `WHATSAPP_ACCESS_TOKEN` set (permanent system user token, not temporary)
- [ ] `WHATSAPP_VERIFY_TOKEN` set
- [ ] `WHATSAPP_APP_SECRET` set
- [ ] WhatsApp webhook URL configured and verified in Meta dashboard
- [ ] WhatsApp webhook subscribed to `messages` field
- [ ] Family phone numbers set in environment variables
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] Test message "help" sent and response received

### Optional integrations (check those configured)

- [ ] Notion: Token and all database IDs set, integration connected to all pages
- [ ] Google Calendar: OAuth token uploaded, calendar IDs set, app published (not testing mode)
- [ ] YNAB: Access token and budget ID set
- [ ] AnyList: Sidecar service deployed, credentials set, sidecar URL configured
- [ ] Outlook: ICS URL set (or iOS Shortcut configured)

### Client handoff

- [ ] Client received the WhatsApp business number
- [ ] Client successfully sent and received a test message
- [ ] Client understands available features and limitations
- [ ] Client knows how to say "help" for feature discovery
- [ ] Privacy expectations documented and agreed upon

---

## Time Estimates Summary

| Step | Minimum viable | Full setup |
|------|---------------|------------|
| 1. Client intake | 15 min | 30 min |
| 2. Family config | 10 min | 10 min |
| 3. Environment file | 5 min | 10 min |
| 4. Railway deploy | 15 min | 20 min |
| 5. WhatsApp provisioning | 30 min | 60 min |
| 6a. Notion | -- | 45 min |
| 6b. Google Calendar | -- | 30 min |
| 6c. YNAB | -- | 10 min |
| 6d. AnyList | -- | 20 min |
| 6e. Outlook | -- | 10 min |
| 7. Health check | 2 min | 2 min |
| 8. Test message | 5 min | 5 min |
| 9. Client handoff | 15 min | 30 min |
| **Total** | **~1.5 hours** | **~4 hours** |

> **Note:** WhatsApp business verification (Step 5) may add 1-7 business days of calendar time. Start this step as early as possible and work on other steps in parallel while waiting for approval.

---

## Appendix: Updating a Client Deployment

### Deploying code updates

```bash
cd garcia-family-assistant
git pull origin main   # Or merge from upstream template
railway up
```

### Updating environment variables

```bash
railway variables set VARIABLE_NAME=new-value
# Service restarts automatically when variables change
```

### Viewing logs

```bash
railway logs           # Recent logs
railway logs --tail     # Follow logs in real-time
```

### Checking service status

```bash
railway status
```
