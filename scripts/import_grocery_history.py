"""Import grocery order history from multiple stores into Notion Grocery History.

Parses PDF receipts from Amazon/Whole Foods, Costco, and Raley's. Uses Claude
to extract items (decoding store abbreviations), then normalizes names across
stores so "CINNTOASTCRN" (Costco) and "Gm Cinn Toast Crunch Xl" (Raley's)
merge into one canonical "Cinnamon Toast Crunch" entry.

Usage:
    python -m scripts.import_grocery_history receipt1.pdf receipt2.pdf ...
    python -m scripts.import_grocery_history data/receipts/    (all PDFs in dir)
    python -m scripts.import_grocery_history --clear data/receipts/  (wipe DB first)

Input formats:
    CSV:  Expected columns: Item Name (or Product), Category (optional)
    Text: One item per line
    PDF:  Receipts from Amazon/Whole Foods, Costco, Raley's — uses Claude to extract
"""

import base64
import csv
import glob
import json
import os
import sys
from collections import Counter

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic
from notion_client import Client

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_GROCERY_HISTORY_DB = os.environ.get("NOTION_GROCERY_HISTORY_DB", "")

# Category detection heuristics (keyword → category)
CATEGORY_KEYWORDS = {
    "Produce": ["apple", "banana", "lettuce", "tomato", "onion", "potato", "carrot",
                 "broccoli", "spinach", "avocado", "pepper", "celery", "garlic",
                 "berry", "grape", "lemon", "lime", "orange", "cucumber", "corn",
                 "mushroom", "kale", "cilantro", "basil", "ginger", "fruit", "veggie",
                 "scallion", "green onion", "zucchini", "squash", "pear", "mango",
                 "blueberr", "strawberr", "raspberr", "cranberr"],
    "Meat": ["chicken", "beef", "pork", "turkey", "salmon", "shrimp", "bacon",
             "sausage", "steak", "ground", "tilapia", "cod", "lamb", "ham", "meat",
             "tenderloin", "bulgogi", "prime tender"],
    "Dairy": ["milk", "cheese", "yogurt", "butter", "cream", "egg", "sour cream",
              "cottage", "mozzarella", "cheddar", "parmesan", "fage", "greek yogurt"],
    "Pantry": ["rice", "pasta", "bread", "cereal", "flour", "sugar", "oil", "sauce",
               "soup", "bean", "tortilla", "cracker", "chip", "nut", "peanut",
               "oat", "honey", "syrup", "vinegar", "spice", "salt", "pesto",
               "toast crunch", "lucky charms", "raisin bran", "froot loop",
               "cookie crisp", "frosted wheat", "mini wheat"],
    "Frozen": ["frozen", "ice cream", "pizza", "waffle", "fries"],
    "Bakery": ["bagel", "muffin", "croissant", "cake", "donut", "roll", "baguette",
               "dave's", "killer bread"],
    "Beverages": ["water", "juice", "soda", "coffee", "tea", "coke", "sprite",
                  "sparkling", "drink", "beer", "wine", "kombucha", "poppi",
                  "snapple", "dr pepper", "zero sugar"],
    "Snacks": ["cookie", "cracker", "chip", "popcorn", "pretzel", "bar", "granola",
               "simple mills"],
    "Supplements": ["protein powder", "vitamin", "supplement", "orgain", "collagen"],
}


