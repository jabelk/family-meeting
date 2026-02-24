# Tasks: Downshiftology Recipe Search

**Input**: Design documents from `/specs/005-downshiftology-recipes/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/recipe-tools.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Notion schema update and foundational module creation

- [x] T001 Add `Source URL` property (type: URL) to the Notion Recipes database — manual step in Notion UI, needed for recipe import deduplication and attribution
- [x] T002 Add `source_url` parameter to `create_recipe()` function in src/tools/notion.py — optional URL parameter, when provided set the Source URL property on the Notion page, default None for backward compatibility with existing cookbook recipes

---

## Phase 2: Foundational — Downshiftology API Client

**Purpose**: Core API access and taxonomy mapping that ALL user stories depend on

**CRITICAL**: No user story work (US1/US2/US3) can begin until this phase is complete

- [x] T003 Create src/tools/downshiftology.py with base module structure — imports (httpx, logging, html, re), constants (DOWNSHIFTOLOGY_API_BASE = "https://downshiftology.com/wp-json/wp/v2"), COURSE_IDS dict mapping lowercase course names to WPRM taxonomy IDs (dinner→22904, main-course→2001, breakfast→1998, appetizer→1999, side-dish→2002, salad→2003, soup→2000, dessert→2004, snack→2005, drinks→2006, sauce→15036, dressing→13345), CUISINE_IDS dict mapping lowercase cuisine names to IDs (american→2013, mexican→2014, italian→2008, mediterranean→2009, french→2007, asian→13246, indian→2010, greek→14244, middle-eastern→13921, japanese→2012, chinese→2011)
- [x] T004 Add `_fetch_recipes(params)` helper function to src/tools/downshiftology.py — httpx.get to WPRM recipe endpoint with `_fields=id,title,link,recipe` plus caller params, `per_page=20` default, filter out roundup posts where `recipe.parent_post_id` is "0" or empty string, return list of recipe dicts, handle httpx errors gracefully with logging
- [x] T005 Add `_format_recipe_summary(recipe)` helper to src/tools/downshiftology.py — extract from API response: name from `recipe["recipe"]["name"]`, total_time from `recipe["recipe"]["total_time"]`, course tags from `recipe["recipe"]["tags"]["course"]`, cuisine from `recipe["recipe"]["tags"]["cuisine"]`, rating from `recipe["recipe"]["rating"]`, link from `recipe["link"]`, return formatted dict with these fields
- [x] T006 Add `_strip_html(text)` helper to src/tools/downshiftology.py — use `html.unescape()` and `re.sub(r'<[^>]+>', '', text)` to strip HTML tags from recipe descriptions and instruction text
- [x] T007 Add `_last_search_results` module-level list and `_dietary_terms` set to src/tools/downshiftology.py — `_last_search_results: list[dict] = []` stores most recent search for follow-up commands, `_dietary_terms` maps dietary keywords to check against recipe name/summary/keyword tags: {"keto", "paleo", "whole30", "gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "low-carb", "high-protein"}

**Checkpoint**: Downshiftology API client ready — user story implementation can begin

---

## Phase 3: User Story 1 — Recipe Search (Priority: P1) MVP

**Goal**: Erin can say "find me a chicken dinner recipe" and get Downshiftology results with names, times, tags, and links

**Independent Test**: Send "find me a chicken dinner recipe" to the bot and verify 3-5 recipes returned with names, times, and links

- [x] T008 [US1] Implement `search_downshiftology(query, course, cuisine, dietary, max_time)` in src/tools/downshiftology.py — build API params: if course provided map to `wprm_course` ID via COURSE_IDS, if cuisine map to `wprm_cuisine` ID via CUISINE_IDS, if query provided add as `search` param, fetch up to 20 results via `_fetch_recipes()`, apply client-side dietary filter (check recipe name + summary + keyword tag names for dietary term), apply client-side max_time filter (recipe.total_time <= max_time), format top 5 results as numbered list using `_format_recipe_summary()`, store results in `_last_search_results`, return formatted text with "Recipe name | Total time | Tags | Link" per line
- [x] T009 [US1] Implement `get_downshiftology_details(result_number)` in src/tools/downshiftology.py — validate result_number is within `_last_search_results` range, re-fetch full recipe by ID from API if needed, extract and format: name, servings, prep/cook/total time, full ingredient list (from `recipe.ingredients_flat` — format as "amount unit name" per line), instructions (from `recipe.instructions_flat` — strip HTML from text, number steps), nutrition summary (calories, protein, carbs, fat from `recipe.nutrition`), dietary tags, link to original recipe, return formatted text
- [x] T010 [US1] Register `search_downshiftology` and `get_downshiftology_details` tools in src/assistant.py — add 2 tool definitions to TOOLS array with parameter schemas per contracts/recipe-tools.md, add 2 entries to TOOL_FUNCTIONS dict mapping to downshiftology module functions, add `from src.tools import downshiftology` to imports, update system prompt with recipe search guidelines: "For recipe searches ('find me a chicken dinner'), use search_downshiftology. For recipe details ('tell me more about number 2'), use get_downshiftology_details. Show results as numbered lists with name, time, and link."

**Checkpoint**: Recipe search fully functional — search and browse Downshiftology via WhatsApp

---

## Phase 4: User Story 2 — Recipe Import (Priority: P2)

**Goal**: Erin can say "save number 2" to import a Downshiftology recipe into the Notion catalogue

**Independent Test**: Search for a recipe, say "save number 1", verify recipe appears in Notion with full details and Source URL

- [x] T011 [US2] Implement `_map_tags(recipe_data)` helper in src/tools/downshiftology.py — map Downshiftology course tags to existing Notion Tags multi-select options (Soup→Soup, Salad→Salad, Main Course/Dinner→Meat, Snack/Dessert→Comfort Food), map Downshiftology cuisine to Notion Cuisine select (American→American, Mexican→Mexican, Italian→Italian, Asian/Chinese/Japanese→Asian, Mediterranean/Greek/Middle Eastern→Mediterranean, all others→Other), return (tags_list, cuisine_string) tuple
- [x] T012 [US2] Implement `import_downshiftology_recipe(result_number, recipe_name)` in src/tools/downshiftology.py — if result_number provided, get recipe from `_last_search_results`, if recipe_name provided search API and use first match, re-fetch full recipe data by WPRM ID, check for duplicate by searching Notion recipes where Source URL matches the recipe link, if duplicate return "This recipe is already saved!", get or create "Downshiftology" cookbook via `get_cookbook_by_name()`/`create_cookbook()`, convert `recipe.ingredients_flat` to JSON format `[{name, quantity, unit}]` where quantity=amount, map tags and cuisine via `_map_tags()`, strip HTML from instructions and join with newlines, call `create_recipe()` with all fields including `source_url=recipe_link` and `photo_url=recipe.image_url`, return confirmation with recipe name, servings, time, ingredient count, and source link
- [x] T013 [US2] Add duplicate detection by Source URL to src/tools/notion.py — add `search_recipes_by_source_url(url)` function that queries NOTION_RECIPES_DB with filter `{"property": "Source URL", "url": {"equals": url}}`, return list of matching recipe dicts (empty if no match)
- [x] T014 [US2] Register `import_downshiftology_recipe` tool in src/assistant.py — add tool definition to TOOLS array per contracts/recipe-tools.md, add entry to TOOL_FUNCTIONS dict, update system prompt: "When Erin says 'save number N' or 'import that recipe' after a Downshiftology search, use import_downshiftology_recipe with the result number."

**Checkpoint**: Recipe import functional — search, save, and find imported recipes in Notion catalogue

---

## Phase 5: User Story 3 — Smart Recommendations (Priority: P3)

**Goal**: Recipe details include grocery history cross-reference showing which ingredients the family already buys

**Independent Test**: Get recipe details and verify ingredient availability notes are included

- [x] T015 [US3] Implement `_cross_reference_grocery_history(ingredients)` in src/tools/downshiftology.py — import `get_all_grocery_items` from notion (or query grocery history directly), build a set of lowercase item names from grocery history, for each recipe ingredient check if `ingredient["name"].lower()` appears as a substring in any grocery history item name, count matches vs total, build lists of matched ingredients ("on hand") and unmatched ("new"), return dict with {matched_count, total_count, on_hand: [...], new_ingredients: [...]}
- [x] T016 [US3] Extend `get_downshiftology_details()` in src/tools/downshiftology.py to include grocery cross-reference — after formatting recipe details, call `_cross_reference_grocery_history()` with the ingredient list, append section: "Grocery match: X/Y ingredients on hand" with list of matched items, and "New ingredients:" with list of unmatched items, handle errors gracefully (if grocery history unavailable, skip this section)
- [x] T017 [US3] Update system prompt in src/assistant.py — add guideline: "When showing recipe details, the response includes which ingredients the family typically buys. Use this to help Erin decide — 'This recipe uses mostly things you already buy' or 'You'd need to pick up tahini and za'atar for this one.'"

**Checkpoint**: Smart recommendations functional — recipe details include ingredient availability based on grocery history

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: System prompt refinements, deployment, and validation

- [x] T018 Update system prompt in src/assistant.py with comprehensive Downshiftology interaction guidelines — explain all 3 recipe tools, natural language pattern mapping ("find me a recipe" → search_downshiftology, "save number N" → import_downshiftology_recipe, "tell me more" → get_downshiftology_details, "what should I make tonight?" → search with dinner course), note that Downshiftology is the only external recipe source
- [x] T019 Deploy to NUC via ./scripts/nuc.sh deploy
- [x] T020 Run quickstart.md validation — Test 1 (recipe search), Test 2 (recipe details), Test 3 (recipe import), Test 4 (duplicate detection), Test 5 (grocery cross-reference), Test 6 (error handling)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — Notion schema + code update
- **Phase 2 (Foundational)**: Depends on Phase 1 (needs create_recipe source_url param)
- **Phase 3 (US1)**: Depends on Phase 2 (needs API client and taxonomy maps)
- **Phase 4 (US2)**: Depends on Phase 2 + Phase 1 (needs API client + source_url in Notion)
- **Phase 5 (US3)**: Depends on Phase 3 (extends get_downshiftology_details)
- **Phase 6 (Polish)**: Depends on all phases complete

### User Story Dependencies

- **US1 (Search)**: Depends on Phase 2 only — no other story dependencies
- **US2 (Import)**: Depends on Phase 2 + T002 (source_url param) — independent of US1 at code level, but US1 provides search results for import flow
- **US3 (Smart Recommendations)**: Depends on US1 (extends get_downshiftology_details function)

### Parallel Opportunities

- T003, T004, T005, T006, T007 can run sequentially (same file) but T003 must be first
- US1 (Phase 3) and US2 (Phase 4) can run in parallel after Phase 2 (different functions, but same file — recommend sequential)
- T013 (Notion function) can run in parallel with T011/T012 (different files)

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2 + Phase 3)

1. T001-T002: Setup — Notion schema + source_url param
2. T003-T007: Build Downshiftology API client
3. T008-T010: Recipe search + details → deploy and validate
4. **STOP and VALIDATE**: Test search via WhatsApp

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. Phase 3 (US1) → Recipe search live (MVP)
3. Phase 4 (US2) → Recipe import live
4. Phase 5 (US3) → Smart recommendations live
5. Phase 6 → Polish and full validation

---

## Notes

- Downshiftology API is public, no authentication needed, CDN-cached responses
- API max per_page is 100; default to 20 for search, use `_fields` param to reduce payload
- Dietary filtering is client-side (API keyword taxonomy is unreliable for dietary labels)
- Roundup posts (parent_post_id = "0") must be filtered out — they're not actual recipes
- Notion rich text limit is 2000 chars — long ingredient lists may be truncated
- Course IDs and Cuisine IDs are hardcoded from research (stable WordPress taxonomy)
