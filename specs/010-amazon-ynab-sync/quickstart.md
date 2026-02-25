# Quickstart: Amazon-YNAB Smart Sync

**Feature**: 010-amazon-ynab-sync | **Date**: 2026-02-24

## Prerequisites

1. Amazon credentials configured:
   - `AMAZON_USERNAME` — Amazon account email
   - `AMAZON_PASSWORD` — Amazon account password
   - `AMAZON_OTP_SECRET_KEY` — TOTP secret from Amazon 2FA setup (the base32 key, not the 6-digit code)
2. Existing YNAB integration working (`YNAB_ACCESS_TOKEN`, `YNAB_BUDGET_ID`)
3. Existing WhatsApp integration working
4. `amazon-orders>=4.0.18` added to requirements.txt

## Setup Steps

1. Add Amazon credentials to `.env`
2. Add `amazon-orders` to requirements.txt
3. Deploy updated container to NUC
4. Configure n8n workflow to call `/api/v1/amazon/sync` at 10pm daily
5. Make a test Amazon purchase and wait for it to appear in YNAB

## Integration Test Scenarios

### Scenario 1: Single-Item Order Match
**Setup**: Purchase one item on Amazon. Wait for charge to import into YNAB.
**Trigger**: Call `/api/v1/amazon/sync`
**Expected**:
- YNAB transaction memo updated with item name
- Item auto-categorized (single item, no confirmation needed)
- Erin receives WhatsApp: "✅ Auto-categorized: [item] → [category]"

### Scenario 2: Multi-Item Order Split Suggestion
**Setup**: Purchase 3 items in one Amazon order. Wait for charge to import.
**Trigger**: Call `/api/v1/amazon/sync`
**Expected**:
- YNAB transaction memo updated with all 3 item names
- Erin receives WhatsApp with split suggestion (amounts + categories)
- Erin replies "yes" → split applied in YNAB with per-item memos

### Scenario 3: Erin Adjusts a Suggestion
**Setup**: Same as Scenario 2, but Erin replies "adjust — put [item] in [category]"
**Expected**:
- Bot modifies the split per Erin's correction
- Split applied with corrected category
- Category mapping updated with correction

### Scenario 4: Refund Transaction
**Setup**: Return an item from a previously synced order. Wait for refund in YNAB.
**Trigger**: Nightly sync
**Expected**:
- Refund matched to original purchase
- Refund categorized to same category as original item
- Erin notified: "Refund of $X applied to [category]"

### Scenario 5: Unmatched Transaction
**Setup**: Amazon Prime membership charge or gift card reload appears in YNAB.
**Trigger**: Nightly sync
**Expected**:
- Known charge type (Prime) → auto-categorized to Subscriptions
- Unknown charge → memo tagged "Unmatched Amazon charge", Erin asked to categorize

### Scenario 6: Duplicate Prevention
**Setup**: Run sync twice on the same day with no new transactions.
**Trigger**: Call `/api/v1/amazon/sync` twice
**Expected**:
- Second run skips all already-processed transactions
- No duplicate WhatsApp messages
- No duplicate YNAB modifications

### Scenario 7: Auto-Split Graduation
**Setup**: Process 15+ suggestions over 2+ weeks with 80%+ unmodified acceptance rate.
**Expected**:
- Bot sends: "I've been getting your Amazon categories right [X]% of the time — want me to start auto-splitting?"
- Erin confirms → auto-split enabled
- Next sync applies splits automatically with summary notification

### Scenario 8: Undo Auto-Split
**Setup**: Auto-split mode is enabled. A transaction is auto-split.
**Trigger**: Erin replies "undo 1"
**Expected**:
- Split reverted to original unsplit transaction
- Original memo and category restored
- Erin can re-categorize manually

## n8n Workflow Configuration

### Nightly Sync (10pm Daily)

1. **Create new n8n workflow**: "Amazon YNAB Sync"
2. **Add Schedule Trigger node**:
   - Trigger interval: Every day
   - Hour: 22 (10pm Pacific)
3. **Add HTTP Request node**:
   - Method: POST
   - URL: `https://mombot.sierrastoryco.com/api/v1/amazon/sync`
   - Headers:
     - `X-N8N-Auth`: `{{$env.N8N_WEBHOOK_SECRET}}`
     - `Content-Type`: `application/json`
   - Timeout: 120000 (2 minutes — Amazon scraping is slow)
4. **Activate workflow**

### Manual Trigger

To test or manually trigger a sync outside the nightly schedule:
- Send a WhatsApp message: "sync my Amazon" (triggers via Claude tool)
- Or call the API directly:
  ```bash
  curl -X POST https://mombot.sierrastoryco.com/api/v1/amazon/sync \
    -H "X-N8N-Auth: $N8N_WEBHOOK_SECRET"
  ```

## Smoke Test (First Deploy)

```bash
# 1. Verify Amazon credentials work
curl -X POST https://mombot.sierrastoryco.com/api/v1/amazon/sync \
  -H "X-N8N-Auth: $N8N_WEBHOOK_SECRET"

# 2. Check logs for successful sync
./scripts/nuc.sh logs fastapi 50

# 3. Verify in YNAB that memos were updated

# 4. Check WhatsApp for Erin's notification
```
