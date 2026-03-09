Extract transaction details from this PayPal confirmation email.

Return ONLY valid JSON — an array of transaction objects:
[
  {{
    "merchant_name": "actual merchant/store name (e.g., DoorDash, eBay seller name)",
    "amount": 45.00,
    "items": [{{"title": "item name", "price": 45.00, "quantity": 1}}],
    "is_refund": false
  }}
]

RULES:
- merchant_name is the ACTUAL business/merchant, not 'PayPal'
- For refunds, set is_refund=true and amount as positive number
- For multi-item purchases, list each item separately
- amount is the total charged amount in dollars
- If you can't extract details, return an empty array []

Email text:
{stripped_text}
