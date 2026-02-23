# Quickstart: AI-Powered Weekly Family Meeting Assistant

**Branch**: `001-ai-meeting-assistant` | **Date**: 2026-02-22 (v2 — expanded scope)

## Prerequisites

Before running the assistant, you need:

1. **Anthropic API key** — from console.anthropic.com
2. **Meta Developer App** — with WhatsApp product added (sandbox is fine for dev)
3. **Notion integration** — created at notion.so/my-integrations, shared with
   the five databases (Action Items, Meal Plans, Meetings, Backlog, Grocery History) and Family Profile page
4. **Google Calendar OAuth credentials** — from Google Cloud Console
   (calendar.events scope — read + write)
5. **YNAB Personal Access Token** — from YNAB Settings > Developer Settings
6. **Outlook ICS URL** — Jason publishes work calendar from outlook.office365.com
7. **AnyList credentials** — email/password for the shared AnyList account

## Scenario 1: Generate Weekly Agenda (US1 — P1)

**Setup**: All services connected, at least one Google Calendar event exists
this week, at least one action item from a prior session exists in Notion.

**Steps**:
1. Send message in WhatsApp group: "prepare this week's agenda"
2. Assistant receives message via webhook
3. Claude calls `get_calendar_events(days_ahead=7)` → fetches all 3 Google Calendars
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

## Scenario 2: Daily Morning Briefing (US5 — P2)

**Setup**: Routine templates defined in Family Profile, grandma schedule
communicated for this week, Jason's Outlook ICS URL configured.

**Steps** (automated via n8n at 7am):
1. n8n cron fires → `POST /api/v1/briefing/daily`
2. Assistant reads Erin's routine template from Family Profile
3. Assistant fetches Jason's Outlook calendar → identifies morning meeting blocks
4. Assistant fetches today's Google Calendar events (all 3 calendars)
5. Assistant checks grandma schedule → selects correct template (Zoey with Erin vs Grandma)
6. Assistant picks one backlog item to surface
7. Assistant writes time blocks to Erin's Google Calendar
8. Assistant sends daily plan to WhatsApp group

**Expected output** (WhatsApp, auto-sent at 7am):
```
*Good morning, Erin! ☀️ Here's your Tuesday:*

*👶 Zoey is with Grandma today (pickup at 3pm)*

*☕ Jason's morning:*
• Free 7-7:30am — breakfast window!
• 8-9:30am: Team standup + 1:1 (busy)
• Free after 9:30am

*📋 Your day:*
• 7:00-7:30  Make Jason breakfast 🍳
• 7:30-8:00  Get kids ready
• 9:00-9:30  Drop off Vienna
• 9:30-10:00 Drop off Zoey at Grandma's
• 10:00-11:30 Exercise / Gym 💪
• 11:30-12:30 Personal development (knitting) 🧶
• 12:30-1:00  Lunch
• 1:00-2:30  Side work / Backlog item
• 2:30-3:00  Pick up Vienna
• 3:00-3:30  Pick up Zoey

*📝 Today's backlog item:*
• Reorganize tupperware cabinet

*📅 Events today:*
• 4pm: Zoey swim class

All blocks are on your calendar! 📱
```

**Verify**: Daily plan reflects correct childcare situation, shows Jason's
meeting windows for breakfast timing, includes time blocks that appear in
Erin's Apple Calendar with push notifications.

## Scenario 3: Capture Action Items (US2 — P3)

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

## Scenario 4: Check Personal Tasks (US2 — P3)

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

## Scenario 5: Weekly Meal Plan (US3 — P4)

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

Want me to push this to AnyList for delivery?
```

## Scenario 6: Budget Check-In (US4 — P5)

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

## Scenario 7: Grocery List to AnyList (US6 — P6)

**Steps**:
1. After meal plan is generated, send: "order groceries" or say "yes" to the prompt
2. Claude calls `push_grocery_list()` → hits AnyList sidecar
3. Sidecar clears old items, pushes new grocery list to shared AnyList

**Expected output**:
```
*🛒 Grocery list sent to AnyList!*

12 items added to your Grocery list.

Open AnyList → tap "Order Pickup or Delivery" → select Whole Foods → review and check out.
```

**Verify**: Items appear in the AnyList app. Erin taps "Order Pickup or
Delivery" and sees items matched to Whole Foods products.

**Fallback** (if sidecar is down):
```
*Couldn't connect to AnyList right now. Here's your list by section:*

*🥩 Meat:*
□ Chicken breast
□ Ground turkey
□ Sausage links
□ Pot roast

*🥬 Produce:*
□ Stir-fry veggies
□ Side salad
□ Mixed veggies
□ Potatoes + carrots

*🧀 Dairy/Deli:*
□ Cheese + bread

*🥫 Pantry:*
□ Rice
□ Taco shells + toppings
□ Pasta + marinara
□ Tomato soup
□ Pizza dough + toppings
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
NOTION_BACKLOG_DB=mno345...
NOTION_FAMILY_PROFILE_PAGE=jkl012...
GOOGLE_CALENDAR_JASON_ID=jason@gmail.com
GOOGLE_CALENDAR_ERIN_ID=erin@gmail.com
GOOGLE_CALENDAR_FAMILY_ID=family123@group.calendar.google.com
OUTLOOK_CALENDAR_ICS_URL=https://outlook.office365.com/owa/calendar/...
YNAB_ACCESS_TOKEN=ynab-token-...
YNAB_BUDGET_ID=last-used
JASON_PHONE=15551234567
ERIN_PHONE=15559876543
ANYLIST_EMAIL=jason@example.com
ANYLIST_PASSWORD=...
```
