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
    """Extract grocery items from PDF receipts using Claude."""
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
                            "Extract every grocery/food item name from this Amazon/Whole Foods receipt. "
                            "Return ONLY a JSON array of strings with the product names. "
                            "Use the actual product name as shown (e.g., '365 Organic Whole Milk' not just 'milk'). "
                            "Exclude non-food items, fees, tips, taxes, and delivery charges. "
                            "Example: [\"365 Organic Whole Milk\", \"Honeycrisp Apples\", \"Dave's Killer Bread\"]"
                        ),
                    },
                ],
            }],
        )

        text = response.content[0].text.strip()
        # Extract JSON array from response
        try:
            # Handle case where Claude wraps in markdown code block
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            items = json.loads(text)
            if isinstance(items, list):
                for name in items:
                    if isinstance(name, str) and name.strip():
                        all_items.append({"name": name.strip(), "category": guess_category(name.strip())})
                print(f"    Found {len(items)} items")
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
        print(f"  {item['frequency']}x {item['name']} [{item['category']}]{star}")

    print(f"\nUploading to Notion Grocery History database...")
    created = upload_to_notion(deduped)
    print(f"\nDone! Uploaded {created} items to Notion.")


if __name__ == "__main__":
    main()
