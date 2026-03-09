"""Environment variable loading and validation."""

import logging
import os
import sys
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from src.family_config import load_family_config
from src.integrations import INTEGRATION_REGISTRY, get_enabled_integrations, get_integration_status

load_dotenv()

REQUIRED_VARS = [
    "ANTHROPIC_API_KEY",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_APP_SECRET",
    "N8N_WEBHOOK_SECRET",
]

logger = logging.getLogger(__name__)


def _load_env():
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        # Allow tests to import the app without real credentials
        if "pytest" in sys.modules or os.getenv("TESTING"):
            logger.warning("Missing env vars (test mode): %s", ", ".join(missing))
            return
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example to .env and fill in all values.", file=sys.stderr)
        sys.exit(1)

    # Log integration status using centralized registry
    enabled = []
    disabled = []
    for name, integration in INTEGRATION_REGISTRY.items():
        if integration.always_enabled or integration.required:
            continue
        status = get_integration_status(name)
        if status == "enabled":
            enabled.append(integration.display_name)
        elif status == "partial":
            set_vars = [v for v in integration.env_vars if os.getenv(v)]
            missing_vars = [v for v in integration.env_vars if not os.getenv(v)]
            logger.warning(
                "%s partially configured (%d/%d vars set, missing: %s)",
                integration.display_name,
                len(set_vars),
                len(integration.env_vars),
                ", ".join(missing_vars),
            )
        else:
            disabled.append(integration.display_name)
    if enabled:
        logger.info("Enabled integrations: %s", ", ".join(enabled))
    if disabled:
        logger.info("Disabled integrations: %s", ", ".join(disabled))


_load_env()

# Compute enabled integrations once at startup
ENABLED_INTEGRATIONS: set[str] = get_enabled_integrations()

# Anthropic
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")

# WhatsApp (required — core messaging interface)
WHATSAPP_PHONE_NUMBER_ID: str = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN: str = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_VERIFY_TOKEN: str = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_APP_SECRET: str = os.environ.get("WHATSAPP_APP_SECRET", "")

# Notion (optional — configure for task/meal/meeting management)
NOTION_TOKEN: str = os.environ.get("NOTION_TOKEN", "")
NOTION_ACTION_ITEMS_DB: str = os.environ.get("NOTION_ACTION_ITEMS_DB", "")
NOTION_MEAL_PLANS_DB: str = os.environ.get("NOTION_MEAL_PLANS_DB", "")
NOTION_MEETINGS_DB: str = os.environ.get("NOTION_MEETINGS_DB", "")
NOTION_FAMILY_PROFILE_PAGE: str = os.environ.get("NOTION_FAMILY_PROFILE_PAGE", "")
NOTION_BACKLOG_DB: str = os.environ.get("NOTION_BACKLOG_DB", "")
NOTION_GROCERY_HISTORY_DB: str = os.environ.get("NOTION_GROCERY_HISTORY_DB", "")

# Google Calendar (optional — configure for calendar integration)
# Generic env vars with legacy fallbacks for existing deployments
GOOGLE_CALENDAR_PARTNER1_ID: str = os.environ.get("GOOGLE_CALENDAR_PARTNER1_ID", "") or os.environ.get(
    "GOOGLE_CALENDAR_JASON_ID", ""
)
GOOGLE_CALENDAR_PARTNER2_ID: str = os.environ.get("GOOGLE_CALENDAR_PARTNER2_ID", "") or os.environ.get(
    "GOOGLE_CALENDAR_ERIN_ID", ""
)
GOOGLE_CALENDAR_FAMILY_ID: str = os.environ.get("GOOGLE_CALENDAR_FAMILY_ID", "")

# Outlook (optional — Jason's work calendar ICS feed)
OUTLOOK_CALENDAR_ICS_URL: str = os.environ.get("OUTLOOK_CALENDAR_ICS_URL", "")

