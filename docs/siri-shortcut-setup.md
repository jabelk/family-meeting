# Siri Voice Access Setup Guide

Set up hands-free voice access to the family assistant via Apple Shortcuts and Siri.

## Prerequisites

- iPhone with iOS 15 or later
- The family assistant server running and publicly accessible
- Your server URL (e.g., `https://mombot.sierracodeco.com`)

## Step 1: Generate API Tokens

The operator (person who manages the server) generates a unique token for each partner.

**On your computer (or in Railway shell):**

```bash
# Partner 1 token
python3 -c "import secrets; print('sc_p1_' + secrets.token_hex(32))"

# Partner 2 token
python3 -c "import secrets; print('sc_p2_' + secrets.token_hex(32))"
```

Save both tokens — you'll need them for the Shortcuts and the server config.

## Step 2: Add Tokens to Server Environment

Add these environment variables to your Railway deployment (or `.env` file):

```
PARTNER1_API_TOKEN=sc_p1_<your-generated-token>
PARTNER2_API_TOKEN=sc_p2_<your-generated-token>
```

Restart the server after adding the variables.

**Verify:** After restart, the `/health` endpoint should show `voice_access: configured: true`.

## Step 3: Create the "Run Our House" Shortcut

This is the general-purpose Shortcut. Say "Hey Siri, run our house" to ask the assistant anything.

### On each partner's iPhone:

1. Open the **Shortcuts** app
2. Tap **+** to create a new Shortcut
3. Tap the name field at the top — name it **"Run Our House"**
4. Add these actions in order:

**Action 1: Dictate Text**
- Search for "Dictate Text" and add it
- This captures what you say after Siri activates

**Action 2: Get Contents of URL**
- Search for "Get Contents of URL" and add it
- **URL:** `https://<your-server>/api/v1/voice/message`
- Tap **Show More** and configure:
  - **Method:** POST
  - **Headers:** Add a header:
    - Key: `Authorization`
    - Value: `Bearer <partner's-token>` (use the token for this specific partner)
  - **Request Body:** JSON
    - Add field `text` → set to the **Dictated Text** variable (tap the variable pill)
    - Add field `channel` → set to text `siri`