def parse_pdfs(filepaths: list[str]) -> list[dict]:
    """Extract grocery items with order dates from PDF receipts using Claude.

    Handles Amazon/Whole Foods, Costco, and Raley's receipt formats.
    Claude decodes store-specific abbreviations into readable product names.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY required for PDF parsing")
        sys.exit(1)

    client = Anthropic(api_key=api_key)
    all_items = []

    for filepath in filepaths:
        print(f"  Extracting items from {os.path.basename(filepath)}...")
        with open(filepath, "rb") as f:
            pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract grocery/food items from this receipt. It may be from "
                            "Amazon/Whole Foods, Costco, or Raley's.\n\n"
                            "Return ONLY a JSON object with this structure:\n"
                            '{"store": "Store Name", "order_date": "YYYY-MM-DD", '
                            '"items": [{"name": "Product Name", "qty": 1, "price": 4.99}, ...]}\n\n'
                            "IMPORTANT RULES:\n"
                            "- Decode ALL abbreviations into full readable product names:\n"
                            '  - Costco: "CINNTOASTCRN" → "Cinnamon Toast Crunch", '
                            '"KS COOKD BCN" → "Kirkland Cooked Bacon", '
                            '"ORG WHL MILK" → "Organic Whole Milk", '
                            '"FAGE GRK 48Z" → "Fage Greek Yogurt 48oz"\n'
                            '  - Raley\'s: "Gm Cinn Toast Crunch Xl" → "General Mills Cinnamon Toast Crunch XL", '
                            '"Kell Frstd Mini Wht B/S" → "Kellogg\'s Frosted Mini Wheats Bite Size"\n'
                            "- For Amazon/Whole Foods, use the product name as shown\n"
                            "- Include quantity and per-unit price. Default qty to 1.\n"
                            "- For Costco, the price shown is total price; if qty>1, compute per-unit price\n"
                            "- Exclude non-food items (cleaning, paper goods, etc.), fees, tips, taxes, "
                            "delivery charges, and coupon/discount lines\n"
                            "- For the date, use the order/purchase/delivery date on the receipt\n"
                            "- For store, use: 'Whole Foods', 'Costco', or 'Raley\\'s'"
                        ),
                    },
                ],
            }],
        )

        text = response.content[0].text.strip()
        try:
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)

            store = data.get("store", "Unknown")
            order_date = data.get("order_date", "")
            items = data.get("items", [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, str):
                        all_items.append({
                            "name": item.strip(),
                            "category": guess_category(item.strip()),
                            "store": store,
                            "order_date": order_date,
                            "qty": 1,
                            "price": None,
                        })
                    elif isinstance(item, dict) and item.get("name"):
                        name = item["name"].strip()
                        all_items.append({
                            "name": name,
                            "category": guess_category(name),
                            "store": store,
                            "order_date": order_date,
                            "qty": item.get("qty", 1),
                            "price": item.get("price"),
                        })
                date_str = f" ({order_date})" if order_date else ""
                print(f"    [{store}] {len(items)} items{date_str}")
            else:
                print(f"    Warning: unexpected response format from {filepath}")
        except json.JSONDecodeError:
            print(f"    Warning: could not parse response from {filepath}")
            print(f"    Raw: {text[:200]}")

    return all_items


def normalize_items(items: list[dict]) -> list[dict]:
    """Use Claude to normalize item names across stores.

    Groups items that are the same product under a canonical name, e.g.:
    - "Organic Whole Milk" (Costco) + "Horizon Organic DHA Omega-3 Milk" (WF)
      → kept separate (different products)
    - "Cinnamon Toast Crunch" (Costco) + "General Mills Cinnamon Toast Crunch XL" (Raley's)
      → merged as "Cinnamon Toast Crunch"
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return items  # Skip normalization if no API key

    # Collect unique names with their stores
    unique_names: dict[str, set[str]] = {}
    for item in items:
        unique_names.setdefault(item["name"], set()).add(item.get("store", "Unknown"))

    if len(unique_names) < 2:
        return items

    print(f"\nNormalizing {len(unique_names)} unique item names across stores...")

    client = Anthropic(api_key=api_key)

    # Build the list for Claude — include store info to help matching
    name_list = []
    for name, stores in sorted(unique_names.items()):
        store_str = "/".join(sorted(stores))
        name_list.append(f"  {name} [{store_str}]")

    # Process in batches of ~150 to stay within context limits
    batch_size = 150
    name_entries = list(unique_names.keys())
    mapping: dict[str, str] = {}

    for batch_start in range(0, len(name_entries), batch_size):
        batch = name_entries[batch_start:batch_start + batch_size]
        batch_lines = []
        for name in batch:
            stores = "/".join(sorted(unique_names[name]))
            batch_lines.append(f"  {name} [{stores}]")

        batch_num = batch_start // batch_size + 1
        total_batches = (len(name_entries) + batch_size - 1) // batch_size
        if total_batches > 1:
            print(f"  Batch {batch_num}/{total_batches} ({len(batch)} items)...")

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8192,
            messages=[{
                "role": "user",
                "content": (
                    "You are normalizing a grocery list across multiple stores (Whole Foods, "
                    "Costco, Raley's). Items that are the SAME product should get the SAME "
                    "canonical name.\n\n"
                    "RULES:\n"
                    "- Merge items that are clearly the same product regardless of store/brand/size:\n"
                    '  e.g., "Cinnamon Toast Crunch" + "General Mills Cinnamon Toast Crunch XL" → "Cinnamon Toast Crunch"\n'
                    '  e.g., "Organic Baby Spinach" (WF) + "Organic Spinach" (Costco) → "Organic Spinach"\n'
                    '  e.g., "Organic Banana, 1 Each" + "Bananas Organic" → "Organic Bananas"\n'
                    "- Keep items SEPARATE if they're genuinely different products:\n"
                    '  e.g., "Horizon Organic DHA Omega-3 Milk" vs "Kirkland Organic Whole Milk" → different\n'
                    '  e.g., "Fage Greek Yogurt" vs "Straus Family Creamery Greek Yogurt" → different\n'
                    "- Use short, clean canonical names (drop size/oz, store brand prefixes like '365 by WFM')\n"
                    "- Keep brand names when they distinguish the product (e.g., 'Dave\\'s Killer Bread')\n\n"
                    "Return ONLY a JSON object mapping original name → canonical name.\n"
                    "Items with no match just map to a cleaned-up version of themselves.\n\n"
                    "Items:\n" + "\n".join(batch_lines)
                ),
            }],
        )

        text = response.content[0].text.strip()
        try:
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            batch_mapping = json.loads(text)
            if isinstance(batch_mapping, dict):
                mapping.update(batch_mapping)
        except json.JSONDecodeError:
            print(f"    Warning: normalization parse error, using original names for batch")
            for name in batch:
                mapping[name] = name

    # Count merges
    canonical_set = set(mapping.values())
    merged = len(mapping) - len(canonical_set)
    if merged > 0:
        print(f"  Merged {merged} duplicate items across stores → {len(canonical_set)} unique")

    # Apply mapping
    for item in items:
        original = item["name"]
        canonical = mapping.get(original, original)
        if canonical != original:
            item["original_name"] = original
        item["name"] = canonical
        # Re-categorize based on canonical name
        item["category"] = guess_category(canonical)

    return items


