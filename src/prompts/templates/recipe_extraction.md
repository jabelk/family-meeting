Extract the recipe from this cookbook page{page_suffix}. Return ONLY valid JSON with these fields:
{{"name": "Recipe Name", "ingredients": [{{"name": "item", "quantity": "2", "unit": "cups"}}], "instructions": ["Step 1...", "Step 2..."], "prep_time": 15, "cook_time": 30, "servings": 4, "tags": ["tag1"], "cuisine": "American"}}

Rules:
- If text is unclear or cut off, include it with [unclear] marker
{multi_page_rule}
- If the image is NOT a recipe, return: {{"error": "not_a_recipe"}}
- For ingredients, always include name; quantity and unit can be empty strings if not specified
- Tags should be from: Keto, Kid-Friendly, Quick (<30min), Vegetarian, Comfort Food, Soup, Salad, Pasta, Meat, Seafood
- Cuisine should be: American, Mexican, Italian, Asian, Mediterranean, or Other
