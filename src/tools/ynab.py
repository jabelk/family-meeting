"""YNAB API wrapper — budget data, transactions, and write operations."""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

from src.config import YNAB_ACCESS_TOKEN, YNAB_BUDGET_ID

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ynab.com/v1"
HEADERS = {"Authorization": f"Bearer {YNAB_ACCESS_TOKEN}"}
CACHE_TTL = 3600  # 1 hour in seconds

# --- Caches ---
_category_cache: dict = {}  # name_lower → {id, name, group, budgeted, activity, balance}
_category_cache_time: float = 0.0

_payee_cache: dict = {}  # name_lower → id
_payee_cache_time: float = 0.0

_account_cache: list = []
_account_cache_time: float = 0.0


def _get_categories() -> dict:
    """Fetch all categories, cache as name→details map with 1-hour TTL."""
    global _category_cache, _category_cache_time
    if _category_cache and (time.time() - _category_cache_time) < CACHE_TTL:
        return _category_cache

    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/categories"
    resp = httpx.get(url, headers=HEADERS)
    resp.raise_for_status()
    groups = resp.json()["data"]["category_groups"]

    cache = {}
    for group in groups:
        for cat in group.get("categories", []):
            if cat.get("hidden") or cat.get("deleted"):
                continue
            cache[cat["name"].lower()] = {
                "id": cat["id"],
                "name": cat["name"],
                "group": group["name"],
                "budgeted": cat["budgeted"],
                "activity": cat["activity"],
                "balance": cat["balance"],
            }
    _category_cache = cache
    _category_cache_time = time.time()
    logger.info("Cached %d YNAB categories", len(cache))
    return cache


def _get_payees() -> dict:
    """Fetch all payees, cache as name→id map with 1-hour TTL."""
    global _payee_cache, _payee_cache_time
    if _payee_cache and (time.time() - _payee_cache_time) < CACHE_TTL:
        return _payee_cache

    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/payees"
    resp = httpx.get(url, headers=HEADERS)
    resp.raise_for_status()
    payees = resp.json()["data"]["payees"]

    cache = {}
    for p in payees:
        if p.get("deleted"):
            continue
        cache[p["name"].lower()] = p["id"]
    _payee_cache = cache
    _payee_cache_time = time.time()
    logger.info("Cached %d YNAB payees", len(cache))
    return cache


def _get_accounts() -> list:
    """Fetch accounts, cache with 1-hour TTL. Returns list of dicts."""
    global _account_cache, _account_cache_time
    if _account_cache and (time.time() - _account_cache_time) < CACHE_TTL:
        return _account_cache

    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/accounts"
    resp = httpx.get(url, headers=HEADERS)
    resp.raise_for_status()
    accounts = resp.json()["data"]["accounts"]

    cache = [
        {
            "id": a["id"],
            "name": a["name"],
            "type": a["type"],
            "closed": a.get("closed", False),
            "balance": a["balance"],
        }
        for a in accounts
    ]
    _account_cache = cache
    _account_cache_time = time.time()
    logger.info("Cached %d YNAB accounts", len(cache))
    return cache


def _fuzzy_match_category(name: str) -> Optional[tuple]:
    """Match a category name case-insensitively. Returns (id, canonical_name) or None.

    1. Exact match (case-insensitive)
    2. Substring contains match
    """
    categories = _get_categories()
    name_lower = name.lower().strip()

    # Exact match
    if name_lower in categories:
        cat = categories[name_lower]
        return (cat["id"], cat["name"])

    # Substring match
    matches = []
    for key, cat in categories.items():
        if name_lower in key or key in name_lower:
            matches.append(cat)

    if len(matches) == 1:
        return (matches[0]["id"], matches[0]["name"])
    return None


def _fuzzy_match_payee(name: str) -> Optional[tuple]:
    """Match a payee name case-insensitively. Returns (id, canonical_name) or None.

    1. Exact match (case-insensitive)
    2. Substring contains match
    """
    payees = _get_payees()
    name_lower = name.lower().strip()

    # Exact match
    if name_lower in payees:
        # Need to find the canonical name
        for key, pid in payees.items():
            if key == name_lower:
                return (pid, name)  # Return the user's casing
        return (payees[name_lower], name)

    # Substring match
    matches = []
    for key, pid in payees.items():
        if name_lower in key or key in name_lower:
            matches.append((pid, key))

    if len(matches) == 1:
        return matches[0]
    return None