def guess_category(item_name: str) -> str:
    """Guess a category for an item based on keyword matching."""
    name_lower = item_name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return category
    return "Other"


def parse_csv(filepath: str) -> list[dict]:
    """Parse a CSV file and return list of {name, category} dicts."""
    items = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        # Try to detect if it's actually a CSV or plain text
        first_line = f.readline()
        f.seek(0)

        if "," in first_line or "\t" in first_line:
            reader = csv.DictReader(f)
            # Find the right column names
            name_col = None
            cat_col = None
            for col in reader.fieldnames or []:
                col_lower = col.strip().lower()
                if col_lower in ("item name", "product", "name", "item", "product name"):
                    name_col = col
                elif col_lower in ("category", "department", "aisle"):
                    cat_col = col

            if not name_col:
                # Fall back to first column
                name_col = (reader.fieldnames or [""])[0]

            for row in reader:
                name = row.get(name_col, "").strip()
                if not name:
                    continue
                category = row.get(cat_col, "").strip() if cat_col else ""
                if not category:
                    category = guess_category(name)
                items.append({"name": name, "category": category})
        else:
            # Plain text, one item per line
            for line in f:
                name = line.strip().lstrip("•-* ")
                if name:
                    items.append({"name": name, "category": guess_category(name)})
    return items


