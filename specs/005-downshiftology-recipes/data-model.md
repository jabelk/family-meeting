# Data Model: Downshiftology Recipe Search

## External Entities (Downshiftology API — read-only)

### WPRM Recipe

Represents a recipe from the Downshiftology WordPress REST API. Read via GET `/wp-json/wp/v2/wprm_recipe`.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | WPRM recipe post ID |
| title.rendered | String | Recipe display name |
| link | URL | Permalink to recipe page |
| recipe.name | String | Recipe name (same as title) |
| recipe.summary | String (HTML) | Short description |
| recipe.image_url | URL | Hero image URL |
| recipe.prep_time | String | Minutes as string (e.g., "10") |
| recipe.cook_time | String | Minutes as string |
| recipe.total_time | String | Minutes as string |
| recipe.servings | String | Serving count as string |
| recipe.ingredients_flat | Array | Flat list of {amount, unit, name, notes} |
| recipe.instructions_flat | Array | Flat list of {name, text (HTML), image_url} |
| recipe.tags.course | Array | Resolved course terms [{term_id, name, slug}] |
| recipe.tags.cuisine | Array | Resolved cuisine terms |
| recipe.tags.keyword | Array | Resolved keyword terms |
| recipe.nutrition | Object | Per-serving: calories, protein, fat, carbs, fiber, etc. |
| recipe.rating | Object | {count, average} |
| recipe.parent_post_id | String | Parent blog post ID; "0" = roundup post (skip) |

### Course Taxonomy

18 course terms used for filtering. Key IDs:

| ID | Name | Count |
|----|------|-------|
| 22904 | Dinner | 108 |
| 2001 | Main Course | 105 |
| 2002 | Side Dish | 93 |
| 1999 | Appetizer | 92 |
| 2003 | Salad | 90 |
| 1998 | Breakfast | 82 |
| 2004 | Dessert | 107 |
| 2006 | Drinks | 64 |
| 2005 | Snack | 47 |
| 2000 | Soup | 30 |

### Cuisine Taxonomy

24 cuisine terms. Key IDs:

| ID | Name | Count |
|----|------|-------|
| 2013 | American | 608 |
| 2014 | Mexican | 72 |
| 2008 | Italian | 44 |
| 2009 | Mediterranean | 31 |
| 2007 | French | 20 |
| 13246 | Asian | 18 |
| 13304 | Irish | 9 |
| 2010 | Indian | 10 |

## Internal Entities (Notion — existing + extended)

### Recipe (existing Notion DB — 1 new property)

Extended from Feature 002. One new property added for external recipe import.

| Property | Type | New? | Notes |
|----------|------|------|-------|
| Name | Title | No | Recipe name |
| Ingredients | Rich Text | No | JSON array `[{name, quantity, unit}]`, max 2000 chars |
| Instructions | Rich Text | No | Newline-joined steps, max 2000 chars |
| Cookbook | Relation | No | Links to Cookbooks DB |
| Prep Time | Number | No | Minutes |
| Cook Time | Number | No | Minutes |
| Servings | Number | No | Integer |
| Photo URL | URL | No | Image URL (R2 for scanned, Downshiftology CDN for imported) |
| Tags | Multi-select | No | Keto, Kid-Friendly, Quick, Vegetarian, Comfort Food, Soup, Salad, Pasta, Meat, Seafood |
| Cuisine | Select | No | American, Mexican, Italian, Asian, Mediterranean, Other |
| Times Used | Number | No | Usage counter |
| Date Added | Date | No | Auto-set on creation |
| **Source URL** | **URL** | **Yes** | **External recipe permalink (null for cookbook recipes)** |

### Cookbook (existing Notion DB — no changes)

Downshiftology is modeled as a Cookbook entry (name: "Downshiftology"). No schema changes needed.

| Property | Type | Notes |
|----------|------|-------|
| Name | Title | "Downshiftology" for imported recipes |
| Description | Rich Text | "Healthy recipes from downshiftology.com" |

## Caching / Session State

### Search Result Cache (in-memory, module-level)

Stores the most recent Downshiftology search results for follow-up commands ("save number 3", "tell me more about 2").

| Field | Type | Notes |
|-------|------|-------|
| wprm_id | Integer | Downshiftology recipe ID for re-fetch |
| name | String | Recipe display name |
| link | URL | Permalink |
| total_time | Integer | Minutes (for display) |
| tags | List[String] | Course + dietary labels |
| cuisine | String | Primary cuisine |
| rating | Float | Average rating |

Cleared and replaced on each new search. Module-level list: `_last_search_results`.

## Tag Mapping

### Downshiftology Course → Notion Tags

| Downshiftology Course | Notion Tag |
|----------------------|------------|
| Soup | Soup |
| Salad | Salad |
| Main Course / Dinner | Meat or Seafood (based on ingredients) |
| Snack | (no direct mapping) |
| Dessert | Comfort Food |
| Breakfast | (no direct mapping) |

### Downshiftology Cuisine → Notion Cuisine

| Downshiftology Cuisine | Notion Cuisine |
|------------------------|----------------|
| American | American |
| Mexican | Mexican |
| Italian | Italian |
| Asian / Chinese / Japanese / Indonesian | Asian |
| Mediterranean / Greek / Middle Eastern | Mediterranean |
| All others | Other |
