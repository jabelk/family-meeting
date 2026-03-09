## amazon_sync_status

Get the current Amazon-YNAB sync status including: last sync time, transactions processed, match rate, acceptance rate, and whether auto-split mode is enabled. Use when Erin asks about Amazon sync, categorization stats, or 'how is the Amazon sync doing?'.

## amazon_sync_trigger

Manually trigger an Amazon-YNAB sync to fetch recent Amazon orders, match them to YNAB transactions, enrich memos with item names, classify items into budget categories, and send split suggestions. Use when Erin says 'sync my Amazon', 'check Amazon orders', or 'categorize Amazon purchases'.

## amazon_spending_breakdown

Get a breakdown of Amazon spending by YNAB category for a given month, with budget comparisons and top purchases. Use when Erin asks 'how are we doing on Amazon spending?', 'Amazon spending breakdown', or 'what are we buying on Amazon?'.

## amazon_set_auto_split

Enable or disable Amazon auto-split mode. When enabled, Amazon purchases are automatically split into YNAB categories without confirmation. Requires 80%+ acceptance rate over 10+ suggestions. Use when Erin says 'yes' to the auto-split graduation prompt, or 'turn off auto-split'.

## amazon_undo_split

Undo a recent Amazon auto-split transaction, reverting it to its original unsplit state. Use when Erin says 'undo' or 'undo 1' after an auto-split notification.
