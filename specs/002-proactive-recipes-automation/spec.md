# Feature Specification: Proactive Automations & Recipe Management

**Feature Branch**: `002-proactive-recipes-automation`
**Created**: 2026-02-22
**Status**: Draft
**Input**: Proactive scheduled automations (grocery reorder suggestions, daily briefing, meal plan generation, budget summaries, calendar conflict detection, action item reminders) via n8n workflows, plus recipe cookbook management where Erin can photograph physical cookbook pages, build a searchable recipe catalogue with OCR-extracted ingredients and instructions, and push ingredients directly to the grocery list.

## Context

Feature 001 (AI Meeting Assistant) delivered the core Mom Bot system: WhatsApp interface, 22 tools, Notion databases, Google Calendar read/write, YNAB, and AnyList grocery integration. All interactions are currently **reactive** — someone sends a message and gets a response.

This feature makes Mom Bot **proactive** — it reaches out with timely information and suggestions without being asked. It also adds **recipe management** — the most-requested new capability from Erin, who wants to digitize her physical cookbooks and connect them to meal planning and grocery ordering.

### What Exists Today
- 3 n8n endpoint stubs in FastAPI (daily briefing, weekly calendar population, grandma schedule prompt) — defined but not wired to n8n workflows
- Grocery History database with 1,348 items across 3 stores, including reorder intervals for 56 staples and 200 regular items
- AnyList integration for pushing grocery lists to Whole Foods delivery
- Full Google Calendar read/write across 3 calendars + Outlook ICS read
- YNAB budget read access
- Action Items and Backlog databases with status tracking
- n8n already running on the NUC (separate Docker container, port 5678)

### Architecture Decision: Dedicated n8n Instance
Jason runs n8n on the NUC for other projects. Mom Bot will use its own n8n instance to keep workflows isolated. This means a second n8n container in the Mom Bot docker-compose stack on a different port.

## User Scenarios & Testing *(mandatory)*

### US1 — Recipe Cookbook Catalogue (Priority: P1)

Erin has several physical cookbooks (keto, general family meals, etc.) and wants to build a personal digital recipe collection. She takes a photo of a cookbook page with her iPhone and sends it directly in the WhatsApp chat. Mom Bot receives the image via the Meta Cloud API webhook, downloads it, uses Claude vision to extract the recipe — name, ingredients, instructions, servings, prep time — and saves it to a searchable catalogue. Each recipe is linked to its source cookbook. Later, she can say "I want the steak dish from the keto book" and Mom Bot finds it, shows the recipe, and offers to add the ingredients to her grocery list.

**Why this priority**: This is the biggest new capability Erin specifically asked for. It creates lasting value — every recipe she photographs builds her personal collection. It also directly feeds into meal planning and grocery ordering (US3), making the whole system more useful over time.

**Independent Test**: Erin photographs one cookbook page, sends it via WhatsApp, and the recipe appears in her Notion recipe catalogue with correct ingredients, instructions, and cookbook attribution. She can then ask for it by name or description and get the recipe back with an option to add ingredients to AnyList.

**Acceptance Scenarios**:

1. **Given** Erin sends a photo of a cookbook page with "save this recipe", **When** Mom Bot processes the image, **Then** it extracts the recipe name, ingredients list (with quantities), instructions, prep/cook time, and servings, saves it to the recipe catalogue linked to the cookbook name, and confirms with a summary.
2. **Given** a recipe has been saved from "The Keto Cookbook", **When** Erin says "what was that steak recipe from the keto book?", **Then** Mom Bot searches the catalogue, finds the matching recipe, and displays the ingredients and key instructions.
3. **Given** Erin is viewing a recipe, **When** she says "add those ingredients to the grocery list", **Then** Mom Bot cross-references ingredients against what she already has (grocery history staples recently ordered) and pushes only the needed items to AnyList.
4. **Given** Erin sends a photo but the image is blurry or partially cut off, **When** Mom Bot processes it, **Then** it extracts what it can, flags unclear portions with "[unclear]" markers, and asks Erin to confirm or re-photograph.
5. **Given** a recipe is already saved with the same name from the same cookbook, **When** Erin sends another photo of it, **Then** Mom Bot recognizes the duplicate and asks whether to update the existing recipe or save as a new version.

