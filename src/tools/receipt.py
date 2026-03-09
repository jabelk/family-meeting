"""Receipt photo → YNAB categorization — extract, match, categorize."""

import json
import logging
from datetime import date, timedelta

from openai import AsyncOpenAI

from src.config import ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None

# Pending receipt state keyed by phone number (conversation context)
_pending_receipts: dict[str, dict] = {}
_pending_unmatched: dict[str, dict] = {}


def _get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# T002: Receipt extraction via OpenAI gpt-4o vision
# ---------------------------------------------------------------------------


async def extract_receipt(image_base64: str, mime_type: str) -> dict:
    """Extract receipt data from an image using OpenAI gpt-4o vision.

    Returns dict with store_name, date, line_items, subtotal, tax, total.
    On failure returns {"error": "description"}.
    """
    if not OPENAI_API_KEY:
        return {"error": "OpenAI API key not configured — cannot process receipt photos."}

    try:
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract all data from this receipt image. Return ONLY valid JSON with these fields:\n"
                                '{"store_name": "Store Name", "date": "YYYY-MM-DD", '
                                '"line_items": [{"name": "item name", "price": 1.99}], '
                                '"subtotal": 0.00, "tax": 0.00, "total": 0.00}\n'
                                "If you cannot read the receipt clearly, return: "
                                '{"error": "brief explanation of what went wrong"}\n'
                                "If this is not a receipt image, return: "
                                '{"error": "This doesn\'t appear to be a receipt."}'
                            ),
                        },
                    ],
                }
            ],
        )

        text = response.choices[0].message.content.strip()
        # Extract JSON from response (may have markdown fences)
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        if "{" in text:
            text = text[text.index("{") : text.rindex("}") + 1]
        return json.loads(text)

    except json.JSONDecodeError:
        logger.warning("Failed to parse receipt extraction response")
        return {"error": "Could not parse the receipt data. Please try a clearer photo."}
    except Exception as e:
        logger.error("Receipt extraction failed: %s", e)
        return {"error": f"Receipt extraction failed: {e}"}


# ---------------------------------------------------------------------------
# T003: Match receipt to YNAB transaction
# ---------------------------------------------------------------------------


def match_receipt_to_ynab(store_name: str, total: float, receipt_date: str) -> list[dict]:
    """Search YNAB for uncategorized transactions matching receipt data.

    Returns list of matching transactions sorted by relevance.
    """
    # Search 7 days before and after receipt date
    try:
        search_date = date.fromisoformat(receipt_date)
    except (ValueError, TypeError):
        search_date = date.today()

    since = (search_date - timedelta(days=7)).isoformat()

    # search_transactions returns a string — we need raw transaction data
    # Call the YNAB API directly for structured data
    try:
        import httpx

        from src.tools.ynab import BASE_URL, HEADERS, YNAB_BUDGET_ID

        url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/transactions"
        resp = httpx.get(url, headers=HEADERS, params={"since_date": since, "type": "uncategorized"})
        resp.raise_for_status()
        txns = resp.json()["data"]["transactions"]
    except Exception as e:
        logger.error("YNAB transaction search failed: %s", e)
        return []

    matches = []
    total_milliunits = int(abs(total) * 1000)
    store_lower = store_name.lower().strip()

    for txn in txns:
        txn_amount = abs(txn["amount"])
        amount_diff = abs(txn_amount - total_milliunits)

        # Amount match within $1.00 tolerance (1000 milliunits)
        if amount_diff > 1000:
            continue

        payee = (txn.get("payee_name") or "").lower()

        # Score: amount closeness + payee match
        score = 0
        if amount_diff == 0:
            score += 100
        elif amount_diff <= 500:
            score += 50

        # Fuzzy payee matching
        if store_lower in payee or payee in store_lower:
            score += 80
        elif any(word in payee for word in store_lower.split() if len(word) > 3):
            score += 40

        # Date proximity bonus
        try:
            txn_date = date.fromisoformat(txn["date"])
            day_diff = abs((txn_date - search_date).days)
            if day_diff == 0:
                score += 30
            elif day_diff <= 2:
                score += 15
        except (ValueError, TypeError):
            pass

        if score > 0:
            matches.append(
                {
                    "id": txn["id"],
                    "payee": txn.get("payee_name", "Unknown"),
                    "amount": txn_amount / 1000,
                    "date": txn["date"],
                    "category": txn.get("category_name") or "Uncategorized",
                    "score": score,
                }
            )

    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches


# ---------------------------------------------------------------------------
# T004: Suggest category based on store/items
# ---------------------------------------------------------------------------