def search_transactions(
    payee: str = "",
    category: str = "",
    since_date: str = "",
    uncategorized_only: bool = False,
) -> str:
    """Search recent transactions by payee, category, date, or uncategorized status."""
    if not since_date:
        today = date.today()
        since_date = today.replace(day=1).isoformat()

    params = {"since_date": since_date}
    if uncategorized_only:
        params["type"] = "uncategorized"

    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/transactions"
    resp = httpx.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    txns = resp.json()["data"]["transactions"]

    # Client-side filters
    if payee:
        payee_lower = payee.lower().strip()
        txns = [t for t in txns if payee_lower in (t.get("payee_name") or "").lower()]
    if category and not uncategorized_only:
        cat_lower = category.lower().strip()
        txns = [t for t in txns if cat_lower in (t.get("category_name") or "").lower()]

    # Sort by date descending
    txns.sort(key=lambda t: t["date"], reverse=True)

    if not txns:
        filters = []
        if payee:
            filters.append(f"payee '{payee}'")
        if category:
            filters.append(f"category '{category}'")
        if uncategorized_only:
            filters.append("uncategorized only")
        return f"No transactions found matching {', '.join(filters) or 'your criteria'} since {since_date}."

    lines = []
    for t in txns[:20]:  # Cap at 20
        amt = t["amount"] / 1000
        cat_name = t.get("category_name") or "Uncategorized"
        lines.append(
            f"- {t['date']} | {t.get('payee_name', 'Unknown')} | ${abs(amt):,.2f} | {cat_name}"
        )

    header = f"Found {len(txns)} transaction(s)"
    if len(txns) > 20:
        header += f" (showing first 20)"
    return header + ":\n" + "\n".join(lines)


def recategorize_transaction(
    payee: str = "",
    amount: float = 0,
    date_str: str = "",
    new_category: str = "",
) -> str:
    """Change the category of an existing transaction."""
    if not new_category:
        return "Please specify the new category name."

    cat_match = _fuzzy_match_category(new_category)
    if not cat_match:
        # Suggest available categories
        categories = _get_categories()
        suggestions = [c["name"] for c in list(categories.values())[:10]]
        return (
            f"Category '{new_category}' not found. "
            f"Some available categories: {', '.join(suggestions)}"
        )

    cat_id, cat_name = cat_match

    # Fetch recent transactions to find the match
    today = date.today()
    since = today.replace(day=1).isoformat()
    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/transactions"
    resp = httpx.get(url, headers=HEADERS, params={"since_date": since})
    resp.raise_for_status()
    txns = resp.json()["data"]["transactions"]

    # Filter by payee
    if payee:
        payee_lower = payee.lower().strip()
        txns = [t for t in txns if payee_lower in (t.get("payee_name") or "").lower()]

    # Filter by amount (within $0.50 tolerance)
    if amount:
        amt_milli = int(abs(amount) * 1000)
        txns = [t for t in txns if abs(abs(t["amount"]) - amt_milli) <= 500]

    # Filter by date
    if date_str:
        txns = [t for t in txns if t["date"] == date_str]

    if len(txns) == 0:
        return "No matching transactions found. Try providing the payee name, amount, or date to narrow down."

    if len(txns) == 1:
        txn = txns[0]
        # Update the transaction
        put_url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/transactions/{txn['id']}"
        put_resp = httpx.put(
            put_url,
            headers=HEADERS,
            json={"transaction": {"category_id": cat_id}},
        )
        put_resp.raise_for_status()
        amt = abs(txn["amount"]) / 1000
        old_cat = txn.get("category_name") or "Uncategorized"
        return (
            f"Recategorized: {txn.get('payee_name', 'Unknown')} ${amt:,.2f} on {txn['date']}\n"
            f"From: {old_cat} → To: {cat_name}"
        )

    if len(txns) <= 5:
        lines = ["Multiple matches found. Which one?\n"]
        for i, t in enumerate(txns, 1):
            amt = abs(t["amount"]) / 1000
            lines.append(
                f"{i}. {t['date']} | {t.get('payee_name', 'Unknown')} | "
                f"${amt:,.2f} | {t.get('category_name') or 'Uncategorized'}"
            )
        lines.append(f"\nReply with the number to recategorize it as '{cat_name}'.")
        return "\n".join(lines)

    return f"Found {len(txns)} matches — too many to list. Please narrow your search by adding the date or amount."


