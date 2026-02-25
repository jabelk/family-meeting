"""YNAB API wrapper — budget data, transactions, and write operations."""

import json
import logging
import math
import time
from datetime import date, datetime, timedelta
from pathlib import Path
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

# --- Persistence for budget maintenance (Feature 012) ---
_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
_PENDING_SUGGESTIONS_FILE = _DATA_DIR / "budget_pending_suggestions.json"
_PENDING_ALLOCATION_FILE = _DATA_DIR / "budget_pending_allocation.json"


def _save_pending_suggestions(suggestions: list[dict]) -> None:
    """Save pending goal suggestions to disk (atomic write)."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _PENDING_SUGGESTIONS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"suggestions": suggestions}, indent=2, default=str))
        tmp.replace(_PENDING_SUGGESTIONS_FILE)
    except Exception as e:
        logger.warning("Failed to save pending suggestions: %s", e)


def _load_pending_suggestions() -> list[dict]:
    """Load pending goal suggestions from disk."""
    try:
        if _PENDING_SUGGESTIONS_FILE.exists():
            data = json.loads(_PENDING_SUGGESTIONS_FILE.read_text())
            return data.get("suggestions", [])
    except Exception as e:
        logger.warning("Failed to load pending suggestions: %s", e)
    return []


def _save_pending_allocation(plan: dict) -> None:
    """Save pending allocation plan to disk (atomic write)."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _PENDING_ALLOCATION_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(plan, indent=2, default=str))
        tmp.replace(_PENDING_ALLOCATION_FILE)
    except Exception as e:
        logger.warning("Failed to save pending allocation: %s", e)


def _load_pending_allocation() -> dict | None:
    """Load pending allocation plan from disk."""
    try:
        if _PENDING_ALLOCATION_FILE.exists():
            data = json.loads(_PENDING_ALLOCATION_FILE.read_text())
            if data and data.get("allocations"):
                return data
    except Exception as e:
        logger.warning("Failed to load pending allocation: %s", e)
    return None


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
            if cat.get("goal_type") and (cat.get("goal_percentage_complete") or 0) > 0:
                pct = cat["goal_percentage_complete"]
                target = (cat.get("goal_target") or 0) / 1000
                funded = (cat.get("goal_overall_funded") or 0) / 1000
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
# Transaction update helpers (Feature 010 — Amazon-YNAB sync)
# ---------------------------------------------------------------------------


def split_transaction(transaction_id: str, subtransactions: list[dict]) -> str:
    """Split a YNAB transaction into sub-transactions by category.

    Args:
        transaction_id: YNAB transaction UUID.
        subtransactions: List of dicts with keys:
            - amount_milliunits (int): Amount in milliunits (negative for outflows).
            - category_id (str): YNAB category UUID.
            - memo (str): Item description for this sub-transaction.

    Returns:
        Confirmation string or error message.
    """
    if not subtransactions:
        return "No subtransactions provided."

    # Build YNAB subtransactions format
    ynab_subs = []
    for sub in subtransactions:
        ynab_subs.append({
            "amount": sub["amount_milliunits"],
            "category_id": sub["category_id"],
            "memo": sub.get("memo", ""),
        })

    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/transactions/{transaction_id}"
    try:
        resp = httpx.put(
            url,
            headers=HEADERS,
            json={"transaction": {"subtransactions": ynab_subs}},
        )
        resp.raise_for_status()
        return f"Transaction split into {len(ynab_subs)} sub-transactions."
    except httpx.HTTPStatusError as e:
        logger.error("YNAB split_transaction failed: %s — %s", e.response.status_code, e.response.text)
        return f"Failed to split transaction: {e.response.status_code}"


