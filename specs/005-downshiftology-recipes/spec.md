# Feature Specification: Downshiftology Recipe Search

**Feature Branch**: `005-downshiftology-recipes`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Downshiftology recipe search and import — Erin can say 'I want a main course with chicken' or 'find me a quick keto dinner' via WhatsApp and get recipe recommendations from Downshiftology.com, informed by past grocery history and existing saved recipes. Results ranked by relevance with links. Option to save/import a Downshiftology recipe into the Notion catalogue for future meal planning."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search Downshiftology Recipes by Natural Language (Priority: P1)

Erin sends a natural language request to the WhatsApp bot — "I want a main course with chicken", "find me a quick keto dinner", or "what Downshiftology recipes use sweet potato?" — and the bot returns a short, scannable list of matching Downshiftology recipes with names, prep times, dietary tags, and direct links to the recipe page.

The bot interprets the request to identify relevant filters: course type (dinner, breakfast, appetizer), main ingredient (chicken, beef, salmon), dietary preference (keto, paleo, whole30, gluten-free), and time constraint (quick/30-minute). Results are ranked by relevance and presented as a numbered list so Erin can quickly scan and pick one.

**Why this priority**: This is the core value — Erin can discover healthy dinner ideas from a trusted source without leaving WhatsApp. Standalone viable: even without import or grocery integration, search results with clickable links deliver immediate value.

**Independent Test**: Send "find me a chicken dinner recipe" to the bot and verify a list of Downshiftology recipes is returned with names, prep times, and links.

**Acceptance Scenarios**:

1. **Given** Erin is in the WhatsApp chat, **When** she sends "I want a main course with chicken", **Then** the bot returns 3-5 Downshiftology recipes matching "main course" + "chicken" with name, prep time, dietary tags, and a link to each recipe.
2. **Given** Erin sends a dietary-specific request like "find me a keto dinner", **When** the bot processes the message, **Then** it filters results to recipes tagged as both keto-friendly and dinner course, returning relevant matches.
3. **Given** Erin sends a time-constrained request like "quick weeknight dinner", **When** the bot processes the message, **Then** it filters to recipes with total time under 30 minutes.
4. **Given** Erin sends a vague request like "what should I make tonight?", **When** the bot processes the message, **Then** it asks a clarifying question ("What protein or dietary preference?") or returns a curated selection of popular dinner recipes.

---

### User Story 2 - Import Downshiftology Recipe to Catalogue (Priority: P2)

After viewing search results, Erin can say "save number 3" or "import that garlic herb cod recipe" and the bot imports the full Downshiftology recipe into the family's Notion recipe catalogue. The imported recipe includes name, ingredients (with quantities), instructions, prep/cook time, servings, dietary tags, cuisine, and a link back to the original Downshiftology page.

Once saved, the recipe appears in the existing catalogue alongside cookbook recipes and is available for meal planning, grocery list generation, and future searches.

**Why this priority**: Import turns discovery into action — recipes move from a website into the family's persistent meal planning system. Without this, Erin would have to manually bookmark or re-search recipes each time.

**Independent Test**: Search for a recipe, then say "save number 2" and verify the recipe appears in the Notion Recipes database with full details and a source link.

**Acceptance Scenarios**:

1. **Given** the bot has just returned search results with numbered recipes, **When** Erin says "save number 2", **Then** the bot fetches the full recipe details and creates a new entry in the Notion recipe catalogue with name, ingredients, instructions, prep/cook time, servings, tags, cuisine, and source link.
2. **Given** Erin tries to import a recipe that already exists in the catalogue (same name and source), **When** the bot attempts to save, **Then** it detects the duplicate and informs Erin ("This recipe is already saved!") instead of creating a duplicate.
3. **Given** a recipe has been imported, **When** Erin later searches her recipe catalogue, **Then** the Downshiftology recipe appears alongside cookbook recipes in search results, distinguishable by its source attribution.

---

### User Story 3 - Smart Recommendations Using Grocery History (Priority: P3)

When Erin searches for recipes, the bot cross-references results with the family's grocery purchase history to prioritize recipes that use ingredients the family already buys regularly. Results include a note like "You usually have chicken, garlic, and olive oil on hand" to help Erin pick recipes that minimize extra shopping.

The bot can also flag when a recipe uses an uncommon ingredient the family hasn't purchased before, helping Erin decide before committing to a recipe.

**Why this priority**: Adds intelligence on top of search — moves from "here are recipes" to "here are recipes you can actually make easily." Depends on US1 working first and provides incremental value over plain search.

**Independent Test**: Search for recipes and verify that results include notes about which ingredients the family already buys, based on grocery history data.

**Acceptance Scenarios**:

1. **Given** Erin searches for "chicken dinner recipes", **When** results are returned, **Then** each result includes a match indicator showing how many key ingredients overlap with the family's recent grocery purchases (e.g., "4/6 ingredients on hand").
2. **Given** a recipe uses an ingredient the family has never purchased, **When** the recipe is displayed, **Then** uncommon ingredients are flagged (e.g., "New ingredient: tahini").
3. **Given** two recipes match the same search criteria, **When** ranking results, **Then** the recipe with more ingredients already in the family's grocery history is ranked higher.

