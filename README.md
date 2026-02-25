# Mom Bot — AI Family Assistant

A WhatsApp-based family assistant powered by Claude that helps busy parents coordinate their household. It manages calendars, budgets, meal planning, grocery ordering, chore tracking, recipe cataloguing, and more — all through natural conversation in a WhatsApp group chat.

Built by a family of four (two parents, two young kids) to solve the real coordination problems of daily life. Currently running 11 features with 50+ tools across 6 integrated services.

## How It Works

```
WhatsApp Group Chat
        |
        v
Meta Cloud API (webhook)
        |
        v
FastAPI Server (Python 3.12)
        |
        v
Claude (Anthropic) — agentic tool loop
        |
        v
┌───────┬──────────┬──────┬─────────┬─────────┐
│Notion │ Google   │ YNAB │ AnyList │ Gmail   │
│(5 DBs)│ Calendar │      │         │ (email  │
│       │ (3 cals) │      │         │  sync)  │
└───────┴──────────┴──────┴─────────┴─────────┘
```

You text the bot in WhatsApp. Claude reads your message, decides which tools to call (calendar, budget, recipes, etc.), executes them, and sends back a formatted response. It remembers conversation context for 24 hours.

Scheduled workflows run via n8n (open-source automation):
- **7:00am** — Daily briefing sent to Erin with calendar, chores, meals, and cross-domain insights
- **10:00pm** — Amazon order sync (matches orders to YNAB transactions)
- **10:05pm** — Email sync (PayPal, Venmo, Apple charges matched to YNAB)
- **Weekly** — Calendar population, budget scan, mid-week check-in

## Features

| # | Feature | What It Does |
|---|---------|-------------|
| 001 | Core Assistant | Weekly meeting agendas, action items, daily planner, calendar read/write, meal plans, grocery lists via AnyList |
| 002 | Recipe Automation | OCR cookbook photos with Claude Vision, save to Notion catalogue, generate grocery lists from recipes |
| 003 | Smart Nudges | Departure reminders, laundry workflow timer, chore suggestions during free windows, quiet day mode |
| 004 | YNAB Budget | Transaction search, recategorization, manual entries, budget moves, category adjustments |
| 005 | Recipe Search | Search Downshiftology.com for new recipes, import to catalogue, cross-reference with grocery history |
| 006 | Feature Discovery | Dynamic help menu, contextual "did you know?" tips, first-time welcome |
| 007 | Chat Memory | 24-hour conversation persistence, multi-turn workflows |
| 008 | Holistic Intelligence | Cross-domain reasoning — connects budget + calendar + meals + tasks into coherent advice |
| 010 | Amazon Sync | Parse Amazon order emails via Gmail API, match to YNAB transactions, auto-categorize with item-level splits |
| 011 | Email Sync | Same as above but for PayPal, Venmo, and Apple subscription charges |

## Example Conversations

```
Erin: what's my day look like?
Bot:  *Your Tuesday Plan* ☀️
      7:00 — Morning routine + breakfast (Jason free until 8:30)
      9:30 — Drop off Vienna at Roy Gomm
      10:00-1:00 — Sandy has Zoey! 🎉
        • Chore block: vacuum living room + start laundry
        • Personal: knitting project (backlog item)
      1:00 — Pick up Zoey from Sandy's
      2:30 — Move laundry to dryer
      3:15 — Pick up Vienna (early — Zoey's gymnastics)
      ...
      Budget note: Groceries at 78% with 6 days left — on track.
      Tonight's dinner: Sheet pan chicken fajitas (30 min, kid-friendly)
```

```
Erin: sync my Amazon
Bot:  [sends detailed message directly to Erin]
      🛒 Amazon Sync — 3 new orders matched
      1️⃣ $87.42 (Feb 23) — 3 items
        • Nature Made Vitamin D3 → Healthcare ($24.99)
        • LEGO Duplo Train → Kids Toys ($42.43)
        • USB-C Cable → Jason Fun ($12.99)
      Reply "1 yes" to split, "1 adjust" to modify
```

```
Erin: can we afford to eat out this weekend?
Bot:  Dining Out is at $890 of $1,200 this month with 5 days left —
      you have about $310 of room. Saturday looks busy (ski lesson
      8-11am, groceries after) so a quick lunch out makes sense.
      Sunday you're free after church. I'd suggest keeping it under
      $80 total to stay on track. Want me to find a restaurant?
```

