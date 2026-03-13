"""Self-diagnostic log querying via Axiom.

When a tool fails, the bot can query its own recent logs to understand
WHY something broke and give the user a specific, helpful explanation
instead of a generic "service is down" message.
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

AXIOM_QUERY_TOKEN = os.getenv("AXIOM_QUERY_TOKEN", "")
AXIOM_DATASET = os.getenv("AXIOM_DATASET", "railway-logs")
_AXIOM_APL_URL = "https://api.axiom.co/v1/datasets/_apl?format=legacy"
_QUERY_TIMEOUT = 5.0  # seconds — keep it fast so it doesn't slow down responses


def _query_axiom(apl: str) -> list[dict[str, Any]]:
    """Run an APL query against Axiom and return matched log entries."""
    if not AXIOM_QUERY_TOKEN:
        return []
    try:
        resp = httpx.post(
            _AXIOM_APL_URL,
            headers={
                "Authorization": f"Bearer {AXIOM_QUERY_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"apl": apl},
            timeout=_QUERY_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "time": m["_time"][:19],
                "message": m.get("data", {}).get("message", ""),
                "severity": m.get("data", {}).get("severity", ""),
            }
            for m in data.get("matches", [])
        ]
    except Exception as exc:
        logger.debug("Axiom query failed (non-critical): %s", exc)
        return []


def query_recent_errors(minutes: int = 5, limit: int = 20) -> list[dict[str, Any]]:
    """Query recent error-level logs from the last N minutes."""
    apl = f"['{AXIOM_DATASET}'] | where data.severity == \"error\" | order by _time desc | limit {limit}"
    return _query_axiom(apl)


def diagnose_tool_failure(tool_name: str, error_msg: str) -> str:
    """Query recent logs and produce a human-readable diagnosis of why a tool failed.

    Returns an empty string if no diagnosis can be determined or if Axiom
    is not configured. The caller should treat empty string as "no additional
    context available."
    """
    if not AXIOM_QUERY_TOKEN:
        return ""

    # Query recent error logs (last 3 minutes, enough to capture the failure chain)
    logs = query_recent_errors(minutes=3, limit=30)
    if not logs:
        return ""

    messages = [entry["message"] for entry in logs]
    all_text = "\n".join(messages).lower()

    diagnoses: list[str] = []

    # --- Pattern matching on log messages ---

    # Google Calendar OAuth
    if "invalid_grant" in all_text or "token has been expired or revoked" in all_text:
        diagnoses.append(
            "Google Calendar's authentication token has expired. "
            "Jason needs to re-authorize via setup_calendar.py (takes ~2 min)."
        )

    # Google Calendar API errors (non-auth)
    elif "google" in tool_name.lower() or "calendar" in tool_name.lower():
        if "httperror" in all_text or "googleapis" in all_text:
            diagnoses.append("Google Calendar API returned an error.")

    # Notion errors
    if "notion" in all_text and ("apiresponseerror" in all_text or "conflict" in all_text):
        diagnoses.append("Notion API returned an error — the service may be experiencing issues.")

    # Anthropic/Claude API
    if "anthropic" in all_text and ("overloaded" in all_text or "529" in all_text or "500" in all_text):
        diagnoses.append("The AI service (Claude) is overloaded or experiencing an outage.")

    # YNAB
    if "ynab" in all_text and ("401" in all_text or "403" in all_text):
        diagnoses.append("YNAB authentication failed — the API token may need to be refreshed.")

    # AnyList sidecar
    if "anylist" in all_text and ("connection refused" in all_text or "connect timeout" in all_text):
        diagnoses.append("The grocery list service (AnyList sidecar) is not responding.")

    # Generic connection issues
    if not diagnoses:
        if "connection refused" in all_text or "connecterror" in all_text:
            diagnoses.append("A service connection was refused — the target service may be down.")
        elif "timeout" in all_text or "timed out" in all_text:
            diagnoses.append("A service request timed out.")
        elif "rate limit" in all_text or "429" in all_text:
            diagnoses.append("An API rate limit was hit — try again in a few minutes.")

    if not diagnoses:
        # Count errors but don't diagnose if nothing matches known patterns
        error_count = sum(1 for entry in logs if entry["severity"] == "error")
        if error_count > 10:
            diagnoses.append(
                f"Multiple errors detected ({error_count} in recent logs) — the system may be under stress."
            )

    return " ".join(diagnoses)