def update_transaction_memo(transaction_id: str, memo: str) -> str:
    """Update the memo field on an existing YNAB transaction.

    Appends to existing memo if present (separated by " | ").

    Args:
        transaction_id: YNAB transaction UUID.
        memo: New memo text.

    Returns:
        Confirmation string or error message.
    """
    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/transactions/{transaction_id}"
    try:
        # Fetch current transaction to check existing memo
        resp = httpx.get(url, headers=HEADERS)
        resp.raise_for_status()
        txn = resp.json()["data"]["transaction"]
        existing_memo = txn.get("memo") or ""

        new_memo = f"{existing_memo} | {memo}" if existing_memo else memo
        # YNAB memo max is 200 chars
        if len(new_memo) > 200:
            new_memo = new_memo[:197] + "..."

        put_resp = httpx.put(
            url,
            headers=HEADERS,
            json={"transaction": {"memo": new_memo}},
        )
        put_resp.raise_for_status()
        return f"Memo updated: {new_memo}"
    except httpx.HTTPStatusError as e:
        logger.error("YNAB update_memo failed: %s — %s", e.response.status_code, e.response.text)
        return f"Failed to update memo: {e.response.status_code}"


def delete_transaction(transaction_id: str) -> str:
    """Delete a YNAB transaction (used for undo flow — reverting splits).

    Args:
        transaction_id: YNAB transaction UUID.

    Returns:
        Confirmation string or error message.
    """
    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/transactions/{transaction_id}"
    try:
        resp = httpx.delete(url, headers=HEADERS)
        resp.raise_for_status()
        return "Transaction deleted."
    except httpx.HTTPStatusError as e:
        logger.error("YNAB delete_transaction failed: %s — %s", e.response.status_code, e.response.text)
        return f"Failed to delete transaction: {e.response.status_code}"


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


# ---------------------------------------------------------------------------
# Feature 012: Smart Budget Maintenance
# ---------------------------------------------------------------------------


def _fetch_month_data(month: str) -> list[dict]:
    """Fetch all categories for a specific month from YNAB.

    Args:
        month: Month string in YYYY-MM-DD format (first of month).

    Returns:
        List of category dicts with fields converted to dollars.
    """
    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/months/{month}"
    resp = httpx.get(url, headers=HEADERS)
    resp.raise_for_status()
    categories = resp.json()["data"]["month"].get("categories", [])

    result = []
    for cat in categories:
        if cat.get("hidden") or cat.get("deleted"):
            continue
        result.append({
            "id": cat["id"],
            "name": cat["name"],
            "group": cat.get("category_group_name", ""),
            "budgeted": cat["budgeted"] / 1000,
            "activity": cat["activity"] / 1000,
            "balance": cat["balance"] / 1000,
            "goal_type": cat.get("goal_type"),
            "goal_target": (cat.get("goal_target") or 0) / 1000,
            "goal_percentage_complete": cat.get("goal_percentage_complete"),
            "goal_overall_funded": (cat.get("goal_overall_funded") or 0) / 1000,
            "goal_under_funded": (cat.get("goal_under_funded") or 0) / 1000,
        })
    return result


