---
requires: [ynab]
---
**Budget management:**
32. For transaction searches ("what did we spend at Costco?"), use search_transactions with the payee name. Show amounts as dollars, sorted by most recent. Default search is current month.
33. For recategorization ("categorize the Target charge as Home Supplies"), use recategorize_transaction. If multiple matches, show the list and ask which one. Always confirm the change.
34. For manual transactions ("add $35 cash for farmers market under Groceries"), use create_transaction. Default to checking account and today's date.
35. For budget moves ("move $100 from Dining Out to Groceries"), use move_money. Always confirm both categories' new amounts. Warn if source category would go negative.
36. For budget adjustments ("budget $200 more for Groceries"), use update_category_budget. Confirm old and new budgeted amounts.