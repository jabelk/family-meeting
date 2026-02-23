# Research: Proactive Automations & Recipe Management

**Feature**: 002-proactive-recipes-automation | **Date**: 2026-02-22

## R1: Recipe Photo Storage — Cloudflare R2

**Decision**: Use Cloudflare R2 free tier with boto3 (S3-compatible API)

**Rationale**: R2 offers 10GB free storage, zero egress costs, and full S3 API compatibility via boto3. No new SDK needed — existing Python ecosystem. Recipe photos at ~2-5MB each means 2,000-5,000 photos before hitting the free tier. Far exceeds expected usage (20-50 recipes/month).

**Alternatives considered**:
- Notion file upload (rejected: 5MB per-file limit, no CDN, consumes block quota)
- AWS S3 (rejected: egress costs, more complex IAM setup for zero benefit)
- Imgur/image hosting (rejected: no API stability guarantees, privacy concerns)
- Local file storage on NUC (rejected: no redundancy, ties photos to hardware)

**Implementation details**:
- Endpoint: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
- Auth: Access Key ID + Secret Access Key (created in Cloudflare dashboard)
- Python: `boto3.client("s3", endpoint_url=..., region_name="auto")`
- Upload: `s3.put_object(Bucket="family-recipes", Key="recipes/{id}.jpg", Body=data, ContentType="image/jpeg")`
- Public access: Generate presigned URLs (1-hour expiry) or enable public bucket access
- Bucket naming: `family-recipes`
- Key pattern: `recipes/{recipe_notion_id}.jpg`

**New environment variables**:
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME` (default: `family-recipes`)

---

## R2: WhatsApp Image Download via Meta Cloud API

**Decision**: Use Meta Graph API two-step media download (get URL → download binary)

**Rationale**: Standard Meta Cloud API flow. Media URLs expire in 5 minutes, so download must happen immediately in the webhook handler. No third-party library needed — httpx handles both API calls.

**Alternatives considered**:
- PyWa library (rejected: adds dependency for a 10-line function; httpx already in requirements)
- Storing media_id for later download (rejected: 5-minute URL expiry makes async processing risky)

**Implementation details**:

Step 1 — Extract media_id from webhook payload:
```python
# In WhatsApp webhook, image messages have:
# message["type"] == "image"
# message["image"]["id"] == media_id
# message["image"]["mime_type"] == "image/jpeg"
# message["image"]["caption"] == "save this from the keto book" (optional)
```

Step 2 — Get download URL:
```
GET https://graph.facebook.com/v21.0/{media_id}
Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}
→ {"url": "https://...", "mime_type": "image/jpeg", "file_size": ...}
```

Step 3 — Download binary:
```
GET {url}
Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}
→ binary image data
```

**Critical timing**: Must complete steps 2+3 within 5 minutes of webhook receipt. Since FastAPI processes in a background task, this is fine — download happens immediately in the handler.

---

## R3: WhatsApp Template Messages for Proactive Sends

**Decision**: Create 3 utility template messages for proactive sends outside the 24-hour window

**Rationale**: The 24-hour messaging window closes if the user hasn't messaged recently. Weekday daily briefings at 7am usually keep the window open (Erin interacts with Mom Bot daily). But Saturday/Sunday proactive messages may fall outside the window if Erin didn't message Friday. Templates are the only way to send outside the window.

**Alternatives considered**:
- Only send proactive messages within 24-hour window (rejected: Saturday meal plan + Sunday budget summary are the most important proactive messages and most likely to be outside the window)
- Send a "ping" message to open the window (rejected: violates Meta policy — can't send free-form messages to open a window)

**Templates needed** (submit via Meta Business Manager):

1. **`daily_briefing`** (utility): "Good morning! Here's your plan for today: {{1}}"
   - {{1}} = truncated briefing summary (template messages have char limits)
   - Fallback: Send template with summary, then follow up with full details once Erin replies

2. **`weekly_meal_plan`** (utility): "Your weekly meal plan and grocery list is ready! Reply to review and approve."
   - Simpler template — actual content sent as follow-up after Erin opens the window by replying

3. **`weekly_summary`** (utility): "Your weekly budget summary is ready. Reply to see details."

**Approval process**: Submit in Meta Business Manager → reviewed within 24 hours → approved templates can be used indefinitely.

**Implementation approach**: Try free-form message first. If Meta returns 131026 error (outside window), fall back to template message. This minimizes template usage since most days the window is open.

---

## R4: Dedicated n8n Instance in Docker Compose

**Decision**: Add a second n8n container (`n8n-mombot`) to the existing docker-compose.yml with SQLite storage (no Postgres needed)

**Rationale**: Jason already runs n8n on the NUC for other projects. A separate container keeps Mom Bot workflows isolated — different data, different credentials, different port. SQLite is sufficient for 7 simple cron workflows (no queue mode, no workers needed).

**Alternatives considered**:
- Share existing n8n instance (rejected: user explicitly wants isolation)
- Queue mode with Redis + Postgres (rejected: massive overkill for 7 cron jobs with 2 users)
- Custom Python scheduler (rejected: violates "Integration Over Building" principle — n8n already exists)
- Cron on host + curl (rejected: no UI for debugging, no retry logic, no execution history)

**Implementation details**:

```yaml
# Added to docker-compose.yml
n8n-mombot:
  image: n8nio/n8n:latest
  container_name: n8n-mombot
  ports:
    - "5679:5678"   # Map to 5679 externally (5678 used by existing n8n)
  environment:
    - N8N_BASIC_AUTH_ACTIVE=true
    - N8N_BASIC_AUTH_USER=${N8N_MOMBOT_USER}
    - N8N_BASIC_AUTH_PASSWORD=${N8N_MOMBOT_PASSWORD}
    - GENERIC_TIMEZONE=America/Los_Angeles
    - TZ=America/Los_Angeles
    - N8N_ENCRYPTION_KEY=${N8N_MOMBOT_ENCRYPTION_KEY}
    - WEBHOOK_URL=http://n8n-mombot:5678
  volumes:
    - n8n_mombot_data:/home/node/.n8n
  networks:
    - family-net
  restart: unless-stopped
