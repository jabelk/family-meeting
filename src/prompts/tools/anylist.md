## get_grocery_history

Get grocery purchase history from past Whole Foods orders. Use when planning meals to reference what the family actually buys. Can filter by category.

## get_staple_items

Get frequently purchased grocery items (staples). Suggest these when generating grocery lists — the family probably needs them every week.

## push_grocery_list

Push grocery list items to AnyList for Whole Foods delivery. Clears old items first, then adds the new list. Erin opens AnyList -> 'Order Pickup or Delivery' -> Whole Foods. If the service is unavailable, returns an error and you should send a formatted list via WhatsApp instead.
