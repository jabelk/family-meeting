# Feature Specification: AI-Powered Weekly Family Meeting Assistant

**Feature Branch**: `001-ai-meeting-assistant`
**Created**: 2026-02-21
**Status**: Implementation In Progress — Paused for requirements review with both partners
**Input**: User description: "app architecture and feature planning — AI intelligence baked in, minimal custom code, leverage existing services"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Weekly Meeting Agenda Generation (Priority: P1)

Before the weekly family meeting (e.g., Sunday evening), either partner messages the assistant from their phone and asks it to prepare this week's agenda. The assistant gathers information from the family's connected services — upcoming calendar events, any pending action items from last week, and recurring topics — and produces a structured, scannable agenda organized by category (calendar/logistics, chores, meals, finances, goals). The agenda is delivered as a clean checklist that both partners can review on their phones.

**Why this priority**: The agenda is the core value proposition. Without it, there's no meeting structure. This single feature replaces the manual effort of remembering what to discuss and turns a chaotic conversation into an organized one.

**Independent Test**: Can be fully tested by sending a message to the assistant and receiving a well-structured agenda. Delivers immediate value even without any other features.

**Acceptance Scenarios**:

1. **Given** the assistant is set up and connected to Google Calendar, **When** a partner asks "prepare this week's agenda", **Then** the assistant returns a structured checklist agenda covering upcoming events, pending action items, and standard meeting categories within 30 seconds.
2. **Given** there were action items from last week's meeting, **When** the agenda is generated, **Then** last week's items appear in a "Review" section with their current status (done/not done).
3. **Given** a partner wants to add a custom topic, **When** they message "add topic: discuss summer trip planning", **Then** the item appears in the next generated agenda under a custom topics section.

---

### User Story 2 — Meeting Action Item Capture (Priority: P3)

During or after the family meeting, either partner messages the assistant with decisions and action items. The assistant parses natural language like "Jason will handle grocery shopping this week, Erin will schedule the dentist appointment for Vienna" and creates structured, assigned action items. Partners can check in during the week to see their tasks and mark them complete.

**Why this priority**: Capturing outcomes is what makes meetings productive rather than just talk. Without tracking action items, the same topics resurface week after week.

**Independent Test**: Can be tested by sending action items via message and later querying "what are my tasks this week?" to see a personalized checklist.

**Acceptance Scenarios**:

1. **Given** the meeting just ended, **When** a partner sends "Jason: grocery shopping, fix kitchen faucet. Erin: schedule Vienna dentist, sign up Zoey for swim class", **Then** the assistant confirms the parsed items and assigns them to the correct person.
2. **Given** action items exist for the week, **When** a partner asks "what's on my list?", **Then** the assistant returns only their assigned items as a checklist.
3. **Given** a partner completed a task, **When** they message "done with grocery shopping", **Then** the assistant marks it complete and confirms.

---

### User Story 3 — Weekly Meal Planning (Priority: P4)

A partner asks the assistant to help plan meals for the week. The assistant suggests a meal plan based on family preferences (two young kids, simple weeknight meals, variety) and produces a structured plan with a consolidated grocery list. Partners can adjust suggestions conversationally ("swap Tuesday for tacos") and the grocery list updates automatically.

**Why this priority**: Meal planning is a recurring weekly pain point that takes significant time. AI is well-suited to generate suggestions and manage the grocery list, but it's not blocking the core meeting workflow.

**Independent Test**: Can be tested by asking "plan meals for this week" and receiving a 7-day meal plan with grocery list. Works standalone without agenda or task features.

**Acceptance Scenarios**:

1. **Given** a partner asks "plan meals for this week", **Then** the assistant returns a 7-day meal plan formatted as a daily list with a consolidated grocery list at the bottom.
2. **Given** a meal plan exists, **When** a partner says "swap Wednesday dinner for pasta", **Then** the assistant updates the plan and adjusts the grocery list accordingly.
3. **Given** the family has dietary preferences or constraints on file, **When** meals are suggested, **Then** suggestions respect those constraints (e.g., kid-friendly, no shellfish).

---