def create_transaction(
    payee: str = "",
    amount: float = 0,
    category: str = "",
    date_str: str = "",
    memo: str = "",
    account: str = "",
) -> str:
    """Create a manual transaction (e.g., cash purchase)."""
    if not payee or not amount or not category:
        return "Please provide payee, amount, and category."

    # Resolve category
    cat_match = _fuzzy_match_category(category)
    if not cat_match:
        categories = _get_categories()
        suggestions = [c["name"] for c in list(categories.values())[:10]]
        return (
            f"Category '{category}' not found. "
            f"Some available categories: {', '.join(suggestions)}"
        )
    cat_id, cat_name = cat_match

    # Resolve account (default: first non-closed checking account)
    accounts = _get_accounts()
    account_id = None
    if account:
        acct_lower = account.lower().strip()
        for a in accounts:
            if acct_lower in a["name"].lower() and not a["closed"]:
                account_id = a["id"]
                break
    if not account_id:
        for a in accounts:
            if a["type"] == "checking" and not a["closed"]:
                account_id = a["id"]
                break
    if not account_id:
        # Fall back to any non-closed account
        for a in accounts:
            if not a["closed"]:
                account_id = a["id"]
                break
    if not account_id:
        return "No open accounts found in YNAB."

    if not date_str:
        date_str = date.today().isoformat()

    # Amount is positive from user, make negative for outflow (milliunits)
    amount_milli = -int(abs(amount) * 1000)

    txn_data = {
        "transaction": {
            "account_id": account_id,
            "date": date_str,
            "amount": amount_milli,
            "payee_name": payee,
            "category_id": cat_id,
            "cleared": "uncleared",
            "approved": True,
        }
    }
    if memo:
        txn_data["transaction"]["memo"] = memo

    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/transactions"
    resp = httpx.post(url, headers=HEADERS, json=txn_data)
    resp.raise_for_status()

    return (
        f"Created transaction:\n"
        f"- Payee: {payee}\n"
        f"- Amount: ${abs(amount):,.2f}\n"
        f"- Category: {cat_name}\n"
        f"- Date: {date_str}"
        + (f"\n- Memo: {memo}" if memo else "")
    )


def update_category_budget(category: str = "", amount: float = 0) -> str:
    """Adjust the budgeted amount for a category this month.

    Args:
        category: Category name (fuzzy matched).
        amount: Dollar amount to add (positive) or subtract (negative).
    """
    if not category or not amount:
        return "Please provide both category name and amount."

    cat_match = _fuzzy_match_category(category)
    if not cat_match:
        categories = _get_categories()
        suggestions = [c["name"] for c in list(categories.values())[:10]]
        return f"Category '{category}' not found. Some available: {', '.join(suggestions)}"

    cat_id, cat_name = cat_match
    today = date.today()
    month_str = today.replace(day=1).isoformat()

    # GET current budgeted amount
    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/months/{month_str}/categories/{cat_id}"
    resp = httpx.get(url, headers=HEADERS)
    resp.raise_for_status()
    cat_data = resp.json()["data"]["category"]
    current_budgeted = cat_data["budgeted"]

    # Compute new amount
    amount_milli = int(amount * 1000)
    new_budgeted = current_budgeted + amount_milli

    # PATCH
    patch_resp = httpx.patch(
        url,
        headers=HEADERS,
        json={"category": {"budgeted": new_budgeted}},
    )
    patch_resp.raise_for_status()

    old_dollars = current_budgeted / 1000
    new_dollars = new_budgeted / 1000
    direction = "increased" if amount > 0 else "decreased"
    return (
        f"Budget for *{cat_name}* {direction} by ${abs(amount):,.2f}\n"
        f"Previous: ${old_dollars:,.2f} → New: ${new_dollars:,.2f}"
    )


