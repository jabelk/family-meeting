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

You need to create 3 databases and 1 page. Create them all at the top level of your workspace.

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

### Page: Family Profile

1. Click **"+ New page"** (regular page, NOT a database)
2. Title it **"Family Profile"**
3. Add this content (copy/paste, then format the headings):

```
## Members
- Jason (partner) — works from home at Cisco
- Erin (partner) — stays at home with the kids
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

## Configuration
- Meeting day: Sunday
```

## Step 4: Connect the Integration to Each Page

This step is critical — your integration has **zero access** until you do this for each database/page.

For **each** of the 4 items (Action Items, Meal Plans, Meetings, Family Profile):

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
- [ ] `NOTION_FAMILY_PROFILE_PAGE` is set
- [ ] All 4 pages have the "Family Meeting Bot" integration connected
- [ ] Erin has been invited as a guest with full access
- [ ] Both phones have the Notion app installed

## Cost

Notion Free Plan includes:
- Unlimited blocks (as long as only 1 workspace member)
- Up to 10 guests (Erin is 1)
- 5 MB file upload limit per file
- 7-day page history

This is more than sufficient for the family meeting assistant.
