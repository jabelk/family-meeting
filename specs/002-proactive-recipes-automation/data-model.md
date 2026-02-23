# Data Model: Proactive Automations & Recipe Management

**Feature**: 002-proactive-recipes-automation | **Date**: 2026-02-22

## New Notion Databases

### Recipes Database

| Property | Type | Configuration | Notes |
|----------|------|---------------|-------|
| Name | Title | (default) | Recipe name extracted from photo |
| Cookbook | Relation | → Cookbooks database | Source cookbook |
| Ingredients | Rich Text | | JSON array: `[{name, quantity, unit}]` — stored as structured text for Claude to parse |
| Instructions | Rich Text | | Ordered step list |
| Prep Time | Number | Minutes | Extracted from photo or estimated |
| Cook Time | Number | Minutes | Extracted from photo or estimated |
| Servings | Number | Integer | |
| Photo URL | URL | | Cloudflare R2 presigned URL or public link |
| Tags | Multi-select | Options: `Keto`, `Kid-Friendly`, `Quick (<30min)`, `Vegetarian`, `Comfort Food`, `Soup`, `Salad`, `Pasta`, `Meat`, `Seafood` | For filtering and meal plan variety |
| Cuisine | Select | Options: `American`, `Mexican`, `Italian`, `Asian`, `Mediterranean`, `Other` | |
| Date Added | Date | | Auto-set on creation |
| Times Used | Number | Integer, default 0 | Incremented when included in a meal plan |
| Last Used | Date | | Updated when included in a meal plan |

### Cookbooks Database

| Property | Type | Configuration | Notes |
|----------|------|---------------|-------|
| Name | Title | (default) | e.g., "The Keto Cookbook", "Family Meals" |
| Description | Rich Text | | Optional notes about the cookbook |
| Recipe Count | Rollup | Count of related Recipes | Auto-calculated |

### Existing Database Changes

#### Grocery History (existing — minor additions)

| Property | Type | Change | Notes |
|----------|------|--------|-------|
| Pending Order | Checkbox | NEW | True when items pushed to AnyList but not yet confirmed ordered |
| Last Push Date | Date | NEW | When items were last pushed to AnyList (for 2-day reminder logic) |

#### Meal Plans (existing — content format change)

No schema changes. The `plan_content` block content changes from free-form text to structured format:

```
## Dinner Plan: Week of [date]

### Monday — Chicken Parmesan (from: Family Meals cookbook)
- Ingredients: [list]
- Prep: 15 min | Cook: 30 min

### Tuesday — Simple Tacos (quick meal — gymnastics day)
- Ingredients: [list]
- Prep: 10 min | Cook: 15 min

[... through Saturday]

### Eating Out: [suggested night based on schedule]

---

## Grocery List
### Whole Foods
- [ ] Item 1 (for: Chicken Parmesan)
- [ ] Item 2 (staple — due for reorder)

### Costco
- [ ] Item 3 (staple — due for reorder)
```

## Entity Relationships

```
Cookbooks ──1:N──→ Recipes
                      │
                      ├──→ (ingredients extracted) ──→ Grocery History (match by name)
                      │
                      └──→ Meal Plans (referenced in plan content)

Grocery History ──→ Reorder Suggestions (computed, ephemeral)
                      │
                      └──→ AnyList (push via sidecar)

Scheduled Workflows (n8n) ──→ FastAPI Endpoints ──→ Claude Tool Loop
```

## State Transitions

### Recipe Lifecycle

```
Photo Received → Extracting → Extracted (review) → Saved
                    │                                  │
                    └── Extraction Failed              └── Used in Meal Plan
                        (ask to re-photograph)              (Times Used++)
```

### Grocery Order Flow

```
Reorder Check → Suggestions Sent → User Approved → Pushed to AnyList
                     │                                    │
                     └── Dismissed                   ┌────┴────┐
                         (skip this week)            │         │
                                              Confirmed    No Response
                                          (update Last     (2-day reminder)
                                           Ordered)            │
                                                          ┌────┴────┐
                                                     Confirmed   Still No
                                                                 (next week
                                                                  re-suggests)
```

### Meal Plan Flow

```
Saturday Morning → Plan Generated → Sent to Erin → Erin Reviews
                                                        │
                                                   ┌────┴────┐
                                              Approves    Swaps Meals
                                                  │           │
                                                  │     Updated Plan
                                                  │           │
                                                  └─────┬─────┘
                                                        │
                                                  Grocery List
                                                  Merged & Sent
                                                        │
                                                  Push to AnyList
```

## Validation Rules

- **Recipe.Name**: Required, non-empty. Must be unique within a cookbook (same name + same cookbook = duplicate prompt).
- **Recipe.Ingredients**: Must be valid JSON array. Each element must have `name` (required), `quantity` (optional), `unit` (optional).
- **Recipe.Photo URL**: Must be a valid URL pointing to R2. Set on creation, immutable.
- **Cookbook.Name**: Required, unique. Case-insensitive matching ("keto book" matches "Keto Book").
- **Reorder threshold**: `days_since_last_order >= avg_reorder_days` for staples/regular items only (skip occasional).
- **Meal plan no-repeat window**: Must not duplicate any meal from the previous 2 meal plans in the database.
- **Grocery deduction threshold**: Items ordered within `0.5 * avg_reorder_days` are considered "in stock" and excluded from suggestions.