---

### Edge Cases

- What happens when Downshiftology's website is unavailable or slow? The bot gracefully reports "Recipe search is temporarily unavailable" and suggests searching saved recipes instead.
- What happens when a search returns zero results? The bot suggests broadening the search ("No keto breakfast recipes with lamb found. Try searching for 'keto breakfast' or 'lamb dinner' instead.").
- What happens when the search query is too vague to filter? The bot asks a follow-up question to narrow down ("What type of meal? Dinner, breakfast, snack?").
- What happens when Erin says "save it" but the bot hasn't shown search results recently? The bot asks "Which recipe would you like to save? Search for one first."
- What happens when a Downshiftology recipe has incomplete data (missing cook time or ingredients)? The bot imports what's available and notes any missing fields.
- What happens when Erin asks for a recipe from a different site? The bot explains it currently searches Downshiftology only and suggests checking saved recipes or asking for a general meal idea.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST search Downshiftology's recipe catalogue by natural language queries, interpreting course type, main ingredient, dietary preference, cooking method, and time constraints.
- **FR-002**: System MUST return 3-5 recipe results per search, each showing recipe name, prep/cook time, dietary tags, and a direct link to the Downshiftology recipe page.
- **FR-003**: System MUST support filtering by course (dinner, breakfast, appetizer, etc.), cuisine (Mediterranean, Mexican, Asian, etc.), dietary label (keto, paleo, whole30, gluten-free, dairy-free, vegetarian, vegan), cooking method (30-minute, slow cooker, air fryer, one-pan), and ingredient keyword.
- **FR-004**: System MUST allow users to import a Downshiftology recipe into the Notion recipe catalogue by referencing a search result number or recipe name.
- **FR-005**: Imported recipes MUST include: name, full ingredient list with quantities, step-by-step instructions, prep time, cook time, servings, dietary tags, cuisine, and a link to the original Downshiftology page.
- **FR-006**: System MUST detect duplicate recipes before import by checking if a recipe with the same name and source already exists in the catalogue.
- **FR-007**: System MUST cross-reference recipe ingredients with the family's grocery purchase history to indicate ingredient availability (e.g., "4/6 ingredients on hand").
- **FR-008**: System MUST flag uncommon or never-purchased ingredients when displaying recipe results or details.
- **FR-009**: System MUST gracefully handle external service unavailability — if the recipe source is unreachable, inform the user and suggest alternatives (saved recipes, general meal ideas).
- **FR-010**: System MUST support follow-up interactions after search — "tell me more about number 2", "save number 3", "show me another page of results".

### Non-Functional Requirements

- **NFR-001**: Recipe search results MUST be returned within 15 seconds of the user's message.
- **NFR-002**: Recipe import MUST complete within 20 seconds, including saving to the catalogue.
- **NFR-003**: The feature MUST NOT exceed 20 external requests per user search to stay within rate-limit budgets for all integrated services.

### Key Entities

- **Downshiftology Recipe**: A recipe from Downshiftology.com — name, ingredients (with quantities and units), instructions (ordered steps), prep time, cook time, total time, servings, course type, cuisine, dietary tags, nutrition info, rating, and source URL.
- **Recipe Catalogue Entry**: An entry in the family's Notion recipe database — includes all imported recipe data plus source attribution (Downshiftology link), date imported, and usage tracking (times used, last used in meal plan).
- **Grocery Match**: A cross-reference between a recipe's ingredients and the family's grocery purchase history — indicates which ingredients are frequently purchased, which were recently bought, and which are new/uncommon.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can search for recipes and receive relevant results within 15 seconds of sending a message, at least 80% of the time.
- **SC-002**: Search results match the user's intent (correct course, dietary preference, ingredient) in at least 4 out of 5 searches as judged by the user.
- **SC-003**: Users can import a recipe from search results into the catalogue in a single follow-up message (e.g., "save number 2") with no additional steps required.
- **SC-004**: Imported recipes contain complete ingredient lists and instructions that match the source material, with no critical data loss.
- **SC-005**: Grocery history cross-referencing correctly identifies at least 70% of ingredients the family regularly purchases when comparing against recipe ingredient lists.

## Assumptions

- Downshiftology.com's public content remains freely accessible for recipe data retrieval. The site is not behind a paywall or login.
- The family's existing grocery purchase history in Notion contains sufficient data (at least 4 weeks of orders) for meaningful ingredient matching.
- Erin is the primary user of this feature. Jason may also use it but the interaction patterns are designed for Erin's workflow.
- Recipe search is limited to Downshiftology.com only. Expanding to other recipe sites is a future enhancement.
- The Notion recipe database schema may need a new "Source URL" property to distinguish imported web recipes from cookbook recipes scanned via photo.
- Dietary tag mapping between Downshiftology's taxonomy and the existing catalogue's tags will use reasonable best-fit matching (e.g., Downshiftology's "Low-Carb/Keto" maps to the catalogue's "Keto" tag).