## Architecture

```
family-meeting/
├── src/
│   ├── app.py              # FastAPI — webhook + n8n endpoints
│   ├── assistant.py         # Claude system prompt, 50+ tools, message loop
│   ├── config.py            # Environment variables
│   ├── whatsapp.py          # Meta Cloud API send/receive
│   ├── conversation.py      # Chat memory (24h window)
│   └── tools/
│       ├── calendar.py      # Google Calendar (3 cals) + Outlook ICS
│       ├── notion.py        # 5 Notion databases
│       ├── ynab.py          # YNAB budget + transactions
│       ├── recipes.py       # Recipe OCR + catalogue
│       ├── downshiftology.py # External recipe search
│       ├── amazon_sync.py   # Amazon order email parsing + YNAB sync
│       ├── email_sync.py    # PayPal/Venmo/Apple email sync
│       ├── nudges.py        # Departure reminders + nudge queue
│       ├── chores.py        # Chore tracking + preferences
│       ├── laundry.py       # Laundry workflow timer
│       ├── proactive.py     # Meal planning + reorder detection
│       ├── discovery.py     # Help menu + contextual tips
│       ├── anylist_bridge.py # AnyList grocery sidecar
│       └── outlook.py       # Outlook ICS feed parser
├── anylist-sidecar/         # Node.js Express server for AnyList API
├── scripts/
│   ├── nuc.sh               # Deployment helper (logs, restart, deploy)
│   ├── setup_calendar.py    # Google OAuth setup
│   └── n8n-workflows/       # n8n workflow JSON files
├── specs/                   # Feature specifications (speckit)
├── .specify/                # Speckit templates + scripts
├── data/                    # Persistent JSON files (sync records, etc.)
├── docker-compose.yml       # 4 services: fastapi, anylist, cloudflared, n8n
├── Dockerfile
└── .env                     # All credentials (not in git)
```

## Deployment

The production stack runs on a home server (Intel NUC, Ubuntu 24.04) via Docker Compose with a Cloudflare Tunnel for public HTTPS.

**Services:**
- `fastapi` — Python app (port 8000)
- `anylist-sidecar` — Node.js AnyList bridge (port 3000)
- `cloudflared` — Cloudflare Tunnel (HTTPS ingress)
- `n8n-mombot` — Workflow automation (port 5679)

**Deploy workflow:** Edit locally → commit → push to GitHub → `./scripts/nuc.sh deploy` (pulls, rebuilds, restarts on NUC via SSH).

## Setup Guide

### Prerequisites

- A server or always-on machine (NUC, Raspberry Pi, cloud VM, etc.)
- Docker and Docker Compose
- A domain name (for Cloudflare Tunnel)
- Accounts: Anthropic, Meta (WhatsApp Business), Notion, Google Cloud, YNAB

### 1. Clone and configure

```bash
git clone https://github.com/jabelk/family-meeting.git
cd family-meeting
cp .env.example .env   # Then fill in all values
```

### 2. Required environment variables

```bash
# Core AI
ANTHROPIC_API_KEY=sk-ant-...          # anthropic.com/dashboard

# WhatsApp (Meta Cloud API)
WHATSAPP_PHONE_NUMBER_ID=...          # Meta Business dashboard
WHATSAPP_ACCESS_TOKEN=...             # Permanent token
WHATSAPP_VERIFY_TOKEN=...             # You choose this (webhook verification)
WHATSAPP_APP_SECRET=...               # For webhook signature verification

# Family phones (with country code, no +)
JASON_PHONE=1234567890
ERIN_PHONE=0987654321

# Notion
NOTION_TOKEN=ntn_...                  # notion.so/my-integrations
NOTION_ACTION_ITEMS_DB=...            # Database IDs from Notion URLs
NOTION_MEAL_PLANS_DB=...
NOTION_MEETINGS_DB=...
NOTION_FAMILY_PROFILE_PAGE=...
NOTION_BACKLOG_DB=...
NOTION_GROCERY_HISTORY_DB=...
NOTION_RECIPES_DB=...
NOTION_COOKBOOKS_DB=...
NOTION_NUDGE_QUEUE_DB=...
NOTION_CHORES_DB=...

# Google Calendar (OAuth — run setup_calendar.py first)
GOOGLE_CALENDAR_JASON_ID=...          # email or calendar ID
GOOGLE_CALENDAR_ERIN_ID=...
GOOGLE_CALENDAR_FAMILY_ID=...

# YNAB
YNAB_ACCESS_TOKEN=...                 # app.ynab.com/settings/developer
YNAB_BUDGET_ID=...                    # From YNAB URL or API

# n8n webhook auth
N8N_WEBHOOK_SECRET=...                # Shared secret you choose

# Optional: Outlook ICS, AnyList, Cloudflare R2
OUTLOOK_CALENDAR_ICS_URL=...
ANYLIST_EMAIL=...
ANYLIST_PASSWORD=...
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
```

