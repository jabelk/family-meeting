"""Recipe management — photo extraction via Claude vision, R2 storage, search."""

import json
import logging
from io import BytesIO

import boto3
from anthropic import Anthropic

from src.config import (
    ANTHROPIC_API_KEY,
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    NOTION_RECIPES_DB,
    NOTION_GROCERY_HISTORY_DB,
)

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ---------------------------------------------------------------------------
# R2 Storage (T011)
# ---------------------------------------------------------------------------

_r2_client = None


def _get_r2_client():
    """Lazy-init the R2 (S3-compatible) client."""
    global _r2_client
    if _r2_client is None:
        if not R2_ACCOUNT_ID or not R2_ACCESS_KEY_ID:
            raise RuntimeError("R2 credentials not configured — set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY in .env")
        _r2_client = boto3.client(
            "s3",
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
    return _r2_client


def upload_photo(image_bytes: bytes, recipe_id: str, mime_type: str) -> str:
    """Upload a recipe photo to Cloudflare R2 and return the public URL.

    Args:
        image_bytes: Raw image data.
        recipe_id: Notion page ID used as the file key.
        mime_type: e.g. 'image/jpeg', 'image/png'.

    Returns:
        Public URL of the uploaded photo.
    """
    ext = "jpg" if "jpeg" in mime_type else mime_type.split("/")[-1]
    key = f"recipes/{recipe_id}.{ext}"

    s3 = _get_r2_client()
    s3.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=key,
        Body=image_bytes,
        ContentType=mime_type,
    )
    url = f"https://{R2_BUCKET_NAME}.{R2_ACCOUNT_ID}.r2.dev/{key}"
    logger.info("Uploaded recipe photo to R2: %s", key)
    return url


# ---------------------------------------------------------------------------
# Recipe Extraction via Claude Vision (T016)
# ---------------------------------------------------------------------------

def extract_and_save_recipe(image_base64: str, mime_type: str, cookbook_name: str = "") -> dict:
    """Extract a recipe from a cookbook photo using Claude vision and save to Notion.

    Args:
        image_base64: Base64-encoded image data.
        mime_type: Image MIME type.
        cookbook_name: Source cookbook name. Defaults to 'Uncategorized'.

    Returns:
        Dict with recipe details and save status.
    """
    from src.tools.notion import (
        create_recipe, get_cookbook_by_name, create_cookbook,
        search_recipes_by_title,
    )
    import base64

    cookbook_name = cookbook_name.strip() or "Uncategorized"

    # Step 1: Extract recipe with Claude vision
    extraction_prompt = (
        "Extract the recipe from this cookbook page. Return ONLY valid JSON with these fields:\n"
        '{"name": "Recipe Name", "ingredients": [{"name": "item", "quantity": "2", "unit": "cups"}], '
        '"instructions": ["Step 1...", "Step 2..."], "prep_time": 15, "cook_time": 30, '
        '"servings": 4, "tags": ["tag1"], "cuisine": "American"}\n\n'
        "Rules:\n"
        "- If text is unclear or cut off, include it with [unclear] marker\n"
        "- If two recipes are visible, extract both as a JSON array\n"
        "- If the image is NOT a recipe, return: {\"error\": \"not_a_recipe\"}\n"
        "- For ingredients, always include name; quantity and unit can be empty strings if not specified\n"
        "- Tags should be from: Keto, Kid-Friendly, Quick (<30min), Vegetarian, Comfort Food, Soup, Salad, Pasta, Meat, Seafood\n"
        "- Cuisine should be: American, Mexican, Italian, Asian, Mediterranean, or Other"
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime_type, "data": image_base64},
                },
                {"type": "text", "text": extraction_prompt},
            ],
        }],
    )

    raw_text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

    try:
        extracted = json.loads(raw_text)
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse recipe extraction", "raw": raw_text[:500]}

    # Handle "not a recipe" response
    if isinstance(extracted, dict) and extracted.get("error") == "not_a_recipe":
        return {"success": False, "error": "not_a_recipe", "message": "That doesn't look like a recipe — did you mean to save a recipe?"}

    # Handle multiple recipes on one page
    recipes_to_save = extracted if isinstance(extracted, list) else [extracted]

    saved_recipes = []
    for recipe_data in recipes_to_save:
        name = recipe_data.get("name", "Untitled Recipe")

        # Step 2: Check for duplicates
        existing = search_recipes_by_title(name)
        for ex in existing:
            if ex.get("cookbook", "").lower() == cookbook_name.lower():
                return {
                    "success": False,
                    "duplicate": True,
                    "existing_id": ex["id"],
                    "name": name,
                    "cookbook": cookbook_name,
                    "message": f"A recipe called '{name}' already exists in '{cookbook_name}'. Would you like to update the existing recipe or save as a new version?",
                }

        # Step 3: Find or create cookbook
        cookbook = get_cookbook_by_name(cookbook_name)
        if not cookbook:
            cookbook_id = create_cookbook(cookbook_name)
        else:
            cookbook_id = cookbook["id"]

        # Step 4: Create recipe in Notion (without photo first to get the page ID)
        ingredients_json = json.dumps(recipe_data.get("ingredients", []))
        instructions = "\n".join(recipe_data.get("instructions", []))

        page_id = create_recipe(
            name=name,
            cookbook_id=cookbook_id,
            ingredients_json=ingredients_json,
            instructions=instructions,
            prep_time=recipe_data.get("prep_time"),
            cook_time=recipe_data.get("cook_time"),
            servings=recipe_data.get("servings"),
            photo_url="",  # Updated after upload
            tags=recipe_data.get("tags", []),
            cuisine=recipe_data.get("cuisine", "Other"),
        )

        # Step 5: Upload photo to R2 and update Notion with URL
        try:
            image_bytes = base64.b64decode(image_base64)
            photo_url = upload_photo(image_bytes, page_id, mime_type)
            from src.tools.notion import update_recipe
            update_recipe(page_id, {"Photo URL": {"url": photo_url}})
        except Exception as e:
            logger.warning("Failed to upload photo to R2: %s", e)
            photo_url = ""

        # Identify unclear portions
        unclear = []
        for step in recipe_data.get("instructions", []):
            if "[unclear]" in step:
                unclear.append(step)
        for ing in recipe_data.get("ingredients", []):
            if "[unclear]" in ing.get("name", ""):
                unclear.append(f"Ingredient: {ing['name']}")

        saved_recipes.append({
            "name": name,
            "cookbook": cookbook_name,
            "ingredients_count": len(recipe_data.get("ingredients", [])),
            "prep_time": recipe_data.get("prep_time"),
            "cook_time": recipe_data.get("cook_time"),
            "servings": recipe_data.get("servings"),
            "unclear_portions": unclear,
            "notion_page_id": page_id,
            "photo_url": photo_url,
        })

    if len(saved_recipes) == 1:
        return {"success": True, "recipe": saved_recipes[0]}
    return {"success": True, "recipes": saved_recipes, "count": len(saved_recipes)}


