"""Email-YNAB Smart Sync — PayPal, Venmo, Apple email parsing, matching, and sync orchestration.

Extends Feature 010 (Amazon-YNAB sync) to parse confirmation emails from PayPal,
Venmo, and Apple, match them to YNAB transactions, enrich memos with actual
merchant/service names, and classify into budget categories.
"""

import json
import logging
import os
import time
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from src.tools.amazon_sync import (
    _get_gmail_service,
    _extract_html_body,
    _strip_html,
    classify_item,
    load_category_mappings,
    save_category_mapping,
    SyncRecord,
    MatchedItem,
    CategoryMapping,
    load_sync_records,
    save_sync_record,
    is_transaction_processed,
    load_sync_config,
    save_sync_config,
    lookup_cached_category,
    _load_json,
    _save_json,
    _DATA_DIR,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pending suggestions file (separate from Amazon sync)
# ---------------------------------------------------------------------------

_EMAIL_PENDING_SUGGESTIONS_FILE = _DATA_DIR / "email_pending_suggestions.json"

# ---------------------------------------------------------------------------
# Provider configuration constants
# ---------------------------------------------------------------------------

PROVIDER_CONFIGS = {
    "paypal": {
        "gmail_query": "from:service@paypal.com OR from:paypal@mail.paypal.com",
        "ynab_payee_filter": "paypal",
        "memo_prefix": "via PayPal",
        "label": "PayPal",
    },
    "venmo": {
        "gmail_query": "from:venmo@venmo.com",
        "ynab_payee_filter": "venmo",
        "memo_prefix": "",
        "label": "Venmo",
    },
    "apple": {
        "gmail_query": "from:no_reply@email.apple.com",
        "ynab_payee_filter": "apple",
        "memo_prefix": "",
        "label": "Apple",
    },
}

# Providers to exclude (handled by Feature 010)
_EXCLUDED_PAYEE_KEYWORDS = ["amazon", "amzn"]


# ---------------------------------------------------------------------------
# Phase 2: Foundational — T003, T004, T005
# ---------------------------------------------------------------------------

def find_provider_transactions(provider: str, days: int = 30) -> list[dict]:
    """Fetch YNAB transactions matching a provider's payee filter, excluding already-processed.

    Returns list of unprocessed transaction dicts with id, amount, date, memo, payee_name.
    """
    import httpx
    from src.tools import ynab

    config = PROVIDER_CONFIGS[provider]
    payee_filter = config["ynab_payee_filter"]

    since_date = (date.today() - timedelta(days=days)).isoformat()
    url = f"{ynab.BASE_URL}/budgets/{ynab.YNAB_BUDGET_ID}/transactions"
    resp = httpx.get(url, headers=ynab.HEADERS, params={"since_date": since_date})
    resp.raise_for_status()
    txns = resp.json()["data"]["transactions"]

    results = []
    for t in txns:
        payee = (t.get("payee_name") or "").lower()
        # Skip if payee doesn't match this provider
        if payee_filter not in payee:
            continue
        # Skip Amazon/AMZN (handled by Feature 010)
        if any(excl in payee for excl in _EXCLUDED_PAYEE_KEYWORDS):
            continue
        # Skip already-processed
        if is_transaction_processed(t["id"]):
            continue
        results.append({
            "id": t["id"],
            "amount": t["amount"],  # milliunits
            "date": t["date"],
            "memo": t.get("memo") or "",
            "payee_name": t.get("payee_name") or "",
            "category_id": t.get("category_id") or "",
            "category_name": t.get("category_name") or "",
            "account_id": t.get("account_id") or "",
        })

    logger.info("Found %d unprocessed %s transactions in YNAB", len(results), provider)
    return results


def _search_provider_emails(provider: str, days: int = 30) -> list[dict]:
    """Search Gmail for confirmation emails from a provider.

    Returns list of {email_id, email_date, html_body, stripped_text}.
    """
    config = PROVIDER_CONFIGS[provider]
    gmail_query = config["gmail_query"]

    after_date = (date.today() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"{gmail_query} after:{after_date}"

    try:
        service = _get_gmail_service()
        results = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
        messages = results.get("messages", [])

        if not messages:
            logger.info("No %s emails found in last %d days", provider, days)
            return []

        emails = []
        for msg_meta in messages:
            msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()

            # Extract date from email headers
            email_date = ""
            for header in msg.get("payload", {}).get("headers", []):
                if header["name"].lower() == "date":
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(header["value"])
                        email_date = dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass
                    break

            html_body = _extract_html_body(msg)
            if not html_body:
                continue

            stripped = _strip_html(html_body)
            if not stripped.strip():
                continue

            emails.append({
                "email_id": msg_meta["id"],
                "email_date": email_date,
                "html_body": html_body,
                "stripped_text": stripped,
            })

        logger.info("Fetched %d %s emails from Gmail", len(emails), provider)
        return emails

    except RuntimeError as e:
        if "OAuth" in str(e):
            logger.error("Gmail OAuth token expired — %s sync skipped", provider)
            raise
        raise
    except Exception as e:
        logger.error("Gmail search failed for %s: %s", provider, e)
        return []


def match_emails_to_transactions(
    ynab_transactions: list[dict],
    parsed_emails: list[dict],
) -> list[dict]:
    """Match YNAB transactions to parsed email transactions by date (±3 days) and exact penny amount.

    parsed_emails: list of dicts from _parse_provider_emails, each with
                   merchant_name, amount, email_date, items, etc.

    Returns list of {ynab_transaction, matched_email, match_type}.
    """
    results = []
    used_emails = set()

    for txn in ynab_transactions:
        txn_amount = abs(txn["amount"])  # milliunits (positive)
        txn_date = date.fromisoformat(txn["date"])
        matched_email = None
        match_type = "unmatched"

        for i, email_txn in enumerate(parsed_emails):
            if i in used_emails:
                continue

            email_date_str = email_txn.get("email_date")
            if not email_date_str:
                continue

            try:
                email_date = date.fromisoformat(email_date_str)
            except ValueError:
                continue

            # Check date within ±3 days
            day_diff = abs((txn_date - email_date).days)
            if day_diff > 3:
                continue

            # Check exact penny match
            email_amount = email_txn.get("amount")
            if email_amount is not None:
                email_amount_milli = int(round(abs(float(email_amount)) * 1000))
                if email_amount_milli == txn_amount:
                    matched_email = email_txn
                    match_type = "exact_amount"
                    used_emails.add(i)
                    break

        results.append({
            "ynab_transaction": txn,
            "matched_email": matched_email,
            "match_type": match_type,
        })

    matched_count = sum(1 for r in results if r["matched_email"])
    logger.info("Matched %d/%d transactions to emails", matched_count, len(results))
    return results


# ---------------------------------------------------------------------------
# Phase 3 US1: Provider-specific parsers — T006, T007, T008
# ---------------------------------------------------------------------------

def _parse_paypal_email(stripped_text: str, email_date: str) -> list[dict]:
    """Parse a PayPal confirmation email into structured transaction data using Claude Haiku."""
    from anthropic import Anthropic
    from src.config import ANTHROPIC_API_KEY

    if len(stripped_text) > 15000:
        stripped_text = stripped_text[:15000]

    # Quick sanity check
    if "$" not in stripped_text:
        return []

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = (
        "Extract transaction details from this PayPal confirmation email.\n\n"
        "Return ONLY valid JSON — an array of transaction objects:\n"
        "[\n"
        "  {\n"
        '    "merchant_name": "actual merchant/store name (e.g., DoorDash, eBay seller name)",\n'
        '    "amount": 45.00,\n'
        '    "items": [{"title": "item name", "price": 45.00, "quantity": 1}],\n'
        '    "is_refund": false\n'
        "  }\n"
        "]\n\n"
        "RULES:\n"
        "- merchant_name is the ACTUAL business/merchant, not 'PayPal'\n"
        "- For refunds, set is_refund=true and amount as positive number\n"
        "- For multi-item purchases, list each item separately\n"
        "- amount is the total charged amount in dollars\n"
        "- If you can't extract details, return an empty array []\n\n"
        f"Email text:\n{stripped_text}"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        parsed = _extract_json_array(text)
        for txn in parsed:
            txn["provider"] = "paypal"
            txn["email_date"] = email_date
            txn.setdefault("items", [])
            txn.setdefault("is_refund", False)
            txn.setdefault("payment_note", "")
        return parsed
    except Exception as e:
        logger.warning("PayPal email parse failed: %s", e)
        return []


def _parse_venmo_email(stripped_text: str, email_date: str) -> list[dict]:
    """Parse a Venmo notification email into structured transaction data using Claude Haiku."""
    from anthropic import Anthropic
    from src.config import ANTHROPIC_API_KEY

    if len(stripped_text) > 15000:
        stripped_text = stripped_text[:15000]

    if "$" not in stripped_text:
        return []

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = (
        "Extract transaction details from this Venmo notification email.\n\n"
        "Return ONLY valid JSON — an array of transaction objects:\n"
        "[\n"
        "  {\n"
        '    "merchant_name": "recipient or sender name (e.g., Sarah M., Pizza Palace)",\n'
        '    "amount": 30.00,\n'
        '    "payment_note": "the payment note/description (e.g., dinner split, rent)",\n'
        '    "direction": "sent or received",\n'
        '    "is_refund": false\n'
        "  }\n"
        "]\n\n"
        "RULES:\n"
        "- merchant_name is the person or business name, not 'Venmo'\n"
        "- payment_note is the note the sender included with the payment\n"
        "- direction: 'sent' if user paid someone, 'received' if user got paid\n"
        "- For business payments, use the business name as merchant_name\n"
        "- amount is always positive (in dollars)\n"
        "- If you can't extract details, return an empty array []\n\n"
        f"Email text:\n{stripped_text}"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        parsed = _extract_json_array(text)
        for txn in parsed:
            txn["provider"] = "venmo"
            txn["email_date"] = email_date
            txn.setdefault("items", [{"title": txn.get("payment_note", "Venmo payment"), "price": txn.get("amount", 0), "quantity": 1}])
            txn.setdefault("is_refund", False)
            txn.setdefault("payment_note", "")
            # Detect business payments: if direction is "sent" and merchant name
            # looks like a business (not a person name), flag it
            merchant = txn.get("merchant_name", "")
            if not txn.get("is_business"):
                # Heuristic: business names often contain LLC, Inc, or are single words (DoorDash, Uber)
                name_parts = merchant.split()
                has_biz_suffix = any(w.lower() in ("llc", "inc", "corp", "ltd", "co") for w in name_parts)
                is_single_word = len(name_parts) == 1 and len(merchant) > 3
                has_no_last_initial = not (len(name_parts) == 2 and len(name_parts[1]) <= 2)
                txn["is_business"] = has_biz_suffix or (is_single_word and has_no_last_initial)
        return parsed
    except Exception as e:
        logger.warning("Venmo email parse failed: %s", e)
        return []


def _parse_apple_email(stripped_text: str, email_date: str) -> list[dict]:
    """Parse an Apple receipt email into structured transaction data using Claude Haiku."""
    from anthropic import Anthropic
    from src.config import ANTHROPIC_API_KEY

    if len(stripped_text) > 15000:
        stripped_text = stripped_text[:15000]

    if "$" not in stripped_text:
        return []

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = (
        "Extract transaction details from this Apple receipt/billing email.\n\n"
        "Return ONLY valid JSON — an array of transaction objects:\n"
        "[\n"
        "  {\n"
        '    "merchant_name": "actual service/app name (e.g., iCloud+ 200GB, Apple Music, Clash of Clans)",\n'
        '    "amount": 12.99,\n'
        '    "is_refund": false\n'
        "  }\n"
        "]\n\n"
        "RULES:\n"
        "- merchant_name is the ACTUAL subscription/app name, not 'Apple' or 'APPLE.COM/BILL'\n"
        "- For iCloud, include the storage tier (e.g., 'iCloud+ 200GB')\n"
        "- For App Store purchases, include the app name\n"
        "- For refunds, set is_refund=true and amount as positive number\n"
        "- One receipt may contain multiple subscriptions or purchases\n"
        "- amount is in dollars\n"
        "- If you can't extract details, return an empty array []\n\n"
        f"Email text:\n{stripped_text}"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        parsed = _extract_json_array(text)
        for txn in parsed:
            txn["provider"] = "apple"
            txn["email_date"] = email_date
            txn.setdefault("items", [{"title": txn.get("merchant_name", "Apple service"), "price": txn.get("amount", 0), "quantity": 1}])
            txn.setdefault("is_refund", False)
            txn.setdefault("payment_note", "")
        return parsed
    except Exception as e:
        logger.warning("Apple email parse failed: %s", e)
        return []


def _extract_json_array(text: str) -> list[dict]:
    """Extract a JSON array from Claude's response text."""
    try:
        if "[" in text:
            json_str = text[text.index("["):text.rindex("]") + 1]
            result = json.loads(json_str)
            if isinstance(result, list):
                return [r for r in result if isinstance(r, dict)]
        elif "{" in text:
            json_str = text[text.index("{"):text.rindex("}") + 1]
            return [json.loads(json_str)]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


# ---------------------------------------------------------------------------
# T009: Parser dispatcher
# ---------------------------------------------------------------------------

_PARSERS = {
    "paypal": _parse_paypal_email,
    "venmo": _parse_venmo_email,
    "apple": _parse_apple_email,
}


def _parse_provider_emails(provider: str, raw_emails: list[dict]) -> list[dict]:
    """Parse raw emails through the provider-specific parser.

    Takes raw_emails from _search_provider_emails, returns list of parsed transaction dicts.
    """
    parser = _PARSERS.get(provider)
    if not parser:
        logger.error("No parser for provider: %s", provider)
        return []

    all_parsed = []
    for email in raw_emails:
        try:
            parsed = parser(email["stripped_text"], email["email_date"])
            for txn in parsed:
                txn["email_id"] = email["email_id"]
            all_parsed.extend(parsed)
        except Exception as e:
            logger.warning("Failed to parse %s email %s: %s", provider, email.get("email_id", "?"), e)

    logger.info("Parsed %d transactions from %d %s emails", len(all_parsed), len(raw_emails), provider)
    return all_parsed


# ---------------------------------------------------------------------------
# T010: Enrich and classify
# ---------------------------------------------------------------------------

def enrich_and_classify_email(matched_transactions: list[dict], provider: str) -> list[dict]:
    """Enrich YNAB memos with email details, classify into categories, create SyncRecords.

    Takes output of match_emails_to_transactions, returns enriched list.
    """
    import httpx
    from src.tools import ynab

    config = PROVIDER_CONFIGS[provider]
    enriched = []

    for match in matched_transactions:
        txn = match["ynab_transaction"]
        email_txn = match["matched_email"]

        if email_txn is None:
            # Tag YNAB memo with unmatched notice
            provider_label = config["label"]
            existing_memo = txn.get("memo", "")
            unmatched_tag = f"Unmatched {provider_label} charge"
            if unmatched_tag not in existing_memo:
                new_memo = f"{unmatched_tag} | {existing_memo}" if existing_memo.strip() else unmatched_tag
                try:
                    import httpx as _hx
                    from src.tools import ynab as _yn
                    memo_url = f"{_yn.BASE_URL}/budgets/{_yn.YNAB_BUDGET_ID}/transactions/{txn['id']}"
                    _hx.patch(memo_url, headers=_yn.HEADERS, json={"transaction": {"memo": new_memo[:200]}})
                except Exception as e:
                    logger.warning("Failed to tag unmatched memo for %s: %s", txn["id"], e)

            enriched.append({
                "ynab_transaction": txn,
                "matched_email": None,
                "sync_record": None,
                "classified_items": [],
                "provider": provider,
            })
            continue

        merchant = email_txn.get("merchant_name", "Unknown")
        is_refund = email_txn.get("is_refund", False)

        # Build provider-specific memo
        if provider == "paypal":
            memo = f"{merchant} via PayPal"
        elif provider == "venmo":
            note = email_txn.get("payment_note", "")
            direction = email_txn.get("direction", "sent")
            is_business = email_txn.get("is_business", False)
            if is_business:
                # Business payment — use merchant name directly
                memo = merchant
            else:
                prefix = "To" if direction == "sent" else "From"
                memo = f"{prefix} {merchant}"
            if note:
                memo += f" — {note}"
        elif provider == "apple":
            memo = merchant
        else:
            memo = merchant

        if is_refund:
            memo = f"Refund: {memo}"

        # Preserve existing memo content
        existing_memo = txn.get("memo", "")
        if existing_memo and existing_memo.strip():
            new_memo = f"{memo} | {existing_memo}"
        else:
            new_memo = memo

        # Update YNAB memo
        try:
            memo_url = f"{ynab.BASE_URL}/budgets/{ynab.YNAB_BUDGET_ID}/transactions/{txn['id']}"
            httpx.patch(
                memo_url,
                headers=ynab.HEADERS,
                json={"transaction": {"memo": new_memo[:200]}},  # YNAB memo limit
            )
        except Exception as e:
            logger.warning("Failed to update memo for %s: %s", txn["id"], e)

        # Classify items
        items = email_txn.get("items", [])
        if not items:
            items = [{"title": merchant, "price": email_txn.get("amount", 0), "quantity": 1}]

        categories = _get_ynab_categories()
        mappings = load_category_mappings()
        classified_items = []

        for item in items:
            title = item.get("title", merchant)
            price = float(item.get("price", 0))

            classification = classify_item(title, price, categories, mappings)
            matched_item = MatchedItem(
                title=title,
                price=price,
                quantity=item.get("quantity", 1),
                classified_category=classification.get("category_name", ""),
                classified_category_id=classification.get("category_id", ""),
                confidence=classification.get("confidence", 0.0),
            )
            classified_items.append(matched_item)

        # Handle refunds: try to match to original purchase
        refund_category_id = ""
        refund_category_name = ""
        if is_refund:
            refund_cat = _find_refund_original_category(merchant, abs(email_txn.get("amount", 0)))
            if refund_cat:
                refund_category_id = refund_cat["category_id"]
                refund_category_name = refund_cat["category_name"]
                for ci in classified_items:
                    ci.classified_category = refund_category_name
                    ci.classified_category_id = refund_category_id
                    ci.confidence = 0.95

        # Determine status: auto-categorize if recurring, high confidence, or auto-mode enabled
        sync_config = load_sync_config()
        is_recurring = _is_recurring_charge(merchant, abs(email_txn.get("amount", 0)))
        all_high_confidence = all(ci.confidence >= 0.9 for ci in classified_items)
        single_item = len(classified_items) == 1

        if is_refund and refund_category_id:
            status = "auto_split"
        elif is_recurring:
            status = "auto_split"
        elif sync_config.email_auto_categorize_enabled and all_high_confidence:
            status = "auto_split"
        elif single_item and all_high_confidence:
            status = "auto_split"
        else:
            status = "split_pending"

        # Apply category for auto_split items
        if status == "auto_split" and classified_items:
            try:
                cat_url = f"{ynab.BASE_URL}/budgets/{ynab.YNAB_BUDGET_ID}/transactions/{txn['id']}"
                # Multi-item split: use YNAB sub-transactions when items have different categories
                unique_cats = set(ci.classified_category_id for ci in classified_items if ci.classified_category_id)
                if len(classified_items) > 1 and len(unique_cats) > 1:
                    # Build sub-transactions for YNAB split
                    subtxns = []
                    for ci in classified_items:
                        amount_milli = -int(round(abs(ci.price) * 1000))  # negative for outflow
                        subtxns.append({
                            "amount": amount_milli,
                            "category_id": ci.classified_category_id,
                            "memo": ci.title[:100],
                        })
                    httpx.patch(
                        cat_url,
                        headers=ynab.HEADERS,
                        json={"transaction": {"subtransactions": subtxns}},
                    )
                else:
                    httpx.patch(
                        cat_url,
                        headers=ynab.HEADERS,
                        json={"transaction": {"category_id": classified_items[0].classified_category_id}},
                    )
            except Exception as e:
                logger.warning("Failed to auto-categorize %s: %s", txn["id"], e)

        # Create sync record
        record = SyncRecord(
            ynab_transaction_id=txn["id"],
            amazon_order_number=email_txn.get("email_id", ""),
            status=status,
            matched_at=datetime.now().isoformat(),
            enriched_at=datetime.now().isoformat(),
            ynab_amount=txn["amount"],
            ynab_date=txn["date"],
            items=[asdict(ci) for ci in classified_items],
            original_memo=txn.get("memo", ""),
            original_category_id=txn.get("category_id", ""),
            provider=provider,
        )

        if status == "auto_split":
            record.split_applied_at = datetime.now().isoformat()

        save_sync_record(record)

        enriched.append({
            "ynab_transaction": txn,
            "matched_email": email_txn,
            "sync_record": record,
            "classified_items": classified_items,
            "provider": provider,
        })

    return enriched


def _get_ynab_categories() -> list[dict]:
    """Fetch YNAB budget categories."""
    import httpx
    from src.tools import ynab

    try:
        url = f"{ynab.BASE_URL}/budgets/{ynab.YNAB_BUDGET_ID}/categories"
        resp = httpx.get(url, headers=ynab.HEADERS)
        resp.raise_for_status()
        groups = resp.json()["data"]["category_groups"]
        categories = []
        for group in groups:
            if group.get("hidden"):
                continue
            for cat in group.get("categories", []):
                if not cat.get("hidden") and not cat.get("deleted"):
                    categories.append({
                        "id": cat["id"],
                        "name": cat["name"],
                        "group": group["name"],
                    })
        return categories
    except Exception as e:
        logger.warning("Failed to fetch YNAB categories: %s", e)
        return []


def _find_refund_original_category(merchant_name: str, amount: float) -> Optional[dict]:
    """Search sync records for a previous transaction from the same merchant to get the original category.

    Looks for same merchant + similar amount within 30 days.
    """
    records = load_sync_records()
    normalized = merchant_name.lower().strip()

    for tid, data in records.items():
        if data.get("status") not in ("auto_split", "split_applied"):
            continue
        items = data.get("items", [])
        for item in items:
            item_title = (item.get("title") or "").lower().strip()
            if normalized in item_title or item_title in normalized:
                item_amount = abs(float(item.get("price", 0)))
                if item_amount > 0 and abs(item_amount - amount) / item_amount < 0.3:
                    return {
                        "category_id": item.get("classified_category_id", ""),
                        "category_name": item.get("classified_category", ""),
                    }
    return None


# ---------------------------------------------------------------------------
# T011: Recurring charge detection + suggestion message formatting
# ---------------------------------------------------------------------------

def _is_recurring_charge(merchant_name: str, amount: float) -> bool:
    """Check if a merchant/amount combination is a known recurring charge.

    Returns True if the merchant exists in category mappings with
    source='user_approved' and confidence >= 0.9, and the amount
    is within ±20% of the mapped amount.
    """
    mappings = load_category_mappings()
    normalized = merchant_name.lower().strip()

    # Direct match
    mapping = mappings.get(normalized)
    if not mapping:
        # Substring match
        for key, m in mappings.items():
            if normalized in key or key in normalized:
                mapping = m
                break

    if not mapping:
        return False

    if mapping.get("source") not in ("user_approved", "user_corrected"):
        return False
    if mapping.get("confidence", 0) < 0.9:
        return False

    # Check amount similarity (±20%) — use last known price from times_used > 0
    # For recurring charges, the mapping existing with high confidence is sufficient
    return True


def format_email_suggestion_message(enriched_transactions: list[dict]) -> str:
    """Format a consolidated WhatsApp suggestion message for email sync results.

    Returns empty string if nothing to report.
    """
    if not enriched_transactions:
        return ""

    auto_items = []
    pending_items = []
    unmatched_items = []

    for entry in enriched_transactions:
        record = entry.get("sync_record")
        if record is None:
            unmatched_items.append(entry)
        elif record.status == "auto_split":
            auto_items.append(entry)
        elif record.status == "split_pending":
            pending_items.append(entry)

    if not auto_items and not pending_items and not unmatched_items:
        return ""

    total = len(auto_items) + len(pending_items) + len(unmatched_items)
    lines = [f"💳 Email Sync — {total} new transaction{'s' if total != 1 else ''}\n"]

    idx = 1

    # Pending items (need Erin's approval)
    for entry in pending_items:
        txn = entry["ynab_transaction"]
        email_txn = entry.get("matched_email", {})
        items = entry.get("classified_items", [])
        provider_label = PROVIDER_CONFIGS.get(entry.get("provider", ""), {}).get("label", "")
        amount_dollars = abs(txn["amount"]) / 1000
        merchant = email_txn.get("merchant_name", "Unknown") if email_txn else "Unknown"

        if len(items) > 1:
            # Multi-item
            lines.append(f"{idx}️⃣ ${amount_dollars:.2f} {provider_label} ({txn['date']}) — {merchant}")
            for item in items:
                lines.append(f"  • {item.title} → {item.classified_category} (${item.price:.2f})")
            lines.append(f'Reply "{idx} yes" to split, "{idx} adjust" to modify, "{idx} skip" to leave\n')
        else:
            # Single item
            cat = items[0].classified_category if items else "Unknown"
            lines.append(f"{idx}️⃣ ${amount_dollars:.2f} {provider_label} ({txn['date']}) — {merchant}")
            lines.append(f"→ {cat}")
            lines.append(f'Reply "{idx} yes" to apply, "{idx} adjust" to modify, "{idx} skip" to leave\n')
        idx += 1

    # Auto-categorized items (brief summary)
    if auto_items:
        if pending_items:
            lines.append("")
        for entry in auto_items:
            txn = entry["ynab_transaction"]
            email_txn = entry.get("matched_email", {})
            items = entry.get("classified_items", [])
            provider_label = PROVIDER_CONFIGS.get(entry.get("provider", ""), {}).get("label", "")
            amount_dollars = abs(txn["amount"]) / 1000
            merchant = email_txn.get("merchant_name", "Unknown") if email_txn else "Unknown"
            cat = items[0].classified_category if items else "?"

            is_refund = (email_txn or {}).get("is_refund", False)
            refund_tag = " (refund)" if is_refund else ""
            lines.append(f"✅ Auto-categorized: ${amount_dollars:.2f} {merchant}{refund_tag} → {cat}")

    # Unmatched items
    if unmatched_items:
        if auto_items or pending_items:
            lines.append("")
        for entry in unmatched_items:
            txn = entry["ynab_transaction"]
            provider_label = PROVIDER_CONFIGS.get(entry.get("provider", ""), {}).get("label", "")
            amount_dollars = abs(txn["amount"]) / 1000
            lines.append(f"❓ ${amount_dollars:.2f} {provider_label} ({txn['date']}) — no matching email found")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# T012: Main orchestrator
# ---------------------------------------------------------------------------

def run_email_sync() -> str | None:
    """Run the email sync for all providers. Returns short status string or None if nothing to do.

    Checks YNAB first (fast), skips if no unprocessed transactions.
    Sends suggestion message directly to Erin via WhatsApp.
    """
    all_enriched = []
    providers_processed = []

    # Check YNAB for unprocessed transactions across all providers (fast)
    provider_txns = {}
    for provider in PROVIDER_CONFIGS:
        try:
            txns = find_provider_transactions(provider)
            if txns:
                provider_txns[provider] = txns
        except Exception as e:
            logger.error("Failed to check YNAB for %s: %s", provider, e)

    if not provider_txns:
        logger.info("Email sync: no new transactions to process")
        return None

    # For each provider with transactions, search Gmail and process
    for provider, txns in provider_txns.items():
        try:
            logger.info("Processing %d %s transactions", len(txns), provider)

            # Search Gmail for matching emails
            raw_emails = _search_provider_emails(provider)
            if not raw_emails:
                # Tag unmatched and continue
                for txn in txns:
                    all_enriched.append({
                        "ynab_transaction": txn,
                        "matched_email": None,
                        "sync_record": None,
                        "classified_items": [],
                        "provider": provider,
                    })
                continue

            # Parse emails
            parsed = _parse_provider_emails(provider, raw_emails)

            # Match to YNAB transactions
            matched = match_emails_to_transactions(txns, parsed)

            # Enrich and classify
            enriched = enrich_and_classify_email(matched, provider)
            all_enriched.extend(enriched)
            providers_processed.append(provider)

        except RuntimeError as e:
            if "OAuth" in str(e):
                logger.error("Gmail OAuth expired — skipping all email sync")
                return None
            logger.error("Error processing %s: %s", provider, e)
        except Exception as e:
            logger.error("Error processing %s: %s", provider, e)

    if not all_enriched:
        return None

    # Format and send suggestion message
    message = format_email_suggestion_message(all_enriched)
    _set_email_pending_suggestions(all_enriched)

    if message:
        try:
            from src.assistant import send_sync_message_direct
            send_sync_message_direct(message)
        except Exception as e:
            logger.error("Failed to send email sync message: %s", e)

    # Update sync config
    config = load_sync_config()
    config.email_last_sync = datetime.now().isoformat()
    save_sync_config(config)

    # Count results for status
    auto_count = sum(1 for m in all_enriched if m.get("sync_record") and m["sync_record"].status == "auto_split")
    pending_count = sum(1 for m in all_enriched if m.get("sync_record") and m["sync_record"].status == "split_pending")
    unmatched_count = sum(1 for m in all_enriched if m.get("matched_email") is None)

    parts = [f"Email sync complete — processed {len(all_enriched)} transactions."]
    if auto_count:
        parts.append(f"{auto_count} auto-categorized.")
    if pending_count:
        parts.append(f"{pending_count} sent to Erin for review.")
    if unmatched_count:
        parts.append(f"{unmatched_count} unmatched (no email found).")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# T013: Pending suggestions & reply handling
# ---------------------------------------------------------------------------

def _set_email_pending_suggestions(enriched_transactions: list[dict]) -> None:
    """Store pending email sync suggestions to disk."""
    pending = [
        m for m in enriched_transactions
        if m.get("sync_record") and m["sync_record"].status == "split_pending"
    ]
    serialized = []
    for m in pending:
        serialized.append({
            "ynab_transaction": m["ynab_transaction"],
            "sync_record_id": m["sync_record"].ynab_transaction_id,
            "classified_items": [asdict(ci) for ci in m.get("classified_items", [])],
            "provider": m.get("provider", ""),
            "matched_email": m.get("matched_email", {}),
        })
    _save_json(_EMAIL_PENDING_SUGGESTIONS_FILE, {"suggestions": serialized})
    logger.info("Saved %d email pending suggestions to disk", len(serialized))


def _load_email_pending_suggestions() -> list[dict]:
    """Load pending email sync suggestions from disk."""
    data = _load_json(_EMAIL_PENDING_SUGGESTIONS_FILE)
    suggestions = data.get("suggestions", [])
    if not suggestions:
        return []

    from src.tools.amazon_sync import load_sync_record as load_record

    result = []
    for entry in suggestions:
        items = [MatchedItem(**ci) for ci in entry.get("classified_items", [])]
        record = load_record(entry["sync_record_id"])
        if record and record.status == "split_pending":
            result.append({
                "ynab_transaction": entry["ynab_transaction"],
                "sync_record": record,
                "classified_items": items,
                "provider": entry.get("provider", ""),
                "matched_email": entry.get("matched_email", {}),
            })
    return result


def handle_email_sync_reply(message_text: str) -> str:
    """Handle Erin's reply to an email sync suggestion.

    Supports: "N yes", "N adjust — [correction]", "N skip"
    """
    import httpx
    from src.tools import ynab
    import re

    pending = _load_email_pending_suggestions()
    if not pending:
        return "No pending email sync suggestions to respond to."

    text = message_text.strip().lower()

    # Parse index and action
    match = re.match(r"(\d+)\s+(yes|adjust|skip)(.*)", text)
    if not match:
        # Default to index 1 if just "yes"/"skip"
        if text.startswith("yes"):
            idx, action, rest = 1, "yes", ""
        elif text.startswith("skip"):
            idx, action, rest = 1, "skip", ""
        elif text.startswith("adjust"):
            idx, action, rest = 1, "adjust", text[6:]
        else:
            return f"I have {len(pending)} pending email sync suggestions. Reply with a number + action (e.g., '1 yes', '2 adjust — put in Groceries', '3 skip')."
    else:
        idx = int(match.group(1))
        action = match.group(2)
        rest = match.group(3)

    if idx < 1 or idx > len(pending):
        return f"Invalid suggestion number. I have {len(pending)} pending suggestions (1-{len(pending)})."

    entry = pending[idx - 1]
    txn = entry["ynab_transaction"]
    record = entry["sync_record"]
    items = entry["classified_items"]

    if action == "yes":
        # Apply suggested category
        if items:
            try:
                cat_url = f"{ynab.BASE_URL}/budgets/{ynab.YNAB_BUDGET_ID}/transactions/{txn['id']}"
                httpx.patch(
                    cat_url,
                    headers=ynab.HEADERS,
                    json={"transaction": {"category_id": items[0].classified_category_id}},
                )
            except Exception as e:
                return f"Failed to apply category: {e}"

            # Save mapping as user-approved
            for item in items:
                mapping = CategoryMapping(
                    item_title_normalized=item.title.lower().strip(),
                    category_name=item.classified_category,
                    category_id=item.classified_category_id,
                    confidence=1.0,
                    source="user_approved",
                    times_used=1,
                    last_used=datetime.now().isoformat(),
                )
                save_category_mapping(mapping)

        # Update sync record
        record.status = "split_applied"
        record.split_applied_at = datetime.now().isoformat()
        save_sync_record(record)

        # Update config stats
        config = load_sync_config()
        config.email_total_suggestions += 1
        config.email_unmodified_accepts += 1
        if not config.email_first_suggestion_date:
            config.email_first_suggestion_date = date.today().isoformat()
        save_sync_config(config)

        # Remove from pending
        _remove_pending_suggestion(idx - 1)

        cat_name = items[0].classified_category if items else "the suggested category"
        return f"Applied: {cat_name} for ${abs(txn['amount'])/1000:.2f}. Mapping saved for future."

    elif action == "skip":
        record.status = "skipped"
        save_sync_record(record)

        config = load_sync_config()
        config.email_total_suggestions += 1
        save_sync_config(config)

        _remove_pending_suggestion(idx - 1)
        return f"Skipped categorization for ${abs(txn['amount'])/1000:.2f}."

    elif action == "adjust":
        # Parse the correction
        correction_text = rest.strip().lstrip("—").lstrip("-").strip()
        if not correction_text:
            return "Please specify the category. Example: '1 adjust — put it in Groceries'"

        # Use Claude to resolve the category name
        categories = _get_ynab_categories()
        resolved = _resolve_category_name(correction_text, categories)
        if not resolved:
            return f"Couldn't find a matching category for '{correction_text}'. Try the exact category name."

        # Apply corrected category
        try:
            cat_url = f"{ynab.BASE_URL}/budgets/{ynab.YNAB_BUDGET_ID}/transactions/{txn['id']}"
            httpx.patch(
                cat_url,
                headers=ynab.HEADERS,
                json={"transaction": {"category_id": resolved["id"]}},
            )
        except Exception as e:
            return f"Failed to apply corrected category: {e}"

        # Save corrected mapping
        for item in items:
            mapping = CategoryMapping(
                item_title_normalized=item.title.lower().strip(),
                category_name=resolved["name"],
                category_id=resolved["id"],
                confidence=1.0,
                source="user_corrected",
                times_used=1,
                last_used=datetime.now().isoformat(),
            )
            save_category_mapping(mapping)

        # Update sync record
        record.status = "split_applied"
        record.split_applied_at = datetime.now().isoformat()
        save_sync_record(record)

        config = load_sync_config()
        config.email_total_suggestions += 1
        save_sync_config(config)

        _remove_pending_suggestion(idx - 1)
        return f"Adjusted: applied '{resolved['name']}' for ${abs(txn['amount'])/1000:.2f}. Mapping saved."

    return "Unrecognized action. Use 'yes', 'adjust — [category]', or 'skip'."


def _remove_pending_suggestion(index: int) -> None:
    """Remove a suggestion from the pending file by index."""
    data = _load_json(_EMAIL_PENDING_SUGGESTIONS_FILE)
    suggestions = data.get("suggestions", [])
    if 0 <= index < len(suggestions):
        suggestions.pop(index)
        _save_json(_EMAIL_PENDING_SUGGESTIONS_FILE, {"suggestions": suggestions})


def _resolve_category_name(text: str, categories: list[dict]) -> Optional[dict]:
    """Resolve a user's natural language category reference to a YNAB category.

    Simple fuzzy match: check if any category name is contained in the text.
    """
    text_lower = text.lower().strip()

    # Exact match
    for cat in categories:
        if cat["name"].lower() == text_lower:
            return cat

    # Contains match
    for cat in categories:
        if cat["name"].lower() in text_lower or text_lower in cat["name"].lower():
            return cat

    # Word overlap match
    text_words = set(text_lower.split())
    best_match = None
    best_overlap = 0
    for cat in categories:
        cat_words = set(cat["name"].lower().split())
        overlap = len(text_words & cat_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = cat
    if best_overlap > 0:
        return best_match

    return None


# ---------------------------------------------------------------------------
# T031: Status
# ---------------------------------------------------------------------------

def get_email_sync_status() -> str:
    """Return email sync status and statistics."""
    config = load_sync_config()
    records = load_sync_records()

    # Count by provider
    provider_counts = {"paypal": 0, "venmo": 0, "apple": 0}
    for tid, data in records.items():
        prov = data.get("provider", "amazon")
        if prov in provider_counts:
            provider_counts[prov] += 1

    total = sum(provider_counts.values())

    parts = ["📊 Email Sync Status\n"]

    if config.email_last_sync:
        parts.append(f"Last sync: {config.email_last_sync[:16]}")
    else:
        parts.append("Last sync: never")

    parts.append(f"Transactions processed: {total}")
    for prov, count in provider_counts.items():
        if count > 0:
            parts.append(f"  • {PROVIDER_CONFIGS[prov]['label']}: {count}")

    if config.email_total_suggestions > 0:
        rate = config.email_unmodified_accepts / config.email_total_suggestions * 100
        parts.append(f"Acceptance rate: {rate:.0f}% ({config.email_unmodified_accepts}/{config.email_total_suggestions})")

    mode = "ON" if config.email_auto_categorize_enabled else "OFF"
    parts.append(f"Auto-categorize: {mode}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# T024-T026: Auto-categorize graduation, toggle, undo
# ---------------------------------------------------------------------------

def get_email_acceptance_rate() -> float:
    """Return the email sync acceptance rate (0.0-1.0)."""
    config = load_sync_config()
    if config.email_total_suggestions == 0:
        return 0.0
    return config.email_unmodified_accepts / config.email_total_suggestions


def check_email_auto_categorize_graduation() -> str | None:
    """Check if email sync should suggest enabling auto-categorize mode.

    Returns suggestion message string, or None if not ready.
    """
    config = load_sync_config()
    if config.email_auto_categorize_enabled:
        return None
    if config.email_total_suggestions < 10:
        return None

    rate = get_email_acceptance_rate()
    if rate < 0.8:
        return None

    # Check 2-week minimum
    if config.email_first_suggestion_date:
        first = date.fromisoformat(config.email_first_suggestion_date)
        if (date.today() - first).days < 14:
            return None

    pct = int(rate * 100)
    return (
        f"I've been getting your PayPal/Venmo/Apple categories right {pct}% of the time "
        f"over {config.email_total_suggestions} transactions. "
        "Want me to start auto-categorizing these? (You can always undo or turn it off.)"
    )


def set_email_auto_categorize(enabled: bool) -> str:
    """Enable or disable auto-categorize mode for email-synced providers."""
    config = load_sync_config()
    config.email_auto_categorize_enabled = enabled
    save_sync_config(config)

    if enabled:
        return "Auto-categorize mode enabled for PayPal, Venmo, and Apple transactions. I'll apply categories automatically for known merchants and recurring charges. Reply 'undo' to revert any categorization."
    else:
        return "Auto-categorize mode disabled. I'll go back to asking you for each transaction."


def handle_email_undo(transaction_index: int) -> str:
    """Revert an auto-categorized email sync transaction.

    Restores original memo and category from SyncRecord.
    """
    import httpx
    from src.tools import ynab

    records = load_sync_records()

    # Find recent auto_split email sync records (not Amazon)
    recent_auto = []
    for tid, data in records.items():
        if data.get("provider", "amazon") in ("paypal", "venmo", "apple"):
            if data.get("status") == "auto_split":
                recent_auto.append((tid, data))

    # Sort by split_applied_at descending
    recent_auto.sort(key=lambda x: x[1].get("split_applied_at", ""), reverse=True)

    if not recent_auto:
        return "No recent email sync auto-categorizations to undo."

    if transaction_index < 1 or transaction_index > len(recent_auto):
        return f"Invalid index. I have {len(recent_auto)} recent auto-categorizations (1-{len(recent_auto)})."

    tid, data = recent_auto[transaction_index - 1]

    # Restore original memo and category
    try:
        url = f"{ynab.BASE_URL}/budgets/{ynab.YNAB_BUDGET_ID}/transactions/{tid}"
        update = {}
        if data.get("original_memo"):
            update["memo"] = data["original_memo"]
        if data.get("original_category_id"):
            update["category_id"] = data["original_category_id"]
        if update:
            httpx.patch(url, headers=ynab.HEADERS, json={"transaction": update})
    except Exception as e:
        return f"Failed to undo: {e}"

    # Update sync record status
    record = SyncRecord(**data)
    record.status = "split_pending"
    record.split_applied_at = ""
    save_sync_record(record)

    items = data.get("items", [])
    item_name = items[0].get("title", "transaction") if items else "transaction"
    amount = abs(data.get("ynab_amount", 0)) / 1000

    return f"Undone: ${amount:.2f} {item_name} reverted to uncategorized. You can re-categorize via WhatsApp."