### User Story 4 — Budget & Finance Check-In (Priority: P5)

During the weekly meeting, a partner asks the assistant for a quick financial summary. The assistant pulls data from YNAB and presents a digestible overview: how the family is tracking against budget categories, notable spending, and progress toward savings goals. No raw numbers dumps — just the highlights that matter for a 5-minute conversation.

**Why this priority**: Financial review is important but less frequent in urgency than agenda and task tracking. YNAB already has a good app; this feature adds value by summarizing it conversationally for the meeting context.

**Independent Test**: Can be tested by asking "how are we doing on budget this month?" and receiving a clear summary with category highlights.

**Acceptance Scenarios**:

1. **Given** YNAB is connected, **When** a partner asks "budget summary", **Then** the assistant returns a summary showing: categories over/under budget, total spent vs. budgeted, and savings goal progress.
2. **Given** a specific category is overspent, **When** the summary is generated, **Then** that category is flagged prominently at the top.
3. **Given** a partner asks "how much have we spent on dining out?", **Then** the assistant returns the specific category total and remaining budget.

---

### User Story 5 — Daily Planner & Morning Briefing (Priority: P2)

Each morning, Erin needs clarity on what her day looks like — especially because it changes depending on whether Zoey is with her or with Jason's mom. The assistant provides a daily overview that accounts for childcare, Jason's meeting schedule (so Erin knows whether to make breakfast), defined chore/responsibility blocks, personal development time, rest/out-of-house time, and any tasks due that day. The goal is to replace procrastination and ambiguity with a clear, doable plan that includes intentional rest.

**Why this priority**: This is Erin's primary pain point — feeling like she's always cleaning with no boundaries, procrastinating on leaving the house, and lacking daily structure. The weekly meeting is useful, but daily awareness is what changes the day-to-day experience. Elevated to P2 because it addresses the most pressing need.

**Independent Test**: Erin messages "what's my day look like?" and receives a structured daily plan that reflects who has Zoey, Jason's availability, her tasks, and blocked-out rest/growth time.

**Acceptance Scenarios**:

1. **Given** it's a weekday morning, **When** Erin asks "what's today's plan?", **Then** the assistant returns a structured daily schedule showing: childcare situation (Zoey with Erin or grandma), Jason's meeting windows (from his work calendar), chore/task block, personal development time, rest/out-of-house time, and any calendar events.
2. **Given** Jason has meetings from 8-10am, **When** the daily plan is generated, **Then** it notes that breakfast should be ready before 8am or after 10am (not during meetings), so Erin can plan without guessing.
3. **Given** Zoey is with grandma today, **When** the daily plan is generated, **Then** it reflects that Erin has more available time and suggests using it for backlog items, exercise, or out-of-house time.
4. **Given** Erin has a personal development task in her backlog (e.g., "reorganize tupperware", "knitting project"), **When** the daily plan is generated, **Then** one backlog item is suggested for today's development/growth block.
5. **Given** Erin does side work for her father's real estate development business, **When** she has work tasks, **Then** those appear in the daily plan alongside household responsibilities.
6. **Given** recurring activities (chores, gym, rest), **When** the daily plan includes them, **Then** the assistant assumes they get done — no check-in or texting required. These are just calendar blocks for structure.
7. **Given** one-off backlog items (e.g., "clean the garage", "reorganize tupperware"), **When** one is assigned for the day/week, **Then** the assistant follows up at the end of the week during the weekly meeting to ask if it was completed or should carry over.

---

### User Story 6 — Grocery List to Delivery (Priority: P6)

After a meal plan is generated, the grocery list should flow into a delivery order with minimal friction. Rather than copying items manually into Whole Foods or Instacart, the assistant bridges the gap — either by generating a tappable Instacart link with the items pre-loaded, or by pushing items to a shared AnyList that connects to Instacart/Whole Foods delivery. Erin taps one link in WhatsApp and reviews/checks out. Primary grocery source is Whole Foods.

**Why this priority**: Meal planning (P4) needs to work first. This is the last-mile convenience layer — nice to have but not blocking the core experience. Also dependent on third-party API access (Instacart is invite-only).

