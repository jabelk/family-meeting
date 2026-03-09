## email_sync_trigger

Manually trigger an email-YNAB sync to fetch recent PayPal, Venmo, and Apple confirmation emails, match them to YNAB transactions, enrich memos with actual merchant/service names, classify into budget categories, and send suggestions. Use when Erin says 'sync my emails', 'check PayPal', 'categorize Venmo', 'what was that Apple charge?', or similar.

## email_sync_status

Get the current email-YNAB sync status including: last sync time, transactions processed by provider (PayPal/Venmo/Apple), acceptance rate, and whether auto-categorize mode is enabled. Use when Erin asks about email sync, PayPal/Venmo/Apple categorization stats.

## email_set_auto_categorize

Enable or disable email sync auto-categorize mode. When enabled, PayPal/Venmo/Apple purchases are automatically categorized without confirmation. Requires 80%+ acceptance rate over 10+ suggestions and 2 weeks of use. Use when Erin says 'yes' to the auto-categorize graduation prompt, or 'turn off auto-categorize for emails'.

## email_undo_categorize

Undo a recent email sync auto-categorization, reverting the transaction to its original state. Use when Erin says 'undo' or 'undo 1' after an email sync auto-categorize notification.
