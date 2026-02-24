# Research: Downshiftology Recipe Search

## R1: Downshiftology API Access Pattern

**Decision**: Use the WordPress REST API (`/wp-json/wp/v2/wprm_recipe`) for all recipe data — no scraping, no authentication needed.

**Rationale**: The WP Recipe Maker (WPRM) plugin exposes a fully public REST API with rich structured data. Every recipe includes ingredients (with quantities/units), instructions (with step photos), nutrition, ratings, taxonomy tags, and timing data. The API supports combined taxonomy filtering (course + cuisine + ingredient + keyword search) with AND logic.

**Alternatives considered**: HTML scraping with BeautifulSoup (fragile, slower), JSON-LD extraction from recipe pages (one page at a time, can't search), RSS feed (only 10 latest posts). REST API is the clear winner.

### Key API Details

- **Total recipes**: 861 (per `X-WP-Total` header)
- **Max per_page**: 100 (returns 400 if exceeded)
- **Supported filters**: `search`, `wprm_course`, `wprm_cuisine`, `wprm_ingredient`, `wprm_keyword` — all combinable
- **_fields parameter**: Works — use `_fields=id,title,link,recipe` to reduce payload
- **Response includes**: Full `recipe` nested object with resolved taxonomy tags, grouped/flat ingredients, grouped/flat instructions, nutrition, and ratings
- **CDN caching**: Responses cached up to 30 days by Cloudflare, so new recipes may lag

### Roundup Post Filtering

Search results include collection/roundup posts (e.g., "60+ Best Mediterranean Diet Recipes") that aren't actual recipes. Filter these by checking `recipe.parent_post_id != "0"` and `!= ""`.

## R2: Natural Language → API Filter Mapping

**Decision**: Let Claude (Opus) interpret the natural language query and map it to API parameters. No custom NLP pipeline needed.

**Rationale**: Claude already interprets tool parameters from natural language. The tool definition specifies available filters (course, cuisine, ingredient keyword, time constraint), and Claude maps "quick keto dinner" to `{course: "dinner", search: "keto", max_time: 30}`. This is the same pattern used for all other tools in the system.

**Filter mapping strategy**:
1. Course → `wprm_course` taxonomy ID (need a static map of 18 course names → IDs)
2. Cuisine → `wprm_cuisine` taxonomy ID (static map of 24 cuisine names → IDs)
3. Ingredient keyword → `search` parameter (API searches title/content)
4. Time constraint → client-side filter on `recipe.total_time`
5. Dietary preference → client-side filter on recipe name/summary/tags (API keyword taxonomy is unreliable for dietary filtering)

## R3: Dietary Label Filtering

**Decision**: Client-side filtering using recipe name, summary, and keyword tags — NOT the `wprm_keyword` taxonomy filter.

**Rationale**: Research found the keyword taxonomy is fragmented. Canonical tags like "gluten-free", "paleo", "vegan" have count=0 — recipes use specific keyword variants instead (e.g., "Paleo Chicken Alfredo"). Filtering via the API would miss most matches. Instead, fetch a broader result set and let the search function filter by checking if dietary terms appear in `recipe.name`, `recipe.summary`, or `recipe.tags.keyword[].name`.

**Dietary term list**: gluten-free, dairy-free, paleo, whole30, keto, low-carb, vegan, vegetarian, nut-free, high-protein.

## R4: Notion Schema Changes

**Decision**: Add one new property (`Source URL`) to the Recipes database. Model Downshiftology as a "cookbook" entry in the existing Cookbooks database.

**Rationale**: The existing schema already has all the fields needed for recipe data (name, ingredients, instructions, prep/cook time, servings, tags, cuisine). The only gap is tracking the external source URL. Adding `Source URL` as a URL property allows deduplication on import and provides a link back to the original.

Modeling Downshiftology as a Cookbook entry (name: "Downshiftology") keeps the data model simple and consistent — imported recipes relate to a cookbook just like photo-scanned recipes do. The existing `search_recipes` function works unchanged.

**Schema change**: Add `Source URL` (URL type) property to Notion Recipes database.

## R5: Ingredient Matching for Grocery History

**Decision**: Use the existing exact-match logic for MVP. Accept that most Downshiftology ingredients will land in the "unknown" bucket initially. Claude can interpret and present the data intelligently.

**Rationale**: The current `recipe_to_grocery_list` uses exact lowercase string matching. Downshiftology ingredient names (e.g., "boneless skinless chicken breasts") won't match grocery history entries (e.g., "chicken breast"). Building fuzzy matching or an alias system adds complexity for limited immediate value.

Instead, for US3 (grocery history cross-referencing), pass the ingredient list to Claude and let it reason about matches — "You usually buy chicken breasts and olive oil" — rather than relying on programmatic matching. This is simpler, more flexible, and leverages Opus's reasoning ability.

**Future enhancement**: Add fuzzy ingredient matching using substring/contains logic similar to `_fuzzy_match_category` in ynab.py.

## R6: Search Result Caching and Session State

**Decision**: Cache the most recent search results in module-level storage (same pattern as `_current_image_data` in assistant.py) so "save number 3" and "tell me more about number 2" work as follow-up commands.

**Rationale**: Claude's tool loop doesn't persist state between messages. When Erin says "save number 3", the bot needs to know what "number 3" referred to from the previous search. A module-level list that stores the last search results (recipe IDs + metadata) allows follow-up commands without re-searching.

**Implementation**: `_last_search_results: list[dict] = []` in the downshiftology module. Updated on each search, cleared on new search. Each entry stores the WPRM recipe ID and enough metadata for import.

## R7: Recipe Import Data Mapping

**Decision**: Map Downshiftology API fields directly to existing Notion recipe properties.

**Mapping**:
| Downshiftology API | Notion Property | Transform |
|---|---|---|
| `recipe.name` | Name (Title) | Direct |
| `recipe.ingredients_flat` | Ingredients (Rich Text) | Convert to JSON array `[{name, quantity, unit}]` |
| `recipe.instructions_flat` | Instructions (Rich Text) | Join step texts with newlines, strip HTML |
| `recipe.prep_time` | Prep Time (Number) | Direct (already minutes) |
| `recipe.cook_time` | Cook Time (Number) | Direct |
| `recipe.servings` | Servings (Number) | Parse string to int |
| `recipe.tags.course` | Tags (Multi-select) | Map to existing tag options |
| `recipe.tags.cuisine` | Cuisine (Select) | Map to existing options, default "Other" |
| `recipe.image_url` | Photo URL (URL) | Direct (use Downshiftology CDN URL) |
| `link` | Source URL (URL) | Direct |
| "Downshiftology" | Cookbook (Relation) | Create/reuse Cookbooks entry |
