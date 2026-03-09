# WhatsApp Business Number Provisioning Guide

This guide covers provisioning a WhatsApp Business phone number via Meta's Direct Cloud API for a new client deployment. It is written for operators, not end users.

> **Scaling path**: Direct Cloud API works well for 1-10 client deployments. At 10-50 clients, consider migrating to Twilio ISV. At 50+ clients, apply for Meta Tech Provider status. This guide covers Direct Cloud API only.

**Time estimate**: 1-2 hours (plus 1-7 business days for business verification).

---

## Prerequisites

Before starting, confirm you have the following:

1. **Facebook Business Manager account** at [business.facebook.com](https://business.facebook.com)
   - Must be a Business Manager, not a personal Facebook account
   - The account owner (operator or client) must have admin access

2. **Business verification status**: Your Business Manager must complete Meta's business verification process. This requires:
   - Legal business name and address
   - Business registration documents (articles of incorporation, utility bill, or tax filing)
   - A business website with a matching domain
   - Phone number that can receive a verification call/SMS

3. **A dedicated phone number**: You need a phone number that:
   - Is not currently registered with any WhatsApp account (personal or business)
   - Can receive SMS or voice calls for one-time verification
   - Will be used exclusively for this client's assistant (no sharing across deployments)

4. **A public HTTPS domain**: The webhook endpoint must be reachable at `https://{your-domain}/webhook`. This is provided by Railway (public domain) or Cloudflare Tunnel (NUC deployment).

> **Note:** If the client's phone number is currently registered with WhatsApp, they must delete their WhatsApp account from that number first. WhatsApp numbers cannot be registered to both a personal account and a Business API account simultaneously.

---

## Step 1: Create a Meta Developer App

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Log in with the Facebook account linked to your Business Manager
3. Click **"My Apps"** (top-right) then **"Create App"**
4. Select app type: **"Business"**
5. Fill in:
   - **App name**: Something identifiable per client (e.g., "Smith Family Assistant")
   - **App contact email**: Operator's email
   - **Business Manager**: Select the correct Business Manager account
6. Click **"Create App"**
7. On the app dashboard, find **"WhatsApp"** in the product list and click **"Set Up"**

---

## Step 2: Create a WhatsApp Business Account

If you do not already have a WhatsApp Business Account (WABA) linked to this Business Manager:

1. In the Meta developer dashboard, go to **WhatsApp** > **Getting Started**
2. Meta will prompt you to create a WhatsApp Business Account or select an existing one
3. Fill in the business display name (this is what recipients see in the chat header)
4. Select the business category that best fits (e.g., "Professional Services" or "Other")
5. Accept the WhatsApp Business Terms of Service

> **Important:** The display name must comply with Meta's [display name guidelines](https://www.facebook.com/business/help/338047025165344). It should reflect the actual business or service name, not a generic description. For example, "Smith Family Helper" is acceptable; "AI Chatbot" is not.

---

## Step 3: Add a Phone Number

1. In the developer dashboard, go to **WhatsApp** > **Getting Started**
2. Under **"Step 1: Select phone numbers"**, click **"Add phone number"**
3. Enter the dedicated phone number (with country code, e.g., +1 555 123 4567)
4. Choose verification method: **SMS** or **Voice call**
5. Enter the verification code when it arrives
6. Once verified, note the following values from the dashboard:
   - **Phone Number ID** (a numeric string like `123456789012345`)
   - **WhatsApp Business Account ID** (a numeric string)

> **Note:** Meta also provides a free test phone number for development. Do not use this for production -- it has sending limits, cannot receive messages from unregistered numbers, and the number changes periodically. Always provision a real number for client deployments.

---

## Step 4: Generate a Permanent System User Access Token

The temporary token shown on the Getting Started page expires in 24 hours. You need a permanent token via a System User.

1. Go to [business.facebook.com/settings](https://business.facebook.com/settings)
2. Navigate to **"Users"** > **"System users"**
3. Click **"Add"** to create a new system user:
   - **Name**: `family-assistant-api` (or similar)
   - **Role**: **Admin**
4. Click **"Create System User"**
5. Now assign the WhatsApp app to this system user:
   - Click the system user you just created
   - Click **"Add Assets"**
   - Select **"Apps"** in the left column
   - Find your app (e.g., "Smith Family Assistant") and toggle it on
   - Set permission level to **"Full Control"**
   - Click **"Save Changes"**
6. Generate the token:
   - Click **"Generate New Token"**
   - Select your app from the dropdown
   - Set token expiration to **"Never"**
   - Select these permissions:
     - `whatsapp_business_messaging` (required -- send and receive messages)
     - `whatsapp_business_management` (required -- manage phone numbers and profiles)
   - Click **"Generate Token"**
7. **Copy the token immediately** -- it is shown only once
8. Store it securely. This becomes the `WHATSAPP_ACCESS_TOKEN` environment variable.

> **Warning:** If you lose this token, you must generate a new one and update the environment variable in your deployment. There is no way to retrieve an existing token after the dialog is closed.

---

## Step 5: Configure the Webhook

The webhook tells Meta where to deliver incoming messages.

1. In the developer dashboard, go to **WhatsApp** > **Configuration**
2. Under **"Webhook"**, click **"Edit"**
3. Set:
   - **Callback URL**: `https://{your-domain}/webhook`
   - **Verify Token**: A custom string you choose (this becomes `WHATSAPP_VERIFY_TOKEN`)
4. Click **"Verify and Save"**

Meta will send a GET request to your callback URL with a `hub.verify_token` parameter. Your server must:
- Check that `hub.verify_token` matches your `WHATSAPP_VERIFY_TOKEN`
- Respond with the `hub.challenge` value from the request

> **Note:** Your server must be running and publicly accessible before you can complete this step. Deploy first, then configure the webhook.

### How verification works

When you click "Verify and Save", Meta sends:

```
GET https://{your-domain}/webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=CHALLENGE_STRING
```

The FastAPI app handles this automatically at the `GET /webhook` endpoint. It validates the verify token and echoes back the challenge string.

---

## Step 6: Subscribe to Webhook Fields

After the webhook URL is verified:

1. Still on the **Configuration** page, scroll to **"Webhook fields"**
2. Click **"Manage"**
3. Subscribe to the following fields:
   - **`messages`** -- incoming messages (text, media, voice notes, reactions, etc.)
   - **`message_templates`** -- status updates when message templates are approved/rejected (only needed if you use template messages for proactive outreach)
4. Click **"Done"**

The `messages` subscription is the critical one. Without it, your server will never receive incoming messages even though the webhook URL is verified.

---

## Step 7: Set Environment Variables

With all values collected, set the following environment variables in your deployment:

```bash
# Railway
railway variables set WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
railway variables set WHATSAPP_ACCESS_TOKEN=your-permanent-system-user-token
railway variables set WHATSAPP_VERIFY_TOKEN=your-chosen-verify-string
railway variables set WHATSAPP_APP_SECRET=your-meta-app-secret

# Or for NUC: add to .env file
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_ACCESS_TOKEN=your-permanent-system-user-token
WHATSAPP_VERIFY_TOKEN=your-chosen-verify-string
WHATSAPP_APP_SECRET=your-meta-app-secret
```

Where to find the **App Secret**:
1. Go to the Meta developer dashboard
2. Select your app
3. Go to **Settings** > **Basic**
4. Click **"Show"** next to **App Secret**
5. Copy the value

The App Secret is used to validate that incoming webhook payloads genuinely originate from Meta (signature verification).

---

## Step 8: Test End-to-End

1. **Health check**: Verify the server is running:
   ```bash
   curl https://{your-domain}/health
   # Expected: {"status":"ok"}
   ```

2. **Send a test message**: From a personal WhatsApp account (one of the family phone numbers configured in the environment), send a message to the business number:
   ```
   help
   ```

3. **Verify the response**: The assistant should reply with a help message listing available features.

4. **Check logs** if no response arrives:
   ```bash
   # Railway
   railway logs

   # NUC
   ./scripts/nuc.sh logs fastapi 50
   ```

5. **Verify webhook delivery** in the Meta dashboard:
   - Go to **WhatsApp** > **Configuration** > **Webhook**
   - Recent deliveries should show `200` status codes

---

## Troubleshooting

### Business verification rejected

Meta may reject business verification for several reasons:

- **Document mismatch**: The business name on submitted documents must match the name in Business Manager exactly. Minor differences (LLC vs Inc, abbreviations) can cause rejection.
- **Unacceptable documents**: Meta requires official government documents. Screenshots, self-created documents, or documents in a language Meta cannot verify are rejected.
- **Website issues**: The business website must be live, match the business name, and have a privacy policy.

**Resolution**:
1. Check the rejection reason in Business Manager under **Security Center** > **Verification**
2. Correct the issue and resubmit
3. Allow 1-7 business days for re-review
4. If repeatedly rejected, contact Meta Business Support through the Business Help Center

### Webhook not receiving messages

If the webhook URL is verified but no messages arrive:

1. **Check webhook field subscriptions**: Go to **Configuration** > **Webhook fields** and confirm `messages` is subscribed (green checkmark).
2. **Check the app is in Live mode**: In the developer dashboard, check the toggle at the top of the page. If the app is in **Development** mode, only phone numbers registered as testers can send messages. Switch to **Live** mode or add the sender as a tester.
3. **Check server logs**: Look for incoming requests at the `/webhook` POST endpoint. If no requests appear, the issue is on Meta's side.
4. **Verify phone number status**: Go to **WhatsApp** > **Phone Numbers**. The number should show status "Connected". If it shows "Pending" or "Disconnected", the number verification may have failed.
5. **Check for IP restrictions**: If your server has firewall rules, Meta's webhook requests come from a range of IPs. Meta does not publish a fixed list; do not restrict by IP.

### Rate limits and messaging tier escalation

Meta enforces messaging tiers for business-initiated conversations:

| Tier | Limit | How to reach |
|------|-------|--------------|
| Unverified | 250 conversations / 24h | Default |
| Tier 1 | 1,000 conversations / 24h | Complete business verification |
| Tier 2 | 10,000 conversations / 24h | Maintain quality, reach 2x current limit |
| Tier 3 | 100,000 conversations / 24h | Maintain quality, reach 2x current limit |
| Unlimited | No limit | Maintain quality, reach Tier 3 |

For a family management service (single-family deployment), you will almost never approach these limits. A single family generates at most a few dozen conversations per day.

**User-initiated conversations** (where the user messages first) have no tier limits. The 24-hour messaging window starts when the user sends a message.

> **Note:** If the assistant needs to initiate contact outside the 24-hour window (e.g., daily briefings, reminders), it must use pre-approved **message templates**. Templates require Meta review and approval, which takes 1-2 business days.

### Phone number quality rating

Meta assigns a quality rating to each phone number based on user feedback:

- **Green (High)**: Normal operation
- **Yellow (Medium)**: Warning -- users may be reporting or blocking your messages
- **Red (Low)**: Risk of restriction -- Meta may reduce your messaging tier

**To maintain high quality**:
- Only message users who have opted in (family members who joined the group)
- Keep messages relevant and useful
- Do not send excessive messages (the assistant has built-in rate limiting)
- Respond to user messages promptly (the assistant handles this automatically)

Check your quality rating at **WhatsApp** > **Phone Numbers** > click the number > **Insights**.

### "AI chatbot" policy compliance

As of Meta's January 2026 policy update, WhatsApp Business accounts used as "AI chatbots" face additional review and potential restrictions.

**Position the service correctly**:
- Describe it as a **"family management service"** or **"family scheduling assistant"** in all Meta-facing contexts (app description, business description, display name)
- Do not use terms like "AI chatbot", "AI agent", or "GPT" in the WhatsApp Business profile or display name
- The business category should be "Professional Services", "Lifestyle", or "Other" -- not "Technology"
- In the WhatsApp Business profile description, emphasize the service aspect: "Helps families manage calendars, meals, budgets, and groceries"

**What to avoid**:
- Do not mention AI, machine learning, or language models in the business profile
- Do not set the display name to anything containing "AI", "Bot", "GPT", or "Claude"
- Do not send messages that explicitly say "I am an AI" -- the assistant's system prompt already handles this appropriately by focusing on helpfulness rather than identity

> **Important:** This is not about deception -- Meta's policy targets generic AI chatbot services, not domain-specific business tools. A family management service that happens to use AI internally is categorically different from a general-purpose AI chatbot. Frame it accurately as what it is: a service that manages family logistics.

---

## Environment Variable Reference

| Variable | Source | Required |
|----------|--------|----------|
| `WHATSAPP_PHONE_NUMBER_ID` | Developer dashboard > WhatsApp > Getting Started | Yes |
| `WHATSAPP_ACCESS_TOKEN` | System User permanent token (Step 4) | Yes |
| `WHATSAPP_VERIFY_TOKEN` | Operator-chosen string (any random string) | Yes |
| `WHATSAPP_APP_SECRET` | Developer dashboard > Settings > Basic > App Secret | Yes |

---

## Appendix: Phone Number Options

### Option A: Buy a number through Meta

Meta partners with phone number providers. In some regions, you can purchase a number directly through the WhatsApp Business Platform setup flow. This is the simplest option when available.

### Option B: Use an existing landline or mobile number

You can register any phone number you own, including:
- A dedicated mobile SIM (recommended for simplicity)
- A VoIP number (e.g., Google Voice, Twilio) -- must be able to receive SMS or calls
- A landline -- Meta will call it with a voice verification code

### Option C: Use a virtual number provider

Services like Twilio, Vonage, or Telnyx can provide dedicated phone numbers. The number must be able to receive at least one SMS or voice call for initial verification. After verification, all messaging goes through the API -- the number does not need to remain active for calls.

> **Recommendation:** For client deployments, use a dedicated mobile SIM or a Twilio number. This ensures the number is stable, verifiable, and not tied to any personal account.
