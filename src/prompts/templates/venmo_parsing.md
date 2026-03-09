Extract transaction details from this Venmo notification email.

Return ONLY valid JSON — an array of transaction objects:
[
  {{
    "merchant_name": "recipient or sender name (e.g., Sarah M., Pizza Palace)",
    "amount": 30.00,
    "payment_note": "the payment note/description (e.g., dinner split, rent)",
    "direction": "sent or received",
    "is_refund": false
  }}
]

RULES:
- merchant_name is the person or business name, not 'Venmo'
- payment_note is the note the sender included with the payment
- direction: 'sent' if user paid someone, 'received' if user got paid
- For business payments, use the business name as merchant_name
- amount is always positive (in dollars)
- If you can't extract details, return an empty array []

Email text:
{stripped_text}