**Independent Test**: After a meal plan is generated, Erin receives a tappable link or notification that pre-populates a grocery cart at Whole Foods/Instacart. She reviews and checks out without manually searching for each item.

**Acceptance Scenarios**:

1. **Given** a meal plan with a grocery list has been generated, **When** Erin says "order groceries" or the assistant offers after meal planning, **Then** the assistant creates a pre-populated shopping list via Instacart or AnyList and sends a tappable link in WhatsApp.
2. **Given** the grocery list is sent to Instacart, **When** Erin taps the link, **Then** she sees items matched to Whole Foods products and can review/edit before checkout.
3. **Given** Instacart API is unavailable, **When** Erin asks to order groceries, **Then** the assistant falls back to sending a well-formatted grocery list organized by store section (produce, dairy, meat, pantry) for manual use.

**Decision**: Use AnyList ($12/year) as the grocery bridge. Push items from the meal plan grocery list to a shared AnyList via API. Erin taps "Order Pickup or Delivery" in the AnyList app → selects Whole Foods via Instacart → reviews and checks out.

---

### Edge Cases

- What happens when Google Calendar has no events for the upcoming week? The assistant generates an agenda with empty calendar section and a note ("No events scheduled — want to plan something?").
- What happens when YNAB API is temporarily unavailable? The assistant skips the finance section and notes it couldn't connect, rather than failing the entire agenda.
- What happens when a message is ambiguous (e.g., "done with dinner")? The assistant asks for clarification: "Did you mean you finished cooking, or should I mark a task complete?"
- What happens when both partners send conflicting action items? The assistant flags the conflict and asks which version to keep.
- What happens when the assistant is contacted outside meeting time? It responds normally — the assistant is available anytime, not just during meetings.
- What happens when Jason's work Outlook calendar can't be read? The assistant notes "Couldn't check Jason's work calendar — you may want to ask him about morning meetings" and still generates the rest of the daily plan.
- What happens when grandma's schedule changes last-minute? Either partner can tell the assistant "mom isn't taking Zoey today" and the daily plan adjusts.
- What happens when the backlog is empty? The assistant suggests adding items during the next weekly meeting or says "No backlog items — enjoy the free time!"
- What happens when the grocery delivery integration is unavailable? The assistant sends a well-formatted list organized by store section as a fallback.

## Clarifications

### Session 2026-02-21

- Q: WhatsApp conversation model — group chat vs individual DMs? → A: Shared family group chat (both partners + assistant in one chat)
- Q: What happens to incomplete action items at week's end? → A: Auto-rollover — incomplete items carry forward to next week's agenda automatically
- Q: Monthly cost comfort level for services? → A: ~$30–50/month baseline, flexible upward for paid services (Notion, task APIs, etc.) that reduce complexity and increase quality

### Session 2026-02-22 (with Erin)