### 3. Google Calendar OAuth setup

```bash
# Download credentials.json from Google Cloud Console
# (OAuth 2.0 Client ID → Desktop application)
python3 scripts/setup_calendar.py
# Opens browser for OAuth consent — authorize with both partners' Gmail accounts
# Creates token.json (mount into Docker container)
```

**Note:** In Google Cloud "testing" mode, tokens expire every 7 days. Re-run `setup_calendar.py` to refresh. Move to "production" mode to get permanent tokens.

### 4. Notion database setup

Create these Notion databases and share them with your integration:

| Database | Required Properties |
|----------|-------------------|
| Action Items | Title, Assignee (select), Status (status), Due Context (select) |
| Meal Plans | Title, Week Start (date), Plan Content (rich text), Grocery List (rich text) |
| Meetings | Title, Date (date), Status (status) |
| Backlog | Title, Assignee (select), Status (status), Category (select), Priority (select) |
| Grocery History | Title, Category (select), Last Ordered (date), Frequency (number) |
| Recipes | Title, Cookbook (relation), Tags (multi-select), Prep Time (number), Cook Time (number) |
| Cookbooks | Title, Recipe Count (rollup) |
| Nudge Queue | Title, Type (select), Status (status), Scheduled For (date) |
| Chores | Title, Frequency (select), Last Done (date), Preference (select) |

Also create a **Family Profile** page with sections for Members, Preferences, Routine Templates, Childcare Schedule, and Configuration.

### 5. WhatsApp Business setup

