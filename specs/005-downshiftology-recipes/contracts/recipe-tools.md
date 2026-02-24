# Contract: Downshiftology Recipe Tool Definitions

## search_downshiftology

**Description**: Search Downshiftology.com for healthy recipes by course, cuisine, ingredient, dietary preference, or time constraint.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | No | Free-text search term (e.g., "chicken", "sweet potato") |
| course | string | No | Course type: dinner, breakfast, lunch, appetizer, side-dish, salad, soup, snack, dessert, drinks |
| cuisine | string | No | Cuisine: american, mexican, italian, mediterranean, asian, french, indian, greek, middle-eastern |
| dietary | string | No | Dietary preference: keto, paleo, whole30, gluten-free, dairy-free, vegan, vegetarian |
| max_time | number | No | Maximum total time in minutes (e.g., 30 for quick meals) |

**Returns**: Formatted numbered list of 3-5 matching recipes, each with:
- Recipe name
- Total time
- Dietary tags and cuisine
- Rating (if available)
- Direct link to Downshiftology recipe page

**Follow-up support**: Results are cached for "save number N", "tell me more about N", and "show more results" commands.

## import_downshiftology_recipe

**Description**: Import a Downshiftology recipe into the family's recipe catalogue for meal planning and grocery lists.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| result_number | number | No | Number from most recent search results (e.g., 2) |
| recipe_name | string | No | Recipe name to search and import (alternative to number) |

**Returns**: Confirmation text with imported recipe details (name, servings, prep/cook time, ingredient count, source link), or error if recipe not found or already exists.

**Behavior**:
- If `result_number` provided: Uses cached search results to identify the recipe
- If `recipe_name` provided: Searches Downshiftology for the recipe, imports first match
- Checks for duplicates by Source URL before creating
- Creates "Downshiftology" cookbook entry if it doesn't exist
- Maps dietary tags and cuisine to existing Notion options

## get_downshiftology_details

**Description**: Get full details of a Downshiftology recipe from search results, including complete ingredient list and instructions.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| result_number | number | Yes | Number from most recent search results |

**Returns**: Full recipe details:
- Name, servings, prep/cook/total time
- Complete ingredient list with quantities
- Step-by-step instructions (plain text, no HTML)
- Nutrition summary (calories, protein, carbs, fat)
- Dietary tags
- Link to original recipe
- Grocery history match (if US3 implemented): "X/Y ingredients on hand"