def move_money(from_category: str = "", to_category: str = "", amount: float = 0) -> str:
    """Move budgeted money from one category to another.

    Args:
        from_category: Source category name (fuzzy matched).
        to_category: Destination category name (fuzzy matched).
        amount: Dollar amount to move (positive number).
    """
    if not from_category or not to_category or not amount:
        return "Please provide source category, destination category, and amount."

    from_match = _fuzzy_match_category(from_category)
    to_match = _fuzzy_match_category(to_category)

    if not from_match:
        return f"Source category '{from_category}' not found."
    if not to_match:
        return f"Destination category '{to_category}' not found."

    from_id, from_name = from_match
    to_id, to_name = to_match

    today = date.today()
    month_str = today.replace(day=1).isoformat()
    amount_milli = int(abs(amount) * 1000)

    # GET current budgeted amounts for both
    from_url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/months/{month_str}/categories/{from_id}"
    to_url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/months/{month_str}/categories/{to_id}"

    from_resp = httpx.get(from_url, headers=HEADERS)
    from_resp.raise_for_status()
    from_data = from_resp.json()["data"]["category"]
    from_budgeted = from_data["budgeted"]

    to_resp = httpx.get(to_url, headers=HEADERS)
    to_resp.raise_for_status()
    to_data = to_resp.json()["data"]["category"]
    to_budgeted = to_data["budgeted"]

    # Warn if source doesn't have enough
    if from_budgeted < amount_milli:
        available = from_budgeted / 1000
        return (
            f"*{from_name}* only has ${available:,.2f} budgeted. "
            f"Would you like to move ${available:,.2f} instead?"
        )

    # PATCH source (decrease)
    patch_from = httpx.patch(
        from_url,
        headers=HEADERS,
        json={"category": {"budgeted": from_budgeted - amount_milli}},
    )
    patch_from.raise_for_status()

    # PATCH destination (increase)
    patch_to = httpx.patch(
        to_url,
        headers=HEADERS,
        json={"category": {"budgeted": to_budgeted + amount_milli}},
    )
    patch_to.raise_for_status()

    new_from = (from_budgeted - amount_milli) / 1000
    new_to = (to_budgeted + amount_milli) / 1000
    return (
        f"Moved ${abs(amount):,.2f} from *{from_name}* to *{to_name}*\n"
        f"- {from_name}: ${from_budgeted / 1000:,.2f} → ${new_from:,.2f}\n"
        f"- {to_name}: ${to_budgeted / 1000:,.2f} → ${new_to:,.2f}"
    )


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


# ---------------------------------------------------------------------------
# Proactive insight functions (called by budget scan endpoint)
# ---------------------------------------------------------------------------

def check_overspend_warnings() -> list:
    """Check for categories >80% spent before the 20th of the month.

    Returns list of dicts: {category_name, spent, budgeted, percent_used, days_remaining}
    """
    today = date.today()
    if today.day >= 20:
        return []  # Only warn before the 20th

    month_str = today.replace(day=1).isoformat()
    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/months/{month_str}"
    resp = httpx.get(url, headers=HEADERS)
    resp.raise_for_status()
    categories = resp.json()["data"]["month"].get("categories", [])

    warnings = []
    for cat in categories:
        if cat.get("hidden") or cat.get("deleted"):
            continue
        budgeted = cat["budgeted"]
        activity = abs(cat["activity"])
        if budgeted <= 0:
            continue

        percent_used = (activity / budgeted) * 100
        if percent_used > 80:
            import calendar as cal_mod
            _, days_in_month = cal_mod.monthrange(today.year, today.month)
            warnings.append({
                "category_name": cat["name"],
                "spent": activity / 1000,
                "budgeted": budgeted / 1000,
                "percent_used": round(percent_used, 1),
                "days_remaining": days_in_month - today.day,
            })

    return warnings


