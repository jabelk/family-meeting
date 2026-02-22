"""Import Whole Foods order history into the Notion Grocery History database.

Parses CSV or text exports from Amazon/Whole Foods orders, deduplicates items,
counts purchase frequency, and marks items ordered 50%+ of the time as staples.

Usage:
    python -m scripts.import_grocery_history orders.csv

Input format (CSV):
    Expected columns: Item Name (or Product), Category (optional), Quantity (optional)
    The script auto-detects common column names.

    Alternatively, a plain text file with one item per line (item name only).
"""

import csv
import os
import sys
from collections import Counter

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

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
    """Count frequency for each item and deduplicate."""
    name_counter: Counter = Counter()
    name_to_category: dict[str, str] = {}

    for item in items:
        normalized = item["name"].strip()
        name_counter[normalized] += 1
        if normalized not in name_to_category:
            name_to_category[normalized] = item["category"]

    total_orders = max(name_counter.values()) if name_counter else 1
    # Staple threshold: items appearing in 50%+ of orders (rough heuristic)
    staple_threshold = max(total_orders * 0.5, 2)

    results = []
    for name, freq in name_counter.most_common():
        results.append({
            "name": name,
            "category": name_to_category[name],
            "frequency": freq,
            "staple": freq >= staple_threshold,
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
            client.pages.create(
                parent={"database_id": NOTION_GROCERY_HISTORY_DB},
                properties={
                    "Item Name": {"title": [{"text": {"content": item["name"]}}]},
                    "Category": {"select": {"name": item["category"]}},
                    "Frequency": {"number": item["frequency"]},
                    "Staple": {"checkbox": item["staple"]},
                },
            )
            created += 1
            if created % 10 == 0:
                print(f"  ... {created} items uploaded")
        except Exception as e:
            print(f"  Warning: Failed to upload '{item['name']}': {e}")

    return created


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_grocery_history <orders.csv>")
        print("\nAccepts CSV (with 'Item Name' or 'Product' column) or plain text (one item per line).")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    print(f"Parsing {filepath}...")
    items = parse_csv(filepath)
    print(f"Found {len(items)} total item entries")

    deduped = deduplicate(items)
    staple_count = sum(1 for i in deduped if i["staple"])
    print(f"Deduplicated to {len(deduped)} unique items ({staple_count} staples)")

    print("\nTop 10 items by frequency:")
    for item in deduped[:10]:
        star = " ⭐" if item["staple"] else ""
        print(f"  {item['frequency']}x {item['name']} [{item['category']}]{star}")

    print(f"\nUploading to Notion Grocery History database...")
    created = upload_to_notion(deduped)
    print(f"\nDone! Uploaded {created} items to Notion.")


if __name__ == "__main__":
    main()