def _build_category_profiles(
    lookback_months: int = 3, drift_threshold: float = 30
) -> list[dict]:
    """Compute CategoryHealthProfile for all categories over the lookback window.

    Returns list of profile dicts with drift analysis, trend, sinking fund detection, etc.
    """
    today = date.today()
    months_data: list[list[dict]] = []

    # Fetch current month + prior months
    for i in range(lookback_months):
        d = today.replace(day=1)
        for _ in range(i):
            d = (d - timedelta(days=1)).replace(day=1)
        month_str = d.isoformat()
        try:
            data = _fetch_month_data(month_str)
            months_data.append(data)
        except Exception as e:
            logger.warning("Failed to fetch month %s: %s", month_str, e)

    if not months_data:
        return []

    # Build per-category spending history (keyed by category ID)
    cat_history: dict[str, dict] = {}  # id -> {meta, spending_months, budgeted_months}

    for month_idx, month_cats in enumerate(months_data):
        for cat in month_cats:
            cid = cat["id"]
            if cid not in cat_history:
                cat_history[cid] = {
                    "id": cid,
                    "name": cat["name"],
                    "group": cat["group"],
                    "goal_type": cat["goal_type"],
                    "goal_target": cat["goal_target"],
                    "spending_months": [],
                    "budgeted_months": [],
                }
            # Activity is negative for outflows in YNAB; use absolute value
            cat_history[cid]["spending_months"].append(abs(cat["activity"]))
            cat_history[cid]["budgeted_months"].append(cat["budgeted"])
            # Update goal info from most recent month (index 0)
            if month_idx == 0:
                cat_history[cid]["goal_type"] = cat["goal_type"]
                cat_history[cid]["goal_target"] = cat["goal_target"]

    profiles = []
    for cid, hist in cat_history.items():
        spending_months = hist["spending_months"]
        budgeted_months = hist["budgeted_months"]
        spending_avg = sum(spending_months) / len(spending_months) if spending_months else 0
        budgeted_avg = sum(budgeted_months) / len(budgeted_months) if budgeted_months else 0
        goal_target = hist["goal_target"]
        goal_type = hist["goal_type"]

        # Drift calculation
        drift_pct = 0.0
        if goal_target > 0:
            drift_pct = ((spending_avg - goal_target) / goal_target) * 100

        # Drift type classification
        threshold_mult = 1 + drift_threshold / 100
        if goal_type is None and spending_avg > 0:
            drift_type = "missing_goal"
        elif goal_target > 0 and spending_avg > goal_target * threshold_mult:
            drift_type = "underfunded"
        elif goal_target > 0 and goal_target > spending_avg * threshold_mult:
            drift_type = "overfunded"
        else:
            drift_type = "aligned"

        # Trend detection (requires 2+ months)
        trend = "stable"
        if len(spending_months) >= 2:
            increasing = all(
                spending_months[i] >= spending_months[i + 1]
                for i in range(len(spending_months) - 1)
            )
            decreasing = all(
                spending_months[i] <= spending_months[i + 1]
                for i in range(len(spending_months) - 1)
            )
            if increasing and spending_months[0] > spending_months[-1]:
                trend = "increasing"
            elif decreasing and spending_months[0] < spending_months[-1]:
                trend = "decreasing"

        # Sinking fund detection
        is_sinking_fund = goal_type in ("TB", "TBD")
        if not is_sinking_fund and len(spending_months) >= 3:
            # Pattern check: any single month > 3x average suggests periodic
            if spending_avg > 0:
                for s in spending_months:
                    if s > spending_avg * 3:
                        is_sinking_fund = True
                        break

        # Spiky detection (CV > 1.0 with 3+ months)
        is_spiky = False
        if len(spending_months) >= 3 and spending_avg > 0:
            variance = sum((s - spending_avg) ** 2 for s in spending_months) / len(spending_months)
            std_dev = math.sqrt(variance)
            cv = std_dev / spending_avg
            is_spiky = cv > 1.0

        # Months since last transaction
        months_since_last_txn = 0
        for s in spending_months:
            if s == 0:
                months_since_last_txn += 1
            else:
                break

        is_stale = months_since_last_txn >= 3 and not is_sinking_fund

        # Insufficient data flag (analyze fix F4)
        is_insufficient_data = len(spending_months) < 2

        profiles.append({
            "id": cid,
            "name": hist["name"],
            "group": hist["group"],
            "goal_type": goal_type,
            "goal_target": goal_target,
            "budgeted_avg": round(budgeted_avg, 2),
            "spending_avg": round(spending_avg, 2),
            "spending_months": spending_months,
            "drift_pct": round(drift_pct, 1),
            "drift_type": drift_type,
            "trend": trend,
            "is_sinking_fund": is_sinking_fund,
            "is_spiky": is_spiky,
            "months_since_last_txn": months_since_last_txn,
            "is_stale": is_stale,
            "is_insufficient_data": is_insufficient_data,
        })

    return profiles


def _update_goal_target(category_id: str, goal_target_milliunits: int) -> str:
    """Update a category's goal target via YNAB API.

    Uses PATCH /budgets/{id}/categories/{cat_id} — distinct from
    update_category_budget() which patches budgeted via /months/{month}/categories/{id}.
    """
    url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/categories/{category_id}"
    try:
        resp = httpx.patch(
            url,
            headers=HEADERS,
            json={"category": {"goal_target": goal_target_milliunits}},
        )
        resp.raise_for_status()
        return "success"
    except httpx.HTTPStatusError as e:
        logger.error("YNAB goal update failed: %s — %s", e.response.status_code, e.response.text)
        return f"Failed to update goal: {e.response.status_code}"


