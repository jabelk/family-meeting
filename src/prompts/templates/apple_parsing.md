Extract transaction details from this Apple receipt/billing email.

Return ONLY valid JSON — an array of transaction objects:
[
  {{
    "merchant_name": "actual service/app name (e.g., iCloud+ 200GB, Apple Music, Clash of Clans)",
    "amount": 12.99,
    "is_refund": false
  }}
]

RULES:
- merchant_name is the ACTUAL subscription/app name, not 'Apple' or 'APPLE.COM/BILL'
- For iCloud, include the storage tier (e.g., 'iCloud+ 200GB')
- For App Store purchases, include the app name
- For refunds, set is_refund=true and amount as positive number
- One receipt may contain multiple subscriptions or purchases
- amount is in dollars
- If you can't extract details, return an empty array []

Email text:
{stripped_text}
