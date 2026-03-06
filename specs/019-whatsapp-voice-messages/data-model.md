# Data Model: WhatsApp Voice Message Support

**Feature**: 019-whatsapp-voice-messages
**Date**: 2026-03-06

## Entities

### Voice Note (transient — not persisted)

A voice note is a transient object that exists only during the transcription pipeline. Once transcribed, it becomes plain text and flows through the existing conversation pipeline.

| Field | Type | Description |
|-------|------|-------------|
| phone | string | Sender phone number (from WhatsApp payload) |
| name | string | Sender display name |
| media_id | string | WhatsApp media ID for downloading the audio |
| mime_type | string | Audio MIME type (typically `audio/ogg; codecs=opus`) |
| audio_bytes | bytes | Raw audio data downloaded from WhatsApp |
| duration_seconds | float | Audio duration (checked via ffprobe before transcription) |
| transcribed_text | string | Output from speech-to-text service |

### Pipeline Flow

```text
WhatsApp webhook payload
  → extract_message() returns {type: "audio", media_id, mime_type}
  → download_media(media_id) returns audio_bytes
  → check_duration(audio_bytes) returns duration_seconds
    → if > 180 seconds: reply "too long" and stop
  → convert_to_mp3(audio_bytes) returns mp3_bytes
  → transcribe(mp3_bytes) returns transcribed_text
    → if empty/failed: reply "couldn't understand" and stop
  → handle_message(phone, "[Voice: \"transcribed_text\"]")
  → normal Claude tool loop → WhatsApp reply
```

### No New Persistent Storage

This feature adds no new files, databases, or JSON stores. The transcribed text is saved in `data/conversations.json` as part of the normal conversation turn — indistinguishable from typed text except for the `[Voice: "..."]` prefix.

## Relationships to Existing Entities

- **Conversation Turn** (in `data/conversations.json`): Voice note transcriptions become conversation turns, same as typed messages.
- **Message** (WhatsApp webhook payload): Voice notes are a new `msg_type` ("audio") alongside existing "text" and "image" types.
