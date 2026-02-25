"""Amazon-YNAB Smart Sync — Gmail email parsing, order matching, classification, and sync orchestration."""

import base64
import httpx
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persistence paths
# ---------------------------------------------------------------------------

_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
_SYNC_RECORDS_FILE = _DATA_DIR / "amazon_sync_records.json"
_CATEGORY_MAPPINGS_FILE = _DATA_DIR / "category_mappings.json"
_SYNC_CONFIG_FILE = _DATA_DIR / "amazon_sync_config.json"


# ---------------------------------------------------------------------------
# Data model classes (from data-model.md)
# ---------------------------------------------------------------------------

@dataclass
class Correction:
    """A record of Erin correcting a category assignment."""
    timestamp: str  # ISO datetime
    from_category: str
    to_category: str
    context: str = ""  # Erin's adjustment message


@dataclass
class MatchedItem:
    """An Amazon item matched to a YNAB transaction, with its classification."""
    title: str
    price: float  # dollars
    quantity: int = 1
    seller: str = ""
    classified_category: str = ""
    classified_category_id: str = ""
    confidence: float = 0.0
    allocated_amount: int = 0  # milliunits (after tax/shipping proration)


@dataclass
class SyncRecord:
    """Tracks a processed YNAB transaction to prevent duplicates."""
    ynab_transaction_id: str
    amazon_order_number: str = ""
    status: str = "unprocessed"  # matched|enriched|split_pending|split_applied|auto_split|skipped|unmatched|refund_applied
    matched_at: str = ""
    enriched_at: str = ""
    split_applied_at: str = ""
    ynab_amount: int = 0  # milliunits
    ynab_date: str = ""
    items: list = field(default_factory=list)  # list of MatchedItem dicts
    suggestion_message_id: str = ""
    original_memo: str = ""
    original_category_id: str = ""


@dataclass
class CategoryMapping:
    """Learned association between Amazon item and YNAB budget category."""
    item_title_normalized: str
    category_name: str
    category_id: str
    confidence: float = 0.0
    source: str = "llm_initial"  # llm_initial|user_approved|user_corrected
    times_used: int = 0
    last_used: str = ""
    corrections: list = field(default_factory=list)  # list of Correction dicts


@dataclass
class SyncConfig:
    """Global configuration for the sync feature."""
    auto_split_enabled: bool = False
    last_sync: str = ""
    total_suggestions: int = 0
    unmodified_accepts: int = 0
    modified_accepts: int = 0
    skips: int = 0
    first_suggestion_date: str = ""
    known_charge_patterns: dict = field(default_factory=lambda: {
        "prime": "Subscriptions",
        "kindle": "Entertainment",
        "audible": "Entertainment",
        "amazon music": "Entertainment",
        "amazon fresh": "Groceries",
        "whole foods": "Groceries",
    })


# ---------------------------------------------------------------------------
# Persistence helpers (atomic JSON read/write, same pattern as discovery.py)
# ---------------------------------------------------------------------------

def _load_json(filepath: Path) -> dict:
    """Load JSON from file. Returns empty dict on failure."""
    try:
        if filepath.exists():
            return json.loads(filepath.read_text())
    except Exception as e:
        logger.warning("Failed to load %s: %s", filepath, e)
    return {}


def _save_json(filepath: Path, data: dict) -> None:
    """Save JSON atomically using tmp-file + rename."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = filepath.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str))
        tmp.replace(filepath)
    except Exception as e:
        logger.warning("Failed to save %s: %s", filepath, e)


# --- Sync Records ---

def load_sync_records() -> dict[str, dict]:
    """Load sync records. Key = ynab_transaction_id."""
    return _load_json(_SYNC_RECORDS_FILE)


def save_sync_record(record: SyncRecord) -> None:
    """Save or update a single sync record."""
    records = load_sync_records()
    records[record.ynab_transaction_id] = asdict(record)
    _save_json(_SYNC_RECORDS_FILE, records)


def is_transaction_processed(ynab_transaction_id: str) -> bool:
    """Check if a transaction has already been processed."""
    records = load_sync_records()
    return ynab_transaction_id in records


# --- Category Mappings ---

def load_category_mappings() -> dict[str, dict]:
    """Load category mappings. Key = item_title_normalized."""
    return _load_json(_CATEGORY_MAPPINGS_FILE)


def save_category_mapping(mapping: CategoryMapping) -> None:
    """Save or update a category mapping."""
    mappings = load_category_mappings()
    mappings[mapping.item_title_normalized] = asdict(mapping)
    _save_json(_CATEGORY_MAPPINGS_FILE, mappings)


def lookup_cached_category(item_title: str) -> Optional[dict]:
    """Look up a cached category mapping by item title. Returns mapping dict or None."""
    mappings = load_category_mappings()
    normalized = item_title.lower().strip()
    if normalized in mappings:
        return mappings[normalized]
    # Keyword substring match from learned patterns
    for key, mapping in mappings.items():
        if key in normalized or normalized in key:
            if mapping.get("confidence", 0) >= 0.8 and mapping.get("source") in ("user_approved", "user_corrected"):
                return mapping
    return None


# --- Sync Config ---

def load_sync_config() -> SyncConfig:
    """Load sync config, creating defaults if missing."""
    data = _load_json(_SYNC_CONFIG_FILE)
    if not data:
        config = SyncConfig()
        save_sync_config(config)
        return config
    # Reconstruct from dict
    return SyncConfig(
        auto_split_enabled=data.get("auto_split_enabled", False),
        last_sync=data.get("last_sync", ""),
        total_suggestions=data.get("total_suggestions", 0),
        unmodified_accepts=data.get("unmodified_accepts", 0),
        modified_accepts=data.get("modified_accepts", 0),
        skips=data.get("skips", 0),
        first_suggestion_date=data.get("first_suggestion_date", ""),
        known_charge_patterns=data.get("known_charge_patterns", SyncConfig().known_charge_patterns),
    )


def save_sync_config(config: SyncConfig) -> None:
    """Save sync config."""
    _save_json(_SYNC_CONFIG_FILE, asdict(config))


# ---------------------------------------------------------------------------
# Gmail API helpers (T007 — Gmail pivot)
# ---------------------------------------------------------------------------

_TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
_GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def _get_gmail_service():
    """Build and return an authenticated Gmail API service."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(_TOKEN_PATH, _GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        else:
            raise RuntimeError(
                "Gmail OAuth token not found or invalid. "
                "Re-run setup_calendar.py to authorize Gmail access."
            )
    return build("gmail", "v1", credentials=creds)


