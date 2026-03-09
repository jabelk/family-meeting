Extract ALL order details from this Amazon order confirmation email.
IMPORTANT: One email may contain MULTIPLE separate orders, each with its own order number and Grand Total. Extract each one.

CRITICAL RULES:
- Order numbers are in format ###-#######-####### (e.g., 112-1730641-1221858). Extract EXACTLY as shown — do NOT invent numbers.
- grand_total is the 'Grand Total:' amount shown for EACH order. This includes tax and shipping — it's what gets charged to the card.
- Item prices may appear as '$ 24 99' meaning $24.99. Convert to decimal.
- If you cannot find a field, set it to null — do NOT guess.

Return ONLY a valid JSON array of orders:
[
  {{
    "order_number": "###-#######-#######",
    "grand_total": 41.08,
    "items": [
      {{"title": "exact product name from email", "price": 24.99, "quantity": 1}}
    ]
  }}
]

Email text:
{clean_text}
