"""Downshiftology.com recipe search, details, and import via WordPress REST API."""

import html
import json
import logging
import re

import httpx

from src.tools import notion

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOWNSHIFTOLOGY_API_BASE = "https://downshiftology.com/wp-json/wp/v2"

# WordPress WPRM taxonomy IDs (stable — researched from live API)
COURSE_IDS: dict[str, int] = {
    "dinner": 22904,
    "main-course": 2001,
    "main course": 2001,
    "breakfast": 1998,
    "appetizer": 1999,
    "side-dish": 2002,
    "side dish": 2002,
    "salad": 2003,
    "soup": 2000,
    "dessert": 2004,
    "snack": 2005,
    "drinks": 2006,
    "sauce": 15036,
    "dressing": 13345,
}

CUISINE_IDS: dict[str, int] = {
    "american": 2013,
    "mexican": 2014,
    "italian": 2008,
    "mediterranean": 2009,
    "french": 2007,
    "asian": 13246,
    "indian": 2010,
    "greek": 14244,
    "middle-eastern": 13921,
    "middle eastern": 13921,
    "japanese": 2012,
    "chinese": 2011,
}

# Dietary terms for client-side filtering
_dietary_terms: set[str] = {
    "keto", "paleo", "whole30", "gluten-free", "dairy-free",
    "vegan", "vegetarian", "nut-free", "low-carb", "high-protein",
}