# ---------------------------------------------------------------------------
# Recipe Search (T017)
# ---------------------------------------------------------------------------

def search_recipes(query: str, cookbook_name: str = "", tags: list[str] | None = None) -> dict:
    """Search the recipe catalogue by name, ingredient, cookbook, or description.

    Uses Notion DB query with filters built from the search terms.
    """
    from src.tools.notion import search_recipes_by_title, get_cookbook_by_name, NOTION_RECIPES_DB
    from src.tools.notion import notion as notion_client

    if not NOTION_RECIPES_DB:
        return {"results": [], "total": 0, "error": "Recipes database not configured"}

    filters = []

    # Title search
    if query:
        filters.append({"property": "Name", "title": {"contains": query}})

    # Cookbook filter
    if cookbook_name:
        cookbook = get_cookbook_by_name(cookbook_name)
        if cookbook:
            filters.append({"property": "Cookbook", "relation": {"contains": cookbook["id"]}})

    # Tags filter
    if tags:
        for tag in tags:
            filters.append({"property": "Tags", "multi_select": {"contains": tag}})

    query_filter = {"and": filters} if len(filters) > 1 else (filters[0] if filters else None)
    kwargs = {"database_id": NOTION_RECIPES_DB}
    if query_filter:
        kwargs["filter"] = query_filter

    results = notion_client.databases.query(**kwargs)
    recipes = []
    for page in results["results"]:
        props = page["properties"]
        from src.tools.notion import _get_title, _get_select
        cookbook_rel = props.get("Cookbook", {}).get("relation", [])
        recipes.append({
            "name": _get_title(props.get("Name", {})),
            "cookbook": cookbook_rel[0]["id"] if cookbook_rel else "",
            "tags": [opt["name"] for opt in props.get("Tags", {}).get("multi_select", [])],
            "prep_time": props.get("Prep Time", {}).get("number"),
            "cook_time": props.get("Cook Time", {}).get("number"),
            "servings": props.get("Servings", {}).get("number"),
            "times_used": props.get("Times Used", {}).get("number", 0),
            "notion_page_id": page["id"],
        })

    return {"results": recipes[:10], "total": len(recipes)}


# ---------------------------------------------------------------------------
# Recipe Details (T018)
# ---------------------------------------------------------------------------

