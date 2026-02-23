"""AnyList sidecar bridge — push grocery lists via the Node.js REST API."""

import logging
import httpx
from src.config import ANYLIST_SIDECAR_URL

logger = logging.getLogger(__name__)

TIMEOUT = 15.0

# Safety thresholds
MAX_ANYLIST_PUSH = 200    # refuse to push more items than this
MAX_ANYLIST_CLEAR = 150   # warn if clearing more than this many items


def push_grocery_list(items: list[str], list_name: str = "Grocery") -> str:
    """Clear the list and push new grocery items to AnyList.

    Args:
        items: List of grocery item names.
        list_name: AnyList list name (default "Grocery").

    Returns status message. Raises on connection failure so the caller
    can fall back to WhatsApp-formatted list.
    """
    if not items:
        return "No items to push."

    if len(items) > MAX_ANYLIST_PUSH:
        logger.error(
            "SAFEGUARD: Refusing to push %d items to AnyList (max %d).",
            len(items), MAX_ANYLIST_PUSH,
        )
        raise ValueError(
            f"Safety limit: {len(items)} grocery items is unusually high "
            f"(max {MAX_ANYLIST_PUSH}). Check the grocery list generation."
        )

    base = ANYLIST_SIDECAR_URL.rstrip("/")

    # Clear old items first
    resp = httpx.post(f"{base}/clear", json={"list": list_name}, timeout=TIMEOUT)
    resp.raise_for_status()
    cleared = resp.json().get("count", 0)
    if cleared > MAX_ANYLIST_CLEAR:
        logger.warning(
            "SAFEGUARD WARNING: Cleared %d items from AnyList (threshold %d). "
            "This is unusually high.", cleared, MAX_ANYLIST_CLEAR,
        )
    logger.info("Cleared %d old items from AnyList", cleared)

    # Add new items in bulk
    resp = httpx.post(
        f"{base}/add-bulk",
        json={"items": items, "list": list_name},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    added = resp.json().get("count", 0)
    logger.info("Added %d items to AnyList", added)

    return f"Pushed {added} items to AnyList. Open the app → 'Order Pickup or Delivery' → Whole Foods."


def clear_grocery_list(list_name: str = "Grocery") -> str:
    """Clear all items from an AnyList list."""
    base = ANYLIST_SIDECAR_URL.rstrip("/")
    resp = httpx.post(f"{base}/clear", json={"list": list_name}, timeout=TIMEOUT)
    resp.raise_for_status()
    count = resp.json().get("count", 0)
    if count > MAX_ANYLIST_CLEAR:
        logger.warning(
            "SAFEGUARD WARNING: Cleared %d items from AnyList '%s' (threshold %d).",
            count, list_name, MAX_ANYLIST_CLEAR,
        )
    return f"Cleared {count} items from {list_name}."


def get_grocery_items(list_name: str = "Grocery") -> str:
    """Get current items from an AnyList list."""
    base = ANYLIST_SIDECAR_URL.rstrip("/")
    resp = httpx.get(f"{base}/items", params={"list": list_name}, timeout=TIMEOUT)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        return "No items on the list."
    lines = [f"- {'✅' if i.get('checked') else '⬜'} {i['name']}" for i in items]
    return "\n".join(lines)
