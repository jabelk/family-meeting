# Notion Setup Guide

This guide walks through setting up Notion for the Family Meeting Assistant from scratch.

## Step 1: Create Your Notion Account

1. Go to [notion.so/signup](https://www.notion.so/signup)
2. Click **"Continue with Google"** and sign in with your Gmail
3. Follow the prompts to create your workspace (name it something like "Jabel Family")

**Important**: Only YOU (Jason) need to be a workspace **member**. Erin gets invited as a **guest** on the shared pages. This keeps you on the free plan with **unlimited blocks**. Adding Erin as a full member would cap the workspace at 1,000 blocks total.

## Step 2: Create the Integration (API Access)

The bot needs an API token to read/write your Notion databases.

1. Go to [notion.so/profile/integrations](https://www.notion.so/profile/integrations)
2. Click **"+ New integration"**
3. Fill in:
   - **Name**: `Family Meeting Bot`
   - **Workspace**: Select your workspace
   - Leave **Type** as "Internal"
4. Click **Submit**
5. On the next page, copy the **Internal Integration Secret** (starts with `ntn_`)
6. Paste it into your `.env` file as `NOTION_TOKEN`

## Step 3: Create the Databases

You need to create 5 databases and 1 page. Create them all at the top level of your workspace.

### Database 1: Action Items

1. In the sidebar, click **"+ New page"**
2. Select **"Database"** (full page, table view)
3. Title it **"Action Items"**
4. Set up these properties (click "+" to add columns):

| Property | Type | Configuration |
|---|---|---|
| Description | Title | (default, already exists) |
| Assignee | Select | Options: `Jason`, `Erin`, `Both` |
| Status | Status | Groups: `Not Started`, `In Progress`, `Done` |
| Due Context | Select | Options: `This Week`, `Ongoing`, `Someday`, `Custom Topic` |
| Created | Date | (no special config) |
| Meeting | Relation | Connect to → Meetings database (create this after Step 3.3) |
| Rolled Over | Checkbox | (no special config) |

### Database 2: Meal Plans

1. Click **"+ New page"** → **"Database"** (full page, table view)
2. Title it **"Meal Plans"**
3. Properties:

| Property | Type | Configuration |
|---|---|---|
| Week Of | Title | (default) |
| Start Date | Date | (no special config) |
| Status | Select | Options: `Draft`, `Active`, `Archived` |

### Database 3: Meetings

1. Click **"+ New page"** → **"Database"** (full page, table view)
2. Title it **"Meetings"**
3. Properties:

| Property | Type | Configuration |
|---|---|---|
| Date | Title | (default) |
| When | Date | (no special config) |
| Status | Select | Options: `Planned`, `In Progress`, `Complete` |

4. **Now go back to Action Items** and add the **Meeting** relation property pointing to this Meetings database.

### Database 4: Backlog

1. Click **"+ New page"** → **"Database"** (full page, table view)
2. Title it **"Backlog"**
3. Properties:

| Property | Type | Configuration |
|---|---|---|
| Description | Title | (default) |
| Category | Select | Options: `Home Improvement`, `Personal Growth`, `Side Work`, `Exercise`, `Other` |
| Assignee | Select | Options: `Jason`, `Erin` |
| Status | Status | Groups: `Not Started`, `In Progress`, `Done` |
| Priority | Select | Options: `High`, `Medium`, `Low` |
| Created | Date | (no special config) |
| Last Surfaced | Date | (no special config — updated by the assistant when suggesting items) |

### Database 5: Grocery History

1. Click **"+ New page"** → **"Database"** (full page, table view)
2. Title it **"Grocery History"**
3. Properties:

| Property | Type | Configuration |
|---|---|---|
| Item Name | Title | (default) |
| Category | Select | Options: `Produce`, `Meat`, `Dairy`, `Pantry`, `Frozen`, `Bakery`, `Beverages`, `Other` |
| Frequency | Number | Number format: Integer |
| Last Ordered | Date | (no special config) |
| Avg Reorder Days | Number | Number format: Number (average days between orders) |
| Avg Price | Number | Number format: Dollar (average price across orders) |
| Store | Multi-select | Options: `Whole Foods`, `Costco`, `Raley's` (tracks where you buy each item) |
| Staple | Checkbox | (items the family buys regularly — 50%+ of orders) |

**Tip**: You can populate this database from your order history using the import script:
```
python -m scripts.import_grocery_history receipt1.pdf receipt2.pdf
python -m scripts.import_grocery_history data/receipts/    # all PDFs in dir
python -m scripts.import_grocery_history --clear data/receipts/  # wipe DB first
```
Supports PDF receipts from Amazon/Whole Foods, Costco, and Raley's. Claude extracts items (decoding store abbreviations), then normalizes names across stores so the same product bought at different stores merges into one entry. Tracks reorder frequency and average prices.

### Page: Family Profile

1. Click **"+ New page"** (regular page, NOT a database)
2. Title it **"Family Profile"**
3. Add this content (copy/paste, then format the headings):

```
## Members
- Jason (partner, father, husband) — works from home at Cisco
- Erin (partner, wife, mother) — stays at home with the kids
- Vienna (daughter, age 5) — kindergarten at Roy Gomm
- Zoey (daughter, age 3)

## Preferences
- Kid-friendly meals preferred

## Recurring Agenda Topics
- Calendar review (upcoming week)
- Action item review (from last week)
- Chore assignments
- Meal planning
- Budget check-in
- Goals and long-term items

## Childcare Schedule
- Sandy Belk (Jason's mom) takes Zoey: Monday 9am-12pm, Tuesday 10am-1pm
- Zoey starts Milestones preschool late April/early May (replaces Sandy days)
- Vienna: kindergarten at Roy Gomm, M-F, 9:30am drop-off (pickup varies by day)

## Weekly Schedule Notes
- Mon: Sandy has Zoey 9-12. Vienna pickup 3:30.
- Tue: Sandy has Zoey 10-1. Vienna pickup 3:15 (early — Zoey's gymnastics).
- Wed: Zoey with Erin. Vienna pickup 3:45.
- Thu: Jason drops off Vienna (BSF at Sparks Christian Fellowship by 10am). Zoey with Erin. Vienna pickup 3:30.
- Fri: Nature class at Bartley Ranch Park 10:20-11:20 (Mar 4–May 27). Vienna pickup 3:30.
- Sat: Leave house 8am → Vienna ski lesson 9-11 (~5 weeks ending late Mar).
- Sun: Leave house 8:15 → church 9-10. Next 4 weeks: grandparents take kids until ~4pm, Jason & Erin attend marriage class.

## Chore Notes
- Laundry: must be home for washer→dryer. Start wash in morning, dryer at ~2:30 before pickup.
- Vacuum and cooking need scheduled blocks.
- Erin likes meal prep but open to efficient daily cooking.
- Best chore windows: Mon morning (Zoey with Sandy), Tue morning (Zoey with Sandy).

## Routine Templates
### Monday (Sandy has Zoey 9-12)
- 7:00-7:30 — Breakfast prep (check Jason's meetings for timing)
- 7:30-8:00 — Kids breakfast + cleanup
- 9:00-9:30 — Drop off Vienna + Zoey to Sandy
- 9:30-10:00 — Start laundry / Vacuum
- 10:00-11:30 — Exercise / Gym or errands
- 11:30-12:00 — Pick up Zoey from Sandy / Lunch
- 12:00-2:00 — Zoey nap / Rest time / Personal development
- 2:00-2:30 — Side work / Backlog item
- 2:30-3:00 — Move laundry to dryer
- 3:00-3:30 — Pick up Vienna

### Tuesday (Sandy has Zoey 10-1)
- 7:00-7:30 — Breakfast prep
- 7:30-8:00 — Kids breakfast + cleanup
- 9:00-9:30 — Drop off Vienna
- 9:30-10:00 — Drop off Zoey at Sandy's / Start laundry
- 10:00-11:30 — Exercise / Gym or errands
- 11:30-12:30 — Personal development (knitting, projects)
- 12:30-1:00 — Pick up Zoey from Sandy / Lunch
- 1:00-2:30 — Zoey nap / Side work / Backlog item
- 2:30-3:00 — Move laundry to dryer
- 3:00-3:15 — Pick up Vienna (early for gymnastics)
- 3:15+ — Zoey's gymnastics class

### Wednesday (Zoey with Erin all day)
- 7:00-7:30 — Breakfast prep
- 7:30-8:00 — Kids breakfast + cleanup
- 9:00-9:30 — Drop off Vienna
- 9:30-11:00 — Chore block (vacuum, laundry start) with Zoey
- 11:00-11:30 — Out-of-house / errand time
- 11:30-12:00 — Lunch
- 12:00-2:00 — Zoey nap / Rest time (get out of house!)
- 2:00-2:30 — Personal development / Side work
- 2:30-3:00 — Move laundry to dryer
- 3:00-3:45 — Backlog item
- 3:45-4:00 — Pick up Vienna

### Thursday (Jason drops off Vienna — BSF by 10am)
- 7:00-7:30 — Breakfast prep
- 7:30-8:00 — Kids breakfast + cleanup
- 8:30-9:00 — Jason drops off Vienna
- 9:00-11:00 — Chore block with Zoey / Start laundry
- 11:00-11:30 — Out-of-house / errand time
- 11:30-12:00 — Lunch
- 12:00-2:00 — Zoey nap / Rest time
- 2:00-2:30 — Personal development / Side work
- 2:30-3:00 — Move laundry to dryer
- 3:00-3:30 — Pick up Vienna

### Friday (Nature class 10:20-11:20, Mar 4–May 27)
- 7:00-7:30 — Breakfast prep
- 7:30-8:00 — Kids breakfast + cleanup
- 9:00-9:30 — Drop off Vienna
- 9:30-10:00 — Quick chores / Start laundry
- 10:00-10:20 — Drive to Bartley Ranch Park
- 10:20-11:20 — Nature class (with Zoey)
- 11:20-12:00 — Lunch
- 12:00-2:00 — Zoey nap / Rest time
- 2:00-2:30 — Personal development / Side work
- 2:30-3:00 — Move laundry to dryer
- 3:00-3:30 — Pick up Vienna

### Saturday (Ski lesson, ~5 weeks ending late Mar)
- 7:30-8:00 — Get kids ready
- 8:00 — Leave house for ski lesson
- 9:00-11:00 — Vienna ski lesson
- 11:00+ — Family time / errands

### Sunday (Church + marriage class, next 4 weeks)
- 8:00-8:15 — Get kids ready
- 8:15 — Leave house for church
- 9:00-10:00 — Church
- 10:00+ — Grandparents take kids until ~4pm
- 10:00-4:00 — Marriage class (Jason & Erin)
- Evening — Weekly family meeting

## Configuration
- Meeting day: Sunday
```

## Step 4: Connect the Integration to Each Page

This step is critical — your integration has **zero access** until you do this for each database/page.

For **each** of the 6 items (Action Items, Meal Plans, Meetings, Backlog, Grocery History, Family Profile):

1. Open the page
2. Click the **"..." menu** (top-right corner)
3. Scroll down to **"+ Add connections"**
4. Search for **"Family Meeting Bot"** and select it
5. Click **Confirm**

## Step 5: Get the Database IDs

For each database, you need its ID for the `.env` file.

1. Open the database as a full page
2. Click **"Share"** (top-right) → **"Copy link"**
3. The URL looks like: `https://www.notion.so/workspace/ba028b01a95548f48500c26971ff0884?v=...`
4. The **32-character string** between the last `/` and the `?` is the database ID

Copy these into your `.env`:

```
NOTION_ACTION_ITEMS_DB=<Action Items database ID>
NOTION_MEAL_PLANS_DB=<Meal Plans database ID>
NOTION_MEETINGS_DB=<Meetings database ID>
NOTION_BACKLOG_DB=<Backlog database ID>
NOTION_GROCERY_HISTORY_DB=<Grocery History database ID>
```

For the **Family Profile page**, do the same — open it, Share → Copy link, extract the ID:

```
NOTION_FAMILY_PROFILE_PAGE=<Family Profile page ID>
```

## Step 6: Invite Erin as a Guest

1. Open each database/page you want Erin to see
2. Click **"Share"** → **"Invite"**
3. Enter Erin's email address
4. Set permission to **"Full access"** (so she can check off grocery items, etc.)
5. Click **"Invite"**
6. Erin will get an email — she clicks the link and signs up with her Google account

Erin will then be able to:
- View and edit action items, meal plans, and meeting agendas
- Check off grocery list items from her phone
- Browse the Family Profile

She won't see the full workspace sidebar, but she can star/favorite the shared pages for quick access.

## Step 7: Install the Notion App (Both Phones)

1. Download **Notion** from the App Store (iPhone)
2. Sign in with Google
3. The shared databases will appear in your sidebar (Jason) or under "Shared with me" (Erin)

## Verification Checklist

After setup, confirm:

- [ ] `NOTION_TOKEN` is set in `.env` (starts with `ntn_`)
- [ ] `NOTION_ACTION_ITEMS_DB` is set (32-char hex string)
- [ ] `NOTION_MEAL_PLANS_DB` is set
- [ ] `NOTION_MEETINGS_DB` is set
- [ ] `NOTION_BACKLOG_DB` is set
- [ ] `NOTION_GROCERY_HISTORY_DB` is set
- [ ] `NOTION_FAMILY_PROFILE_PAGE` is set
- [ ] All 6 pages have the "Family Meeting Bot" integration connected
- [ ] Family Profile includes Routine Templates section
- [ ] Erin has been invited as a guest with full access
- [ ] Both phones have the Notion app installed

## Cost

Notion Free Plan includes:
- Unlimited blocks (as long as only 1 workspace member)
- Up to 10 guests (Erin is 1)
- 5 MB file upload limit per file
- 7-day page history

This is more than sufficient for the family meeting assistant.