def suggest_category(store_name: str, line_items: list[dict]) -> dict:
    """Suggest a YNAB category based on store name and line items.

    Uses cached mappings first, falls back to Claude Haiku classification.
    """
    from src.tools.amazon_sync import lookup_cached_category
    from src.tools.ynab import _get_categories

    # 1. Check cached mappings for store name
    cached = lookup_cached_category(store_name)
    if cached:
        return {
            "category_name": cached["category_name"],
            "category_id": cached["category_id"],
            "confidence": min(cached.get("confidence", 0.9), 1.0),
            "source": "cached",
        }

    # 2. Check cached mappings for line items
    for item in line_items[:5]:  # Check first 5 items
        cached = lookup_cached_category(item.get("name", ""))
        if cached:
            return {
                "category_name": cached["category_name"],
                "category_id": cached["category_id"],
                "confidence": min(cached.get("confidence", 0.8), 1.0),
                "source": "cached",
            }

    # 3. LLM classification via Claude Haiku
    if not ANTHROPIC_API_KEY:
        return {"category_name": "", "category_id": "", "confidence": 0.0, "source": "none"}

    try:
        from anthropic import Anthropic

        categories = _get_categories()
        cat_names = [c["name"] for c in categories.values()]

        items_text = ", ".join(item.get("name", "") for item in line_items[:10]) if line_items else "unknown items"

        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Classify this purchase into one YNAB budget category.\n"
                        f"Store: {store_name}\n"
                        f"Items: {items_text}\n\n"
                        f"Available categories: {', '.join(cat_names)}\n\n"
                        f'Return JSON only: {{"category": "Category Name", "confidence": 0.85}}'
                    ),
                }
            ],
        )

        text = response.content[0].text.strip()
        if "{" in text:
            json_str = text[text.index("{") : text.rindex("}") + 1]
            result = json.loads(json_str)
            cat_name = result.get("category", "")

            # Match to actual category ID
            for c in categories.values():
                if c["name"].lower() == cat_name.lower():
                    return {
                        "category_name": c["name"],
                        "category_id": c["id"],
                        "confidence": float(result.get("confidence", 0.5)),
                        "source": "llm",
                    }
    except Exception as e:
        logger.error("Receipt category classification failed: %s", e)

    return {"category_name": "", "category_id": "", "confidence": 0.0, "source": "none"}


# ---------------------------------------------------------------------------
# T005: Main receipt processing tool (US1)
# ---------------------------------------------------------------------------


async def process_receipt(image_base64: str, mime_type: str, phone: str = "") -> str:
    """Process a receipt photo: extract data, match YNAB, suggest category.

    This is the main tool function called by Claude when it sees a receipt image.
    """
    # Step 1: Extract receipt data via OpenAI vision
    receipt_data = await extract_receipt(image_base64, mime_type)

    if "error" in receipt_data:
        return receipt_data["error"]

    store_name = receipt_data.get("store_name", "Unknown")
    receipt_date = receipt_data.get("date", date.today().isoformat())
    total = float(receipt_data.get("total", 0))
    line_items = receipt_data.get("line_items", [])
    tax = receipt_data.get("tax", 0)

    if total == 0:
        return "I couldn't extract a total from this receipt. Could you send a clearer photo?"

    # Format extracted data summary
    summary_lines = [f"*Receipt from {store_name}*", f"Date: {receipt_date}"]
    if line_items:
        summary_lines.append(f"Items ({len(line_items)}):")
        for item in line_items[:8]:  # Show up to 8 items
            summary_lines.append(f"  - {item.get('name', '?')}: ${float(item.get('price', 0)):.2f}")
        if len(line_items) > 8:
            summary_lines.append(f"  ... and {len(line_items) - 8} more items")
    if tax:
        summary_lines.append(f"Tax: ${float(tax):.2f}")
    summary_lines.append(f"*Total: ${total:.2f}*")

    # Step 2: Match to YNAB transaction
    matches = match_receipt_to_ynab(store_name, total, receipt_date)

    # Step 3: Suggest category
    category = suggest_category(store_name, line_items)

    summary = "\n".join(summary_lines)

    if not matches:
        # No YNAB match — store for later retry
        _pending_unmatched[phone] = {
            "store_name": store_name,
            "total": total,
            "date": receipt_date,
            "line_items": line_items,
            "category": category,
        }
        cat_note = ""
        if category.get("category_name"):
            cat_note = (
                f"\n\nBased on the store/items, this would likely be categorized as *{category['category_name']}*."
            )

        return (
            f"{summary}\n\n"
            f"No matching uncategorized YNAB transaction found (I checked the last 7 days). "
            f"The transaction may still be pending.{cat_note}\n\n"
            f"Ask me to check again later once the charge posts."
        )

    if len(matches) > 1:
        # Multiple matches — ask user to pick
        match_lines = [f"{summary}\n\nI found {len(matches)} possible YNAB matches:"]
        for i, m in enumerate(matches[:5], 1):
            match_lines.append(f"{i}. {m['payee']} — ${m['amount']:.2f} on {m['date']}")
        match_lines.append("\nWhich one matches this receipt? (reply with the number)")

        _pending_receipts[phone] = {
            "matches": matches[:5],
            "store_name": store_name,
            "total": total,
            "category": category,
            "line_items": line_items,
            "awaiting_selection": True,
        }
        return "\n".join(match_lines)

    # Single match — suggest categorization
    match = matches[0]
    cat_name = category.get("category_name", "")

    _pending_receipts[phone] = {
        "transaction_id": match["id"],
        "payee": match["payee"],
        "amount": match["amount"],
        "date": match["date"],
        "category_name": cat_name,
        "category_id": category.get("category_id", ""),
        "store_name": store_name,
        "line_items": line_items,
    }

    if cat_name:
        return (
            f"{summary}\n\n"
            f"Matched YNAB transaction: *{match['payee']}* — ${match['amount']:.2f} on {match['date']}\n\n"
            f"Suggested category: *{cat_name}*\n\n"
            f"Reply *yes* to categorize, or tell me a different category."
        )
    else:
        return (
            f"{summary}\n\n"
            f"Matched YNAB transaction: *{match['payee']}* — ${match['amount']:.2f} on {match['date']}\n\n"
            f"What YNAB category should this go under?"
        )


