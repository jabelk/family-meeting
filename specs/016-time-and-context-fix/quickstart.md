# Quickstart: Time Awareness & Extended Conversation Context

**Feature**: 016-time-and-context-fix | **Date**: 2026-03-03

## Prerequisites

- Running FastAPI server (local or Docker)
- WhatsApp access or curl for testing

## Verification Scenarios

### Scenario 1: Time Injected in User Message

Verify that the current time appears in the user message content sent to Claude.

```bash
# Check server logs after sending a WhatsApp message
./scripts/nuc.sh logs fastapi 20

# Look for log output showing the user message includes a timestamp prefix like:
# "[Current time: Monday, March 3, 2026 at 12:30 PM Pacific]"
# before the actual message content
```

### Scenario 2: Time-Aware Schedule Generation

Send a WhatsApp message in the afternoon asking for a daily plan.

```
Message (sent at 2:00 PM): "plan my day"
```

**Expected**: Response starts from 2:00 PM onward. No morning activities (8 AM breakfast, 9 AM school drop-off, etc.) appear in the plan.

**Fail condition**: Any time block before the current time appears in the response.

### Scenario 3: Past-Time Reminder Detection

Send a WhatsApp message requesting a reminder for a time that has already passed.

```
Message (sent at 3:00 PM): "remind me today at 1:45 to call Banfield"
```

**Expected**: Bot recognizes 1:45 PM has passed and asks if Erin means tomorrow, or offers an alternative time.

**Fail condition**: Bot creates a calendar event for 1:45 PM today without comment.

### Scenario 4: Correct "Today" Resolution

Send a message and verify the bot uses the correct calendar date.

```
Message (sent at any time): "what do I have today?"
```

**Expected**: Bot shows today's actual calendar events, not yesterday's or tomorrow's.

### Scenario 5: Extended Context — Same-Day Recall

Send two messages with a gap, verify the bot remembers the first.

```
Message 1 (10:00 AM): "Let's do chicken tacos for dinner tonight"
Message 2 (4:00 PM): "What are we having for dinner?"
```

**Expected**: Bot recalls "chicken tacos" from the earlier message.

### Scenario 6: Extended Context — Multi-Day Recall

Send a message, wait a day, then reference it.

```
Day 1 message: "I need to call the dentist about Vienna's appointment"
Day 2 message: "Did I mention anything about a dentist call?"
```

**Expected**: Bot recalls the Day 1 message about calling the dentist.

**Previous behavior**: After 24 hours of inactivity, history was wiped. This should now work.

### Scenario 7: 7-Day Expiration

Verify that turns older than 7 days are pruned.

```python
# Manually check conversations.json after 7+ days
# Old turns should be removed on next access
import json
from pathlib import Path

data = json.loads(Path("data/conversations.json").read_text())
for phone, conv in data.items():
    print(f"{phone}: {len(conv['turns'])} turns, last_active: {conv['last_active']}")
    for i, turn in enumerate(conv['turns']):
        ts = turn.get('timestamp', 'no timestamp')
        print(f"  Turn {i}: {ts}")
```

### Scenario 8: Conversation Retention Constants

Verify the constants are updated correctly.

```python
from src import conversation
assert conversation.CONVERSATION_TIMEOUT == 604800, f"Expected 604800 (7 days), got {conversation.CONVERSATION_TIMEOUT}"
assert conversation.MAX_CONVERSATION_TURNS == 100, f"Expected 100, got {conversation.MAX_CONVERSATION_TURNS}"
print("Constants verified: 7-day timeout, 100-turn limit")
```
