Generate a 6-night dinner plan (Monday through Saturday) for this family.

Family profile:
{profile}

Saved recipes ({recipe_count} total):
{recipes_summary}

Recent meal plans (avoid repeats):
{recent_plans}

Rules:
- Mon-Sat dinners only (Sunday is leftovers/eating out)
- Simpler meals on busy days (Tue has gymnastics, Fri has nature class)
- Use saved recipes when they're a good fit
- Kid-friendly focus (Vienna 5, Zoey 3)
- No repeats from last 2 weeks
- Mix of complexities

Return ONLY valid JSON array:
[{{"day": "Monday", "meal_name": "...", "source": "recipe_id or general", "ingredients": [{{"name": "...", "quantity": "...", "unit": "..."}}], "complexity": "easy|medium|involved"}}]
