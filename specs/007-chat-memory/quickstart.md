# Quickstart: Chat Memory & Conversation Persistence

## Prerequisites

- Bot deployed on NUC via `./scripts/nuc.sh deploy`
- WhatsApp webhook functional
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

Use a test phone number (e.g., `+10000000001`) to avoid affecting real user data.

---

## Test 1: Basic Follow-Up (US1)

**Goal**: Verify the bot remembers context from the previous message.

```bash
# Step 1: Ask about the calendar
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000001', 'what is on our calendar this week?'))
"

# Step 2: Follow up (within 30 seconds)
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000001', 'what about next week?'))
"
```

**Expected**: Step 2 returns calendar events for next week without needing to specify "calendar" — the bot understands the context.

---

## Test 2: Multi-Step Recipe Workflow (US2)

**Goal**: Verify a 3+ step workflow works without repeating context.

```bash
# Step 1: Search
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000002', 'find me a chicken dinner recipe'))
"

# Step 2: Get details (wait a few seconds between steps)
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000002', 'tell me more about number 1'))
"

# Step 3: Save
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000002', 'save that one'))
"
```

**Expected**: Each step builds on the previous — no "I don't know what recipe you mean" errors.

---

## Test 3: Conversation Expiry (US3)

**Goal**: Verify stale conversations don't leak into new topics.

```bash
# Step 1: Start a conversation about recipes
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000003', 'search for keto breakfast ideas'))
"

# Step 2: Manually expire the conversation by editing the file
docker compose exec fastapi python3 -c "
import json
from pathlib import Path
f = Path('/app/data/conversations.json')
data = json.loads(f.read_text())
# Set last_active to 2 hours ago
from datetime import datetime, timedelta
old_time = (datetime.now() - timedelta(hours=2)).isoformat()
data['+10000000003']['last_active'] = old_time
f.write_text(json.dumps(data, indent=2))
print('Expired conversation')
"

# Step 3: Send a new message on a different topic
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000003', 'what is our budget looking like?'))
"
```

**Expected**: Step 3 responds with budget info, no recipe context leaking in.

---

## Test 4: Restart Persistence (US3 - SC-005)

**Goal**: Verify conversation history survives a container restart.

```bash
# Step 1: Start a conversation
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000004', 'what did we spend at Costco?'))
"

# Step 2: Verify file exists
docker compose exec fastapi ls -la /app/data/conversations.json

# Step 3: Restart the container
docker compose restart fastapi

# Step 4: Follow up (within 30 min of step 1)
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000004', 'what about Target?'))
"
```

**Expected**: Step 4 understands this is a follow-up about transaction searches.

---

## Test 5: Per-User Isolation (FR-006)

**Goal**: Verify conversations are independent per phone number.

```bash
# Step 1: User A asks about recipes
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000005', 'find me a pasta recipe'))
"

# Step 2: User B asks about budget
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000006', 'what is our grocery budget?'))
"

# Step 3: User A follows up
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('+10000000005', 'tell me more about number 1'))
"
```

**Expected**: Step 3 references User A's pasta recipes, not User B's budget.

---

## Test 6: System Messages Excluded (FR-007)

**Goal**: Verify automated messages don't pollute user conversation history.

```bash
# Step 1: Send a system message (simulates daily briefing)
docker compose exec fastapi python3 -c "
from src.assistant import handle_message
print(handle_message('system', 'Generate daily plan for Erin'))
"

# Step 2: Check conversation file doesn't have 'system' entry
docker compose exec fastapi python3 -c "
import json
from pathlib import Path
data = json.loads(Path('/app/data/conversations.json').read_text())
print('system in conversations:', 'system' in data)
print('Keys:', list(data.keys()))
"
```

**Expected**: "system" is NOT in the conversations file.

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