def deduplicate(items: list[dict]) -> list[dict]:
    """Count frequency for each item, track order dates and stores, and deduplicate.

    Classifies items into three tiers based on purchase consistency:
      - Staple:     4+ distinct orders spanning 60+ days (always keep in stock)
      - Regular:    2-3 distinct orders (periodic purchases)
      - Occasional: 1 order (recipe/event one-off, or just trying something)
    """
    from datetime import datetime

    name_counter: Counter = Counter()
    name_to_category: dict[str, str] = {}
    name_to_dates: dict[str, list[str]] = {}
    name_to_prices: dict[str, list[float]] = {}
    name_to_stores: dict[str, set[str]] = {}

    for item in items:
        normalized = item["name"].strip()
        name_counter[normalized] += 1
        if normalized not in name_to_category:
            name_to_category[normalized] = item["category"]

        order_date = item.get("order_date", "")
        if order_date:
            name_to_dates.setdefault(normalized, []).append(order_date)

        price = item.get("price")
        if price is not None:
            name_to_prices.setdefault(normalized, []).append(float(price))

        store = item.get("store", "")
        if store:
            name_to_stores.setdefault(normalized, set()).add(store)

    results = []
    for name, freq in name_counter.most_common():
        dates = sorted(set(name_to_dates.get(name, [])))
        prices = name_to_prices.get(name, [])
        stores = sorted(name_to_stores.get(name, set()))
        distinct_orders = len(dates)

        # Calculate average days between orders and date span
        avg_days = None
        span_days = 0
        if len(dates) >= 2:
            parsed = []
            for d in dates:
                try:
                    parsed.append(datetime.strptime(d, "%Y-%m-%d"))
                except ValueError:
                    pass
            if len(parsed) >= 2:
                span_days = (parsed[-1] - parsed[0]).days
                intervals = [(parsed[i+1] - parsed[i]).days for i in range(len(parsed)-1)]
                avg_days = round(sum(intervals) / len(intervals))

        # Classify: Staple / Regular / Occasional
        if distinct_orders >= 4 and span_days >= 60:
            item_type = "Staple"
        elif distinct_orders >= 2:
            item_type = "Regular"
        else:
            item_type = "Occasional"

        results.append({
            "name": name,
            "category": name_to_category[name],
            "frequency": freq,
            "type": item_type,
            "staple": item_type == "Staple",
            "stores": stores,
            "order_dates": dates,
            "first_ordered": dates[0] if dates else None,
            "last_ordered": dates[-1] if dates else None,
            "avg_reorder_days": avg_days,
            "avg_price": round(sum(prices) / len(prices), 2) if prices else None,
        })
    return results


def clear_notion_db() -> int:
    """Delete all existing pages from the Grocery History database."""
    if not NOTION_TOKEN or not NOTION_GROCERY_HISTORY_DB:
        return 0

    client = Client(auth=NOTION_TOKEN)
    deleted = 0

    # Paginate through all pages
    has_more = True
    start_cursor = None
    while has_more:
        kwargs = {"database_id": NOTION_GROCERY_HISTORY_DB, "page_size": 100}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor
        response = client.databases.query(**kwargs)

        for page in response["results"]:
            client.pages.update(page_id=page["id"], archived=True)
            deleted += 1
            if deleted % 50 == 0:
                print(f"  ... {deleted} items cleared")

        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")

    return deleted