```

**n8n connects to FastAPI** at `http://fastapi:8000` (Docker internal network).

**New environment variables**:
- `N8N_MOMBOT_USER`
- `N8N_MOMBOT_PASSWORD`
- `N8N_MOMBOT_ENCRYPTION_KEY`

---

## R5: Claude Vision for Recipe OCR

**Decision**: Use Anthropic Claude vision (image input to Claude Haiku 4.5) for recipe extraction — same SDK already in use

**Rationale**: Claude vision handles cookbook photos well — typed text, varied layouts, ingredient lists, step-by-step instructions. No separate OCR service needed. The anthropic SDK already supports image inputs via base64 or URL. Using the same Claude Haiku 4.5 model keeps costs low (~$0.001 per image).

**Alternatives considered**:
- Google Cloud Vision OCR + GPT parsing (rejected: adds 2 new services, more complexity)
- Tesseract OCR (rejected: poor accuracy on cookbook photos with varied fonts/layouts)
- Apple Vision framework on device (rejected: requires iOS app development, violates mobile-first WhatsApp approach)

**Implementation details**:

```python
# Recipe extraction prompt pattern
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=2000,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mime_type, "data": base64_image}
            },
            {
                "type": "text",
                "text": "Extract the recipe from this cookbook page. Return JSON: {name, ingredients: [{name, quantity, unit}], instructions: [steps], prep_time, cook_time, servings}. Mark unclear text as [unclear]."
            }
        ]
    }]
)
```

**Cost estimate**: Haiku 4.5 vision ~$0.001/image. At 50 recipes/month = $0.05/month.

---

## R6: Recipe Search Strategy

**Decision**: Use Notion database query with title/text search + Claude for natural language interpretation

**Rationale**: Notion's database query supports text filtering on title and rich_text properties. For exact matches ("chicken parmesan") this works directly. For fuzzy/natural language queries ("the steak dish from the keto book"), use Claude to interpret the query and generate Notion filter parameters, then search.

**Alternatives considered**:
- Full-text search engine (Elasticsearch, Meilisearch) (rejected: overkill for <500 recipes, adds infrastructure)
- Embedding-based vector search (rejected: requires vector DB, complex for the scale)
- Client-side filtering (rejected: Notion API pagination makes full-scan expensive)