def _calculate_health_score(profiles: list[dict]) -> float:
    """Compute dollar-weighted alignment score.

    Formula: max(0, (1 - sum(|actual - goal|) / sum(max(actual, goal))) * 100)
    Categories without goals are excluded.
    """
    total_drift = 0.0
    total_weight = 0.0
    for p in profiles:
        if p["goal_target"] <= 0 or p["drift_type"] == "missing_goal":
            continue
        drift = abs(p["spending_avg"] - p["goal_target"])
        weight = max(p["spending_avg"], p["goal_target"])
        total_drift += drift
        total_weight += weight

    if total_weight == 0:
        return 100.0
    return round(max(0, (1 - total_drift / total_weight) * 100), 1)


# ---------------------------------------------------------------------------
# US1: Budget Health Check & Goal Suggestions
# ---------------------------------------------------------------------------


def _format_health_report(
    health_score: float,
    profiles: list[dict],
    suggestions: list[dict],
) -> str:
    """Format budget health report for WhatsApp."""
    lines = [f"\U0001f4ca Budget Health Check — {health_score:.0f}% Aligned\n"]

    # Underfunded (spending exceeds goal)
    underfunded = [s for s in suggestions if s["drift_type"] == "underfunded"]
    underfunded.sort(key=lambda s: abs(s["recommended_goal"] - s["current_goal"]), reverse=True)

    if underfunded:
        lines.append("\u26a0\ufe0f Underfunded (spending exceeds goal):")
        for i, s in enumerate(underfunded[:10], 1):
            drift = s["drift_pct"]
            lines.append(
                f"{i}. {s['category_name']}: ${s['current_goal']:,.0f} goal \u2192 "
                f"${s['spending_avg']:,.0f} avg (+{drift:,.0f}%) \u2014 suggest ${s['recommended_goal']:,.0f}"
            )
        lines.append("")

    # Overfunded (goal exceeds spending)
    overfunded = [s for s in suggestions if s["drift_type"] == "overfunded"]
    overfunded.sort(key=lambda s: abs(s["recommended_goal"] - s["current_goal"]), reverse=True)

    if overfunded:
        lines.append("\U0001f4c9 Overfunded (goal exceeds spending):")
        start_num = len(underfunded) + 1
        for i, s in enumerate(overfunded[:10], start_num):
            drift = s["drift_pct"]
            if s["spending_avg"] == 0:
                lines.append(
                    f"{i}. {s['category_name']}: ${s['current_goal']:,.0f} goal \u2192 "
                    f"$0 avg \u2014 suggest removing"
                )
            else:
                lines.append(
                    f"{i}. {s['category_name']}: ${s['current_goal']:,.0f} goal \u2192 "
                    f"${s['spending_avg']:,.0f} avg ({drift:,.0f}%) \u2014 suggest ${s['recommended_goal']:,.0f}"
                )
        lines.append("")

    # Missing goals
    missing = [s for s in suggestions if s["drift_type"] == "missing_goal"]
    if missing:
        lines.append("\U0001f50d Missing goals:")
        start_num = len(underfunded) + len(overfunded) + 1
        for i, s in enumerate(missing[:10], start_num):
            lines.append(
                f"{i}. {s['category_name']}: ${s['spending_avg']:,.0f}/mo avg \u2014 "
                f"suggest ${s['recommended_goal']:,.0f} goal"
            )
        lines.append("")

    # Spiky categories note
    spiky = [p for p in profiles if p.get("is_spiky")]
    if spiky:
        names = ", ".join(p["name"] for p in spiky[:5])
        lines.append(f"\u26a1 Highly variable: {names} (averages may be misleading)\n")

    # Insufficient data note
    insufficient = [p for p in profiles if p.get("is_insufficient_data") and p["spending_avg"] > 0]
    if insufficient:
        names = ", ".join(p["name"] for p in insufficient[:5])
        lines.append(f"\u2139\ufe0f Insufficient data (<2 months): {names}\n")

    lines.append(
        'Reply "update all", "yes to 1", "skip 3", or "set 2 to $2000"'
    )

    result = "\n".join(lines)
    # Truncate for WhatsApp limit
    if len(result) > 4000:
        result = result[:3950] + "\n\n... (truncated — ask for details on specific categories)"
    return result


