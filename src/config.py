"""Environment variable loading and validation."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "ANTHROPIC_API_KEY",
    "NOTION_TOKEN",
    "NOTION_ACTION_ITEMS_DB",
    "NOTION_MEAL_PLANS_DB",
    "NOTION_MEETINGS_DB",
    "NOTION_FAMILY_PROFILE_PAGE",
    "GOOGLE_CALENDAR_JASON_ID",
    "GOOGLE_CALENDAR_ERIN_ID",
    "GOOGLE_CALENDAR_FAMILY_ID",
    "YNAB_ACCESS_TOKEN",
    "YNAB_BUDGET_ID",
]


def _load_env():
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example to .env and fill in all values.", file=sys.stderr)
        sys.exit(1)


_load_env()

# Anthropic
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]

# WhatsApp (optional — only needed for webhook server)
WHATSAPP_PHONE_NUMBER_ID: str = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN: str = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_VERIFY_TOKEN: str = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_APP_SECRET: str = os.environ.get("WHATSAPP_APP_SECRET", "")

# Notion
NOTION_TOKEN: str = os.environ["NOTION_TOKEN"]
NOTION_ACTION_ITEMS_DB: str = os.environ["NOTION_ACTION_ITEMS_DB"]
NOTION_MEAL_PLANS_DB: str = os.environ["NOTION_MEAL_PLANS_DB"]
NOTION_MEETINGS_DB: str = os.environ["NOTION_MEETINGS_DB"]
NOTION_FAMILY_PROFILE_PAGE: str = os.environ["NOTION_FAMILY_PROFILE_PAGE"]
NOTION_BACKLOG_DB: str = os.environ.get("NOTION_BACKLOG_DB", "")
NOTION_GROCERY_HISTORY_DB: str = os.environ.get("NOTION_GROCERY_HISTORY_DB", "")

# Google Calendar (3 calendars)
GOOGLE_CALENDAR_JASON_ID: str = os.environ["GOOGLE_CALENDAR_JASON_ID"]
GOOGLE_CALENDAR_ERIN_ID: str = os.environ["GOOGLE_CALENDAR_ERIN_ID"]
GOOGLE_CALENDAR_FAMILY_ID: str = os.environ["GOOGLE_CALENDAR_FAMILY_ID"]

CALENDAR_IDS: dict[str, str] = {
    "jason": GOOGLE_CALENDAR_JASON_ID,
    "erin": GOOGLE_CALENDAR_ERIN_ID,
    "family": GOOGLE_CALENDAR_FAMILY_ID,
}

# Outlook (optional — Jason's work calendar ICS feed)
OUTLOOK_CALENDAR_ICS_URL: str = os.environ.get("OUTLOOK_CALENDAR_ICS_URL", "")

# YNAB
YNAB_ACCESS_TOKEN: str = os.environ["YNAB_ACCESS_TOKEN"]
YNAB_BUDGET_ID: str = os.environ["YNAB_BUDGET_ID"]

# Family phone mapping (optional — only needed for WhatsApp webhook)
JASON_PHONE: str = os.environ.get("JASON_PHONE", "")
ERIN_PHONE: str = os.environ.get("ERIN_PHONE", "")

PHONE_TO_NAME: dict[str, str] = {}
if JASON_PHONE:
    PHONE_TO_NAME[JASON_PHONE] = "Jason"
if ERIN_PHONE:
    PHONE_TO_NAME[ERIN_PHONE] = "Erin"

# AnyList (optional — grocery integration)
ANYLIST_SIDECAR_URL: str = os.environ.get("ANYLIST_SIDECAR_URL", "http://anylist-sidecar:3000")

# Cloudflare R2 (recipe photo storage — optional, needed for Feature 002)
R2_ACCOUNT_ID: str = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID: str = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY: str = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME: str = os.environ.get("R2_BUCKET_NAME", "family-recipes")

# Notion — Recipe databases (optional, needed for Feature 002)
NOTION_RECIPES_DB: str = os.environ.get("NOTION_RECIPES_DB", "")
NOTION_COOKBOOKS_DB: str = os.environ.get("NOTION_COOKBOOKS_DB", "")

# Notion — Nudge Queue and Chores databases (Feature 003)
NOTION_NUDGE_QUEUE_DB: str = os.environ.get("NOTION_NUDGE_QUEUE_DB", "")
NOTION_CHORES_DB: str = os.environ.get("NOTION_CHORES_DB", "")

# n8n webhook auth (shared secret for /api/v1/* endpoint protection)
N8N_WEBHOOK_SECRET: str = os.environ.get("N8N_WEBHOOK_SECRET", "")

# Gmail API is used for Feature 010 Amazon-YNAB sync (reads Amazon order emails).
# Auth handled via token.json (shared with Google Calendar OAuth).
