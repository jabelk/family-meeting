"""YNAB API wrapper — read budget data for financial summaries."""

import logging
from datetime import date
import httpx
from src.config import YNAB_ACCESS_TOKEN, YNAB_BUDGET_ID

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ynab.com/v1"
HEADERS = {"Authorization": f"Bearer {YNAB_ACCESS_TOKEN}"}


def get_budget_summary(month: str = "", category: str = "") -> str:
    """Get budget summary for a month, optionally filtered to one category.

    Args:
        month: Month in YYYY-MM-DD format (first of month). Defaults to current month.
        category: Optional category name to filter to.

    Returns formatted text with budget status per category, overspent flags,
    and savings goal progress.
    """
    if not month:
        today = date.today()
        month = today.replace(day=1).isoformat()

    try:
        url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/months/{month}"
        resp = httpx.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        month_data = data["data"]["month"]
        categories = month_data.get("categories", [])

        if category:
            # Filter to specific category
            match = [c for c in categories if category.lower() in c["name"].lower()]
            if not match:
                return f"Category '{category}' not found in budget."
            cat = match[0]
            budgeted = cat["budgeted"] / 1000
            spent = abs(cat["activity"]) / 1000
            balance = cat["balance"] / 1000
            return (
                f"*{cat['name']}*\n"
                f"Budgeted: ${budgeted:,.2f}\n"
                f"Spent: ${spent:,.2f}\n"
                f"Remaining: ${balance:,.2f}"
            )

        # Full summary
        over_budget = []
        on_track = []
        total_budgeted = 0
        total_spent = 0

        for cat in categories:
            if cat.get("hidden") or cat.get("deleted"):
                continue
            name = cat["name"]
            budgeted = cat["budgeted"] / 1000
            spent = abs(cat["activity"]) / 1000
            balance = cat["balance"] / 1000

            if budgeted == 0 and spent == 0:
                continue

            total_budgeted += budgeted
            total_spent += spent

            entry = f"- {name}: ${spent:,.0f} / ${budgeted:,.0f}"
            if balance < 0:
                entry += f" (+${abs(balance):,.0f} over)"
                over_budget.append(entry)
            else:
                entry += f" (${balance:,.0f} left)"
                on_track.append(entry)

        # Goals
        goals = []
        for cat in categories:
            if cat.get("goal_type") and cat.get("goal_percentage_complete", 0) > 0:
                pct = cat["goal_percentage_complete"]
                target = cat.get("goal_target", 0) / 1000
                funded = cat.get("goal_overall_funded", 0) / 1000
                if target > 0:
                    goals.append(f"- {cat['name']}: {pct}% (${funded:,.0f} / ${target:,.0f})")

        lines = []
        if over_budget:
            lines.append("*Over budget:*")
            lines.extend(over_budget)
        if on_track:
            lines.append("\n*On track:*")
            lines.extend(on_track[:5])  # Top 5 to keep it concise
            if len(on_track) > 5:
                lines.append(f"  ...and {len(on_track) - 5} more categories on track")
        if goals:
            lines.append("\n*Savings Goals:*")
            lines.extend(goals)
        lines.append(f"\n*Total spent:* ${total_spent:,.0f} / ${total_budgeted:,.0f} budgeted")
        return "\n".join(lines)

    except Exception as e:
        logger.error("YNAB API error: %s", e)
        raise
