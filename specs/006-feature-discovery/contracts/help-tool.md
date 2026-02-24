# Contract: Help & Feature Discovery Tool

## get_help

**Description**: Generate a personalized help menu showing all bot capabilities grouped by category, with example phrases using real family data where available. Use when someone says "help", "what can you do?", or similar.

**Parameters**: None

**Returns**: Formatted WhatsApp-ready text with 6 categories, each containing:
- Category icon and name
- 1-3 capability descriptions
- 1-2 example phrases (personalized from live data when available, static fallback otherwise)

**Personalization behavior**:
- Tries to fetch live data (cookbooks, budget categories, staple items) for relevant examples
- Falls back to hardcoded family-relevant examples if any tool call fails
- Never shows generic examples like "search for pizza" — always uses family context

**Example output**:
```
Here's everything I can help with! Try any of these:

🍳 *Recipes & Cooking*
Search Downshiftology for new recipes, browse your saved collection, or import favorites.
• "find me a chicken dinner recipe"
• "search for keto breakfast ideas"

💰 *Budget & Spending*
Check your YNAB budget, search transactions, or move money between categories.
• "what did we spend at Costco?"
• "how's our Groceries budget?"

📅 *Calendar & Reminders*
View upcoming events, create shared reminders, or generate your daily plan.
• "what's on our calendar this week?"
• "remind Jason to pick up dog at 12:30"

🛒 *Groceries & Meal Planning*
Generate meal plans, build grocery lists, and push to AnyList for delivery.
• "what's for dinner this week?"
• "order groceries"

🏠 *Chores & Home*
Track chores, set a laundry timer, customize preferences, or view your history.
• "started laundry"
• "what chores have I done this week?"

📋 *Family Management*
Manage action items, backlog projects, meeting agendas, and family profile.
• "what's my day look like?"
• "add to backlog: organize garage"

Just type any of these or ask me in your own words!
```
