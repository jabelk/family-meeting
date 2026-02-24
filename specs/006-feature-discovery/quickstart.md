# Quickstart: Feature Discovery & Onboarding

## Prerequisites

- Existing family meeting assistant deployed (FastAPI + Docker Compose on NUC)
- WhatsApp bot working with existing tool loop
- All existing tools operational (recipes, budget, calendar, groceries, chores)

## Setup Steps

### Step 1: Add Help Tool

Add `get_help()` function to a new or existing tools module that generates the personalized help menu by fetching live data from existing tools.

### Step 2: Update System Prompt

Add feature discovery rules to the system prompt:
- Help trigger detection (respond to "help", "what can you do?", etc.)
- "Did you know?" tip instructions with trigger-context mapping
- Tip frequency limit (max 1 per response)

### Step 3: Add Welcome Logic

Add first-time user detection in the message handler. Track welcomed phones in memory. Prepend a brief welcome on first contact.

### Step 4: Register Tool

Add `get_help` tool definition to TOOLS array and TOOL_FUNCTIONS dict in assistant.py.

### Step 5: Deploy

```bash
git add . && git commit -m "feat: feature discovery and onboarding" && git push
./scripts/nuc.sh deploy
```

## Validation

### Test 1: Help Menu (US1)

1. Send "what can you do?" to the bot
2. Verify response contains 6 categories with icons and bold headers
3. Verify each category has at least 1 example phrase
4. Copy one example phrase and send it — verify the bot handles it correctly

### Test 2: Help Trigger Variations (US1)

1. Send "help" — verify help menu appears
2. Send "what are your features?" — verify help menu appears
3. Send "show me what you can do" — verify help menu appears

### Test 3: Help Doesn't Break State (US1)

1. Search for a Downshiftology recipe
2. Send "help" — verify help menu appears
3. Send "tell me more about number 1" — verify recipe details still work (search cache not cleared)

### Test 4: "Did You Know?" Tips (US2)

1. Ask "what's for dinner this week?" (triggers meal plan)
2. Verify a contextual tip is appended (e.g., about recipe search or grocery push)
3. Send another message in the same conversation
4. Verify no additional tip is appended to the second response

### Test 5: First-Time Welcome (US3)

1. Restart the container (clears in-memory welcome tracking)
2. Send a message from Erin's phone
3. Verify a brief welcome message is prepended to the response
4. Send another message from Erin
5. Verify no welcome message on the second message

### Test 6: Fallback Examples (Edge Case)

1. Verify help menu still works even if a personalization source is unavailable
2. Check that static examples are family-relevant ("Costco", "chicken dinner") not generic

## Troubleshooting

- **Help menu not appearing**: Check system prompt for help trigger rules. Verify tool is registered in TOOLS and TOOL_FUNCTIONS.
- **Tips appearing too often**: Check system prompt tip frequency instructions. Should be max 1 per response.
- **Welcome repeating after restart**: Expected behavior — in-memory tracking resets on container restart. Harmless for 2 users.
- **Personalized examples missing**: Check that underlying tools (list_cookbooks, get_staple_items) are working. Fallback to static examples should cover this.