def upload_to_notion(items: list[dict]) -> int:
    """Upload deduplicated items to Notion Grocery History database."""
    if not NOTION_TOKEN or not NOTION_GROCERY_HISTORY_DB:
        print("Error: NOTION_TOKEN and NOTION_GROCERY_HISTORY_DB must be set in .env")
        return 0

    client = Client(auth=NOTION_TOKEN)
    created = 0

    for item in items:
        try:
            properties = {
                "Item Name": {"title": [{"text": {"content": item["name"]}}]},
                "Category": {"select": {"name": item["category"]}},
                "Type": {"select": {"name": item.get("type", "Occasional")}},
                "Frequency": {"number": item["frequency"]},
                "Staple": {"checkbox": item["staple"]},
            }
            if item.get("last_ordered"):
                properties["Last Ordered"] = {"date": {"start": item["last_ordered"]}}
            if item.get("avg_reorder_days") is not None:
                properties["Avg Reorder Days"] = {"number": item["avg_reorder_days"]}
            if item.get("avg_price") is not None:
                properties["Avg Price"] = {"number": item["avg_price"]}
            if item.get("stores"):
                properties["Store"] = {
                    "multi_select": [{"name": s} for s in item["stores"]]
                }

            client.pages.create(
                parent={"database_id": NOTION_GROCERY_HISTORY_DB},
                properties=properties,
            )
            created += 1
            if created % 10 == 0:
                print(f"  ... {created} items uploaded")
        except Exception as e:
            print(f"  Warning: Failed to upload '{item['name']}': {e}")

    return created


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_grocery_history [--clear] <file_or_dir> [file2 ...]")
        print("\nOptions:")
        print("  --clear    Delete all existing items from Notion DB before importing")
        print("\nAccepts:")
        print("  CSV file (with 'Item Name' or 'Product' column)")
        print("  Text file (one item per line)")
        print("  PDF files (receipts from Whole Foods, Costco, Raley's)")
        print("  Directory path (processes all PDFs in it)")
        sys.exit(1)

    # Parse flags
    args = sys.argv[1:]
    do_clear = "--clear" in args
    args = [a for a in args if not a.startswith("--")]

    # Collect all input files
    input_files = []
    for arg in args:
        if os.path.isdir(arg):
            pdfs = sorted(glob.glob(os.path.join(arg, "*.pdf")))
            print(f"Found {len(pdfs)} PDFs in {arg}/")
            input_files.extend(pdfs)
        elif os.path.exists(arg):
            input_files.append(arg)
        else:
            print(f"Warning: File not found: {arg}")

    if not input_files:
        print("Error: No valid input files found")
        sys.exit(1)

    # Split into PDFs and CSV/text
    pdf_files = [f for f in input_files if f.lower().endswith(".pdf")]
    csv_files = [f for f in input_files if not f.lower().endswith(".pdf")]

    items = []
    if pdf_files:
        print(f"Processing {len(pdf_files)} PDF receipt(s) with Claude...")
        items.extend(parse_pdfs(pdf_files))
    for filepath in csv_files:
        print(f"Parsing {filepath}...")
        items.extend(parse_csv(filepath))

    print(f"\nFound {len(items)} total item entries")

    # Normalize names across stores
    if any(item.get("store") for item in items):
        items = normalize_items(items)

    deduped = deduplicate(items)

    # Type breakdown
    type_counts = Counter(i["type"] for i in deduped)
    print(f"Deduplicated to {len(deduped)} unique items:")
    print(f"  Staples:    {type_counts.get('Staple', 0)} (4+ orders, 60+ day span)")
    print(f"  Regular:    {type_counts.get('Regular', 0)} (2-3 orders)")
    print(f"  Occasional: {type_counts.get('Occasional', 0)} (one-off purchases)")

    # Store summary
    all_stores = set()
    for item in deduped:
        all_stores.update(item.get("stores", []))
    if all_stores:
        print(f"Stores: {', '.join(sorted(all_stores))}")
        multi_store = sum(1 for i in deduped if len(i.get("stores", [])) > 1)
        if multi_store:
            print(f"Items found at multiple stores: {multi_store}")

    # Show staples
    staples = [i for i in deduped if i["type"] == "Staple"]
    if staples:
        print(f"\nStaples ({len(staples)} items — always keep in stock):")
        for item in staples:
            reorder = f" (every ~{item['avg_reorder_days']}d)" if item.get("avg_reorder_days") else ""
            price = f" ${item['avg_price']:.2f}" if item.get("avg_price") else ""
            stores = f" @{'+'.join(item['stores'])}" if item.get("stores") else ""
            print(f"  {item['frequency']}x {item['name']} [{item['category']}]{price}{reorder}{stores}")

    # Show top regulars
    regulars = [i for i in deduped if i["type"] == "Regular"]
    if regulars:
        print(f"\nTop Regular items ({len(regulars)} total):")
        for item in regulars[:10]:
            price = f" ${item['avg_price']:.2f}" if item.get("avg_price") else ""
            stores = f" @{'+'.join(item['stores'])}" if item.get("stores") else ""
            print(f"  {item['frequency']}x {item['name']} [{item['category']}]{price}{stores}")

    if do_clear:
        print(f"\nClearing existing Notion Grocery History database...")
        cleared = clear_notion_db()
        print(f"Cleared {cleared} existing items")

    print(f"\nUploading to Notion Grocery History database...")
    created = upload_to_notion(deduped)
    print(f"\nDone! Uploaded {created} items to Notion.")


if __name__ == "__main__":
    main()
