# Quickstart: AI-Powered Weekly Family Meeting Assistant

**Branch**: `001-ai-meeting-assistant` | **Date**: 2026-02-21

## Prerequisites

Before running the assistant, you need:

1. **Anthropic API key** — from console.anthropic.com
2. **Meta Developer App** — with WhatsApp product added (sandbox is fine for dev)
3. **Notion integration** — created at notion.so/my-integrations, shared with
   the four databases (Action Items, Meal Plans, Meetings) and Family Profile page
4. **Google Calendar OAuth credentials** — from Google Cloud Console
   (calendar.readonly scope)
5. **YNAB Personal Access Token** — from YNAB Settings > Developer Settings

## Scenario 1: Generate Weekly Agenda (P1 MVP)

**Setup**: All services connected, at least one Google Calendar event exists
this week, at least one action item from a prior session exists in Notion.

**Steps**:
1. Send message in WhatsApp group: "prepare this week's agenda"
2. Assistant receives message via webhook
3. Claude calls `get_calendar_events(days_ahead=7)` → fetches Google Calendar
4. Claude calls `get_action_items(status="Not Started")` → fetches open items from Notion
5. Claude calls `get_family_profile()` → reads recurring topics
6. Claude formats structured agenda and returns it
7. Assistant sends formatted agenda to WhatsApp group

**Expected output** (in WhatsApp):
```
*Weekly Agenda — Feb 23, 2026*

*📅 This Week*
• Mon: Vienna school pickup 3pm
• Wed: Dentist — Vienna
• Sat: Dinner at the Johnsons

*✅ Review Last Week*
• ⬜ Jason: Fix kitchen faucet (rolled over)
• ✅ Erin: Signed up Zoey for swim class

*🏠 Chores*
• [To be assigned during meeting]

*🍽 Meals*
• No meal plan yet — "plan meals" to create one

*💰 Finances*
• Ask me for "budget summary" during the meeting

*📌 Custom Topics*
• [None — "add topic: ..." to add one]
```

**Verify**: Agenda contains real calendar events, shows rolled-over action
items, and is formatted as a scannable checklist.

## Scenario 2: Capture Action Items (P2)

**Steps**:
1. Send: "Jason: grocery shopping, fix kitchen faucet. Erin: schedule dentist for Vienna"
2. Claude parses the natural language and calls `add_action_item()` for each
3. Assistant confirms in group chat

**Expected output**:
```
*Got it! Action items added:*

*Jason:*
• Grocery shopping
• Fix kitchen faucet

*Erin:*
• Schedule dentist for Vienna

All items added to this week's list.
```

**Verify**: Items appear in Notion Action Items database with correct
assignee, status "Not Started", and linked to this week's meeting.

## Scenario 3: Check Personal Tasks (P2)

**Steps**:
1. Jason sends: "what's on my list?"
2. Claude calls `get_action_items(assignee="Jason", status="Not Started")`
3. Returns Jason's items only

**Expected output**:
```
*Jason's tasks this week:*
• ⬜ Grocery shopping
• ⬜ Fix kitchen faucet

2 items remaining. Say "done with [task]" to check one off.
```

## Scenario 4: Weekly Meal Plan (P3)

**Steps**:
1. Send: "plan meals for this week"
2. Claude generates a 7-day plan (using family preferences from profile)
3. Claude calls `save_meal_plan()` to persist in Notion
4. Returns plan + grocery list

**Expected output**:
```
*Meal Plan — Week of Feb 23*

*Monday*: Chicken stir-fry with rice
*Tuesday*: Tacos (ground turkey, kid-friendly)
*Wednesday*: Pasta with marinara + side salad
*Thursday*: Sheet pan sausage & veggies
*Friday*: Pizza night (homemade or takeout)
*Saturday*: Grilled cheese + tomato soup
*Sunday*: Slow cooker pot roast

*🛒 Grocery List:*
□ Chicken breast
□ Stir-fry veggies
□ Rice
□ Ground turkey
□ Taco shells + toppings
□ Pasta + marinara
□ Sausage links
□ Mixed veggies
□ Pizza dough + toppings
□ Bread + cheese
□ Tomato soup
□ Pot roast + potatoes + carrots
```

## Scenario 5: Budget Check-In (P4)

**Steps**:
1. Send: "budget summary"
2. Claude calls `get_budget_summary(month="2026-02-01")`
3. Returns formatted summary

**Expected output**:
```
*Budget Summary — February 2026*

*⚠️ Over budget:*
• Dining Out: $280 / $200 (+$80)

*✅ On track:*
• Groceries: $420 / $600 ($180 left)
• Gas: $85 / $150 ($65 left)
• Entertainment: $45 / $100 ($55 left)

*🎯 Savings Goals:*
• Emergency Fund: 72% complete
• Summer Trip: $800 / $2,000

*Total spent this month:* $2,340 / $4,200 budgeted
```

## Environment Variables

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_ACCESS_TOKEN=EAAx...
WHATSAPP_VERIFY_TOKEN=my-custom-verify-token
NOTION_TOKEN=ntn_...
NOTION_ACTION_ITEMS_DB=abc123...
NOTION_MEAL_PLANS_DB=def456...
NOTION_MEETINGS_DB=ghi789...
NOTION_FAMILY_PROFILE_PAGE=jkl012...
GOOGLE_CALENDAR_ID=family123@group.calendar.google.com
YNAB_ACCESS_TOKEN=ynab-token-...
YNAB_BUDGET_ID=last-used
JASON_PHONE=15551234567
ERIN_PHONE=15559876543
```
