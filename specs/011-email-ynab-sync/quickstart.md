# Quickstart: Email-YNAB Smart Sync (PayPal, Venmo, Apple)

**Feature**: 011-email-ynab-sync | **Date**: 2026-02-25

## Prerequisites

1. Gmail API OAuth configured (already set up for Feature 010 — Amazon sync):
   - Gmail read-only scope (`gmail.readonly`) already authorized
   - `credentials.json` and `token.json` present in project root
   - PayPal/Venmo/Apple confirmation emails arrive at `jbelk122@gmail.com`
2. Existing YNAB integration working (`YNAB_ACCESS_TOKEN`, `YNAB_BUDGET_ID`)
3. Existing WhatsApp integration working
4. Feature 010 (Amazon-YNAB sync) deployed and operational

## Setup Steps

1. Deploy updated container to NUC (new `email_sync.py` module)
2. Configure n8n workflow to call `/api/v1/email/sync` at 10:05pm daily (5 min after Amazon sync)
3. Verify by making a PayPal purchase and waiting for next sync

## Integration Test Scenarios

### Scenario 1: PayPal Single-Item Transaction
**Setup**: Make a PayPal purchase (e.g., DoorDash). Wait for charge to import into YNAB with payee "PayPal".
**Trigger**: Call `POST /api/v1/email/sync`
**Expected**:
- YNAB transaction memo updated with "DoorDash via PayPal"
- Erin receives WhatsApp with category suggestion (e.g., "Eating Out")
- Erin replies "yes" → category applied in YNAB

### Scenario 2: Apple Subscription (Recurring)
**Setup**: Apple iCloud+ subscription charges $12.99 and imports into YNAB as "APPLE.COM/BILL".
**Trigger**: Nightly sync
**Expected**:
- Memo updated with "iCloud+ 200GB"
- If first time: suggestion sent to Erin for approval
- If previously approved: auto-categorized to "Subscriptions" (recurring charge detection)
- Summary: "Auto-categorized: $12.99 iCloud+ → Subscriptions"

### Scenario 3: Venmo Person-to-Person Payment
**Setup**: Send $30 via Venmo to Sarah with note "dinner split". Wait for YNAB import with payee "Venmo".
**Trigger**: Nightly sync
**Expected**:
- Memo updated with "To Sarah M. — dinner split"
- Erin receives category suggestion based on payment note
- If note is vague (e.g., "thanks"), flagged for Erin with recipient name and amount

### Scenario 4: PayPal Multi-Item Purchase
**Setup**: Make an eBay purchase via PayPal with 3 items in one transaction.
**Trigger**: Call `POST /api/v1/email/sync`
**Expected**:
- Email parsed for all 3 items with individual prices
- Split suggestion sent to Erin (amounts + categories per item)
- Erin replies "yes" → YNAB transaction split with per-item memos

### Scenario 5: Refund Detection
**Setup**: Receive a PayPal refund for a previously synced transaction.
**Trigger**: Nightly sync
**Expected**:
- Refund matched to original purchase by amount and date proximity
- Categorized to same category as original charge
- Erin notified: "Refund of $X from [merchant] applied to [category]"

### Scenario 6: Unmatched Transaction
**Setup**: A PayPal charge appears in YNAB but no matching email exists (e.g., Erin's separate PayPal account, or PayPal instant transfer).
**Trigger**: Nightly sync
**Expected**:
- Memo tagged with "Unmatched PayPal charge"
- Erin asked to categorize via WhatsApp

### Scenario 7: No New Transactions (Silent)
**Setup**: No new PayPal/Venmo/Apple transactions today.
**Trigger**: Nightly sync
**Expected**:
- Sync completes silently, no WhatsApp message
- Logs show "no new transactions to process"

### Scenario 8: Duplicate Prevention
**Setup**: Run sync twice on same day with no new transactions.
**Trigger**: Call `/api/v1/email/sync` twice
**Expected**:
- Second run skips all already-processed transactions
- No duplicate WhatsApp messages or YNAB modifications

### Scenario 9: Auto-Categorize Graduation
**Setup**: Process 15+ email suggestions over 2+ weeks with 80%+ acceptance rate.
**Expected**:
- Bot suggests enabling auto-categorize mode
- Erin confirms → auto-categorize enabled for email providers
- Known recurring charges and previously approved merchants auto-categorized

### Scenario 10: Cross-Provider Category Learning
**Setup**: Erin approves "DoorDash → Eating Out" from a PayPal transaction. Later DoorDash appears via Venmo.
**Trigger**: Nightly sync
**Expected**:
- DoorDash via Venmo auto-categorized to "Eating Out" (learned from PayPal approval)
- Shared category mapping works across providers

## n8n Workflow Configuration

### Email Sync (10:05pm Daily)

1. **Create new n8n workflow**: "Email YNAB Sync"
2. **Add Schedule Trigger node**:
   - Trigger interval: Every day
   - Hour: 22, Minute: 5 (10:05pm Pacific — 5 min after Amazon sync)
3. **Add HTTP Request node**:
   - Method: POST
   - URL: `http://fastapi:8000/api/v1/email/sync`
   - Headers:
     - `X-N8N-Auth`: `{{$env.N8N_WEBHOOK_SECRET}}`
     - `Content-Type`: `application/json`
   - Timeout: 300000 (5 minutes — multiple provider email fetch + parsing)
4. **Activate workflow**

### Manual Trigger

To test or manually trigger a sync outside the nightly schedule:
- Send a WhatsApp message: "sync my emails" or "check PayPal/Venmo/Apple" (triggers via Claude tool)
- Or call the API directly:
  ```bash
  curl -X POST https://mombot.sierrastoryco.com/api/v1/email/sync \
    -H "X-N8N-Auth: $N8N_WEBHOOK_SECRET"
  ```

## Smoke Test (First Deploy)

```bash
# 1. Verify email sync can fetch provider emails
curl -X POST https://mombot.sierrastoryco.com/api/v1/email/sync \
  -H "X-N8N-Auth: $N8N_WEBHOOK_SECRET"

# 2. Check logs for successful sync
./scripts/nuc.sh logs fastapi 50

# 3. Verify in YNAB that memos were updated for any PayPal/Venmo/Apple transactions

# 4. Check WhatsApp for Erin's notification (if transactions found)
```