def _extract_html_body(message: dict) -> str:
    """Extract HTML body from a Gmail API message payload."""
    payload = message.get("payload", {})

    # Direct body
    if payload.get("mimeType") == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Check parts (and nested multipart)
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        for subpart in part.get("parts", []):
            if subpart.get("mimeType") == "text/html":
                data = subpart.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    return ""


import re


def _strip_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace to produce clean text for parsing."""
    # Remove style and script blocks entirely
    text = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # Replace <br>, <tr>, <p>, <div> with newlines for structure
    text = re.sub(r"<br[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(tr|p|div|td|li|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common entities
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#36;", "$")
    # Collapse whitespace but preserve newlines
    lines = [" ".join(line.split()) for line in text.split("\n")]
    text = "\n".join(line for line in lines if line.strip())
    return text


def _parse_order_email(html_body: str, email_date: str = "") -> list[dict]:
    """Use Claude to parse Amazon order confirmation email into structured data.

    Strips HTML first, then sends clean text to Claude Haiku.
    One email may contain multiple orders — returns a list of order dicts.
    Each dict has keys: order_number, order_date, grand_total, items.
    Returns empty list if parsing fails.
    """
    from anthropic import Anthropic
    from src.config import ANTHROPIC_API_KEY

    # Strip HTML to plain text — dramatically reduces noise for Claude
    clean_text = _strip_html(html_body)

    # Truncate to stay within token limits
    if len(clean_text) > 15000:
        clean_text = clean_text[:15000]

    # Quick sanity check: does this look like an Amazon order email?
    if "order" not in clean_text.lower() or "$" not in clean_text:
        logger.debug("Email doesn't look like an Amazon order confirmation, skipping")
        return []

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = (
        "Extract ALL order details from this Amazon order confirmation email.\n"
        "IMPORTANT: One email may contain MULTIPLE separate orders, each with its own "
        "order number and Grand Total. Extract each one.\n\n"
        "CRITICAL RULES:\n"
        "- Order numbers are in format ###-#######-####### (e.g., 112-1730641-1221858). "
        "Extract EXACTLY as shown — do NOT invent numbers.\n"
        "- grand_total is the 'Grand Total:' amount shown for EACH order. "
        "This includes tax and shipping — it's what gets charged to the card.\n"
        "- Item prices may appear as '$ 24 99' meaning $24.99. Convert to decimal.\n"
        "- If you cannot find a field, set it to null — do NOT guess.\n\n"
        "Return ONLY a valid JSON array of orders:\n"
        "[\n"
        "  {\n"
        '    "order_number": "###-#######-#######",\n'
        '    "grand_total": 41.08,\n'
        '    "items": [\n'
        '      {"title": "exact product name from email", "price": 24.99, "quantity": 1}\n'
        "    ]\n"
        "  }\n"
        "]\n\n"
        f"Email text:\n{clean_text}"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()

        # Parse as JSON array or single object
        if "[" in text:
            json_str = text[text.index("["):text.rindex("]") + 1]
            raw_orders = json.loads(json_str)
        elif "{" in text:
            json_str = text[text.index("{"):text.rindex("}") + 1]
            raw_orders = [json.loads(json_str)]
        else:
            return []

        if not isinstance(raw_orders, list):
            raw_orders = [raw_orders]

        # Validate and normalize each order
        validated = []
        for order in raw_orders:
            if not isinstance(order, dict):
                continue

            # Set order_date from email Date header (not in email body)
            order["order_date"] = email_date or None

            # Validate order number format
            order_num = order.get("order_number")
            if order_num and not re.match(r"^\d{3}-\d{7}-\d{7}$", str(order_num)):
                logger.warning("Rejected invalid order number: %s", order_num)
                order["order_number"] = None

            # Validate grand_total
            grand_total = order.get("grand_total")
            if grand_total is not None:
                try:
                    grand_total = float(grand_total)
                    if grand_total <= 0 or grand_total > 5000:
                        logger.warning("Rejected unreasonable total: %s", grand_total)
                        order["grand_total"] = None
                    else:
                        order["grand_total"] = grand_total
                except (ValueError, TypeError):
                    order["grand_total"] = None

            # Must have grand_total to be useful for matching
            if order.get("grand_total") is None:
                continue

            logger.info(
                "Parsed order %s: date=%s total=%.2f items=%d",
                order.get("order_number", "?"),
                order.get("order_date", "?"),
                order.get("grand_total", 0),
                len(order.get("items", [])),
            )
            validated.append(order)

        return validated

    except Exception as e:
        logger.warning("Claude email parsing failed: %s", e)

    return []


# ---------------------------------------------------------------------------
# Amazon order fetching via Gmail API (T007)
# ---------------------------------------------------------------------------

def get_amazon_orders(days: int = 30) -> tuple[list[dict], bool]:
    """Fetch Amazon order data from Gmail order confirmation emails.

    Searches Gmail for Amazon order confirmation emails, parses HTML with Claude
    to extract structured order data.

    Returns:
        Tuple of (orders_list, auth_failed).
        - orders_list: List of order dicts with keys: order_number, order_date,
          grand_total, items (list of {title, price, quantity}), shipments.
        - auth_failed: True if Gmail OAuth failed (caller should notify per FR-015).
    """
    try:
        service = _get_gmail_service()
    except Exception as e:
        logger.error("Gmail auth failed: %s", e)
        return [], True

    since_date = (date.today() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"from:auto-confirm@amazon.com after:{since_date}"

    try:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=50
        ).execute()
        messages = results.get("messages", [])

        if not messages:
            logger.info("No Amazon order emails found in last %d days", days)
            return [], False

        orders = []
        seen_order_numbers = set()
        for msg_meta in messages:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_meta["id"], format="full"
                ).execute()
                html_body = _extract_html_body(msg)
                if not html_body:
                    continue

                # Extract email Date header as order date
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                email_date_str = headers.get("Date", "")
                email_date = ""
                if email_date_str:
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(email_date_str)
                        email_date = dt.date().isoformat()
                    except Exception:
                        pass

                parsed_orders = _parse_order_email(html_body, email_date)
                for parsed in parsed_orders:
                    # Deduplicate by order number
                    order_num = parsed.get("order_number", "")
                    if order_num and order_num in seen_order_numbers:
                        continue
                    if order_num:
                        seen_order_numbers.add(order_num)
                    orders.append(parsed)
            except Exception as e:
                logger.warning("Failed to process email %s: %s", msg_meta["id"], e)
                continue

        logger.info(
            "Parsed %d Amazon orders from %d emails (last %d days)",
            len(orders), len(messages), days,
        )
        return orders, False

    except Exception as e:
        logger.error("Gmail API error: %s", e)
        auth_keywords = ("token", "auth", "credentials", "oauth", "expired", "invalid_grant")
        is_auth = any(kw in str(e).lower() for kw in auth_keywords)
        return [], is_auth


# ---------------------------------------------------------------------------
# T008: Find unprocessed Amazon transactions in YNAB
# ---------------------------------------------------------------------------

def find_amazon_transactions(days: int = 30) -> list[dict]:
    """Fetch YNAB transactions with Amazon payee, filter out already-processed ones.

    Returns list of unprocessed transaction dicts with id, amount, date, memo, payee_name.
    """
    from src.tools import ynab

    since_date = (date.today() - timedelta(days=days)).isoformat()
    url = f"{ynab.BASE_URL}/budgets/{ynab.YNAB_BUDGET_ID}/transactions"
    resp = httpx.get(url, headers=ynab.HEADERS, params={"since_date": since_date})
    resp.raise_for_status()
    txns = resp.json()["data"]["transactions"]

    # Filter to Amazon payees
    amazon_txns = []
    for t in txns:
        payee = (t.get("payee_name") or "").lower()
        if "amazon" in payee or "amzn" in payee:
            if not is_transaction_processed(t["id"]):
                amazon_txns.append({
                    "id": t["id"],
                    "amount": t["amount"],  # milliunits
                    "date": t["date"],
                    "memo": t.get("memo") or "",
                    "payee_name": t.get("payee_name") or "",
                    "category_id": t.get("category_id") or "",
                    "category_name": t.get("category_name") or "",
                    "account_id": t.get("account_id") or "",
                })

    logger.info("Found %d unprocessed Amazon transactions in YNAB", len(amazon_txns))
    return amazon_txns


# ---------------------------------------------------------------------------
# T009: Match Amazon orders to YNAB transactions
# ---------------------------------------------------------------------------

def match_orders_to_transactions(
    ynab_transactions: list[dict],
    amazon_orders: list[dict],
) -> list[dict]:
    """Match YNAB transactions to Amazon orders by date (±3 days) and exact penny amount.

    Returns list of {ynab_transaction, matched_order, match_type} dicts.
    Unmatched transactions get matched_order=None.
    """
    results = []
    used_orders = set()  # Track order numbers already matched

    for txn in ynab_transactions:
        txn_amount = abs(txn["amount"])  # milliunits (positive)
        txn_date = date.fromisoformat(txn["date"])
        matched_order = None
        match_type = "unmatched"

        for order in amazon_orders:
            order_num = order.get("order_number", "") or ""
            if order_num in used_orders:
                continue

            order_date_str = order.get("order_date")
            if not order_date_str:
                continue

            # Parse order date (already ISO format from Claude parsing)
            try:
                order_date = date.fromisoformat(order_date_str)
            except ValueError:
                continue

            # Check date within ±3 days
            day_diff = abs((txn_date - order_date).days)
            if day_diff > 3:
                continue

            # Check exact penny match on grand_total
            grand_total = order.get("grand_total")
            if grand_total is not None:
                order_amount_milli = int(round(abs(grand_total) * 1000))
                if order_amount_milli == txn_amount:
                    matched_order = order
                    match_type = "grand_total"
                    used_orders.add(order_num)
                    break

            # Try shipment subtotals for partial shipment matching
            for shipment in order.get("shipments", []):
                ship_total = shipment.get("total") or shipment.get("grand_total")
                if ship_total is not None:
                    ship_milli = int(round(abs(ship_total) * 1000))
                    if ship_milli == txn_amount:
                        matched_order = order
                        match_type = "shipment"
                        used_orders.add(order_num)
                        break
            if matched_order:
                break

        results.append({
            "ynab_transaction": txn,
            "matched_order": matched_order,
            "match_type": match_type,
        })

    matched = sum(1 for r in results if r["matched_order"])
    logger.info("Matched %d/%d transactions to Amazon orders", matched, len(results))
    return results


# ---------------------------------------------------------------------------
# T010: Classify item into YNAB budget category
# ---------------------------------------------------------------------------

def classify_item(
    item_title: str,
    item_price: float,
    category_list: list[dict],
    past_mappings: dict,
) -> dict:
    """Classify an Amazon item into a YNAB budget category.

    Priority: cached exact match → keyword match → Claude Haiku LLM call.

    Returns dict with category_name, category_id, confidence.
    """
    # 1. Check cached exact match
    cached = lookup_cached_category(item_title)
    if cached:
        return {
            "category_name": cached["category_name"],
            "category_id": cached["category_id"],
            "confidence": min(cached.get("confidence", 0.9), 1.0),
        }

    # 2. LLM classification via Claude Haiku
    try:
        from anthropic import Anthropic
        from src.config import ANTHROPIC_API_KEY

        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        cat_names = [c["name"] for c in category_list]

        # Build examples from past mappings (up to 10 recent)
        examples = []
        for title, mapping in list(past_mappings.items())[:10]:
            examples.append(f'  "{title}" → {mapping["category_name"]}')
        examples_text = "\n".join(examples) if examples else "  (no past examples yet)"

        prompt = (
            f"Given the family's YNAB budget categories:\n{', '.join(cat_names)}\n\n"
            f"And these past categorization decisions:\n{examples_text}\n\n"
            f'Classify this Amazon item: "{item_title}" (${item_price:.2f})\n\n'
            'Return ONLY valid JSON: {"category": "exact category name from list above", "confidence": 0.0-1.0, "reasoning": "brief explanation"}'
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        # Extract JSON from response
        if "{" in text:
            json_str = text[text.index("{"):text.rindex("}") + 1]
            result = json.loads(json_str)

            # Match category name to ID
            cat_name = result.get("category", "")
            cat_id = ""
            for c in category_list:
                if c["name"].lower() == cat_name.lower():
                    cat_id = c["id"]
                    cat_name = c["name"]  # Use canonical name
                    break

            if cat_id:
                return {
                    "category_name": cat_name,
                    "category_id": cat_id,
                    "confidence": float(result.get("confidence", 0.5)),
                }

    except Exception as e:
        logger.error("LLM classification failed for '%s': %s", item_title, e)

    # 3. Fallback — return empty (caller handles unclassified items)
    return {"category_name": "", "category_id": "", "confidence": 0.0}


# ---------------------------------------------------------------------------
# T011: Enrich memos and classify matched transactions
# ---------------------------------------------------------------------------

def enrich_and_classify(matched_transactions: list[dict]) -> list[dict]:
    """For each matched transaction: update memo, classify items, handle single-item auto-split.

    Returns enriched list with classification results added.
    """
    from src.tools import ynab

    categories = ynab._get_categories()
    cat_list = [{"id": c["id"], "name": c["name"]} for c in categories.values()]
    past_mappings = load_category_mappings()

    enriched = []
    for match in matched_transactions:
        txn = match["ynab_transaction"]
        order = match["matched_order"]

        if order is None:
            # Check if this is a refund (positive amount = inflow)
            if txn["amount"] > 0:
                refund_result = match_refund(txn)
                if refund_result:
                    match["refund_result"] = refund_result
                    enriched.append(match)
                    continue

            # Try known charge patterns for unmatched transactions (T030)
            pattern_result = handle_known_charge_patterns(txn)
            if pattern_result:
                match["pattern_result"] = pattern_result
                enriched.append(match)
                continue

            # Truly unmatched
            enriched.append(match)
            continue

        items = order.get("items", []) or []
        if not items:
            enriched.append(match)
            continue

        # Build item names for memo
        item_names = []
        classified_items = []
        for item in items:
            title = item.get("title", "") or "Unknown item"
            price = item.get("price", 0) or 0
            qty = item.get("quantity", 1) or 1
            item_names.append(title[:50])  # Truncate long titles

            classification = classify_item(title, price, cat_list, past_mappings)
            classified_items.append(MatchedItem(
                title=title,
                price=float(price),
                quantity=qty,
                seller=item.get("seller", "") or "",
                classified_category=classification["category_name"],
                classified_category_id=classification["category_id"],
                confidence=classification["confidence"],
            ))

        # Update memo with item names (T005)
        memo_text = ", ".join(item_names)
        if len(memo_text) > 150:
            memo_text = memo_text[:147] + "..."
        ynab.update_transaction_memo(txn["id"], memo_text)

        # Proportional tax/shipping allocation (FR-010)
        total_item_price = sum(ci.price * ci.quantity for ci in classified_items)
        txn_total = abs(txn["amount"])  # milliunits
        for ci in classified_items:
            if total_item_price > 0:
                proportion = (ci.price * ci.quantity) / total_item_price
            else:
                proportion = 1.0 / len(classified_items)
            ci.allocated_amount = int(round(txn_total * proportion))

        # Ensure amounts sum exactly to transaction total
        allocated_sum = sum(ci.allocated_amount for ci in classified_items)
        if classified_items and allocated_sum != txn_total:
            classified_items[-1].allocated_amount += (txn_total - allocated_sum)

        # Create sync record
        now = datetime.now().isoformat()
        record = SyncRecord(
            ynab_transaction_id=txn["id"],
            amazon_order_number=order.get("order_number", "") or "",
            status="enriched",
            matched_at=now,
            enriched_at=now,
            ynab_amount=txn["amount"],
            ynab_date=txn["date"],
            items=[asdict(ci) for ci in classified_items],
            original_memo=txn.get("memo") or "",
            original_category_id=txn.get("category_id") or "",
        )

        # Single-item orders: auto-categorize directly (FR-006)
        if len(classified_items) == 1 and classified_items[0].category_id:
            ci = classified_items[0]
            ynab.split_transaction(txn["id"], [{
                "amount_milliunits": txn["amount"],  # Keep original sign
                "category_id": ci.classified_category_id,
                "memo": ci.title[:200],
            }])
            record.status = "auto_split"
            record.split_applied_at = now
            logger.info("Auto-categorized single-item order: %s → %s", ci.title, ci.classified_category)

        save_sync_record(record)
        match["classified_items"] = classified_items
        match["sync_record"] = record
        enriched.append(match)

    return enriched


# ---------------------------------------------------------------------------
# T012: Format suggestion message for WhatsApp
# ---------------------------------------------------------------------------

def format_suggestion_message(enriched_transactions: list[dict]) -> str:
    """Build consolidated WhatsApp message with split suggestions.

    Returns formatted message string, or empty string if nothing to suggest.
    """
    suggestions = []  # multi-item transactions needing approval
    auto_splits = []  # single-item auto-categorized
    unmatched = []  # couldn't match to Amazon order

    for match in enriched_transactions:
        txn = match["ynab_transaction"]
        record = match.get("sync_record")

        if record and record.status == "auto_split":
            items = match.get("classified_items", [])
            if items:
                ci = items[0]
                auto_splits.append(
                    f"• ${abs(txn['amount']) / 1000:.2f} ({txn['date']}) — {ci.title[:40]}\n"
                    f"  ✅ Auto-categorized → {ci.classified_category}"
                )
            continue

        if match["matched_order"] is None:
            unmatched.append(
                f"• ${abs(txn['amount']) / 1000:.2f} ({txn['date']}) — unmatched\n"
                f"  Tagged as \"Unmatched Amazon charge\" — what category?"
            )
            continue

        items = match.get("classified_items", [])
        if not items:
            continue

        # Multi-item suggestion
        idx = len(suggestions) + 1
        lines = [f"{idx}️⃣ ${abs(txn['amount']) / 1000:.2f} ({txn['date']}) — {len(items)} items:"]
        for ci in items:
            amt = abs(ci.allocated_amount) / 1000
            uncertain = " ⚠️" if ci.confidence < 0.7 else ""
            lines.append(f"  • {ci.title[:40]} → {ci.classified_category} (${amt:.2f}){uncertain}")

        lines.append(f'Reply "{idx} yes" to split, "{idx} adjust" to modify, "{idx} skip" to leave as-is')
        suggestions.append("\n".join(lines))

        # Update record to split_pending
        if record:
            record.status = "split_pending"
            save_sync_record(record)

    # Large purchase tips (T027)
    large_tips = check_large_purchases(enriched_transactions)

    if not suggestions and not auto_splits and not unmatched and not large_tips:
        return ""

    parts = ["📦 Amazon Sync"]
    if suggestions:
        parts[0] += f" — {len(suggestions)} need review"
        parts.append("")
        parts.extend(suggestions)
    if auto_splits:
        parts.append("")
        parts.extend(auto_splits)
    if unmatched:
        parts.append("")
        parts.extend(unmatched)
    if large_tips:
        parts.append("")
        parts.extend(large_tips)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# T013: Handle Erin's reply to sync suggestions
# ---------------------------------------------------------------------------

# Module-level storage for pending suggestions (indexed by position)
_pending_suggestions: list[dict] = []


def set_pending_suggestions(enriched_transactions: list[dict]) -> None:
    """Store pending suggestions so replies can reference them by index."""
    global _pending_suggestions
    _pending_suggestions = [
        m for m in enriched_transactions
        if m.get("sync_record") and m["sync_record"].status == "split_pending"
    ]


def handle_sync_reply(message_text: str) -> str:
    """Parse Erin's reply to a sync suggestion and apply the action.

    Supports: "N yes", "N adjust — [correction]", "N skip", "yes" (if only one pending).
    """
    from src.tools import ynab

    text = message_text.strip().lower()
    config = load_sync_config()

    # Parse index and action
    parts = text.split(None, 1)
    if not parts:
        return ""

    # Handle single pending shorthand ("yes", "skip")
    idx = 1
    action = text
    if parts[0].isdigit():
        idx = int(parts[0])
        action = parts[1] if len(parts) > 1 else ""
    elif len(_pending_suggestions) != 1:
        return ""  # Can't determine which transaction

    if idx < 1 or idx > len(_pending_suggestions):
        return f"Transaction #{idx} not found. Valid range: 1-{len(_pending_suggestions)}."

    match = _pending_suggestions[idx - 1]
    txn = match["ynab_transaction"]
    record = match.get("sync_record")
    items = match.get("classified_items", [])

    if not record or not items:
        return "No pending suggestion found for that transaction."

    now = datetime.now().isoformat()

    if action.startswith("yes"):
        # Apply suggested split
        subs = []
        for ci in items:
            subs.append({
                "amount_milliunits": -abs(ci.allocated_amount),  # negative for outflow
                "category_id": ci.classified_category_id,
                "memo": ci.title[:200],
            })
        result = ynab.split_transaction(txn["id"], subs)
        record.status = "split_applied"
        record.split_applied_at = now
        save_sync_record(record)

        # Save mappings as user_approved
        for ci in items:
            save_category_mapping(CategoryMapping(
                item_title_normalized=ci.title.lower().strip(),
                category_name=ci.classified_category,
                category_id=ci.classified_category_id,
                confidence=max(ci.confidence, 0.9),
                source="user_approved",
                times_used=1,
                last_used=now,
            ))

        # Update acceptance stats
        config.total_suggestions += 1
        config.unmodified_accepts += 1
        if not config.first_suggestion_date:
            config.first_suggestion_date = date.today().isoformat()
        save_sync_config(config)

        return f"✅ Split applied for ${abs(txn['amount']) / 1000:.2f} Amazon order ({len(items)} items)."

    elif action.startswith("skip"):
        record.status = "skipped"
        save_sync_record(record)
        config.total_suggestions += 1
        config.skips += 1
        if not config.first_suggestion_date:
            config.first_suggestion_date = date.today().isoformat()
        save_sync_config(config)
        return f"⏭️ Skipped — memo enrichment kept, no split applied."

    elif action.startswith("adjust"):
        # Parse correction context
        correction_text = action.replace("adjust", "").strip().lstrip("—-–").strip()
        record.status = "split_applied"
        record.split_applied_at = now
        save_sync_record(record)

        config.total_suggestions += 1
        config.modified_accepts += 1
        if not config.first_suggestion_date:
            config.first_suggestion_date = date.today().isoformat()
        save_sync_config(config)

        # The actual adjustment is handled by Claude interpreting the natural language
        # correction and calling the appropriate tools. We record the stats here.
        return (
            f"📝 Noted your adjustment: \"{correction_text}\". "
            f"I'll apply the corrected split and remember this for next time."
        )

    return ""


# ---------------------------------------------------------------------------
# Sync status (for tool registration)
# ---------------------------------------------------------------------------

def get_sync_status() -> str:
    """Return current sync status and statistics."""
    config = load_sync_config()
    records = load_sync_records()

    total = len(records)
    matched = sum(1 for r in records.values() if r.get("status") not in ("unmatched",))
    split = sum(1 for r in records.values() if r.get("status") in ("split_applied", "auto_split"))

    acceptance_rate = 0
    total_sug = config.total_suggestions
    if total_sug > 0:
        acceptance_rate = round((config.unmodified_accepts / total_sug) * 100, 1)

    lines = [
        "📊 Amazon Sync Status:",
        f"• Last sync: {config.last_sync or 'Never'}",
        f"• Transactions processed: {total}",
        f"• Orders matched: {matched}",
        f"• Splits applied: {split}",
        f"• Suggestions sent: {total_sug}",
        f"• Acceptance rate: {acceptance_rate}% ({config.unmodified_accepts} unmodified / {total_sug} total)",
        f"• Auto-split mode: {'✅ Enabled' if config.auto_split_enabled else '❌ Disabled'}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# T017: Nightly sync orchestrator
# ---------------------------------------------------------------------------

def run_nightly_sync() -> str | None:
    """Full nightly sync pipeline. Returns WhatsApp message or None if nothing to report.

    1. Fetch Amazon orders (last 30 days)
    2. Find unprocessed Amazon transactions in YNAB
    3. Match orders to transactions
    4. Enrich memos + classify items
    5. Format suggestion message (or auto-split if enabled)
    6. Return message for WhatsApp (caller sends it)

    Errors are logged but never returned as user-facing messages (US2-AS4).
    """
    try:
        # Fetch Amazon orders
        orders, auth_failed = get_amazon_orders()
        if auth_failed:
            return "⚠️ Amazon sync paused — Gmail OAuth token expired. Ask Jason to re-run setup_calendar.py on the NUC."
        if not orders:
            logger.info("Nightly sync: no Amazon orders found")
            return None

        # Find unprocessed YNAB transactions
        txns = find_amazon_transactions()
        if not txns:
            logger.info("Nightly sync: no new transactions to process")
            return None

        # Match and enrich
        matched = match_orders_to_transactions(txns, orders)
        enriched = enrich_and_classify(matched)

        # Check for auto-split mode (US3)
        config = load_sync_config()
        if config.auto_split_enabled:
            return _run_auto_split(enriched, config)

        # Suggestion mode — format message
        message = format_suggestion_message(enriched)
        set_pending_suggestions(enriched)

        # Timeout sweep — mark old pending suggestions as skipped (T031)
        _sweep_timed_out_suggestions()

        # Check auto-split graduation (T021)
        graduation_msg = check_auto_split_graduation()
        if graduation_msg:
            message = (message + "\n\n" + graduation_msg) if message else graduation_msg

        # Update last sync
        config.last_sync = datetime.now().isoformat()
        save_sync_config(config)

        return message if message else None

    except Exception as e:
        logger.error("Nightly sync failed: %s", e)
        return None  # Silent failure per US2-AS4


def _run_auto_split(enriched: list[dict], config: SyncConfig) -> str | None:
    """Apply auto-splits for high-confidence items, fall back to suggestions for low-confidence (T022).

    When auto_split_enabled is True:
    - Items with confidence >= 0.7: auto-split without confirmation
    - Items with confidence < 0.7: fall back to suggestion flow for that transaction (AS3)
    """
    from src.tools import ynab

    auto_split_lines = []
    needs_suggestion = []  # low-confidence transactions fall back to suggestions

    for match in enriched:
        txn = match["ynab_transaction"]
        record = match.get("sync_record")
        items = match.get("classified_items", [])

        if not record or not items:
            continue

        # Already auto-categorized (single item) — skip
        if record.status == "auto_split":
            ci = items[0]
            auto_split_lines.append(f"  • {ci.title[:40]} → {ci.classified_category} (${abs(ci.allocated_amount) / 1000:.2f})")
            continue

        # Check if any item has low confidence
        low_confidence = any(ci.confidence < 0.7 for ci in items)

        if low_confidence:
            # Fall back to suggestion flow for this transaction
            needs_suggestion.append(match)
            continue

        # All items high confidence — auto-split
        subs = []
        for ci in items:
            subs.append({
                "amount_milliunits": -abs(ci.allocated_amount),
                "category_id": ci.classified_category_id,
                "memo": ci.title[:200],
            })

        try:
            ynab.split_transaction(txn["id"], subs)
            record.status = "auto_split"
            record.split_applied_at = datetime.now().isoformat()
            save_sync_record(record)

            amt = abs(txn["amount"]) / 1000
            item_summary = ", ".join(f"{ci.title[:30]} → {ci.classified_category}" for ci in items)
            auto_split_lines.append(f"  • ${amt:.2f}: {item_summary}")

            # Update acceptance stats (auto-splits count as unmodified accepts)
            config.total_suggestions += 1
            config.unmodified_accepts += 1
        except Exception as e:
            logger.error("Auto-split failed for %s: %s", txn["id"], e)

    # Build summary message
    parts = []
    if auto_split_lines:
        parts.append(f"✅ Auto-split {len(auto_split_lines)} Amazon transaction(s):")
        parts.extend(auto_split_lines)

    # Handle low-confidence items via suggestion flow
    if needs_suggestion:
        suggestion_msg = format_suggestion_message(needs_suggestion)
        set_pending_suggestions(needs_suggestion)
        if suggestion_msg:
            parts.append("")
            parts.append(suggestion_msg)

    config.last_sync = datetime.now().isoformat()
    save_sync_config(config)
    return "\n".join(parts) if parts else None


def _sweep_timed_out_suggestions() -> None:
    """Mark pending suggestions older than 24 hours as skipped (T031)."""
    records = load_sync_records()
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    config = load_sync_config()
    updated = False

    for txn_id, record in records.items():
        if record.get("status") == "split_pending":
            enriched_at = record.get("enriched_at", "")
            if enriched_at and enriched_at < cutoff:
                record["status"] = "skipped"
                config.total_suggestions += 1
                config.skips += 1
                updated = True
                logger.info("Timed out pending suggestion for %s", txn_id)

    if updated:
        _save_json(_SYNC_RECORDS_FILE, records)
        save_sync_config(config)


# ---------------------------------------------------------------------------
# T020: Acceptance rate calculation
# ---------------------------------------------------------------------------

def get_acceptance_rate() -> float:
    """Calculate unmodified acceptance rate (0.0-1.0)."""
    config = load_sync_config()
    if config.total_suggestions == 0:
        return 0.0
    return config.unmodified_accepts / config.total_suggestions


# ---------------------------------------------------------------------------
# T021: Auto-split graduation check
# ---------------------------------------------------------------------------

def check_auto_split_graduation() -> str | None:
    """Check if acceptance rate qualifies for auto-split graduation.

    Criteria: 14+ days since first suggestion, 80%+ acceptance rate,
    10+ suggestions, auto_split not already enabled.

    Returns WhatsApp message if graduation prompt should be sent, else None.
    """
    config = load_sync_config()

    if config.auto_split_enabled:
        return None
    if config.total_suggestions < 10:
        return None
    if not config.first_suggestion_date:
        return None

    days_since = (date.today() - date.fromisoformat(config.first_suggestion_date)).days
    if days_since < 14:
        return None

    rate = get_acceptance_rate()
    if rate < 0.8:
        return None

    pct = round(rate * 100)
    return (
        f"I've been getting your Amazon categories right {pct}% of the time "
        f"over the past {days_since} days ({config.unmodified_accepts}/{config.total_suggestions} "
        f"unmodified). Want me to start auto-splitting? You can always undo or turn it off."
    )


def set_auto_split(enabled: bool) -> str:
    """Enable or disable auto-split mode with validation."""
    config = load_sync_config()

    if enabled and not config.auto_split_enabled:
        # Validate qualification
        rate = get_acceptance_rate()
        if config.total_suggestions < 10 or rate < 0.8:
            return (
                f"Auto-split requires 80%+ acceptance rate over 10+ suggestions. "
                f"Current: {round(rate * 100)}% ({config.total_suggestions} suggestions)."
            )

    config.auto_split_enabled = enabled
    save_sync_config(config)
    status = "enabled" if enabled else "disabled"
    return f"✅ Auto-split mode {status}."


# ---------------------------------------------------------------------------
# T023: Undo flow
# ---------------------------------------------------------------------------

def handle_undo(transaction_index: int) -> str:
    """Undo an auto-split by reverting to original unsplit transaction.

    Looks up the most recent auto-split records and reverts by index.
    """
    from src.tools import ynab

    records = load_sync_records()
    # Get recent auto-split records (for undo referencing)
    auto_splits = [
        (txn_id, r) for txn_id, r in records.items()
        if r.get("status") == "auto_split"
    ]

    if not auto_splits:
        return "No auto-split transactions found to undo."

    # Sort by split_applied_at descending (most recent first)
    auto_splits.sort(key=lambda x: x[1].get("split_applied_at", ""), reverse=True)

    if transaction_index < 1 or transaction_index > len(auto_splits):
        return f"Invalid index. Valid range: 1-{len(auto_splits)}."

    txn_id, record = auto_splits[transaction_index - 1]

    try:
        # Delete the split transaction
        ynab.delete_transaction(txn_id)

        # Restore original memo and category
        original_memo = record.get("original_memo", "")
        original_cat = record.get("original_category_id", "")

        if original_memo or original_cat:
            ynab.update_transaction_memo(txn_id, original_memo or "")

        # Update record status
        record["status"] = "undone"
        records[txn_id] = record
        _save_json(_SYNC_RECORDS_FILE, records)

        return f"↩️ Undo complete — reverted split on ${abs(record.get('ynab_amount', 0)) / 1000:.2f} transaction. You can re-categorize manually in YNAB."

    except Exception as e:
        logger.error("Undo failed for %s: %s", txn_id, e)
        return f"Undo failed: {e}. You can fix this manually in YNAB."


# ---------------------------------------------------------------------------
# T029: Refund matching
# ---------------------------------------------------------------------------

def match_refund(txn: dict) -> str | None:
    """Match a refund (positive Amazon transaction) to an original purchase.

    Tries exact amount match, then item-level partial refund match.
    Returns WhatsApp-formatted result or None.
    """
    from src.tools import ynab

    refund_amount = abs(txn["amount"])  # milliunits
    txn_date = date.fromisoformat(txn["date"])
    records = load_sync_records()

    # Try exact match to original purchase amount
    for txn_id, record in records.items():
        if record.get("status") not in ("split_applied", "auto_split"):
            continue
        if abs(record.get("ynab_amount", 0)) == refund_amount:
            rec_date = record.get("ynab_date", "")
            if rec_date:
                day_diff = abs((txn_date - date.fromisoformat(rec_date)).days)
                if day_diff <= 60:  # refunds can take a while
                    # Apply refund to same categories
                    items = record.get("items", [])
                    if items and len(items) == 1:
                        cat_id = items[0].get("classified_category_id", "")
                        if cat_id:
                            ynab.split_transaction(txn["id"], [{
                                "amount_milliunits": txn["amount"],
                                "category_id": cat_id,
                                "memo": f"Refund: {items[0].get('title', '')[:150]}",
                            }])
                    # Record refund
                    save_sync_record(SyncRecord(
                        ynab_transaction_id=txn["id"],
                        amazon_order_number=record.get("amazon_order_number", ""),
                        status="refund_applied",
                        matched_at=datetime.now().isoformat(),
                        ynab_amount=txn["amount"],
                        ynab_date=txn["date"],
                        items=items,
                    ))
                    return f"↩️ Refund of ${refund_amount / 1000:.2f} matched to original order — applied to same category."

    # Try item-level partial refund match
    for txn_id, record in records.items():
        if record.get("status") not in ("split_applied", "auto_split"):
            continue
        for item in record.get("items", []):
            item_amt = abs(item.get("allocated_amount", 0))
            if item_amt == refund_amount:
                cat_id = item.get("classified_category_id", "")
                if cat_id:
                    ynab.split_transaction(txn["id"], [{
                        "amount_milliunits": txn["amount"],
                        "category_id": cat_id,
                        "memo": f"Partial refund: {item.get('title', '')[:150]}",
                    }])
                save_sync_record(SyncRecord(
                    ynab_transaction_id=txn["id"],
                    amazon_order_number=record.get("amazon_order_number", ""),
                    status="refund_applied",
                    matched_at=datetime.now().isoformat(),
                    ynab_amount=txn["amount"],
                    ynab_date=txn["date"],
                    items=[item],
                ))
                return f"↩️ Partial refund of ${refund_amount / 1000:.2f} matched — applied to {item.get('classified_category', 'original category')}."

    return None  # Unmatched refund — caller asks Erin


# ---------------------------------------------------------------------------
# T030: Known charge pattern handling
# ---------------------------------------------------------------------------

def handle_known_charge_patterns(txn: dict) -> str | None:
    """Check unmatched Amazon transactions against known charge patterns.

    Returns result message if auto-categorized, None if truly unmatched.
    """
    from src.tools import ynab

    config = load_sync_config()
    payee = (txn.get("payee_name") or "").lower()
    memo = (txn.get("memo") or "").lower()
    combined = f"{payee} {memo}"

    for pattern, category_name in config.known_charge_patterns.items():
        if pattern in combined:
            # Find category ID
            categories = ynab._get_categories()
            cat_id = ""
            for cid, cat in categories.items():
                if cat["name"].lower() == category_name.lower():
                    cat_id = cid
                    break

            if cat_id:
                ynab.split_transaction(txn["id"], [{
                    "amount_milliunits": txn["amount"],
                    "category_id": cat_id,
                    "memo": f"Auto: {pattern.title()} charge",
                }])

                save_sync_record(SyncRecord(
                    ynab_transaction_id=txn["id"],
                    status="auto_split",
                    matched_at=datetime.now().isoformat(),
                    split_applied_at=datetime.now().isoformat(),
                    ynab_amount=txn["amount"],
                    ynab_date=txn["date"],
                    original_memo=txn.get("memo") or "",
                    original_category_id=txn.get("category_id") or "",
                ))
                return f"✅ Known charge: {pattern.title()} → {category_name}"

    # Tag as unmatched
    ynab.update_transaction_memo(txn["id"], "Unmatched Amazon charge")
    save_sync_record(SyncRecord(
        ynab_transaction_id=txn["id"],
        status="unmatched",
        matched_at=datetime.now().isoformat(),
        ynab_amount=txn["amount"],
        ynab_date=txn["date"],
        original_memo=txn.get("memo") or "",
    ))
    return None  # Truly unmatched — suggestion message will ask Erin


# ---------------------------------------------------------------------------
# T025: Amazon spending breakdown
# ---------------------------------------------------------------------------

def get_amazon_spending_breakdown(month: str = "") -> str:
    """Aggregate sync records by category for the given month, compare against YNAB budgets.

    Returns formatted breakdown: spending per category, comparison with budget goals.
    """
    from src.tools import ynab

    records = load_sync_records()

    # Determine month filter
    if month:
        target_month = month[:7]  # YYYY-MM
    else:
        target_month = date.today().strftime("%Y-%m")

    # Aggregate by category
    category_totals: dict[str, float] = {}
    for record in records.values():
        rec_date = record.get("ynab_date", "")
        if not rec_date or rec_date[:7] != target_month:
            continue
        for item in record.get("items", []):
            cat = item.get("classified_category") or "Uncategorized"
            amt = abs(item.get("allocated_amount", 0)) / 1000  # milliunits to dollars
            category_totals[cat] = category_totals.get(cat, 0) + amt

    if not category_totals:
        return f"No Amazon spending data for {target_month}."

    # Get budget data for comparison
    budget_data = {}
    try:
        summary = ynab.get_budget_summary(f"{target_month}-01")
        if isinstance(summary, list):
            for cat in summary:
                if isinstance(cat, dict):
                    budget_data[cat.get("name", "")] = {
                        "budgeted": cat.get("budgeted", 0),
                        "activity": cat.get("activity", 0),
                    }
    except Exception:
        pass  # Budget comparison is optional

    # Format breakdown
    total_amazon = sum(category_totals.values())
    lines = [f"📦 Amazon Spending — {target_month}", f"Total: ${total_amazon:,.2f}\n"]

    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    for cat_name, amount in sorted_cats:
        budget_note = ""
        if cat_name in budget_data:
            budgeted = budget_data[cat_name].get("budgeted", 0) / 1000
            if budgeted > 0:
                pct = (amount / budgeted) * 100
                status = "within goal" if pct <= 100 else f"${amount - budgeted:,.0f} over"
                budget_note = f" — {status}"
        lines.append(f"  • ${amount:,.2f} {cat_name}{budget_note}")

    # Top items insight
    top_items = []
    for record in records.values():
        if record.get("ynab_date", "")[:7] != target_month:
            continue
        for item in record.get("items", []):
            top_items.append((item.get("title", ""), abs(item.get("allocated_amount", 0)) / 1000))
    top_items.sort(key=lambda x: x[1], reverse=True)
    if top_items:
        lines.append(f"\nTop purchases:")
        for title, amt in top_items[:5]:
            lines.append(f"  • ${amt:,.2f} — {title[:50]}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# T026: Recurring purchase detection
# ---------------------------------------------------------------------------

def detect_recurring_purchases() -> list[dict]:
    """Scan category mappings and sync records for items that appear monthly.

    Returns list of {title, category, avg_amount, interval_days, occurrences}.
    """
    records = load_sync_records()

    # Group items by normalized title
    item_dates: dict[str, list[tuple[str, float]]] = {}
    for record in records.values():
        rec_date = record.get("ynab_date", "")
        for item in record.get("items", []):
            title = item.get("title", "").lower().strip()
            amt = abs(item.get("allocated_amount", 0)) / 1000
            if title:
                item_dates.setdefault(title, []).append((rec_date, amt))

    recurring = []
    for title, entries in item_dates.items():
        if len(entries) < 2:
            continue

        # Sort by date
        entries.sort()
        dates = [date.fromisoformat(d) for d, _ in entries]
        amounts = [a for _, a in entries]

        # Calculate average interval between purchases
        intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        avg_interval = sum(intervals) / len(intervals)

        # Monthly pattern: average interval between 25-35 days
        if 25 <= avg_interval <= 35:
            recurring.append({
                "title": entries[0][0].split("|")[0] if "|" in entries[0][0] else title,  # Use original case if available
                "category": "",
                "avg_amount": sum(amounts) / len(amounts),
                "interval_days": round(avg_interval),
                "occurrences": len(entries),
            })
            # Fill category from mappings
            cached = lookup_cached_category(title)
            if cached:
                recurring[-1]["category"] = cached.get("category_name", "")

    return recurring


# ---------------------------------------------------------------------------
# T027: Large purchase handling
# ---------------------------------------------------------------------------

LARGE_PURCHASE_THRESHOLD = 200  # dollars


def check_large_purchases(enriched_transactions: list[dict]) -> list[str]:
    """Detect purchases above threshold and generate advisory tips.

    Returns list of tip strings to append to suggestion messages.
    """
    tips = []
    for match in enriched_transactions:
        items = match.get("classified_items", [])
        for ci in items:
            total_dollars = abs(ci.allocated_amount) / 1000
            if total_dollars >= LARGE_PURCHASE_THRESHOLD:
                tips.append(
                    f"💰 Large purchase: {ci.title[:40]} (${total_dollars:,.2f}) — "
                    f"this might come from a sinking fund. Currently categorized as "
                    f"{ci.classified_category or 'uncategorized'}."
                )
    return tips