**Action 3: Get Dictionary Value**
- Search for "Get Dictionary Value" and add it
- Get value for key: `success`
- From: **Contents of URL** (the previous action's output)

**Action 4: If**
- Search for "If" and add it
- Condition: **Dictionary Value** *is* `1` (or `true`)

**Action 5 (inside If):** Get Dictionary Value
- Key: `message`
- From: **Contents of URL**

**Action 6 (inside If):** Speak Text
- Speak: **Dictionary Value** (the message)

**Action 7 (inside Otherwise):** Speak Text
- Speak: `"Sorry, I couldn't reach your assistant right now. Try again in a moment."`

**Action 8:** End If

5. Tap **Done**

### Test it:
Say **"Hey Siri, run our house"** → speak a request like "What's on the calendar tomorrow?" → hear the response.

---

## Step 4: Create Preset Shortcuts

These are faster, single-purpose Shortcuts for the most common tasks.

### "Family Calendar"

**Trigger phrase:** "Hey Siri, family calendar"

1. Create a new Shortcut named **"Family Calendar"**
2. Add **Get Contents of URL**:
   - URL: `https://<your-server>/api/v1/voice/preset`
   - Method: POST
   - Header: `Authorization: Bearer <token>`
   - Body (JSON): `channel` = `preset`, `preset_action` = `calendar`
3. Add **Get Dictionary Value**: key `message` from Contents of URL
4. Add **Speak Text**: speak the Dictionary Value

### "Grocery Add"

**Trigger phrase:** "Hey Siri, grocery add"

1. Create a new Shortcut named **"Grocery Add"**
2. Add **Ask for Input**: "What do you want to add?"
3. Add **Get Contents of URL**:
   - URL: `https://<your-server>/api/v1/voice/preset`
   - Method: POST
   - Header: `Authorization: Bearer <token>`
   - Body (JSON): `channel` = `preset`, `preset_action` = `grocery_add`, `text` = Provided Input
4. Add **Get Dictionary Value**: key `message` from Contents of URL
5. Add **Speak Text**: speak the Dictionary Value

### "What's for Dinner"

**Trigger phrase:** "Hey Siri, what's for dinner"

1. Create a new Shortcut named **"What's for Dinner"**
2. Add **Get Contents of URL**:
   - URL: `https://<your-server>/api/v1/voice/preset`
   - Method: POST
   - Header: `Authorization: Bearer <token>`
   - Body (JSON): `channel` = `preset`, `preset_action` = `dinner`
3. Add **Get Dictionary Value**: key `message` from Contents of URL
4. Add **Speak Text**: speak the Dictionary Value

### "Remind Me"

**Trigger phrase:** "Hey Siri, remind me"

1. Create a new Shortcut named **"Remind Me"**
2. Add **Ask for Input**: "What do you want to be reminded about?"
3. Add **Get Contents of URL**:
   - URL: `https://<your-server>/api/v1/voice/preset`
   - Method: POST
   - Header: `Authorization: Bearer <token>`
   - Body (JSON): `channel` = `preset`, `preset_action` = `remind`, `text` = Provided Input
4. Add **Get Dictionary Value**: key `message` from Contents of URL
5. Add **Speak Text**: speak the Dictionary Value

---

## Step 5: Physical Triggers (Optional)

### Back Tap (iPhone 8+)

Triple-tap the back of your iPhone to launch the assistant Shortcut.

1. Go to **Settings > Accessibility > Touch > Back Tap**
2. Tap **Triple Tap**
3. Scroll down to **Shortcuts** and select **"Run Our House"**

> Recommended: Use triple-tap (not double-tap) to avoid accidental triggers.

### Action Button (iPhone 15 Pro+)

Press and hold the Action Button to launch the assistant.

1. Go to **Settings > Action Button**
2. Scroll to **Shortcut**
3. Select **"Run Our House"**

### Lock Screen Widget

Add a Shortcuts widget to your lock screen for one-tap access.

1. Long-press the lock screen → tap **Customize**
2. Tap the widget area below the time
3. Add the **Shortcuts** widget
4. Configure it to show **"Run Our House"**

---

## Troubleshooting

### "I couldn't reach your assistant"
- Check that the server is running: visit `https://<your-server>/health`
- Verify the token is correct in the Shortcut's Authorization header
- Make sure `PARTNER1_API_TOKEN` or `PARTNER2_API_TOKEN` is set in the server's environment

### Shortcut times out (spins for 25 seconds)
- This means the assistant is taking too long. For complex requests, you'll hear "Working on that — I'll send the answer to WhatsApp."
- If it happens on simple requests, check server logs for errors

### "Invalid API token" error
- The Bearer token in the Shortcut doesn't match what's configured on the server
- Regenerate the token and update both the server env var and the Shortcut

### Siri says "Sorry, there was a problem with the app"
- Make sure the Shortcut name is simple (no special characters)
- Try saying "Hey Siri, run our house" more clearly
- Check that the Shortcut runs correctly when tapped manually in the Shortcuts app

### Rate limiting
- The server allows 5 requests per 60 seconds per user
- If you're getting rate limited, wait a moment and try again

---

## Testing with curl

You can test the voice endpoints directly:

```bash
# General voice command
curl -X POST https://<server>/api/v1/voice/message \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"text":"What is on the calendar tomorrow?","channel":"siri"}'

# Preset: calendar
curl -X POST https://<server>/api/v1/voice/preset \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"channel":"preset","preset_action":"calendar"}'

# Preset: grocery add
curl -X POST https://<server>/api/v1/voice/preset \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"channel":"preset","preset_action":"grocery_add","text":"milk and bananas"}'
```

Expected response format:
```json
{
  "success": true,
  "message": "Tomorrow you have swim lessons at 10 and a playdate at 1.",
  "error": null,
  "sent_to_whatsapp": false
}
```