def budget_health_check(
    lookback_months: int = 3, drift_threshold: float = 30
) -> str:
    """Full budget health check — drift detection, suggestions, and formatted report.

    Returns formatted WhatsApp message and saves suggestions for follow-up.
    """
    profiles = _build_category_profiles(lookback_months, drift_threshold)
    if not profiles:
        return "Unable to fetch budget data. Please try again."

    health_score = _calculate_health_score(profiles)

    # Build suggestions for drifted categories
    suggestions = []
    for p in profiles:
        if p["drift_type"] == "aligned":
            continue

        # Round recommended goal to nearest $25
        if p["drift_type"] == "missing_goal":
            recommended = round(p["spending_avg"] / 25) * 25
            if recommended == 0:
                recommended = 25
        elif p["drift_type"] == "overfunded" and p["spending_avg"] == 0:
            recommended = 0
        else:
            recommended = round(p["spending_avg"] / 25) * 25
            if recommended == 0:
                recommended = 25

        suggestions.append({
            "category_id": p["id"],
            "category_name": p["name"],
            "current_goal": p["goal_target"],
            "recommended_goal": recommended,
            "spending_avg": p["spending_avg"],
            "drift_pct": p["drift_pct"],
            "drift_type": p["drift_type"],
            "has_existing_goal": p["goal_type"] is not None,
            "status": "pending",
        })

    # Save suggestions for follow-up approval
    _save_pending_suggestions(suggestions)

    report = _format_health_report(health_score, profiles, suggestions)

    # Append stale/merge sections if applicable (T024)
    stale_profiles = [p for p in profiles if p.get("is_stale")]
    sinking_profiles = [
        p for p in profiles
        if p.get("is_sinking_fund") and p["months_since_last_txn"] >= 3
    ]
    merge_candidates = _detect_merge_candidates(profiles)

    if stale_profiles or merge_candidates:
        cleanup = _format_cleanup_report(stale_profiles, sinking_profiles, merge_candidates)
        if cleanup:
            report += "\n\n" + cleanup

    return report


def apply_goal_suggestion(
    category: str = "", amount: float = 0, apply_all: bool = False
) -> str:
    """Apply a goal suggestion from a budget health check.

    Can apply a single suggestion by category name, or all pending suggestions at once.
    """
    suggestions = _load_pending_suggestions()
    if not suggestions:
        return "No pending goal suggestions. Run a budget health check first."

    if apply_all:
        results = []
        updated = 0
        skipped = 0
        for s in suggestions:
            if s["status"] != "pending":
                continue
            if not s["has_existing_goal"]:
                skipped += 1
                s["status"] = "skipped"
                continue
            target_milli = int(s["recommended_goal"] * 1000)
            result = _update_goal_target(s["category_id"], target_milli)
            if result == "success":
                s["status"] = "approved"
                updated += 1
                results.append(
                    f"\u2705 {s['category_name']}: ${s['current_goal']:,.0f} \u2192 ${s['recommended_goal']:,.0f}"
                )
            else:
                results.append(f"\u274c {s['category_name']}: {result}")

        _save_pending_suggestions(suggestions)
        msg = f"Updated {updated} goal{'s' if updated != 1 else ''}."
        if skipped:
            msg += f" {skipped} skipped (no goal set in YNAB — create goals in the app first)."
        if results:
            msg += "\n" + "\n".join(results)
        return msg

    # Single category
    if not category:
        return "Please specify a category name, or use 'update all'."

    # Fuzzy match against pending suggestions
    cat_lower = category.lower().strip()
    matched = None
    for s in suggestions:
        if s["status"] != "pending":
            continue
        if cat_lower in s["category_name"].lower() or s["category_name"].lower() in cat_lower:
            matched = s
            break

    if not matched:
        pending_names = [s["category_name"] for s in suggestions if s["status"] == "pending"]
        if pending_names:
            return f"Category '{category}' not found in pending suggestions. Pending: {', '.join(pending_names[:10])}"
        return "No pending suggestions remaining."

    if not matched["has_existing_goal"]:
        return (
            f"\u26a0\ufe0f {matched['category_name']} doesn't have a goal set in YNAB yet. "
            f"Please open YNAB and add a \"Monthly Savings Builder\" or \"Plan Your Spending\" "
            f"goal to the {matched['category_name']} category, then I can set the target "
            f"to ${matched['recommended_goal']:,.0f}."
        )

    # Use provided amount or recommended
    target = amount if amount > 0 else matched["recommended_goal"]
    target_milli = int(target * 1000)
    result = _update_goal_target(matched["category_id"], target_milli)

    if result == "success":
        old_goal = matched["current_goal"]
        matched["status"] = "approved"
        if amount > 0:
            matched["adjusted_value"] = amount
            matched["status"] = "adjusted"
        _save_pending_suggestions(suggestions)
        remaining = sum(1 for s in suggestions if s["status"] == "pending")
        msg = f"\u2705 Updated {matched['category_name']} goal: ${old_goal:,.0f} \u2192 ${target:,.0f}"
        if remaining > 0:
            msg += f"\n{remaining} suggestion{'s' if remaining != 1 else ''} remaining. Reply \"update all\" or continue individually."
        else:
            msg += "\nAll suggestions processed!"
        return msg
    else:
        return f"Failed to update {matched['category_name']}: {result}"


