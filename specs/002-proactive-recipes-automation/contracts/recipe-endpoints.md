# Contract: Recipe Endpoints

**Feature**: 002-proactive-recipes-automation | **Date**: 2026-02-22

## Overview

Recipe management is handled entirely through the WhatsApp conversational interface (Claude tool loop). No direct REST endpoints are needed for recipe CRUD — Claude calls the tools internally. The contracts below define the **tool interfaces** that Claude uses.

## WhatsApp Webhook Extension

The existing `POST /webhook` handler is extended to detect image messages and route them to recipe extraction.

### Image Message Detection

```
# Existing webhook payload for text:
message.type == "text" → existing handle_message flow

# New: image message detection:
message.type == "image" → download media → handle_message with image context
```

### Image Processing Flow

```
1. Webhook receives message with type="image"
2. Extract media_id from message.image.id
3. GET https://graph.facebook.com/v21.0/{media_id}
   Headers: Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}
   Response: {url, mime_type, file_size}
4. GET {url}
   Headers: Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}
   Response: binary image data
5. Pass to handle_message as image content (base64) + caption text
6. Claude determines intent from caption:
   - "save this recipe" / "save from keto book" → recipe extraction
   - No recipe context → treat as general image question
```

## Claude Tool Definitions

### extract_and_save_recipe

```json
{
  "name": "extract_and_save_recipe",
  "description": "Extract recipe from a cookbook photo using Claude vision and save to the recipe catalogue. Called when a user sends a cookbook photo with intent to save.",
  "input_schema": {
    "type": "object",
    "properties": {
      "image_base64": {
        "type": "string",
        "description": "Base64-encoded image data"
      },
      "mime_type": {
        "type": "string",
        "description": "Image MIME type (image/jpeg, image/png)"
      },
      "cookbook_name": {
        "type": "string",
        "description": "Name of the source cookbook (from user's message). Default: 'Uncategorized'"
      }
    },
    "required": ["image_base64", "mime_type"]
  }
}
```

**Returns**:
```json
{
  "success": true,
  "recipe": {
    "name": "Grilled Steak with Herb Butter",
    "cookbook": "The Keto Cookbook",
    "ingredients_count": 12,
    "prep_time": 15,
    "cook_time": 20,
    "servings": 4,
    "unclear_portions": ["Step 3 temperature was partially cut off — assumed 400°F"],
    "notion_page_id": "abc123...",
    "photo_url": "https://family-recipes.r2.cloudflarestorage.com/recipes/abc123.jpg"
  }
}
```

### search_recipes

```json
{
  "name": "search_recipes",
  "description": "Search the recipe catalogue by name, ingredient, cookbook, or description.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Natural language search query (e.g., 'steak from keto book', 'chicken recipes', 'recipes with spinach')"
      },
      "cookbook_name": {
        "type": "string",
        "description": "Optional: filter to specific cookbook"
      },
      "tags": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional: filter by tags (e.g., ['Keto', 'Quick (<30min)'])"
      }
    },
    "required": ["query"]
  }
}
```

**Returns**:
```json
{
  "results": [
    {
      "name": "Grilled Steak with Herb Butter",
      "cookbook": "The Keto Cookbook",
      "tags": ["Keto", "Meat"],
      "prep_time": 15,
      "cook_time": 20,
      "servings": 4,
      "times_used": 3,
      "notion_page_id": "abc123..."
    }
  ],
  "total": 1
}
```

### get_recipe_details

```json
{
  "name": "get_recipe_details",
  "description": "Get full recipe details including ingredients and instructions.",
  "input_schema": {
    "type": "object",
    "properties": {
      "recipe_id": {
        "type": "string",
        "description": "Notion page ID of the recipe"
      }
    },
    "required": ["recipe_id"]
  }
}
```

**Returns**:
```json
{
  "name": "Grilled Steak with Herb Butter",
  "cookbook": "The Keto Cookbook",
  "ingredients": [
    {"name": "ribeye steak", "quantity": "2", "unit": "lbs"},
    {"name": "butter", "quantity": "4", "unit": "tbsp"},
    {"name": "fresh rosemary", "quantity": "2", "unit": "sprigs"}
  ],
  "instructions": [
    "Season steaks with salt and pepper...",
    "Heat grill to high...",
    "Grill 4 minutes per side for medium-rare..."
  ],
  "prep_time": 15,
  "cook_time": 20,
  "servings": 4,
  "photo_url": "https://...",
  "tags": ["Keto", "Meat"]
}
```

### recipe_to_grocery_list

```json
{
  "name": "recipe_to_grocery_list",
  "description": "Generate a grocery list from a recipe, cross-referencing against recently ordered items to avoid duplicates.",
  "input_schema": {
    "type": "object",
    "properties": {
      "recipe_id": {
        "type": "string",
        "description": "Notion page ID of the recipe"
      },
      "servings_multiplier": {
        "type": "number",
        "description": "Scale ingredients (default 1.0)"
      }
    },
    "required": ["recipe_id"]
  }
}
```

**Returns**:
```json
{
  "needed_items": [
    {"name": "ribeye steak", "quantity": "2 lbs", "store": "Whole Foods"},
    {"name": "fresh rosemary", "quantity": "2 sprigs", "store": "Whole Foods"}
  ],
  "already_have": [
    {"name": "butter", "reason": "ordered 5 days ago (avg reorder: 21 days)"},
    {"name": "salt", "reason": "staple — ordered 8 days ago"}
  ],
  "unknown_items": [
    {"name": "herb butter mix", "note": "not in grocery history — will add as-is"}
  ]
}
```

### list_cookbooks

```json
{
  "name": "list_cookbooks",
  "description": "List all cookbooks in the catalogue with recipe counts.",
  "input_schema": {
    "type": "object",
    "properties": {}
  }
}
```

**Returns**:
```json
{
  "cookbooks": [
    {"name": "The Keto Cookbook", "recipe_count": 12, "notion_page_id": "..."},
    {"name": "Family Meals", "recipe_count": 8, "notion_page_id": "..."},
    {"name": "Uncategorized", "recipe_count": 3, "notion_page_id": "..."}
  ]
}
```