- Erin's name corrected (was previously "Sarah" throughout)
- Erin's primary pain point: feels like she's always cleaning, no defined boundaries on chore time vs rest time
- Wants daily structure: chore block, rest/out-of-house time, personal development (knitting, home improvement projects), exercise, side work for father's real estate business
- Needs the assistant to know Jason's meeting schedule so she can plan breakfast timing
- Jason's breakfast: 1 scrambled egg, 2 bacon, high fiber tortilla, sriracha ketchup + Crystal hot sauce, Coke Zero or Diet Dr Pepper
- Childcare varies: Zoey is with Erin most days, Jason's mom watches Zoey 1-2 half days/week
- Vienna school drop-off: 9:30am M-F
- Erin wants a personal backlog of growth/home improvement tasks (reorganize tupperware, knitting, etc.) — reviewed weekly, one item surfaced daily
- New User Story 5 (Daily Planner) added at P2, bumping Action Items to P3, Meals to P4, Budget to P5
- Calendar setup: Jason has Google Calendar (personal) + Outlook (work, Cisco), plus a shared Google Calendar for family events
- Erin has her own Google Calendar (personal) + access to the shared family Google Calendar
- Erin uses Apple Calendar app on iPhone/MacBook Pro with Google Calendar synced in — she does NOT want to log into Notion
- Erin's primary interface is WhatsApp only — text the agent, it updates everything for her and tells her what's going on
- Decision: Option C — routine templates stored in Notion, assistant writes actual calendar blocks to Erin's Google Calendar weekly. Erin just sees her schedule in Apple Calendar with push notifications as reminders.
- The assistant needs Google Calendar WRITE access (not just read) to create time blocks for Erin
- AnyList chosen for grocery delivery bridge ($12/year) — Erin prefers it, connects to Instacart/Whole Foods
- Jason has a local NUC server running n8n (workflow automation) on home WiFi — can be used for scheduled tasks (weekly calendar population, daily briefing cron, recurring syncs) without additional cloud hosting costs
- Data backend decision deferred to planning phase. Options under consideration: Notion (current, code written), SQLite on NUC, Obsidian (markdown + git sync), Postgres on NUC, JSON in GitHub repo. Graphiti knowledge graph evaluated and ruled out (overkill for 2 users / 4 entities). Key criteria: "just works", minimal maintenance, Jason can browse data if needed, Erin never leaves WhatsApp.
- Grocery history: Jason can do a one-time export of past Whole Foods orders from Amazon order history. This data lives on the agent side (Notion "Grocery History" database) — not in AnyList. Claude uses it for smarter meal planning (suggesting meals based on what the family actually buys), accurate item naming (matching Whole Foods product names for better Instacart matching), and staple detection (auto-suggesting frequently purchased items).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept natural language messages from both partners via a conversational interface accessible on iPhone
- **FR-002**: System MUST connect to Google Calendars (shared family calendar, Jason's personal, Erin's personal) for both reading events AND writing time blocks (chore blocks, rest time, development time, etc.) to Erin's calendar. System MUST also read Jason's work Outlook calendar for meeting schedule awareness
- **FR-003**: System MUST use an AI service as the core intelligence layer for parsing messages, generating agendas, and producing meal plans — not custom NLP code
- **FR-004**: System MUST persist action items, meal plans, and meeting history between conversations
- **FR-005**: System MUST produce all output as structured checklists or categorized lists, never unformatted prose
- **FR-006**: System MUST support two named users (both partners) with individual task assignments
- **FR-007**: System MUST connect to YNAB API to read budget data for financial summaries
- **FR-008**: System MUST allow partners to add, complete, and review action items conversationally
- **FR-009**: System MUST generate meal plans with consolidated grocery lists
- **FR-010**: System MUST remember family context across sessions (kids' names, preferences, recurring patterns)
- **FR-011**: System MUST deliver responses within 30 seconds for standard requests
- **FR-012**: System MUST handle service outages (Calendar, YNAB) gracefully by skipping that section rather than failing entirely
- **FR-013**: System MUST use WhatsApp as the primary conversational interface via a shared family group chat (both partners + assistant), leveraging rich formatting (bold, lists, links)
- **FR-014**: System MUST generate daily plans that account for: childcare schedule (who has Zoey), Jason's meeting windows (from work + personal calendars), defined chore blocks, personal development/growth time, rest/out-of-house time, exercise, and any side work obligations
- **FR-015**: System MUST maintain a personal backlog of one-off tasks for Erin (e.g., clean the garage, reorganize tupperware, knitting projects) that gets reviewed and updated weekly. One item is surfaced daily. Backlog items require follow-up at the weekly meeting (done or carry over). Recurring activities (chores, gym, rest) are assumed done — no tracking or check-in needed, just calendar blocks for structure.
- **FR-016**: System MUST track recurring childcare schedule (Sandy Belk: Mon 9-12, Tue 10-1; future: Milestones preschool late Apr/May) and adapt daily plans based on who has Zoey that day
- **FR-017**: System MUST read Jason's work calendar (Outlook) to determine his meeting schedule so Erin can plan breakfast timing and know his availability
- **FR-018**: System MUST write daily time blocks (chores, rest, development, exercise, etc.) to Erin's Google Calendar so they appear as events in her Apple Calendar app with push notifications
- **FR-019**: System MUST be Erin's sole interface — she texts WhatsApp, the assistant handles everything (Notion updates, calendar writes, schedule lookups). She should never need to open Notion.
- **FR-020**: System MUST populate Erin's calendar weekly based on routine templates defined during the weekly meeting, and adjust blocks when context changes (e.g., "mom isn't taking Zoey today")
- **FR-021**: System MUST bridge the meal plan grocery list to AnyList ($12/year), which connects to Instacart/Whole Foods for delivery. Erin taps "Order" in AnyList app to review and check out.

### Key Entities

- **Meeting**: A weekly event with a date, generated agenda, and captured action items
- **Agenda**: A structured document with categorized sections (calendar, action item review, chores, meals, finances, goals, custom topics)
- **Action Item**: A task with an assignee (which partner), description, status (pending/complete), due context (this week / ongoing), and creation date. Incomplete items auto-rollover to the next week's agenda until explicitly completed or dropped.
- **Meal Plan**: A weekly plan with daily meals and a consolidated grocery list
- **Family Profile**: Persistent context — partner names, kids' names and ages, dietary preferences, recurring topics, linked service credentials, daily routines, and personal preferences
- **Daily Plan**: A structured daily schedule with time blocks for childcare, chores, personal development, rest, exercise, and side work — generated on demand based on that day's context
- **Backlog**: A running list of home improvement, personal growth, and project tasks that Erin works through at her own pace — reviewed and refreshed weekly

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A complete weekly meeting agenda can be generated in under 30 seconds from a single message
- **SC-002**: Both partners can access and interact with the assistant from their iPhones without any technical setup beyond initial onboarding
- **SC-003**: 90% of action items spoken in natural language are correctly parsed and assigned on the first try
- **SC-004**: Weekly meal plan generation with grocery list takes under 60 seconds
- **SC-005**: The system requires fewer than 100 lines of custom business logic — the AI service handles the intelligence; custom code is orchestration only
- **SC-006**: Both partners report that the weekly meeting feels more organized after 4 weeks of use
- **SC-007**: The assistant correctly identifies and flags at least 80% of incomplete action items from the previous week

### Constraints

- Monthly operating budget: ~$30–50/month baseline, flexible upward if paid services (e.g., Notion, purpose-built task/data management APIs) meaningfully reduce custom code complexity or increase quality
- Prefer subscribing to a managed service over building equivalent functionality

### Assumptions

- Both partners use iPhones and are comfortable with conversational messaging
- There are three Google Calendars: Jason's personal, Erin's personal, and a shared family calendar (both partners have access). All sync to Apple Calendar on Erin's iPhone/MacBook.
- Jason also has a work Outlook calendar (Cisco) that can be read for meeting schedules
- Google Calendar API will need WRITE access (not just readonly) to create time blocks on Erin's calendar
- Erin's only interface is WhatsApp — she does not log into Notion. Notion is the backend data store only, managed entirely through the assistant.
- Erin uses Apple Calendar app on iPhone and MacBook Pro as her calendar viewer
- YNAB is actively used and has current budget data
- The family is okay with AI services processing their calendar, task, and budget data
- Weekly meetings happen on a consistent day (assumed Sunday, configurable)
- The two children (ages 3 and 5) are not direct users of the system
- An always-on backend service is acceptable (cloud-hosted)
- Sandy Belk (Jason's mom) takes Zoey Monday 9-12 and Tuesday 10-1. This will shift to Milestones preschool late April/early May.
- Vienna's school drop-off is 9:30am M-F (Erin drops off, except Thursday — Jason drops off for BSF)
- Vienna's pickup varies: Tue 3:15 (gymnastics), Wed 3:45, other days 3:30
- Erin does occasional side work for her father's real estate development business
- Jason has a local Intel NUC server at home running n8n (workflow automation), accessible on home WiFi. This can be used for scheduled automations (e.g., weekly calendar population, daily briefing triggers, recurring syncs) without paying for cloud hosting of those workflows.
- AnyList ($12/year) is the chosen grocery bridge — connects to Instacart/Whole Foods for delivery

### Family Profile Details (to be stored in Notion)

**Jason:**
- Works from home at Cisco
- Has Google Calendar (personal) + Outlook (work)
- Breakfast preference: 1 scrambled egg, 2 bacon, high fiber tortilla, sriracha ketchup + Crystal hot sauce, Coke Zero or Diet Dr Pepper
- Thursday: does driving drop-off for Vienna (needs to be at BSF at Sparks Christian Fellowship by 10am)

**Erin:**
- Stays at home with the kids
- Drops off Vienna at school (Roy Gomm) at 9:30am M-F (except Thu — Jason drops off)
- Learning knitting (personal development)
- Does side work for her father's real estate development business
- Wants defined daily structure: chore time, rest/out-of-house time, personal development, exercise
- Wants to make Jason breakfast consistently
- Tends to procrastinate on getting out of the house — the assistant should help with this
- Laundry pain point: must be home for washer→dryer transfer; good time for dryer is 2:30 before Vienna pickup
- Wants scheduled blocks for vacuum, laundry, and cooking
- Likes meal prep but open to efficient daily cooking if the schedule works better

**Childcare:**
- Zoey (age 3): with Erin most days
- Sandy Belk (Jason's mom) takes Zoey: Monday 9am-12pm, Tuesday 10am-1pm
- Zoey will start Milestones preschool late April/early May (replaces Sandy's babysitting days)
- Vienna (age 5): kindergarten at Roy Gomm, M-F. Pickup varies: Tue 3:15 (gymnastics), Wed 3:45, other days 3:30

**Weekly Activities:**
- Tue: Zoey's gymnastics class (after 3:15 Vienna pickup)
- Fri: Nature class at Bartley Ranch Park 10:20-11:20 (March 4 – May 27)
- Sat: Vienna's ski lesson 9-11, leave house by 8am (~5 weeks, ending late March)
- Sun: Church 9-10, leave house by 8:15. Next 4 weeks: Erin's parents take kids after church until ~4pm → Jason & Erin attend marriage class

---

### Session 2026-02-22 (Erin schedule review)

- Sandy Belk (MIL) childcare schedule confirmed: Mon 9-12, Tue 10-1 (not "1-2 days varies")
- Vienna pickup times vary by day: Tue 3:15 (gymnastics), Wed 3:45, default 3:30
- Thursday: Jason does Vienna drop-off (BSF at Sparks Christian Fellowship by 10am)
- Nature class at Bartley Ranch Park Fri 10:20-11:20 (Mar 4–May 27)
- Vienna ski lesson Sat 9-11 (~5 weeks), leave house 8am
- Church Sun 9-10, leave 8:15. Erin's parents take kids after church til ~4pm for next 4 weeks → marriage class
- Zoey starts Milestones preschool late April/early May (replaces Sandy days)
- Erin needs laundry scheduling — must be home for washer→dryer transfer. Idea: dryer at 2:30 before pickup.
- Needs vacuum and cooking blocks scheduled
- Likes meal prep but open to efficient daily cooking
- Each day of the week is genuinely different — generic "with Zoey / with grandma" templates are insufficient
- Routine templates must be day-specific (Mon-Sun) to account for varying pickups, activities, and childcare

## Future User Stories (shaped by Erin's feedback)

### User Story 7 — Day-Specific Routine Templates (Priority: P2)

The current daily planner uses two generic templates ("Zoey with Erin" vs "Zoey with Grandma"), but Erin's actual week is far more varied. Each day has different pickup times, activities, and childcare arrangements. The assistant should use day-of-week-specific routine templates that account for these differences and generate plans that match reality.

**Acceptance Scenarios:**

1. **Given** it's Tuesday morning, **When** the daily plan is generated, **Then** it shows Sandy has Zoey 10-1, Vienna pickup at 3:15 (not 3:30), and Zoey's gymnastics after pickup.
2. **Given** it's Thursday morning, **When** the daily plan is generated, **Then** it shows Jason is doing Vienna drop-off (not Erin), and Erin's morning opens up earlier.
3. **Given** it's Friday during nature class season (Mar 4–May 27), **When** the daily plan is generated, **Then** it includes travel to Bartley Ranch Park by 10:00 and nature class 10:20-11:20.
4. **Given** it's Saturday during ski season, **When** the daily plan is generated, **Then** it shows "leave house by 8am" and ski lesson 9-11.
5. **Given** it's Sunday during the 4-week marriage class window, **When** the daily plan is generated, **Then** it shows church, grandparents taking kids, and marriage class — with no chore blocks scheduled (it's a free afternoon).

### User Story 8 — Intelligent Chore Scheduling (Priority: P2)

Erin struggles with knowing when to vacuum, do laundry, and cook. Laundry is especially tricky because she must be physically home for the washer-to-dryer transfer. The assistant should schedule chore blocks intelligently based on the day's constraints, not just drop in a generic "chore block."

**Acceptance Scenarios:**

1. **Given** it's a day where Erin is home all morning (e.g., Wed, Thu, Fri), **When** the daily plan is generated, **Then** it schedules "start laundry" in the morning chore block and "move to dryer" at ~2:30 before Vienna pickup.
2. **Given** it's Monday (Sandy has Zoey 9-12), **When** the daily plan is generated, **Then** it suggests vacuum during the kid-free morning window since vacuuming is easier without a toddler.
3. **Given** Erin has asked about meal prep vs daily cooking, **When** the weekly meal plan is generated, **Then** the assistant suggests which meals to prep on Sunday (during grandparent time) vs cook fresh on busy days, based on that week's schedule density.
4. **Given** a day has tight time blocks (e.g., Friday with nature class), **When** the daily plan is generated, **Then** chore blocks are shorter or deferred to a less packed day, with a note like "Light chore day — catch up tomorrow."

### User Story 9 — Seasonal & Temporary Schedule Management (Priority: P3)

The family has several time-limited recurring activities (ski lessons ~5 weeks, nature class Mar-May, marriage class 4 weeks). The assistant should track end dates and automatically remove activities from the template when they expire, without manual intervention.

**Acceptance Scenarios:**

1. **Given** Vienna's ski lessons end after ~5 weeks, **When** the end date passes, **Then** Saturday morning plans no longer include ski lessons and the assistant notes the freed-up time.
2. **Given** the marriage class runs for 4 Sundays, **When** the 4 weeks are over, **Then** Sunday afternoon plans revert to normal (kids come home after church, no marriage class block).
3. **Given** Zoey starts Milestones preschool in late April, **When** the transition happens, **Then** the Monday/Tuesday templates update from "Sandy has Zoey" to "Zoey at preschool" with the new drop-off/pickup times.
4. **Given** a seasonal activity is approaching its end, **When** the weekly meeting agenda is generated, **Then** it flags "Last week of ski lessons!" or "Nature class ends May 27" so the family can plan ahead.

## Future Enhancements (Backlog)

### YNAB Budget Write Operations
The YNAB API v1 supports write operations beyond the current read-only integration:
- **Recategorize transactions** — "Move that $45 charge to Restaurants"
- **Update category budgets** — "Budget $200 more for Groceries this month"
- **Create manual transactions** — "Add a $20 cash transaction for the farmers market"
- **Proactive suggestions** — Claude could flag uncategorized transactions and suggest categories

API supports: PATCH transactions (recategorize), PATCH category budgeted amounts, POST new transactions. Does NOT support creating/deleting categories or modifying goals.

Estimated scope: ~100 lines (3 new ynab.py functions + 3 tool definitions). See `memory/ynab-write.md` for full research.

---

## Implementation History

> **Note**: A v1 implementation was completed 2026-02-22 covering core FastAPI webhook, Claude assistant (12 tools), Notion/Calendar/YNAB integrations, and deployment configs. The scope was subsequently expanded with User Stories 5 (Daily Planner) and 6 (Grocery Delivery), plus Outlook ICS, Google Calendar write, AnyList integration, and n8n automations. A new v2 `tasks.md` (T001-T045) is now the source of truth for all remaining work. The v1 task IDs are retired.
