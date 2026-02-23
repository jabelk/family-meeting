"""Import Whole Foods order history into the Notion Grocery History database.

Parses CSV, text, or PDF exports from Amazon/Whole Foods orders, deduplicates
items, counts purchase frequency, and marks items ordered 50%+ of the time as
staples.

Usage:
    python -m scripts.import_grocery_history orders.csv
    python -m scripts.import_grocery_history receipt1.pdf receipt2.pdf ...
    python -m scripts.import_grocery_history data/receipts/    (all PDFs in dir)

Input formats:
    CSV:  Expected columns: Item Name (or Product), Category (optional)
    Text: One item per line
    PDF:  Amazon/Whole Foods order receipts — uses Claude to extract item names
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
                 "mushroom", "kale", "cilantro", "basil", "ginger", "fruit", "veggie"],
    "Meat": ["chicken", "beef", "pork", "turkey", "salmon", "shrimp", "bacon",
             "sausage", "steak", "ground", "tilapia", "cod", "lamb", "ham", "meat"],
    "Dairy": ["milk", "cheese", "yogurt", "butter", "cream", "egg", "sour cream",
              "cottage", "mozzarella", "cheddar", "parmesan"],
    "Pantry": ["rice", "pasta", "bread", "cereal", "flour", "sugar", "oil", "sauce",
               "soup", "bean", "tortilla", "cracker", "chip", "nut", "peanut",
               "oat", "honey", "syrup", "vinegar", "spice", "salt", "pepper"],
    "Frozen": ["frozen", "ice cream", "pizza", "waffle", "fries"],
    "Bakery": ["bagel", "muffin", "croissant", "cake", "donut", "roll", "baguette"],
    "Beverages": ["water", "juice", "soda", "coffee", "tea", "coke", "sprite",
                  "sparkling", "drink", "beer", "wine", "kombucha"],
}


def parse_pdfs(filepaths: list[str]) -> list[dict]:
    """Extract grocery items with order dates from PDF receipts using Claude."""
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
                            "Extract the order date and every grocery/food item from this Amazon/Whole Foods receipt. "
                            "Return ONLY a JSON object with this structure:\n"
                            '{"order_date": "YYYY-MM-DD", "items": [{"name": "Product Name", "qty": 1, "price": 4.99}, ...]}\n'
                            "Use the actual product name as shown (e.g., '365 Organic Whole Milk' not just 'milk'). "
                            "Include quantity and price per item if shown. Default qty to 1 if not listed. "
                            "Exclude non-food items, fees, tips, taxes, and delivery charges. "
                            "For the date, use the order/delivery date shown on the receipt."
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

            order_date = data.get("order_date", "")
            items = data.get("items", [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, str):
                        # Backwards compat: plain string list
                        all_items.append({
                            "name": item.strip(),
                            "category": guess_category(item.strip()),
                            "order_date": order_date,
                            "qty": 1,
                            "price": None,
                        })
                    elif isinstance(item, dict) and item.get("name"):
                        name = item["name"].strip()
                        all_items.append({
                            "name": name,
                            "category": guess_category(name),
                            "order_date": order_date,
                            "qty": item.get("qty", 1),
                            "price": item.get("price"),
                        })
                date_str = f" (ordered {order_date})" if order_date else ""
                print(f"    Found {len(items)} items{date_str}")
            else:
                print(f"    Warning: unexpected response format from {filepath}")
        except json.JSONDecodeError:
            print(f"    Warning: could not parse response from {filepath}")
            print(f"    Raw: {text[:200]}")

    return all_items


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


def deduplicate(items: list[dict], total_orders: int = 0) -> list[dict]:
    """Count frequency for each item, track order dates, and deduplicate."""
    from datetime import datetime

    name_counter: Counter = Counter()
    name_to_category: dict[str, str] = {}
    name_to_dates: dict[str, list[str]] = {}
    name_to_prices: dict[str, list[float]] = {}

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

    if not total_orders:
        total_orders = len(set(d for dates in name_to_dates.values() for d in dates)) or 1
    staple_threshold = max(total_orders * 0.5, 2)

    results = []
    for name, freq in name_counter.most_common():
        dates = sorted(set(name_to_dates.get(name, [])))
        prices = name_to_prices.get(name, [])

        # Calculate average days between orders
        avg_days = None
        if len(dates) >= 2:
            parsed = []
            for d in dates:
                try:
                    parsed.append(datetime.strptime(d, "%Y-%m-%d"))
                except ValueError:
                    pass
            if len(parsed) >= 2:
                intervals = [(parsed[i+1] - parsed[i]).days for i in range(len(parsed)-1)]
                avg_days = round(sum(intervals) / len(intervals))

        results.append({
            "name": name,
            "category": name_to_category[name],
            "frequency": freq,
            "staple": freq >= staple_threshold,
            "order_dates": dates,
            "first_ordered": dates[0] if dates else None,
            "last_ordered": dates[-1] if dates else None,
            "avg_reorder_days": avg_days,
            "avg_price": round(sum(prices) / len(prices), 2) if prices else None,
        })
    return results


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
                "Frequency": {"number": item["frequency"]},
                "Staple": {"checkbox": item["staple"]},
            }
            if item.get("last_ordered"):
                properties["Last Ordered"] = {"date": {"start": item["last_ordered"]}}
            if item.get("avg_reorder_days") is not None:
                properties["Avg Reorder Days"] = {"number": item["avg_reorder_days"]}
            if item.get("avg_price") is not None:
                properties["Avg Price"] = {"number": item["avg_price"]}

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
        print("Usage: python -m scripts.import_grocery_history <file_or_dir> [file2 ...]")
        print("\nAccepts:")
        print("  CSV file (with 'Item Name' or 'Product' column)")
        print("  Text file (one item per line)")
        print("  PDF files (Amazon/Whole Foods receipts — uses Claude to extract)")
        print("  Directory path (processes all PDFs in it)")
        sys.exit(1)

    # Collect all input files
    input_files = []
    for arg in sys.argv[1:]:
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

    print(f"Found {len(items)} total item entries")

    deduped = deduplicate(items)
    staple_count = sum(1 for i in deduped if i["staple"])
    print(f"Deduplicated to {len(deduped)} unique items ({staple_count} staples)")

    print("\nTop 10 items by frequency:")
    for item in deduped[:10]:
        star = " ⭐" if item["staple"] else ""
        reorder = f" (every ~{item['avg_reorder_days']}d)" if item.get("avg_reorder_days") else ""
        price = f" ${item['avg_price']:.2f}" if item.get("avg_price") else ""
        last = f" last:{item['last_ordered']}" if item.get("last_ordered") else ""
        print(f"  {item['frequency']}x {item['name']} [{item['category']}]{price}{reorder}{last}{star}")

    print(f"\nUploading to Notion Grocery History database...")
    created = upload_to_notion(deduped)
    print(f"\nDone! Uploaded {created} items to Notion.")


if __name__ == "__main__":
    main()
