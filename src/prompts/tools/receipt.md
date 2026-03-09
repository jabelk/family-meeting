## process_receipt

Extract data from a receipt photo and match to an uncategorized YNAB transaction. Call this when the user sends a photo that looks like a receipt, purchase confirmation, or checkout summary. Uses OpenAI vision to read the receipt, then searches YNAB for matching uncategorized transactions and suggests a category. No parameters needed — reads the current image from the conversation.

## confirm_receipt_categorization

Confirm or override the category for a receipt matched to a YNAB transaction. Call after process_receipt when the user approves the suggested category (leave category_override empty) or provides a different one (set category_override to the new category name). Updates the YNAB transaction and saves the mapping for future use.

## retry_receipt_match

Re-check YNAB for a previously unmatched receipt. Call when the user asks to "check again" or "try matching" a receipt that had no YNAB match earlier (e.g., the transaction was pending). No parameters needed.

## split_receipt_transaction

Split a receipt's matched YNAB transaction across multiple budget categories. Call when the user wants to split a receipt (e.g., says "split" or "split it") after process_receipt identified items in different categories. Analyzes each line item, groups by category, and creates a split transaction in YNAB. No parameters needed.
