# Quickstart: Holistic Family Intelligence

## Prerequisites

- Bot deployed on NUC via `./scripts/nuc.sh deploy`
- Chat memory (feature 007) working
- SSH access to NUC (`ssh warp-nuc`)

## Test Method

All tests use SSH + docker compose exec to call `handle_message()` directly:

```bash
ssh warp-nuc
cd ~/family-meeting
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('PHONE', 'MESSAGE'))
"
```

Use test phone numbers to avoid affecting real user data.

---

## Test 1: Cross-Domain Question (US1)

**Goal**: Verify the bot connects dots across domains for broad questions.

```bash
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000001', 'how is our week looking?'))
"
```

**Expected**: Response mentions 2+ domains (e.g., calendar events AND budget status or meal plan status). Data is woven into narrative advice, not separate bulleted sections per domain. Includes at least one specific recommendation.

**Failure indicators**: Response only shows calendar events. Response has separate "Calendar:", "Budget:", "Meals:" sections. No actionable advice.

---

## Test 2: Cross-Domain Decision Question (US1)

**Goal**: Verify the bot checks multiple domains for decision questions.

```bash
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000001', 'can we afford to eat out this weekend?'))
"
```

**Expected**: Response checks restaurant budget remaining AND weekend calendar AND whether a meal is already planned. Gives a specific yes/no recommendation with reasoning.

**Failure indicators**: Only checks budget without considering meal plan. Only shows a number without recommendation.

---

## Test 3: Single-Domain Stays Focused (US1)

**Goal**: Verify the bot doesn't force cross-domain when not needed.

```bash
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000002', 'what did we spend at Costco this month?'))
"
```

**Expected**: Direct answer about Costco transactions. Response length comparable to pre-feature behavior. No unnecessary budget/meal/calendar additions.

**Failure indicators**: Response is significantly longer with unrelated domain data.

---

## Test 4: Enhanced Daily Briefing (US2)

**Goal**: Verify the daily briefing includes cross-domain insights.

```bash
docker compose exec fastapi python3 -c "
from src.assistant import generate_daily_plan
print(generate_daily_plan('erin'))
"
```

**Expected**: Briefing includes traditional elements (schedule, time blocks, Zoey status, backlog pick) PLUS at least one cross-domain insight connecting schedule to meals, budget, or tasks. Example: "Tonight's dinner is [X] — 30 min prep works since you have Awana's at 6" or "Grocery budget is tight — this week's meals lean on pantry staples."

**Failure indicators**: Briefing looks identical to pre-feature behavior with no cross-domain connections.

---

## Test 5: Briefing Conversation Follow-Up (US2)

**Goal**: Verify Erin can adjust the briefing via conversation.

```bash
# Step 1: Generate briefing
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000003', 'give me my daily briefing'))
"

# Step 2: Follow up with adjustment (within a few seconds)
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000003', 'swap tonight dinner for something easier'))
"
```

**Expected**: Step 2 understands the context from Step 1 (conversation memory) and acts on the adjustment using existing tools (handle_meal_swap or equivalent).

**Failure indicators**: Bot doesn't understand what "tonight's dinner" refers to.

---

## Test 6: Meeting Prep (US3)

**Goal**: Verify the meeting prep generates a comprehensive agenda.

```bash
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000004', 'prep me for our family meeting'))
"
```

**Expected**: Structured agenda with all 5 sections: (1) Budget snapshot with headline insight, (2) Calendar review (past + upcoming), (3) Action items (completed vs overdue), (4) Meal plan status, (5) Top priorities/discussion points. Each section has a bold headline and supporting bullets.

**Failure indicators**: Missing sections. Raw data dumps without insights. No synthesized priorities at the end.

---

## Test 7: Meeting Prep Endpoint (US3)

**Goal**: Verify the n8n endpoint works.

```bash
docker compose exec fastapi python3 -c "
import httpx
resp = httpx.post('http://localhost:8000/api/v1/meetings/prep-agenda',
    headers={'Authorization': 'Bearer \$(cat /app/.env | grep N8N_AUTH_TOKEN | cut -d= -f2)'})
print(resp.status_code, resp.json().get('status'))
"
```

**Expected**: Status 200, `{"status": "ok", "agenda": "..."}`.

**Note**: If n8n auth is complex, test via `generate_meeting_prep()` directly instead:

```bash
docker compose exec fastapi python3 -c "
from src.assistant import generate_meeting_prep
print(generate_meeting_prep())
"
```

---

## Cleanup

```bash
# Remove test conversation data
docker compose exec fastapi python3 -c "
from pathlib import Path
import json
f = Path('/app/data/conversations.json')
data = json.loads(f.read_text()) if f.exists() else {}
for key in list(data.keys()):
    if key.startswith('+1000000000'):
        del data[key]
f.write_text(json.dumps(data, indent=2))
print('Cleaned up test data')
"
```