**Implementation approach**:
1. Claude interprets user query → extracts: recipe name keywords, cookbook name, ingredient keywords
2. Query Notion Recipes DB with filters: title contains keywords AND/OR cookbook relation matches
3. If multiple results, Claude ranks by relevance and presents top 3
4. If no results, Claude suggests similar options

---

## R7: Meal Plan Generation Strategy

**Decision**: Use Claude with context injection (saved recipes, grocery history, recent plans, weekly schedule) to generate dinner plans

**Rationale**: Claude already has the family profile context. By injecting saved recipes, recent meal plans (last 2 weeks), and schedule density per day, Claude can generate contextually appropriate dinner suggestions. Simpler meals on busy days (gymnastics Tuesday, both kids Wednesday-Friday), recipes from the catalogue when applicable.

**Alternatives considered**:
- Deterministic algorithm (rejected: can't handle the nuance of "kid-friendly", "keto-ish", "simple for busy days")
- Recipe recommendation API (rejected: no service knows Erin's saved recipes or family schedule)

**Implementation approach**:
1. Gather context: saved recipes (all), last 2 weeks' meal plans, weekly schedule, grocery history staples
2. Build prompt: "Generate 6 dinner suggestions for Mon-Sat. [context]. Use saved recipes when appropriate. Simpler meals on [busy days]. Avoid: [last 2 weeks' meals]."
3. Claude returns structured plan: `[{day, meal_name, source (recipe_id or "general"), ingredients, complexity}]`
4. Generate merged grocery list: recipe ingredients + reorder staples - recently ordered items
5. Present to Erin for review/adjustment

---

## R8: Grocery List Deduplication and Merging

**Decision**: Merge meal plan ingredients with reorder staples, then deduct recently ordered items

**Rationale**: The Saturday message combines meal plan + grocery reorder into one list. Need to avoid duplicates (e.g., milk appears in both a recipe and as a reorder staple) and avoid suggesting items bought recently.

**Implementation approach**:
1. **Meal plan ingredients**: Extract from each meal (saved recipe → exact ingredients; general suggestion → Claude-generated ingredient list)
2. **Reorder staples**: Query Grocery History where `days_since_last_order > avg_reorder_days`
3. **Merge**: Combine both lists, deduplicating by normalized item name (use same normalization logic from import script)
4. **Deduct**: Remove items where `last_ordered` is within 50% of `avg_reorder_days` (recently bought)
5. **Group by store**: Use Grocery History store data for known items; unknown items default to "Whole Foods"
6. **Present**: Grouped list with quantities from recipes, store attribution

---

## R9: Calendar Conflict Detection Logic

**Decision**: Compare events across all 4 calendars against family routine patterns

**Rationale**: Conflict detection needs two layers: (1) hard conflicts — two events overlap in time, and (2) soft conflicts — a calendar event overlaps with a family routine from the Family Profile (e.g., work meeting during pickup time). The routine templates in the Family Profile provide the reference schedule.

**Implementation approach**:
1. Fetch all events for target day from: Jason Google, Erin Google, Family shared, Jason Outlook
2. Parse routine templates for the day (pickup times, Sandy dropoff, etc.)
3. Detect hard conflicts: any two events with overlapping time ranges
4. Detect soft conflicts: any event overlapping a routine entry (Vienna pickup, Zoey dropoff, etc.)
5. For each conflict, generate suggestion: "Erin, can you cover Vienna's 3:15 pickup? Jason has a meeting 2:30-3:30."
6. Include in daily briefing (mornings) and weekly scan (Sunday evening)

---

## R10: Order Confirmation and Reminder Flow

**Decision**: Track AnyList push events and send 2-day reminder if no confirmation

**Rationale**: When Erin approves groceries and they're pushed to AnyList, the system needs to know when she actually places the order (to update Last Ordered dates). A simple confirmation flow: after pushing to AnyList, set a "pending confirmation" flag. If Erin says "groceries ordered" within 2 days, update Last Ordered. If not, send a gentle reminder.

**Implementation approach**:
1. When items pushed to AnyList, store in Notion (new property or simple key-value): `last_anylist_push_date`, `pending_items`
2. Add n8n workflow: daily check at 10am — if `last_anylist_push_date` was 2+ days ago and no confirmation, send reminder
3. When Erin confirms ("groceries ordered", "ordered", "done"), update `Last Ordered` for all pending items in Grocery History
4. Clear pending state after confirmation
