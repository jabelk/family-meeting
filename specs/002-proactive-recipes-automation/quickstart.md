# Quickstart: Proactive Automations & Recipe Management

**Feature**: 002-proactive-recipes-automation | **Date**: 2026-02-22

## Prerequisites

- Feature 001 fully deployed (FastAPI + AnyList sidecar + Cloudflare Tunnel on NUC)
- WhatsApp webhook receiving messages
- Notion databases set up (Action Items, Meal Plans, Meetings, Backlog, Grocery History)
- Google Calendar + YNAB configured
- Python 3.12 + `.venv` virtual environment

## New Infrastructure Setup

### 1. Cloudflare R2 Bucket

1. Log into Cloudflare dashboard → R2 → Create bucket
2. Bucket name: `family-recipes`
3. Create API token: R2 → Manage R2 API Tokens → Create API Token
   - Permissions: Object Read & Write
   - Scope: `family-recipes` bucket only
4. Copy Account ID, Access Key ID, Secret Access Key
5. Add to `.env`:
   ```
   R2_ACCOUNT_ID=<your-account-id>
   R2_ACCESS_KEY_ID=<your-access-key>
   R2_SECRET_ACCESS_KEY=<your-secret-key>
   R2_BUCKET_NAME=family-recipes
   ```

### 2. Notion Databases (2 new)

Create in Notion and connect the "Family Meeting Bot" integration:

**Recipes Database**:
- Name (Title), Cookbook (Relation → Cookbooks), Ingredients (Rich Text), Instructions (Rich Text)
- Prep Time (Number), Cook Time (Number), Servings (Number)
- Photo URL (URL), Tags (Multi-select), Cuisine (Select)
- Date Added (Date), Times Used (Number), Last Used (Date)

**Cookbooks Database**:
- Name (Title), Description (Rich Text)

Add to `.env`:
```
NOTION_RECIPES_DB=<recipes-database-id>
NOTION_COOKBOOKS_DB=<cookbooks-database-id>
```

Update Grocery History DB (add 2 properties):
- Pending Order (Checkbox)
- Last Push Date (Date)

### 3. n8n Mom Bot Instance

Add to `docker-compose.yml`:
```yaml
n8n-mombot:
  image: n8nio/n8n:latest
  container_name: n8n-mombot
  ports:
    - "5679:5678"
  environment:
    - N8N_BASIC_AUTH_ACTIVE=true
    - N8N_BASIC_AUTH_USER=${N8N_MOMBOT_USER}
    - N8N_BASIC_AUTH_PASSWORD=${N8N_MOMBOT_PASSWORD}
    - GENERIC_TIMEZONE=America/Los_Angeles
    - TZ=America/Los_Angeles
    - N8N_ENCRYPTION_KEY=${N8N_MOMBOT_ENCRYPTION_KEY}
  volumes:
    - n8n_mombot_data:/home/node/.n8n
  networks:
    - family-net
  restart: unless-stopped
```

Add to `.env`:
```
N8N_MOMBOT_USER=admin
N8N_MOMBOT_PASSWORD=<generate-strong-password>
N8N_MOMBOT_ENCRYPTION_KEY=<generate-random-key>
N8N_WEBHOOK_SECRET=<shared-secret-for-api-auth>
```

### 4. WhatsApp Template Messages

Submit 3 templates in Meta Business Manager:
1. `daily_briefing` — "Good morning! Here's your plan for today: {{1}}"
2. `weekly_meal_plan` — "Your weekly meal plan and grocery list is ready! Reply to review and approve."
3. `weekly_summary` — "Your weekly budget summary is ready. Reply to see details."

### 5. New Python Dependencies

```
boto3>=1.35.0
```

Add to `requirements.txt` and rebuild Docker image.

## Development Order

Implement in priority order (each user story is independently testable):

1. **US1 — Recipe Catalogue** (P1): `src/tools/recipes.py` + Notion recipe CRUD + R2 upload + WhatsApp image handling
2. **US2 — Grocery Reorder** (P2): `src/tools/proactive.py` reorder check + endpoint
3. **US3 — Meal Planning** (P3): meal plan generation + grocery merge in `proactive.py`
4. **US4 — n8n Workflows** (P4): Docker setup + 8 workflow configs
5. **US5 — Conflict Detection** (P5): calendar conflict logic in `proactive.py`
6. **US6 — Action Item Reminders** (P6): mid-week check-in endpoint
7. **US7 — Budget Summary** (P7): format + send endpoint

## Verification

After each user story, test manually:
- US1: Send a cookbook photo via WhatsApp → recipe appears in Notion with R2 photo link
- US2: Call `POST /api/v1/grocery/reorder-check` → get grouped suggestions
- US3: Call `POST /api/v1/meals/plan-week` → get dinner plan + merged grocery list
- US4: Check n8n UI at `:5679` → all 8 workflows present and scheduled
- US5: Create overlapping test event → daily briefing flags conflict
- US6: Create incomplete action items → Wednesday check-in reports them
- US7: Call `POST /api/v1/budget/weekly-summary` → formatted spending report sent

## Environment Variables Summary (new for this feature)

```
# Cloudflare R2
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=family-recipes

# Notion (2 new databases)
NOTION_RECIPES_DB=
NOTION_COOKBOOKS_DB=

# n8n Mom Bot instance
N8N_MOMBOT_USER=admin
N8N_MOMBOT_PASSWORD=
N8N_MOMBOT_ENCRYPTION_KEY=
N8N_WEBHOOK_SECRET=
```
