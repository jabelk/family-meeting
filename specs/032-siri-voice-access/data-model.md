# Data Model: Siri Voice Access

**Feature Branch**: `032-siri-voice-access`
**Date**: 2026-03-10

## Entities

### VoiceRequest (inbound)

Represents a voice-initiated request from an Apple Shortcut to the assistant server.

| Field          | Type     | Description                                         | Constraints                       |
|----------------|----------|-----------------------------------------------------|-----------------------------------|
| text           | string   | Transcribed voice input from Siri/Dictate Text      | Required for /voice/message and preset grocery_add/remind; optional for preset calendar/dinner. Max 1000 chars |
| channel        | string   | Source channel identifier (request: "siri" or "preset"; logged as "siri" or "preset:\<action\>") | Required, enum: "siri", "preset"  |
| preset_action  | string   | Preset Shortcut action type (if channel is "preset") | Optional, enum: "calendar", "grocery_add", "dinner", "remind" |

Identity is derived from the Bearer token — not passed in the request body.

### VoiceResponse (outbound)

Represents the assistant's response formatted for Shortcut consumption.

| Field            | Type    | Description                                              | Constraints                |
|------------------|---------|----------------------------------------------------------|----------------------------|
| success          | boolean | Whether the request was processed successfully            | Required                   |
| message          | string  | Voice-optimized response text (for Siri Speak Text)       | Required, max ~150 words   |
| error            | string  | Error description (when success is false)                 | Optional                   |
| sent_to_whatsapp | boolean | Whether a longer response was sent to WhatsApp fallback   | Required, default false    |

### ShortcutToken (configuration)

Per-user API tokens mapping to family member identity.

| Field       | Type   | Description                              | Constraints                        |
|-------------|--------|------------------------------------------|------------------------------------|
| token       | string | Bearer token value                       | Required, format: `sc_p{N}_{hex}`  |
| phone       | string | Phone number of the associated user      | Required, must exist in PHONE_TO_NAME |
| partner_num | int    | Partner number (1 or 2)                  | Required, 1 or 2                   |

Stored as env vars `PARTNER1_API_TOKEN` / `PARTNER2_API_TOKEN`. Mapped to phone numbers at startup.

## Relationships

```
ShortcutToken --[authenticates]--> VoiceRequest --[produces]--> VoiceResponse
                                        |
                                        v
                                  handle_message()  (existing assistant pipeline)
                                        |
                                        v
                              ConversationLog  (existing, with channel annotation)
```

## State Transitions

VoiceRequest processing has two paths:

```
Request received
    ├── Fast path (response within ~18s)
    │       └── Return VoiceResponse with full message
    │
    └── Slow path (response exceeds ~18s)
            ├── Return VoiceResponse with acknowledgment message
            └── Continue processing → send result to WhatsApp
```

## Changes to Existing Entities

### ConversationLog (existing — annotation only)

The existing conversation logging mechanism needs a `channel` annotation to distinguish voice-initiated interactions from WhatsApp messages. The specific implementation (metadata field, log prefix, etc.) is left to the implementation phase.

Required annotations:
- `"whatsapp"` — existing WhatsApp messages (default, no change)
- `"siri"` — general voice command via Siri Shortcut
- `"preset:<action>"` — preset Shortcut with specific action type
