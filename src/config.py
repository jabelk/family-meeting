"""Environment variable loading and validation."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "ANTHROPIC_API_KEY",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_VERIFY_TOKEN",
    "NOTION_TOKEN",
    "NOTION_ACTION_ITEMS_DB",
    "NOTION_MEAL_PLANS_DB",
    "NOTION_MEETINGS_DB",
    "NOTION_FAMILY_PROFILE_PAGE",
    "GOOGLE_CALENDAR_ID",
    "YNAB_ACCESS_TOKEN",
    "YNAB_BUDGET_ID",
    "JASON_PHONE",
    "ERIN_PHONE",
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

# WhatsApp
WHATSAPP_PHONE_NUMBER_ID: str = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
WHATSAPP_ACCESS_TOKEN: str = os.environ["WHATSAPP_ACCESS_TOKEN"]
WHATSAPP_VERIFY_TOKEN: str = os.environ["WHATSAPP_VERIFY_TOKEN"]

# Notion
NOTION_TOKEN: str = os.environ["NOTION_TOKEN"]
NOTION_ACTION_ITEMS_DB: str = os.environ["NOTION_ACTION_ITEMS_DB"]
NOTION_MEAL_PLANS_DB: str = os.environ["NOTION_MEAL_PLANS_DB"]
NOTION_MEETINGS_DB: str = os.environ["NOTION_MEETINGS_DB"]
NOTION_FAMILY_PROFILE_PAGE: str = os.environ["NOTION_FAMILY_PROFILE_PAGE"]

# Google Calendar
GOOGLE_CALENDAR_ID: str = os.environ["GOOGLE_CALENDAR_ID"]

# YNAB
YNAB_ACCESS_TOKEN: str = os.environ["YNAB_ACCESS_TOKEN"]
YNAB_BUDGET_ID: str = os.environ["YNAB_BUDGET_ID"]

# Family phone mapping (phone number → partner name)
JASON_PHONE: str = os.environ["JASON_PHONE"]
ERIN_PHONE: str = os.environ["ERIN_PHONE"]

PHONE_TO_NAME: dict[str, str] = {
    JASON_PHONE: "Jason",
    ERIN_PHONE: "Erin",
}