1. Create a Meta Business account and WhatsApp Business app at [developers.facebook.com](https://developers.facebook.com)
2. Set up a phone number (you can use a test number)
3. Configure the webhook URL: `https://yourdomain.com/webhook`
4. Subscribe to `messages` webhook field
5. Generate a permanent access token

### 6. Deploy

```bash
# Local development
docker compose up --build

# Production (on your server)
docker compose up -d --build

# With Cloudflare Tunnel for HTTPS
# Configure tunnel to point to http://fastapi:8000
```

### 7. Import n8n workflows

```bash
# Copy workflow files into n8n container
docker compose cp scripts/n8n-workflows/. n8n-mombot:/tmp/workflows/

# Import each workflow
docker compose exec n8n-mombot n8n import:workflow --input=/tmp/workflows/daily-briefing.json
# ... repeat for each workflow file

# Activate workflows via n8n UI at http://your-server:5679
```

## Customizing for Your Family

This bot was built for a specific family — you'll need to customize it for yours:

1. **System prompt** (`src/assistant.py` — `SYSTEM_PROMPT`): Replace family member names, schedules, preferences, and rules with your own. This is the bot's personality and knowledge base.

2. **Tools**: Enable/disable features by adding/removing tools from the `TOOLS` list and `TOOL_FUNCTIONS` dict in `assistant.py`. Each tool module in `src/tools/` is independent.

3. **Schedules**: Update n8n workflows for your timezone and preferred automation times.

4. **Categories**: YNAB category mappings, recipe tags, chore lists — all configurable through the bot itself ("I like to vacuum on Wednesdays", "add to backlog: organize garage").

## How This Was Built — Claude Code + Speckit

This entire project was built using [Claude Code](https://claude.ai/code) (Anthropic's CLI coding agent) with a spec-driven development workflow called **Speckit**.

### What is Claude Code?

Claude Code is a terminal-based AI coding assistant. You describe what you want in natural language, and it reads your codebase, writes code, runs commands, and iterates until the feature works. It's like pair programming with an AI that can see your entire project.

```bash
# Install
npm install -g @anthropic-ai/claude-code

# Run in your project directory
cd family-meeting
claude
```

Then you just talk to it: "Add a new endpoint that syncs PayPal transactions" and it reads the relevant files, writes the code, tests it, and commits.

### What is Speckit?

Speckit is a spec-driven development framework (included in this repo under `.specify/`) that structures how features get built. Instead of jumping straight into code, you go through a pipeline:

```
/speckit.specify  →  Write a feature spec from natural language
/speckit.clarify  →  Ask 3-5 targeted questions to resolve ambiguities
/speckit.plan     →  Generate technical plan (data model, API contracts, research)
/speckit.tasks    →  Break the plan into dependency-ordered implementation tasks
/speckit.analyze  →  Cross-check spec/plan/tasks for inconsistencies
/speckit.implement → Execute all tasks phase-by-phase with checkpoints
```

Each step produces a markdown artifact in `specs/###-feature-name/`:
- `spec.md` — What to build and why (user-focused, no tech details)
- `plan.md` — How to build it (architecture, tech stack, file structure)
- `data-model.md` — Entities, fields, relationships
- `contracts/` — API endpoints, tool definitions
- `tasks.md` — Ordered checklist of implementation tasks
- `research.md` — Technical decisions and alternatives considered

### Why this workflow matters

When you're building with AI, the quality of what you get out depends entirely on the quality of what you put in. Speckit forces you to:

1. **Think before coding** — The spec phase makes you articulate what you actually want
2. **Resolve ambiguity early** — The clarify phase catches "what if?" scenarios before they become bugs
3. **Plan the architecture** — The plan phase prevents the AI from making ad-hoc decisions that don't fit your codebase
4. **Track progress** — The task list gives you (and the AI) a clear checklist to execute against
5. **Validate consistency** — The analyze phase catches when the spec says one thing but the tasks do another

### Example: Building Feature 011 (Email-YNAB Sync)

Here's how a feature goes from idea to production:

```bash
# Start Claude Code
claude

# 1. Describe the feature
> /speckit.specify Automated PayPal, Venmo, and Apple subscription
  categorization for YNAB — use the existing Gmail API integration to
  parse transaction confirmation emails...

# Claude creates specs/011-email-ynab-sync/spec.md with user stories,
# functional requirements, success criteria, and edge cases

# 2. Clarify ambiguities
> /speckit.clarify

# Claude asks 3-5 targeted questions:
# "Should refunds be auto-categorized or require confirmation?"
# "Should the sync run for all providers in parallel or sequentially?"

# 3. Generate technical plan
> /speckit.plan

# Creates plan.md, data-model.md, contracts/api-endpoints.md, research.md

# 4. Generate tasks
> /speckit.tasks

# Creates tasks.md with 32 tasks across 6 phases, dependency-ordered

# 5. Validate everything is consistent
> /speckit.analyze

# Finds 5 issues (e.g., "recurring charge detection is in Phase 5 but
# needed by Phase 3"). Fix them before implementing.

# 6. Implement
> /speckit.implement

# Claude executes all 32 tasks: creates files, writes functions,
# adds tool definitions, creates API endpoints, builds n8n workflows.
# Each task gets checked off as it completes.

# 7. Deploy and test
> commit this and deploy to NUC and do end to end test

# Claude commits, pushes, SSHes to the NUC, rebuilds Docker,
# triggers the sync endpoint, and verifies results in the logs.
```

The entire Feature 011 — from spec to production deployment with 13 real transactions processed — was built in a single Claude Code session.

### Tips for using Claude Code effectively

- **Start with Speckit** for any non-trivial feature. Even if it feels slow, the planning prevents expensive rework.
- **Read the CLAUDE.md file** — this is how Claude Code knows about your project. Keep it updated with architecture decisions, conventions, and deployment info.
- **Let it deploy** — Claude Code can SSH to servers, run Docker commands, check logs, and iterate on failures. Don't copy-paste commands manually.
- **Trust but verify** — Check the spec and plan before saying "implement." The AI will faithfully execute a bad plan.
- **Use the analyze step** — It catches real bugs (like a function defined in Phase 5 but needed in Phase 3).

## License

This is a personal project shared for reference. The Speckit framework (`.specify/`) is reusable for any project. Feel free to fork and adapt for your family.