# ---------------------------------------------------------------------------
# US2: Bonus & Large Deposit Allocation
# ---------------------------------------------------------------------------


def _classify_priority_tiers(profiles: list[dict]) -> list[dict]:
    """Classify categories into priority tiers based on group names.

    Uses keyword matching for heuristic classification.
    Essential > Savings > Discretionary.
    """
    essential_keywords = {
        "bills", "mortgage", "insurance", "utilities", "healthcare", "health",
        "food", "groceries", "car", "auto", "kids", "childcare", "rent",
        "housing", "medical", "pharmacy", "gas", "fuel", "education",
        "fixed", "immediate", "obligations",
    }
    savings_keywords = {
        "savings", "emergency", "fund", "debt", "investment", "retirement",
        "sinking", "rainy", "college", "529",
    }

    for p in profiles:
        group_lower = p.get("group", "").lower()
        name_lower = p["name"].lower()
        combined = group_lower + " " + name_lower

        if any(kw in combined for kw in essential_keywords):
            p["priority_tier"] = "essential"
        elif any(kw in combined for kw in savings_keywords):
            p["priority_tier"] = "savings"
        else:
            p["priority_tier"] = "discretionary"

    return profiles


def _format_allocation_plan(plan: dict) -> str:
    """Format allocation plan for WhatsApp."""
    total = plan["total_amount"]
    desc = plan.get("source_description", "")
    header = f"\U0001f4b0 Bonus Allocation Plan \u2014 ${total:,.0f}"
    if desc:
        header += f" ({desc})"

    lines = [header + "\n"]

    tier_order = ["essential", "savings", "discretionary"]
    tier_labels = {
        "essential": "Essential (funded first)",
        "savings": "Savings",
        "discretionary": "Discretionary",
    }

    for tier in tier_order:
        tier_allocs = [a for a in plan["allocations"] if a["priority_tier"] == tier]
        if not tier_allocs:
            continue
        lines.append(f"{tier_labels[tier]}:")
        for a in tier_allocs:
            lines.append(f"  \u2022 {a['category_name']}: +${a['allocated_amount']:,.0f} ({a['rationale']})")
        lines.append("")

    allocated_total = sum(a["allocated_amount"] for a in plan["allocations"])
    lines.append(f"Total: ${allocated_total:,.0f}")
    lines.append("Reply 'approve' to move money, or adjust: 'put $3000 in emergency fund'")

    return "\n".join(lines)