# ---------------------------------------------------------------------------
# T006: Confirm receipt categorization (US1)
# ---------------------------------------------------------------------------


async def confirm_receipt_categorization(phone: str, category_override: str = "") -> str:
    """Confirm or override receipt categorization and update YNAB."""
    from src.tools.amazon_sync import CategoryMapping, save_category_mapping
    from src.tools.ynab import _fuzzy_match_category, recategorize_transaction

    pending = _pending_receipts.get(phone)
    if not pending:
        return "No pending receipt to categorize."

    # Handle multi-match selection
    if pending.get("awaiting_selection"):
        return "Please select which transaction matches by replying with the number."

    payee = pending.get("payee", "")
    amount = pending.get("amount", 0)
    txn_date = pending.get("date", "")

    # Determine category
    if category_override:
        matched = _fuzzy_match_category(category_override)
        if not matched:
            return f"Category '{category_override}' not found in YNAB. Please check the name and try again."
        cat_id, cat_name = matched
        source = "user_corrected"
    else:
        cat_name = pending.get("category_name", "")
        cat_id = pending.get("category_id", "")
        source = "user_approved"
        if not cat_name:
            return "Please tell me which YNAB category to use."

    # Update YNAB transaction
    result = recategorize_transaction(payee=payee, amount=amount, date_str=txn_date, new_category=cat_name)

    if "Recategorized" in result or "recategorized" in result.lower():
        # Save category mapping for future use
        from datetime import datetime

        store_name = pending.get("store_name", payee)
        mapping = CategoryMapping(
            item_title_normalized=store_name.lower().strip(),
            category_name=cat_name,
            category_id=cat_id,
            confidence=0.95 if source == "user_approved" else 0.9,
            source=source,
            times_used=1,
            last_used=datetime.now().isoformat(),
        )
        save_category_mapping(mapping)

        # Clear pending state
        _pending_receipts.pop(phone, None)
        return f"Done! {result}\n\nI'll remember that {store_name} goes under *{cat_name}* for next time."

    # Clear pending on failure too
    _pending_receipts.pop(phone, None)
    return result


# ---------------------------------------------------------------------------
# T013: Retry receipt match (US2)
# ---------------------------------------------------------------------------