def check_uncategorized_pileup() -> dict | None:
    """Check for 3+ uncategorized transactions older than 48 hours.

    Returns {count, total_amount, oldest_date} or None.
    """
    today = date.today()
    since = today.replace(day=1).isoformat()
    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/transactions"
    resp = httpx.get(url, headers=HEADERS, params={"since_date": since, "type": "uncategorized"})
    resp.raise_for_status()
    txns = resp.json()["data"]["transactions"]

    # Filter to transactions older than 48 hours
    cutoff = (datetime.now(tz=ZoneInfo("America/Los_Angeles")) - timedelta(hours=48)).date().isoformat()
    old_txns = [t for t in txns if t["date"] <= cutoff]

    if len(old_txns) >= 3:
        total = sum(abs(t["amount"]) for t in old_txns) / 1000
        oldest = min(t["date"] for t in old_txns)
        return {"count": len(old_txns), "total_amount": total, "oldest_date": oldest}

    return None


def check_spending_anomalies() -> list:
    """Check if any category is 50%+ above its 3-month rolling average.

    Returns list of dicts: {category_name, current_amount, average_amount, percent_above}
    """
    today = date.today()
    months = []
    for i in range(3):
        d = today.replace(day=1) - timedelta(days=1)  # Go to prev month end
        for _ in range(i):
            d = d.replace(day=1) - timedelta(days=1)
        months.append(d.replace(day=1).isoformat())

    # Also need months offset correctly - let's recalculate
    months = []
    d = today.replace(day=1)
    for i in range(1, 4):  # Previous 3 months
        d_prev = (d - timedelta(days=1)).replace(day=1)
        months.append(d_prev.isoformat())
        d = d_prev

    # Gather activity per category for past 3 months
    history: dict[str, list[float]] = {}  # name → [activity1, activity2, activity3]
    for m in months:
        url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/months/{m}"
        resp = httpx.get(url, headers=HEADERS)
        resp.raise_for_status()
        cats = resp.json()["data"]["month"].get("categories", [])
        for cat in cats:
            if cat.get("hidden") or cat.get("deleted"):
                continue
            name = cat["name"]
            if name not in history:
                history[name] = []
            history[name].append(abs(cat["activity"]) / 1000)

    # Get current month
    current_month = today.replace(day=1).isoformat()
    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/months/{current_month}"
    resp = httpx.get(url, headers=HEADERS)
    resp.raise_for_status()
    current_cats = resp.json()["data"]["month"].get("categories", [])

    anomalies = []
    for cat in current_cats:
        if cat.get("hidden") or cat.get("deleted"):
            continue
        name = cat["name"]
        current = abs(cat["activity"]) / 1000
        if name in history and len(history[name]) >= 2 and current > 0:
            avg = sum(history[name]) / len(history[name])
            if avg > 0 and current > avg * 1.5:
                anomalies.append({
                    "category_name": name,
                    "current_amount": round(current, 2),
                    "average_amount": round(avg, 2),
                    "percent_above": round(((current - avg) / avg) * 100, 1),
                })

    return anomalies


def check_savings_goals() -> list:
    """Check if savings goals are falling behind expected pace.

    Returns list of dicts: {category_name, goal_target, funded, shortfall, percent_complete, expected_percent}
    """
    today = date.today()
    import calendar as cal_mod
    _, days_in_month = cal_mod.monthrange(today.year, today.month)
    expected_progress = (today.day / days_in_month) * 100

    current_month = today.replace(day=1).isoformat()
    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/months/{current_month}"
    resp = httpx.get(url, headers=HEADERS)
    resp.raise_for_status()
    categories = resp.json()["data"]["month"].get("categories", [])

    gaps = []
    for cat in categories:
        if not cat.get("goal_type"):
            continue
        pct_complete = cat.get("goal_percentage_complete", 0) or 0
        target = (cat.get("goal_target") or 0) / 1000
        funded = (cat.get("goal_overall_funded") or 0) / 1000

        # Behind by more than 15 percentage points
        if pct_complete < (expected_progress - 15) and target > 0:
            gaps.append({
                "category_name": cat["name"],
                "goal_target": target,
                "funded": funded,
                "shortfall": round(target - funded, 2),
                "percent_complete": pct_complete,
                "expected_percent": round(expected_progress, 1),
            })

    return gaps