def get_recipe_details(recipe_id: str) -> dict:
    """Get full recipe details including ingredients and instructions."""
    from src.tools.notion import notion as notion_client, _get_title, _get_select

    page = notion_client.pages.retrieve(page_id=recipe_id)
    props = page["properties"]

    # Parse ingredients JSON from rich text
    ingredients_rt = props.get("Ingredients", {}).get("rich_text", [])
    ingredients_text = "".join(rt.get("plain_text", "") for rt in ingredients_rt)
    try:
        ingredients = json.loads(ingredients_text) if ingredients_text else []
    except json.JSONDecodeError:
        ingredients = [{"name": ingredients_text, "quantity": "", "unit": ""}]

    # Parse instructions from rich text
    instructions_rt = props.get("Instructions", {}).get("rich_text", [])
    instructions_text = "".join(rt.get("plain_text", "") for rt in instructions_rt)
    instructions = instructions_text.split("\n") if instructions_text else []

    cookbook_rel = props.get("Cookbook", {}).get("relation", [])

    return {
        "name": _get_title(props.get("Name", {})),
        "cookbook_id": cookbook_rel[0]["id"] if cookbook_rel else "",
        "ingredients": ingredients,
        "instructions": instructions,
        "prep_time": props.get("Prep Time", {}).get("number"),
        "cook_time": props.get("Cook Time", {}).get("number"),
        "servings": props.get("Servings", {}).get("number"),
        "photo_url": props.get("Photo URL", {}).get("url", ""),
        "tags": [opt["name"] for opt in props.get("Tags", {}).get("multi_select", [])],
        "cuisine": _get_select(props.get("Cuisine", {})),
        "times_used": props.get("Times Used", {}).get("number", 0),
    }


# ---------------------------------------------------------------------------
# List Cookbooks (T019)
# ---------------------------------------------------------------------------

def list_cookbooks() -> dict:
    """List all cookbooks with recipe counts."""
    from src.tools.notion import list_cookbooks as notion_list_cookbooks
    return notion_list_cookbooks()


# ---------------------------------------------------------------------------
# Recipe → Grocery List (T020)
# ---------------------------------------------------------------------------

def recipe_to_grocery_list(recipe_id: str, servings_multiplier: float = 1.0) -> dict:
    """Generate a grocery list from a recipe, deducting recently ordered items.

    Cross-references ingredients against Grocery History to categorize as:
    - needed: not recently ordered
    - already_have: ordered within 50% of avg reorder interval
    - unknown: not found in grocery history (added as-is)
    """
    from src.tools.notion import notion as notion_client, _get_title

    details = get_recipe_details(recipe_id)
    ingredients = details.get("ingredients", [])

    needed = []
    already_have = []
    unknown = []

    # Build grocery history lookup if available
    history_map = {}
    if NOTION_GROCERY_HISTORY_DB:
        try:
            all_items = notion_client.databases.query(
                database_id=NOTION_GROCERY_HISTORY_DB,
                page_size=100,
            )
            for page in all_items["results"]:
                props = page["properties"]
                item_name = _get_title(props.get("Item Name", {})).lower()
                last_ordered_prop = props.get("Last Ordered", {}).get("date")
                avg_reorder = props.get("Avg Reorder Days", {}).get("number")
                store_options = props.get("Store", {}).get("multi_select", [])
                store = store_options[0]["name"] if store_options else "Whole Foods"
                history_map[item_name] = {
                    "last_ordered": last_ordered_prop.get("start") if last_ordered_prop else None,
                    "avg_reorder_days": avg_reorder,
                    "store": store,
                }
        except Exception as e:
            logger.warning("Failed to load grocery history: %s", e)

    from datetime import date
    today = date.today()

    for ing in ingredients:
        name = ing.get("name", "")
        quantity = ing.get("quantity", "")
        unit = ing.get("unit", "")

        # Scale quantity
        if servings_multiplier != 1.0 and quantity:
            try:
                scaled = float(quantity) * servings_multiplier
                quantity = str(int(scaled)) if scaled == int(scaled) else f"{scaled:.1f}"
            except ValueError:
                pass

        qty_str = f"{quantity} {unit}".strip() if quantity or unit else ""

        # Check against history
        name_lower = name.lower()
        history = history_map.get(name_lower)

        if history:
            last_ordered = history["last_ordered"]
            avg_reorder = history["avg_reorder_days"]
            store = history["store"]

            if last_ordered and avg_reorder:
                days_since = (today - date.fromisoformat(last_ordered)).days
                if days_since < avg_reorder * 0.5:
                    already_have.append({
                        "name": name,
                        "reason": f"ordered {days_since} days ago (avg reorder: {avg_reorder} days)",
                    })
                    continue

            needed.append({"name": name, "quantity": qty_str, "store": store})
        else:
            unknown.append({"name": name, "quantity": qty_str, "note": "not in grocery history — will add as-is"})

    return {
        "recipe": details["name"],
        "needed_items": needed,
        "already_have": already_have,
        "unknown_items": unknown,
    }
