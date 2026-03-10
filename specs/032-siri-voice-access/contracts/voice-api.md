# API Contract: Voice Message Endpoint

**Feature Branch**: `032-siri-voice-access`
**Date**: 2026-03-10

## POST /api/v1/voice/message

General-purpose voice endpoint. Accepts natural language text from Siri and returns a voice-optimized response.

### Authentication

`Authorization: Bearer <per-user-token>` header. Token maps to user identity server-side.

### Request

```json
{
  "text": "What's on the calendar tomorrow?",
  "channel": "siri"
}
```

| Field   | Type   | Required | Description                       |
|---------|--------|----------|-----------------------------------|
| text    | string | Yes      | Transcribed voice input           |
| channel | string | Yes      | `"siri"` for general voice command |

### Response (success)

HTTP 200:
```json
{
  "success": true,
  "message": "Tomorrow you have Lily's swim lessons at 10 AM and a dentist appointment at 2 PM.",
  "sent_to_whatsapp": false
}
```

### Response (success — slow, fallback to WhatsApp)

HTTP 200:
```json
{
  "success": true,
  "message": "Working on it — I'll send the details to WhatsApp.",
  "sent_to_whatsapp": true
}
```

### Response (error)

HTTP 200 (Shortcuts can't read status codes):
```json
{
  "success": false,
  "error": "I couldn't process that request right now. Try again in a moment.",
  "sent_to_whatsapp": false
}
```

### Response (auth failure)

HTTP 401:
```json
{
  "detail": "Invalid API token"
}
```

Note: Shortcuts will treat non-200 responses as a failed action. The Shortcut should have an error handling path for this case.

### Response (rate limit)

HTTP 429:
```json
{
  "detail": "Rate limit exceeded. Try again in a moment."
}
```

---

## POST /api/v1/voice/preset

Preset quick-action endpoint. Accepts a specific action type with optional parameters for optimized handling.

### Authentication

Same as `/api/v1/voice/message`.

### Request — Calendar Check

```json
{
  "channel": "preset",
  "preset_action": "calendar"
}
```

### Request — Grocery Add

```json
{
  "channel": "preset",
  "preset_action": "grocery_add",
  "text": "milk and eggs"
}
```

### Request — Dinner Question

```json
{
  "channel": "preset",
  "preset_action": "dinner"
}
```

### Request — Reminder

```json
{
  "channel": "preset",
  "preset_action": "remind",
  "text": "pick up dry cleaning tomorrow at 3"
}
```

| Field         | Type   | Required | Description                                   |
|---------------|--------|----------|-----------------------------------------------|
| channel       | string | Yes      | `"preset"` for preset Shortcuts               |
| preset_action | string | Yes      | `"calendar"`, `"grocery_add"`, `"dinner"`, `"remind"` |
| text          | string | Conditional | Required for `grocery_add` and `remind`; optional for others |

### Response

Same format as `/api/v1/voice/message`. Preset actions may produce faster responses since they can skip the classification step and route directly to the appropriate tool.

---

## Apple Shortcut Configuration

### General-Purpose Shortcut: "Run Our House"

```
Trigger: "Hey Siri, run our house"
Flow:
  1. Dictate Text → [user_input]
  2. Get Contents of URL:
     - URL: https://<server>/api/v1/voice/message
     - Method: POST
     - Headers: Authorization: Bearer <user_token>
     - Body (JSON): {"text": [user_input], "channel": "siri"}
  3. Get Dictionary Value "success" from [response]
  4. If [success] = true:
     a. Get Dictionary Value "message" from [response]
     b. Speak Text [message]
  5. Otherwise:
     a. Get Dictionary Value "error" from [response]
     b. Speak Text [error]
     c. (Fallback if no error field): Speak Text "Sorry, I couldn't reach your assistant."
```

### Preset Shortcut: "Family Calendar"

```
Trigger: "Hey Siri, family calendar"
Flow:
  1. Get Contents of URL:
     - URL: https://<server>/api/v1/voice/preset
     - Method: POST
     - Headers: Authorization: Bearer <user_token>
     - Body (JSON): {"channel": "preset", "preset_action": "calendar"}
  2. Get Dictionary Value "message" from [response]
  3. Speak Text [message]
```

### Preset Shortcut: "Grocery Add"

```
Trigger: "Hey Siri, grocery add"
Flow:
  1. Ask for Input: "What do you want to add?" → [item]
  2. Get Contents of URL:
     - URL: https://<server>/api/v1/voice/preset
     - Method: POST
     - Headers: Authorization: Bearer <user_token>
     - Body (JSON): {"channel": "preset", "preset_action": "grocery_add", "text": [item]}
  3. Get Dictionary Value "message" from [response]
  4. Speak Text [message]
```

### Preset Shortcut: "What's for Dinner"

```
Trigger: "Hey Siri, what's for dinner"
Flow:
  1. Get Contents of URL:
     - URL: https://<server>/api/v1/voice/preset
     - Method: POST
     - Headers: Authorization: Bearer <user_token>
     - Body (JSON): {"channel": "preset", "preset_action": "dinner"}
  2. Get Dictionary Value "message" from [response]
  3. Speak Text [message]
```

### Preset Shortcut: "Remind Me"

```
Trigger: "Hey Siri, remind me"
Flow:
  1. Ask for Input: "What do you want to be reminded about?" → [reminder]
  2. Get Contents of URL:
     - URL: https://<server>/api/v1/voice/preset
     - Method: POST
     - Headers: Authorization: Bearer <user_token>
     - Body (JSON): {"channel": "preset", "preset_action": "remind", "text": [reminder]}
  3. Get Dictionary Value "message" from [response]
  4. Speak Text [message]
```
