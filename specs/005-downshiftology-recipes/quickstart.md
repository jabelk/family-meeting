# Quickstart: Downshiftology Recipe Search

## Prerequisites

- Existing family meeting assistant deployed (FastAPI + Docker Compose on NUC)
- WhatsApp bot working with existing tool loop
- Notion Recipes and Cookbooks databases configured
- Internet access from NUC (for Downshiftology API calls)

## Setup Steps

### Step 1: Add Source URL Property to Notion

Add a new `Source URL` property (type: URL) to the Notion Recipes database. This stores the Downshiftology permalink for imported recipes.

### Step 2: Add Downshiftology Search Tools

Add 3 new tool functions to `src/tools/downshiftology.py` (new file):
- `search_downshiftology()` — search by course, cuisine, ingredient, dietary, time
- `import_downshiftology_recipe()` — import from search results or by name
- `get_downshiftology_details()` — full recipe details from search results

### Step 3: Register Tools in Assistant

Add 3 new tool definitions to `src/assistant.py` TOOLS array and TOOL_FUNCTIONS dict. Update system prompt with recipe search guidelines.

### Step 4: Update Notion Recipe Functions

Add `source_url` parameter to `create_recipe()` in `src/tools/notion.py`. Update `search_recipes_by_title()` to include Source URL in results.

### Step 5: Deploy

```bash
git add . && git commit -m "feat: Downshiftology recipe search" && git push
./scripts/nuc.sh deploy
```

## Validation

### Test 1: Recipe Search (US1)

1. Send "find me a chicken dinner recipe" to the bot
2. Verify 3-5 Downshiftology recipes are returned with names, times, and links
3. Send "show me keto breakfast ideas"
4. Verify results are filtered to breakfast + keto-relevant recipes

### Test 2: Recipe Details (US1)

1. After a search, send "tell me more about number 2"
2. Verify full recipe details are shown: ingredients, instructions, nutrition
3. Verify the Downshiftology link is included

### Test 3: Recipe Import (US2)

1. After a search, send "save number 1"
2. Verify recipe appears in Notion Recipes database with:
   - Full name, ingredients, instructions
   - Prep/cook time, servings
   - Source URL pointing to Downshiftology
   - Cookbook relation set to "Downshiftology"
3. Try importing the same recipe again
4. Verify duplicate detection ("This recipe is already saved!")

### Test 4: Duplicate Detection (US2)

1. Import a recipe
2. Send "save number 1" again for the same recipe
3. Verify the bot says it's already saved

### Test 5: Grocery History Cross-Reference (US3)

1. Search for a recipe
2. Send "tell me more about number 1"
3. Verify the response includes ingredient availability notes based on grocery history
4. Verify uncommon ingredients are flagged

### Test 6: Error Handling

1. Search for something with no results ("lamb keto breakfast")
2. Verify the bot suggests broadening the search
3. Say "save number 5" when only 3 results were shown
4. Verify the bot handles the out-of-range number gracefully

## Troubleshooting

- **"Recipe search unavailable"**: Downshiftology API may be down or blocked. Check NUC internet connectivity and try `curl https://downshiftology.com/wp-json/wp/v2/wprm_recipe?per_page=1` from the container.
- **Slow search results**: The API is CDN-cached but initial requests may take 3-5 seconds. Combined filters reduce result size and speed up processing.
- **Missing dietary tags**: Downshiftology's keyword taxonomy is fragmented — dietary filtering is done client-side by checking recipe names and summaries, not API taxonomy. Some recipes may not have clear dietary labels.
- **Truncated ingredients**: Notion rich text has a 2000-character limit. Very long ingredient lists may be truncated on import. This affects <5% of recipes.
- **"Cookbook not found"**: The "Downshiftology" cookbook is auto-created on first import. If it fails, manually create a Cookbook entry named "Downshiftology" in Notion.