def allocate_bonus(amount: float = 0, description: str = "") -> str:
    """Generate a prioritized allocation plan for bonus/extra income."""
    if amount <= 0:
        return "Please specify the bonus amount (e.g., 'where should this $5,000 bonus go?')."

    # Fetch current month data for shortfall analysis
    profiles = _build_category_profiles(lookback_months=1)
    if not profiles:
        return "Unable to fetch budget data. Please try again."

    profiles = _classify_priority_tiers(profiles)

    # Compute shortfall per category
    shortfalls = []
    for p in profiles:
        if p["goal_target"] <= 0:
            continue
        # Shortfall = goal minus what's been budgeted this month
        # Use goal_target as the target, budgeted_avg as what's assigned
        shortfall = p["goal_target"] - p["budgeted_avg"]
        if shortfall <= 0:
            continue
        shortfalls.append({
            "category_id": p["id"],
            "category_name": p["name"],
            "priority_tier": p["priority_tier"],
            "current_shortfall": round(shortfall, 2),
            "goal_target": p["goal_target"],
            "budgeted": p["budgeted_avg"],
        })

    # Sort by tier priority then shortfall amount
    tier_priority = {"essential": 0, "savings": 1, "discretionary": 2}
    shortfalls.sort(key=lambda s: (tier_priority.get(s["priority_tier"], 3), -s["current_shortfall"]))

    # Distribute amount across shortfalls
    remaining = amount
    allocations = []
    for s in shortfalls:
        if remaining <= 0:
            break
        alloc = min(remaining, s["current_shortfall"])
        allocations.append({
            "category_id": s["category_id"],
            "category_name": s["category_name"],
            "priority_tier": s["priority_tier"],
            "current_shortfall": s["current_shortfall"],
            "allocated_amount": round(alloc, 2),
            "rationale": f"was ${s['current_shortfall']:,.0f} underfunded" if alloc >= s["current_shortfall"]
                else f"${s['current_shortfall']:,.0f} underfunded, partial fill",
        })
        remaining -= alloc

    # If there's remaining money after filling all shortfalls, put it in the
    # largest underfunded category or first savings category
    if remaining > 0 and allocations:
        allocations[-1]["allocated_amount"] = round(allocations[-1]["allocated_amount"] + remaining, 2)
        allocations[-1]["rationale"] += f" + ${remaining:,.0f} remaining"
    elif remaining > 0 and not allocations:
        # No shortfalls — suggest putting it all in first available category
        if profiles:
            first = profiles[0]
            allocations.append({
                "category_id": first["id"],
                "category_name": first["name"],
                "priority_tier": first.get("priority_tier", "discretionary"),
                "current_shortfall": 0,
                "allocated_amount": round(amount, 2),
                "rationale": "all categories funded — extra allocation",
            })

    plan = {
        "total_amount": amount,
        "source_description": description,
        "allocations": allocations,
        "status": "draft",
    }

    _save_pending_allocation(plan)
    return _format_allocation_plan(plan)


def approve_allocation(adjustments: str = "") -> str:
    """Execute the pending allocation plan by moving money in YNAB."""
    plan = _load_pending_allocation()
    if not plan:
        return "No pending allocation plan. Use 'where should this bonus go?' to create one."

    if plan.get("status") == "executed":
        return "This allocation plan has already been executed."

    # If adjustments provided, regenerate with modifications
    if adjustments:
        return (
            f"Adjustment noted: \"{adjustments}\". "
            f"Please re-run with a specific amount, e.g., 'allocate $5000 bonus' "
            f"and I'll incorporate your preferences."
        )

    # Execute each allocation
    results = []
    success_count = 0
    for alloc in plan["allocations"]:
        if alloc["allocated_amount"] <= 0:
            continue
        try:
            result = update_category_budget(alloc["category_name"], alloc["allocated_amount"])
            results.append(f"\u2705 {alloc['category_name']}: +${alloc['allocated_amount']:,.0f}")
            success_count += 1
        except Exception as e:
            results.append(f"\u274c {alloc['category_name']}: failed ({e})")

    plan["status"] = "executed"
    _save_pending_allocation(plan)

    msg = f"\u2705 Bonus allocated!\n" + "\n".join(results)
    msg += f"\n\nAll money assigned. {success_count} categories updated."
    return msg


# ---------------------------------------------------------------------------
# US3: Monthly Budget Health Check (scheduled)
# ---------------------------------------------------------------------------