# Module-level cache for follow-up commands ("save number 3", "tell me more about 2")
_last_search_results: list[dict] = []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities."""
    return re.sub(r"<[^>]+>", "", html.unescape(text)).strip()


def _fetch_recipes(params: dict) -> list[dict]:
    """Fetch WPRM recipes from the Downshiftology API.

    Filters out roundup posts (parent_post_id == "0" or empty).
    """
    url = f"{DOWNSHIFTOLOGY_API_BASE}/wprm_recipe"
    default_params = {
        "_fields": "id,title,link,recipe",
        "per_page": 20,
    }
    default_params.update(params)

    try:
        resp = httpx.get(url, params=default_params, timeout=15.0)
        resp.raise_for_status()
        recipes = resp.json()
    except httpx.HTTPError as e:
        logger.error("Downshiftology API error: %s", e)
        return []

    # Filter out roundup/collection posts
    return [
        r for r in recipes
        if r.get("recipe", {}).get("parent_post_id") not in ("0", "", None)
    ]


def _format_recipe_summary(recipe: dict) -> dict:
    """Extract key fields from a WPRM recipe API response."""
    r = recipe.get("recipe", {})
    tags = r.get("tags", {})

    course_names = [t.get("name", "") for t in tags.get("course", [])]
    cuisine_names = [t.get("name", "") for t in tags.get("cuisine", [])]
    keyword_names = [t.get("name", "") for t in tags.get("keyword", [])]

    rating = r.get("rating", {})
    try:
        avg_rating = float(rating.get("average", 0)) if isinstance(rating, dict) else 0
    except (ValueError, TypeError):
        avg_rating = 0

    total_time = r.get("total_time", "")
    try:
        total_time_int = int(total_time) if total_time else 0
    except (ValueError, TypeError):
        total_time_int = 0

    return {
        "wprm_id": recipe.get("id"),
        "name": _strip_html(r.get("name", "") or recipe.get("title", {}).get("rendered", "")),
        "total_time": total_time_int,
        "course": course_names,
        "cuisine": cuisine_names,
        "keywords": keyword_names,
        "rating": avg_rating,
        "link": recipe.get("link", ""),
    }


# ---------------------------------------------------------------------------
# US1: Recipe Search
# ---------------------------------------------------------------------------

def search_downshiftology(
    query: str = "",
    course: str = "",
    cuisine: str = "",
    dietary: str = "",
    max_time: int = 0,
) -> str:
    """Search Downshiftology for recipes by course, cuisine, ingredient, dietary, or time.

    Returns a formatted numbered list of up to 5 matching recipes.
    """
    global _last_search_results

    params: dict = {}
    if query:
        params["search"] = query
    if course:
        course_id = COURSE_IDS.get(course.lower())
        if course_id:
            params["wprm_course"] = course_id
    if cuisine:
        cuisine_id = CUISINE_IDS.get(cuisine.lower())
        if cuisine_id:
            params["wprm_cuisine"] = cuisine_id

    recipes = _fetch_recipes(params)
    if not recipes:
        _last_search_results = []
        return "No recipes found on Downshiftology. Try broadening your search (e.g., just 'chicken' or 'dinner')."

    # Format summaries
    summaries = [_format_recipe_summary(r) for r in recipes]

    # Client-side dietary filter
    if dietary:
        dietary_lower = dietary.lower().strip()
        filtered = []
        for s in summaries:
            searchable = " ".join([
                s["name"].lower(),
                " ".join(k.lower() for k in s["keywords"]),
            ])
            if dietary_lower in searchable:
                filtered.append(s)
        summaries = filtered if filtered else summaries  # fall back if no matches

    # Client-side max_time filter
    if max_time and max_time > 0:
        filtered = [s for s in summaries if 0 < s["total_time"] <= max_time]
        summaries = filtered if filtered else summaries

    # Take top 5
    summaries = summaries[:5]
    _last_search_results = summaries

    if not summaries:
        return "No recipes matched your filters. Try broadening your search."

    lines = []
    for i, s in enumerate(summaries, 1):
        time_str = f"{s['total_time']} min" if s['total_time'] else "Time N/A"
        tags = ", ".join(s["course"] + s["cuisine"])
        rating_str = f" | {s['rating']:.1f}★" if s["rating"] else ""
        lines.append(f"{i}. {s['name']} | {time_str} | {tags}{rating_str}\n   {s['link']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# US1: Recipe Details
# ---------------------------------------------------------------------------

def get_downshiftology_details(result_number: int) -> str:
    """Get full details of a recipe from the most recent search results.

    Args:
        result_number: 1-based index from the search results list.
    """
    if not _last_search_results:
        return "No recent search results. Please search for recipes first."

    if result_number < 1 or result_number > len(_last_search_results):
        return f"Invalid number. Please choose between 1 and {len(_last_search_results)}."

    cached = _last_search_results[result_number - 1]
    wprm_id = cached["wprm_id"]

    # Re-fetch full recipe data by ID
    try:
        resp = httpx.get(
            f"{DOWNSHIFTOLOGY_API_BASE}/wprm_recipe/{wprm_id}",
            params={"_fields": "id,title,link,recipe"},
            timeout=15.0,
        )
        resp.raise_for_status()
        recipe_data = resp.json()
    except httpx.HTTPError as e:
        logger.error("Failed to fetch recipe %s: %s", wprm_id, e)
        return f"Couldn't fetch recipe details. Try the link directly: {cached['link']}"

    r = recipe_data.get("recipe", {})

    # Basic info
    name = _strip_html(r.get("name", ""))
    servings = r.get("servings", "N/A")
    prep_time = r.get("prep_time", "N/A")
    cook_time = r.get("cook_time", "N/A")
    total_time = r.get("total_time", "N/A")

    # Ingredients
    ingredients_flat = r.get("ingredients_flat", [])
    ingredient_lines = []
    for ing in ingredients_flat:
        amount = ing.get("amount", "")
        unit = ing.get("unit", "")
        ing_name = ing.get("name", "")
        notes = ing.get("notes", "")
        line = f"  - {amount} {unit} {ing_name}".strip()
        if notes:
            line += f" ({_strip_html(notes)})"
        ingredient_lines.append(line)

    # Instructions
    instructions_flat = r.get("instructions_flat", [])
    instruction_lines = []
    for i, step in enumerate(instructions_flat, 1):
        text = _strip_html(step.get("text", ""))
        if text:
            instruction_lines.append(f"  {i}. {text}")

    # Nutrition
    nutrition = r.get("nutrition", {})
    nutrition_parts = []
    if nutrition:
        for key in ("calories", "protein", "carbohydrates", "fat", "fiber"):
            val = nutrition.get(key, "")
            if val:
                label = "carbs" if key == "carbohydrates" else key
                nutrition_parts.append(f"{label}: {val}")

    # Dietary / keyword tags
    tags = r.get("tags", {})
    keyword_names = [t.get("name", "") for t in tags.get("keyword", [])]
    dietary_tags = [k for k in keyword_names if k.lower() in _dietary_terms]

    link = recipe_data.get("link", cached["link"])

    # Build output
    sections = [f"*{name}*"]
    sections.append(f"Servings: {servings} | Prep: {prep_time} min | Cook: {cook_time} min | Total: {total_time} min")

    if dietary_tags:
        sections.append(f"Dietary: {', '.join(dietary_tags)}")

    if ingredient_lines:
        sections.append(f"\n*Ingredients ({len(ingredient_lines)}):*")
        sections.append("\n".join(ingredient_lines))

    if instruction_lines:
        sections.append(f"\n*Instructions ({len(instruction_lines)} steps):*")
        sections.append("\n".join(instruction_lines))

    if nutrition_parts:
        sections.append(f"\n*Nutrition (per serving):* {' | '.join(nutrition_parts)}")

    sections.append(f"\nRecipe: {link}")

    # Cross-reference grocery history (US3)
    try:
        grocery_section = _cross_reference_grocery_history(ingredients_flat)
        if grocery_section:
            sections.append(grocery_section)
    except Exception as e:
        logger.warning("Grocery cross-reference failed: %s", e)

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# US2: Recipe Import
# ---------------------------------------------------------------------------

def _map_tags(recipe_data: dict) -> tuple[list[str], str]:
    """Map Downshiftology course/cuisine tags to Notion Tags and Cuisine values.

    Returns (tags_list, cuisine_string).
    """
    tags = recipe_data.get("tags", {})
    course_names = {t.get("name", "").lower() for t in tags.get("course", [])}
    cuisine_names = {t.get("name", "").lower() for t in tags.get("cuisine", [])}

    # Map course → Notion Tags
    notion_tags: list[str] = []
    if "soup" in course_names:
        notion_tags.append("Soup")
    if "salad" in course_names:
        notion_tags.append("Salad")
    if "main course" in course_names or "dinner" in course_names:
        # Check ingredients for meat vs seafood
        ingredients_text = " ".join(
            ing.get("name", "").lower()
            for ing in recipe_data.get("ingredients_flat", [])
        )
        if any(w in ingredients_text for w in ("shrimp", "salmon", "fish", "tuna", "cod", "crab")):
            notion_tags.append("Seafood")
        else:
            notion_tags.append("Meat")
    if "dessert" in course_names or "snack" in course_names:
        notion_tags.append("Comfort Food")

    # Map cuisine → Notion Cuisine
    cuisine_map = {
        "american": "American",
        "mexican": "Mexican",
        "italian": "Italian",
        "asian": "Asian", "chinese": "Asian", "japanese": "Asian", "indonesian": "Asian",
        "mediterranean": "Mediterranean", "greek": "Mediterranean", "middle eastern": "Mediterranean",
        "middle-eastern": "Mediterranean",
    }
    notion_cuisine = "Other"
    for cn in cuisine_names:
        mapped = cuisine_map.get(cn)
        if mapped:
            notion_cuisine = mapped
            break

    return notion_tags, notion_cuisine


def import_downshiftology_recipe(
    result_number: int = 0,
    recipe_name: str = "",
) -> str:
    """Import a Downshiftology recipe into the Notion catalogue.

    Args:
        result_number: 1-based index from most recent search results.
        recipe_name: Alternative — search by name and import first match.
    """
    # Determine which recipe to import
    if result_number:
        if not _last_search_results:
            return "No recent search results. Please search for recipes first."
        if result_number < 1 or result_number > len(_last_search_results):
            return f"Invalid number. Please choose between 1 and {len(_last_search_results)}."
        cached = _last_search_results[result_number - 1]
        wprm_id = cached["wprm_id"]
        recipe_link = cached["link"]
    elif recipe_name:
        # Search by name
        results = _fetch_recipes({"search": recipe_name, "per_page": 1})
        if not results:
            return f"Couldn't find a recipe matching '{recipe_name}' on Downshiftology."
        summary = _format_recipe_summary(results[0])
        wprm_id = summary["wprm_id"]
        recipe_link = summary["link"]
    else:
        return "Please provide a result number or recipe name to import."

    # Check for duplicates by Source URL
    existing = notion.search_recipes_by_source_url(recipe_link)
    if existing:
        return f"This recipe is already saved! '{existing[0]['name']}' is already in your catalogue."

    # Fetch full recipe data
    try:
        resp = httpx.get(
            f"{DOWNSHIFTOLOGY_API_BASE}/wprm_recipe/{wprm_id}",
            params={"_fields": "id,title,link,recipe"},
            timeout=15.0,
        )
        resp.raise_for_status()
        recipe_data = resp.json()
    except httpx.HTTPError as e:
        logger.error("Failed to fetch recipe %s for import: %s", wprm_id, e)
        return "Failed to fetch recipe from Downshiftology. Please try again."

    r = recipe_data.get("recipe", {})

    # Get or create "Downshiftology" cookbook
    cookbook = notion.get_cookbook_by_name("Downshiftology")
    if not cookbook:
        cookbook_id = notion.create_cookbook("Downshiftology", "Healthy recipes from downshiftology.com")
    else:
        cookbook_id = cookbook["id"]

    # Map fields
    name = _strip_html(r.get("name", ""))

    # Ingredients → JSON format [{name, quantity, unit}]
    ingredients = []
    for ing in r.get("ingredients_flat", []):
        ingredients.append({
            "name": ing.get("name", ""),
            "quantity": ing.get("amount", ""),
            "unit": ing.get("unit", ""),
        })
    ingredients_json = json.dumps(ingredients)

    # Instructions → plain text
    instructions = []
    for i, step in enumerate(r.get("instructions_flat", []), 1):
        text = _strip_html(step.get("text", ""))
        if text:
            instructions.append(f"{i}. {text}")
    instructions_text = "\n".join(instructions)

    # Times
    prep_time = None
    try:
        prep_time = int(r.get("prep_time", 0)) if r.get("prep_time") else None
    except (ValueError, TypeError):
        pass

    cook_time = None
    try:
        cook_time = int(r.get("cook_time", 0)) if r.get("cook_time") else None
    except (ValueError, TypeError):
        pass

    servings = None
    try:
        servings = int(r.get("servings", 0)) if r.get("servings") else None
    except (ValueError, TypeError):
        pass

    # Tags and cuisine
    notion_tags, notion_cuisine = _map_tags(r)

    # Photo
    photo_url = r.get("image_url", "")

    # Create in Notion
    page_id = notion.create_recipe(
        name=name,
        cookbook_id=cookbook_id,
        ingredients_json=ingredients_json,
        instructions=instructions_text,
        prep_time=prep_time,
        cook_time=cook_time,
        servings=servings,
        photo_url=photo_url,
        tags=notion_tags if notion_tags else None,
        cuisine=notion_cuisine,
        source_url=recipe_link,
    )

    return (
        f"Saved! *{name}* imported to your recipe catalogue.\n"
        f"- Servings: {servings or 'N/A'}\n"
        f"- Time: {r.get('total_time', 'N/A')} min\n"
        f"- Ingredients: {len(ingredients)}\n"
        f"- Cookbook: Downshiftology\n"
        f"- Source: {recipe_link}"
    )


# ---------------------------------------------------------------------------
# US3: Grocery History Cross-Reference
# ---------------------------------------------------------------------------

def _cross_reference_grocery_history(ingredients_flat: list[dict]) -> str:
    """Cross-reference recipe ingredients against grocery purchase history.

    Returns a formatted section showing which ingredients the family buys.
    """
    grocery_items = notion.get_all_grocery_items()
    if not grocery_items:
        return ""

    grocery_set = set(grocery_items)
    on_hand = []
    new_ingredients = []

    for ing in ingredients_flat:
        ing_name = ing.get("name", "").strip()
        if not ing_name:
            continue
        ing_lower = ing_name.lower()

        # Check if ingredient matches any grocery history item (substring match)
        matched = any(
            ing_lower in item or item in ing_lower
            for item in grocery_set
        )
        if matched:
            on_hand.append(ing_name)
        else:
            new_ingredients.append(ing_name)

    total = len(on_hand) + len(new_ingredients)
    if total == 0:
        return ""

    lines = [f"\n*Grocery match: {len(on_hand)}/{total} ingredients on hand*"]
    if on_hand:
        lines.append(f"  You typically buy: {', '.join(on_hand[:8])}")
    if new_ingredients:
        lines.append(f"  New for you: {', '.join(new_ingredients[:8])}")

    return "\n".join(lines)