---

### US2 — Proactive Grocery Reorder Suggestions (Priority: P2)

Every week (Saturday morning), Mom Bot checks the Grocery History database for staple and regular items that are due for reorder based on their average purchase interval. It sends a WhatsApp message grouped by store (Whole Foods, Costco, Raley's) with the items that are due or overdue. Erin can approve, modify, or dismiss the list, and confirmed items get pushed to AnyList.

**Why this priority**: The grocery history data (56 staples, 200 regular items with reorder intervals) is already in Notion — this feature activates that data. It saves Erin the mental load of tracking what's running low and reduces forgotten-item trips.

**Independent Test**: On Saturday morning, the system sends a WhatsApp message listing staple items due for reorder (based on days since last ordered vs average reorder interval), grouped by store. Erin replies "add the Whole Foods ones" and those items appear in AnyList.

**Acceptance Scenarios**:

1. **Given** it is Saturday morning and organic spinach was last ordered 35 days ago (avg reorder: 30 days), **When** the reorder check runs, **Then** organic spinach appears in the "Whole Foods — due this week" section of the message.
2. **Given** the reorder suggestion lists 8 items across 2 stores, **When** Erin replies "add all except the bacon", **Then** 7 items are pushed to AnyList and the message confirms what was added.
3. **Given** Erin replies "we still have spinach, skip it", **When** the system processes her response, **Then** spinach is excluded from the current list (but will appear again next week if still due).
4. **Given** no staple items are currently due for reorder, **When** the Saturday check runs, **Then** no message is sent (don't send empty/unnecessary notifications).

---

### US3 — Smart Meal Plan with Auto Grocery List (Priority: P3)

Saturday morning, Mom Bot sends a single combined message: a weekly dinner plan (6 nights, since the family eats out ~1 night) plus a merged grocery list that includes both reorder staples that are due and meal-specific ingredients. The meal plan accounts for dietary preferences, schedule density (busy days get simpler meals), saved recipes, and recent plans (avoid repetition). The grocery list deducts items likely already in stock. Erin reviews, adjusts, and approves — then the grocery list goes to AnyList.

**Why this priority**: Builds on the recipe catalogue (US1) and grocery data. Meal planning is one of Erin's weekly pain points. Combining AI-suggested meals with automatic grocery ordering removes significant mental overhead.

**Independent Test**: Saturday morning, Mom Bot sends a 6-night dinner plan with estimated grocery list. Erin adjusts 2 meals and approves. The final grocery list lands in AnyList.

**Acceptance Scenarios**:

1. **Given** it is Saturday and the family has 3 saved recipes and a grocery history, **When** the meal plan generator runs, **Then** it suggests 6 nights of dinners that are kid-friendly, avoids duplicating the previous 2 weeks' plans, and considers schedule density (e.g., simpler meals on Tuesday when Erin has gymnastics pickup).
2. **Given** the meal plan includes "Chicken Parmesan" from the recipe catalogue, **When** the grocery list is generated, **Then** the ingredients come from the saved recipe with correct quantities, and items recently ordered (like organic spinach bought 3 days ago) are excluded.
3. **Given** Erin says "swap Wednesday for tacos", **When** Mom Bot adjusts the plan, **Then** the grocery list updates accordingly — taco ingredients added, removed pasta ingredients.
4. **Given** Erin approves the final plan, **When** she says "send to AnyList", **Then** items are split by preferred store (using grocery history store data) and pushed to AnyList.

---

### US4 — n8n Scheduled Workflows (Priority: P4)

Wire up the existing FastAPI endpoint stubs to actual n8n scheduled workflows in a dedicated Mom Bot n8n instance. This includes the daily morning briefing (7am M-F), weekly calendar population (Sunday 7pm), grandma schedule prompt (Monday 9am), Saturday meal & grocery planner (Saturday 9am — combines reorder suggestions + meal plan into one message), budget summary (Sunday 5pm), mid-week action item check-in (Wednesday noon), and calendar conflict detection (Sunday 7:30pm + daily).

**Why this priority**: This is the infrastructure that makes US2, US3, and the daily briefing proactive. Without n8n cron triggers, all features remain reactive. However, each automation endpoint can be tested manually first — n8n just adds the scheduling.

**Independent Test**: Create one n8n workflow (daily briefing) that fires at 7am and sends Erin her morning plan via WhatsApp. Verify it runs automatically for 3 consecutive days.

**Acceptance Scenarios**:

1. **Given** the Mom Bot n8n instance is running, **When** it is 7:00 AM on a weekday, **Then** the daily briefing workflow fires, hits the FastAPI endpoint, and Erin receives her morning plan in WhatsApp.
2. **Given** a workflow fails (e.g., FastAPI is down), **When** n8n detects the failure, **Then** it retries once after 5 minutes and logs the error (no silent failures).
3. **Given** all 8 scheduled workflows are configured, **When** a full week passes, **Then** each workflow has fired at its expected time and produced the expected output.

---

### US5 — Calendar Conflict Detection (Priority: P5)

As part of the weekly calendar population (Sunday evening) and daily briefing (weekday mornings), Mom Bot checks all 4 calendars (Jason personal, Jason work/Outlook, Erin personal, Family shared) for time conflicts. It identifies hard conflicts (overlapping events) and soft conflicts (e.g., Jason has a work meeting during his usual Thursday Vienna drop-off). Conflicts are reported in WhatsApp with suggested resolutions.

**Why this priority**: With 4 calendars and varying daily schedules, conflicts are common but easy to miss. This prevents last-minute scrambles ("who's picking up Vienna?").

**Independent Test**: Create a test calendar event that overlaps with Vienna's pickup time on Tuesday. The daily briefing flags the conflict and suggests Erin cover pickup.

**Acceptance Scenarios**:

1. **Given** Jason has a 2:30-3:30 work meeting on Tuesday (Vienna pickup is 3:15), **When** the daily briefing runs Tuesday morning, **Then** it flags "Jason's meeting conflicts with Vienna's 3:15 pickup — Erin, can you cover?"
2. **Given** no calendar conflicts exist for the day, **When** the briefing runs, **Then** no conflict section appears (don't clutter with "no conflicts found").
3. **Given** a conflict is detected on Sunday's weekly scan, **When** the conflict report is sent, **Then** it includes all conflicts for the coming week with day and time, affected people, and suggested resolution.

---

### US6 — Mid-Week Action Item Reminders (Priority: P6)

On Wednesday at noon, Mom Bot checks Notion Action Items for tasks assigned "This Week" that haven't been started, and tasks that were rolled over from previous weeks. It sends a brief, non-naggy mid-week check-in to WhatsApp showing progress and flagging at-risk items.

**Why this priority**: Prevents the "same items every week" problem. A single mid-week nudge is enough to catch items falling through the cracks without being annoying.

**Independent Test**: Create 4 action items for "This Week" (2 done, 2 not started), and verify the Wednesday check-in correctly reports progress and flags the 2 incomplete items.

**Acceptance Scenarios**:

1. **Given** 6 action items are assigned for this week and 3 are done, **When** Wednesday noon arrives, **Then** the check-in shows "3 of 6 items done" with the 3 remaining items listed by assignee.
2. **Given** an action item has been rolled over twice, **When** it appears in the check-in, **Then** it is flagged as high priority ("rolled over 2x — still relevant?").
3. **Given** all action items are complete, **When** Wednesday noon arrives, **Then** no message is sent (or a brief "all caught up!" if there were items earlier in the week).

---

### US7 — Weekly Budget Summary (Priority: P7)

Sunday afternoon before the family meeting, Mom Bot pulls the YNAB budget data and sends a concise spending summary to WhatsApp. It highlights categories that are over budget, tracks week-over-week trends, and flags notable spending. This becomes a natural discussion point during the weekly meeting.

**Why this priority**: The YNAB integration already exists (read-only). This just activates it on a schedule. Lower priority because YNAB has its own good app — the value is in the proactive delivery and meeting context.

**Independent Test**: On Sunday at 5pm, the budget summary arrives in WhatsApp showing over/under budget categories and total spending.

**Acceptance Scenarios**:

1. **Given** the Dining Out category is $30 over budget, **When** the Sunday summary runs, **Then** it appears in the "Over Budget" section with the amount and percentage.
2. **Given** no categories are over budget, **When** the summary runs, **Then** it shows a brief "all on track" message with total spent vs total budget.

---

### Edge Cases

- What happens when Erin sends a recipe photo but it's not a recipe (e.g., a photo of the kids)? Mom Bot should recognize it's not a recipe and respond helpfully ("That doesn't look like a recipe — did you mean to save a recipe?").
- What happens when a cookbook page has two recipes on it? Mom Bot should extract both and ask which one(s) to save.
- What happens when the WhatsApp 24-hour messaging window has expired? Proactive messages use pre-approved Meta template messages as fallbacks. Daily briefing interaction typically keeps the window open.
- What happens when n8n fires a workflow but FastAPI is temporarily down? n8n retries once after 5 minutes. If still failing, logs the error without spamming the family chat.
- What happens when the grocery reorder check has no items due? No message is sent — avoid unnecessary notifications.
- What happens when Erin asks for a recipe but the search is ambiguous (e.g., "the chicken one")? Mom Bot shows the top 3 matches and asks her to pick.
- What happens when a recipe ingredient doesn't match any known grocery item? Mom Bot adds it to AnyList as-is with the recipe's quantity (e.g., "2 cups arborio rice").
- What happens when a meal plan meal comes from a saved recipe vs a general suggestion? Saved recipes use exact ingredients; general suggestions use Claude's knowledge of typical ingredient lists.
- What happens when Erin pushes groceries to AnyList but never confirms the order? After 2 days, Mom Bot asks "Did you end up ordering those groceries? Want me to update the list?" If no reply, Last Ordered stays unchanged and the items will appear as due again next week.

## Requirements *(mandatory)*

### Functional Requirements

**Recipe Management**
- **FR-001**: System MUST extract recipe name, ingredients (with quantities and units), instructions, prep time, cook time, servings, and source cookbook from a photograph of a cookbook page.
- **FR-002**: System MUST store recipes in a searchable catalogue with the original photo uploaded to cloud storage (e.g., Cloudflare R2) and linked from the recipe entry for visual reference.
- **FR-003**: System MUST support natural language recipe search — by name, ingredient, cookbook, cuisine type, or description ("the steak dish from the keto book").
- **FR-004**: System MUST generate a grocery list from a recipe's ingredients, cross-referencing against recently ordered items to avoid duplicates.
- **FR-005**: System MUST link each recipe to its source cookbook and support browsing by cookbook ("show me all recipes from the keto book").
- **FR-006**: System MUST handle imperfect photos — partial text, angled shots, handwritten notes — by extracting what it can and flagging uncertain portions.

**Proactive Grocery**
- **FR-007**: System MUST check grocery staple and regular items against their average reorder intervals and identify items due for repurchase.
- **FR-008**: System MUST group reorder suggestions by store (Whole Foods, Costco, Raley's) based on historical purchase data.
- **FR-009**: System MUST allow users to approve, modify, or dismiss reorder suggestions via WhatsApp reply.
- **FR-010**: System MUST push confirmed grocery items to AnyList, organized by store section.
- **FR-010a**: System MUST update "Last Ordered" dates in Grocery History when Erin confirms an order was placed (e.g., "groceries ordered"). If no confirmation arrives within 2 days of an AnyList push, system MUST send a gentle reminder asking if the order went through.

**Meal Planning**
- **FR-011**: System MUST generate a weekly dinner plan (6 nights, accounting for ~1 eat-out night per week) that considers family dietary preferences, schedule density per day, saved recipes, and ingredient overlap.
- **FR-012**: System MUST avoid repeating meals from the previous 2 weeks of meal plans.
- **FR-013**: System MUST produce a consolidated grocery list from the meal plan, deducting items likely already in stock.
- **FR-014**: System MUST allow users to swap individual meals and have the grocery list update accordingly.

**Scheduled Workflows**
- **FR-015**: System MUST run scheduled workflows via a dedicated n8n instance isolated from other projects on the same server.
- **FR-016**: System MUST support at least 7 scheduled workflows running concurrently without interference (daily briefing, weekly calendar, grandma prompt, Saturday meal+grocery, budget summary, mid-week check-in, conflict detection).
- **FR-017**: System MUST retry failed workflow executions once before logging the failure.
- **FR-018**: System MUST respect the WhatsApp 24-hour messaging window by using pre-approved template messages when the window has expired.

**Calendar & Reminders**
- **FR-019**: System MUST detect time conflicts across all 4 calendars (3 Google + 1 Outlook) and report them with suggested resolutions.
- **FR-020**: System MUST detect "soft conflicts" where a calendar event overlaps with a family routine (e.g., work meeting during pickup time).
- **FR-021**: System MUST send mid-week action item check-ins that show progress and flag rolled-over items.

**Budget**
- **FR-022**: System MUST deliver a weekly budget summary highlighting over-budget categories and spending trends.

### Key Entities

- **Recipe**: Name, ingredients (list of name + quantity + unit), instructions (ordered steps), prep time, cook time, servings, source cookbook, photo reference, date added, tags/cuisine type.
- **Cookbook**: Name (e.g., "The Keto Cookbook", "Erin's Family Meals"), description, recipe count. Assigned by Erin when saving recipes.
- **Reorder Suggestion**: Generated weekly from Grocery History items where days-since-last-order exceeds the average reorder interval. Grouped by store. Ephemeral — not persisted, generated fresh each week.
- **Scheduled Workflow**: Name, cron schedule, target endpoint, retry policy, last run status, last run time.

### Key Constraints

- WhatsApp image messages have a 16MB limit (sufficient for cookbook photos).
- WhatsApp proactive messages outside the 24-hour window require pre-approved Meta template messages.
- Claude vision (image analysis) is used for recipe extraction — no separate OCR service needed.
- The dedicated n8n instance must run on a different port than the existing n8n (5678).
- Notion free plan: unlimited blocks but 5MB file upload limit per file. Recipe photos are stored in cloud storage (Cloudflare R2 free tier) and linked from Notion, avoiding the size limit entirely.
- AnyList has no "by store" concept — items are added to a single list. Store grouping is informational for the user, not pushed to AnyList.

### Assumptions

- Erin will photograph one recipe per image (if two recipes appear on one page, she sends the full page and specifies which one, or Mom Bot extracts both).
- Cookbook names are provided by Erin when saving recipes (e.g., "save this from the keto book"). If no cookbook is specified, it's saved under "Uncategorized".
- The daily briefing interaction (7am) keeps the WhatsApp 24-hour window open for all subsequent proactive messages that day. For Saturday/Sunday messages, Friday's interaction or a template message is used.
- Recipe photos are taken with an iPhone in reasonable lighting — no need to handle extremely degraded images.
- YNAB budget data is refreshed by the YNAB app (not by Mom Bot) — the system reads the current state.
- The grocery reorder check uses the `Last Ordered` date from the Grocery History database, which is updated when new receipts are imported (manual process for now).

### Family Profile Details

- **Erin's cookbooks**: Multiple physical cookbooks including at least one keto-focused book and general family meal books. Exact titles to be captured as she photographs recipes.
- **Dietary preferences**: Kid-friendly dinners for Vienna (5) and Zoey (3). Erin is interested in keto/healthy options. Jason's breakfast is fixed (1 scrambled egg, 2 bacon, high-fiber tortilla, hot sauce, Coke Zero). Jason buys lunch from a local restaurant. Erin meal preps kid lunches separately.
- **Eating out**: Family eats out ~1 night per week (dinner plan covers 6 nights).
- **Shopping patterns**: Primarily Whole Foods (delivery via AnyList), Costco (in-store, bulk), Raley's (local pickup). Whole Foods is the main weekly shop; Costco every 2-3 weeks.
- **Schedule density**: Monday and Tuesday mornings are the lightest (grandma has Zoey). Wednesday-Friday Erin has both kids. Weekends are activity-heavy (ski, church).

## Clarifications

### Session 2026-02-22

- Q: Where should recipe photos be stored given Notion's 5MB upload limit? → A: Upload to a free cloud storage service (e.g., Cloudflare R2 free tier) and link from Notion. Preserves full-quality originals with no size constraints.
- Q: What meals does the 7-day meal plan cover? → A: Dinner only (6 nights — they eat out ~1 night/week). Jason buys lunch from a local restaurant. Erin meal preps kid lunches separately and will provide her own options for that. Weekend breakfasts are flexible but not planned by the system.
- Q: Should the recipe catalogue support online recipe URLs in addition to cookbook photos? → A: Photos only for this feature. URL-based recipe import noted as a future enhancement.
- Q: Should Saturday's grocery reorder and meal plan be separate messages or combined? → A: Combined into one Saturday morning message — meal plan + merged grocery list that includes both reorder staples and meal-specific ingredients.
- Q: How should "Last Ordered" dates stay fresh for reorder accuracy? → A: Update when Erin confirms "groceries ordered" after AnyList push. If no confirmation within ~2 days of pushing to AnyList, send a gentle reminder to confirm the order was placed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Erin can photograph a cookbook page and have the complete recipe saved to her catalogue in under 60 seconds (from sending the photo to receiving confirmation).
- **SC-002**: Erin can find any saved recipe by name, ingredient, or cookbook within one conversational exchange ("the steak from the keto book" returns the right recipe).
- **SC-003**: Weekly grocery reorder suggestions correctly identify 80%+ of items that are actually needed (measured by Erin's acceptance rate over 4 weeks).
- **SC-004**: Meal plan suggestions require fewer than 3 adjustments on average before Erin approves (measured over 4 weeks).
- **SC-005**: All scheduled workflows run at their expected times with 95%+ reliability over a 30-day period.
- **SC-006**: Calendar conflicts are detected and reported before they cause a scheduling problem (zero missed pickups or double-bookings due to undetected conflicts).
- **SC-007**: The recipe catalogue grows to 20+ recipes within the first month of use (indicating Erin finds value in the feature).
- **SC-008**: Time spent on weekly meal planning + grocery ordering is reduced by at least 50% compared to the manual process (self-reported by Erin).

## Future Enhancements

- **URL-based recipe import**: Send a recipe URL in WhatsApp and have the system scrape and extract the recipe (same catalogue, different input method).
- **Automatic receipt import**: Detect new Whole Foods/Costco/Raley's order emails and auto-import receipts without manual PDF download.
- **Kid lunch meal prep planning**: Erin provides her meal prep rotation; system tracks which preps were done recently and suggests the next one.
- **Restaurant night suggestions**: Based on budget remaining and family preferences, suggest where to eat out on the weekly restaurant night.