# YNAB (optional — configure for budget integration)
YNAB_ACCESS_TOKEN: str = os.environ.get("YNAB_ACCESS_TOKEN", "")
YNAB_BUDGET_ID: str = os.environ.get("YNAB_BUDGET_ID", "")

# Family config (loaded from config/family.yaml — see src/family_config.py)
try:
    FAMILY_CONFIG: dict = load_family_config()
except Exception as e:
    if "pytest" in sys.modules or os.getenv("TESTING"):
        logger.warning("Family config failed to load (test mode): %s", e)
        FAMILY_CONFIG = {}
    else:
        logger.warning("Family config failed to load: %s — using defaults", e)
        FAMILY_CONFIG = {}

# Timezone (from family config, defaults to America/Los_Angeles)
TIMEZONE_STR: str = FAMILY_CONFIG.get("timezone", "America/Los_Angeles")
TIMEZONE: ZoneInfo = ZoneInfo(TIMEZONE_STR)

# Dynamic calendar keys using partner names from config
_p1 = FAMILY_CONFIG.get("partner1_name", "partner1").lower()
_p2 = FAMILY_CONFIG.get("partner2_name", "partner2").lower()
CALENDAR_IDS: dict[str, str] = {
    _p1: GOOGLE_CALENDAR_PARTNER1_ID,
    _p2: GOOGLE_CALENDAR_PARTNER2_ID,
    "family": GOOGLE_CALENDAR_FAMILY_ID,
}
ALL_CALENDAR_NAMES: list[str] = list(CALENDAR_IDS.keys())
DEFAULT_CALENDAR: str = _p2  # primary household manager's calendar

# Family phone mapping (optional — only needed for WhatsApp webhook)
# Generic env vars with legacy fallbacks for existing deployments
PARTNER1_PHONE: str = os.environ.get("PARTNER1_PHONE", "") or os.environ.get("JASON_PHONE", "")
PARTNER2_PHONE: str = os.environ.get("PARTNER2_PHONE", "") or os.environ.get("ERIN_PHONE", "")
PRIMARY_PHONE: str = PARTNER2_PHONE  # household manager — receives proactive messages

# Legacy aliases for backward compatibility
JASON_PHONE: str = PARTNER1_PHONE
ERIN_PHONE: str = PARTNER2_PHONE

PHONE_TO_NAME: dict[str, str] = {}
if PARTNER1_PHONE:
    PHONE_TO_NAME[PARTNER1_PHONE] = FAMILY_CONFIG.get("partner1_name", "Partner1")
if PARTNER2_PHONE:
    PHONE_TO_NAME[PARTNER2_PHONE] = FAMILY_CONFIG.get("partner2_name", "Partner2")

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

# API auth — shared secret for /api/v1/* endpoint protection.
# Named N8N_WEBHOOK_SECRET for historical reasons; used on both Railway and NUC deployments.
N8N_WEBHOOK_SECRET: str = os.environ.get("N8N_WEBHOOK_SECRET", "")

# Gmail API is used for Feature 010 Amazon-YNAB sync (reads Amazon order emails).
# Auth handled via token.json (shared with Google Calendar OAuth).

# OpenAI (optional — used for voice note transcription, Feature 019)
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")

# Google OAuth (optional — for loading Calendar credentials from env vars in containers)
GOOGLE_TOKEN_JSON: str = os.environ.get("GOOGLE_TOKEN_JSON", "")
GOOGLE_CREDENTIALS_JSON: str = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")

# Scheduler (enabled by default; set to "false" to disable in-app APScheduler)
SCHEDULER_ENABLED: bool = os.environ.get("SCHEDULER_ENABLED", "true").lower() != "false"

# Upstream update notifications (optional — for template repo instances)
ADMIN_PHONE: str = os.environ.get("ADMIN_PHONE", "") or PRIMARY_PHONE
UPSTREAM_REMOTE: str = os.environ.get("UPSTREAM_REMOTE", "upstream")