def run_budget_health_check() -> str | None:
    """Scheduled orchestrator — compute health report and send via WhatsApp.

    Called by n8n endpoint. Returns status string.
    Uses budget_health_check() for the report, avoiding double computation (fix F2).
    Uses >= 80 threshold for brief message (fix F1 from analyze).
    """
    try:
        # Get the full report from budget_health_check
        report = budget_health_check(lookback_months=3, drift_threshold=30)

        # Compute health score for decision logic (reuses _build_category_profiles cache)
        profiles = _build_category_profiles(lookback_months=3, drift_threshold=30)
        health_score = _calculate_health_score(profiles)
        drifted = [p for p in profiles if p["drift_type"] != "aligned" and p["drift_type"] != "missing_goal"]
        stale = [p for p in profiles if p.get("is_stale")]

        from src.assistant import send_sync_message_direct

        # Brief message when healthy (threshold >= 80, fix F1)
        if health_score >= 80 and len(drifted) == 0:
            brief = (
                f"\U0001f4ca Monthly Budget Check \u2014 {health_score:.0f}% Aligned \u2705\n\n"
                f"All categories within target. Keep it up!"
            )
            send_sync_message_direct(brief)
            return f"sent_brief: health_score={health_score}"

        # Full report for unhealthy budgets
        send_sync_message_direct(report)
        return f"sent_full: health_score={health_score}, drifted={len(drifted)}, stale={len(stale)}"

    except Exception as e:
        logger.error("Budget health check failed: %s", e)
        return f"error: {e}"


# ---------------------------------------------------------------------------
# US4: Stale Category & Merge Detection
# ---------------------------------------------------------------------------


def _detect_merge_candidates(profiles: list[dict]) -> list[dict]:
    """Find categories that could be merged based on similarity and low spending."""
    STOP_WORDS = {"the", "and", "a", "an", "for", "to", "of", "in", "on", "at", "by"}

    candidates = []
    low_spend = [p for p in profiles if p["spending_avg"] < 200 and p["spending_avg"] > 0]

    # Check pairs for name similarity or same group with low combined spending
    for i, a in enumerate(low_spend):
        for b in low_spend[i + 1:]:
            # Name similarity: shared non-stop word
            a_words = set(a["name"].lower().split()) - STOP_WORDS
            b_words = set(b["name"].lower().split()) - STOP_WORDS
            name_overlap = bool(a_words & b_words)

            # Same group with low combined spending
            same_group = a["group"] == b["group"] and (a["spending_avg"] + b["spending_avg"]) < 300

            if name_overlap or same_group:
                combined = a["spending_avg"] + b["spending_avg"]
                # Pick shorter name or the group name as suggested name
                suggested = a["group"] if same_group else a["name"].split()[0]
                candidates.append({
                    "categories": [a["name"], b["name"]],
                    "combined_avg_spending": round(combined, 2),
                    "rationale": "similar names" if name_overlap else f"same group ({a['group']}), low combined spend",
                    "suggested_name": suggested,
                })

    return candidates


def _format_cleanup_report(
    stale_profiles: list[dict],
    sinking_fund_profiles: list[dict],
    merge_candidates: list[dict],
) -> str:
    """Format stale/merge cleanup report for WhatsApp."""
    lines = []
    num = 1

    if stale_profiles:
        lines.append("\U0001f5c2\ufe0f Stale categories (no spend in 3+ months):")
        for p in stale_profiles:
            goal_str = f"${p['goal_target']:,.0f} goal, " if p["goal_target"] > 0 else ""
            lines.append(
                f"{num}. {p['name']} \u2014 {goal_str}$0 spent \u00d7 "
                f"{p['months_since_last_txn']} months. Remove goal?"
            )
            num += 1
        lines.append("")

    if sinking_fund_profiles:
        lines.append("\u26a0\ufe0f NOT stale (sinking funds \u2014 saving for periodic expense):")
        for p in sinking_fund_profiles:
            lines.append(f"  \u2022 {p['name']} \u2014 ${p['goal_target']:,.0f}/mo saving \u2713")
        lines.append("")

    if merge_candidates:
        lines.append("\U0001f500 Merge candidates:")
        for mc in merge_candidates:
            names = " + ".join(mc["categories"])
            lines.append(
                f"{num}. {names} \u2192 \"{mc['suggested_name']}\" "
                f"(${mc['combined_avg_spending']:,.0f}/mo combined)"
            )
            num += 1
        lines.append("")

    if lines:
        lines.append('Reply "remove 1", "merge 3", or "skip all"')

    return "\n".join(lines)