async def retry_receipt_match(phone: str) -> str:
    """Re-check YNAB for a previously unmatched receipt."""
    unmatched = _pending_unmatched.get(phone)
    if not unmatched:
        return "No pending unmatched receipt to check. Send a receipt photo first."

    matches = match_receipt_to_ynab(unmatched["store_name"], unmatched["total"], unmatched["date"])

    if not matches:
        return (
            f"Still no matching transaction for {unmatched['store_name']} "
            f"(${unmatched['total']:.2f} on {unmatched['date']}). "
            f"Try again once the charge posts to your account."
        )

    category = unmatched.get("category", {})

    if len(matches) == 1:
        match = matches[0]
        cat_name = category.get("category_name", "")

        _pending_receipts[phone] = {
            "transaction_id": match["id"],
            "payee": match["payee"],
            "amount": match["amount"],
            "date": match["date"],
            "category_name": cat_name,
            "category_id": category.get("category_id", ""),
            "store_name": unmatched["store_name"],
            "line_items": unmatched.get("line_items", []),
        }
        _pending_unmatched.pop(phone, None)

        if cat_name:
            return (
                f"Found a match! *{match['payee']}* — ${match['amount']:.2f} on {match['date']}\n\n"
                f"Suggested category: *{cat_name}*\n\n"
                f"Reply *yes* to categorize, or tell me a different category."
            )
        return (
            f"Found a match! *{match['payee']}* — ${match['amount']:.2f} on {match['date']}\n\n"
            f"What YNAB category should this go under?"
        )

    # Multiple matches
    match_lines = [f"Found {len(matches)} possible matches:"]
    for i, m in enumerate(matches[:5], 1):
        match_lines.append(f"{i}. {m['payee']} — ${m['amount']:.2f} on {m['date']}")
    match_lines.append("\nWhich one matches this receipt?")

    _pending_receipts[phone] = {
        "matches": matches[:5],
        "store_name": unmatched["store_name"],
        "total": unmatched["total"],
        "category": category,
        "line_items": unmatched.get("line_items", []),
        "awaiting_selection": True,
    }
    _pending_unmatched.pop(phone, None)
    return "\n".join(match_lines)


# ---------------------------------------------------------------------------
# T017-T019: Multi-category split (US3)
# ---------------------------------------------------------------------------


def analyze_receipt_categories(line_items: list[dict]) -> dict:
    """Classify each line item and group by category.

    Returns {"categories": [{"name", "id", "items", "subtotal"}], "is_mixed": bool}.
    """
    if not line_items:
        return {"categories": [], "is_mixed": False}

    category_groups: dict[str, dict] = {}

    for item in line_items:
        item_name = item.get("name", "")
        item_price = float(item.get("price", 0))
        if not item_name or item_price == 0:
            continue

        cat = suggest_category(item_name, [item])
        cat_name = cat.get("category_name") or "Uncategorized"
        cat_id = cat.get("category_id", "")

        if cat_name not in category_groups:
            category_groups[cat_name] = {"name": cat_name, "id": cat_id, "items": [], "subtotal": 0.0}
        category_groups[cat_name]["items"].append({"name": item_name, "price": item_price})
        category_groups[cat_name]["subtotal"] += item_price

    categories = sorted(category_groups.values(), key=lambda c: c["subtotal"], reverse=True)
    return {"categories": categories, "is_mixed": len(categories) >= 2}


async def split_receipt_transaction(phone: str) -> str:
    """Split a pending receipt transaction across multiple YNAB categories."""
    from src.tools.ynab import _fuzzy_match_category, split_transaction

    pending = _pending_receipts.get(phone)
    if not pending:
        return "No pending receipt to split."

    txn_id = pending.get("transaction_id")
    if not txn_id:
        return "No matched YNAB transaction to split. Match a receipt first."

    line_items = pending.get("line_items", [])
    if not line_items:
        return "No line items available for splitting."

    analysis = analyze_receipt_categories(line_items)
    if not analysis["is_mixed"]:
        return "All items appear to be in the same category — no split needed."

    # Build subtransactions
    subtxns = []
    breakdown_lines = ["Split breakdown:"]
    for cat_group in analysis["categories"]:
        cat_name = cat_group["name"]
        cat_id = cat_group["id"]

        # Ensure we have a valid category ID
        if not cat_id:
            matched = _fuzzy_match_category(cat_name)
            if matched:
                cat_id = matched[0]
                cat_name = matched[1]
            else:
                continue

        amount_milliunits = -int(cat_group["subtotal"] * 1000)  # Negative for outflows
        item_names = ", ".join(i["name"] for i in cat_group["items"][:3])
        memo = item_names[:200] if item_names else cat_name

        subtxns.append({"amount_milliunits": amount_milliunits, "category_id": cat_id, "memo": memo})
        breakdown_lines.append(f"  *{cat_name}*: ${cat_group['subtotal']:.2f} ({len(cat_group['items'])} items)")

    if not subtxns:
        return "Could not map items to valid YNAB categories for splitting."

    result = split_transaction(txn_id, subtxns)

    _pending_receipts.pop(phone, None)
    return f"Done! {result}\n\n" + "\n".join(breakdown_lines)
