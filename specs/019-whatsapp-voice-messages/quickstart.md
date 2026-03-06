# Quickstart: WhatsApp Voice Message Support

**Feature**: 019-whatsapp-voice-messages
**Date**: 2026-03-06

## Prerequisites

- NUC deployed with latest code (`./scripts/nuc.sh deploy`)
- `OPENAI_API_KEY` set in `.env` and pushed to NUC (`./scripts/nuc.sh env`)
- ffmpeg installed in the Docker image (verified during build)

## Validation Scenarios

### Scenario 1: Basic Voice Note (P1 — MVP)

1. Open WhatsApp group chat on iPhone
2. Hold the microphone button and say: "What's on my calendar today?"
3. Send the voice note

**Expected**: Bot responds within 15 seconds with today's calendar events, same as if you had typed the question. Response includes a brief quote of the transcribed text.

### Scenario 2: Actionable Voice Command (P1)

1. Send a voice note saying: "Add eggs and butter to the grocery list"

**Expected**: Bot adds eggs and butter to the grocery list and confirms, same as a typed message.

### Scenario 3: Short Voice Note (P1 — edge case)

1. Send a very short voice note: just say "yes"

**Expected**: Bot processes the single word and responds appropriately in context.

### Scenario 4: Noisy/Unclear Audio (P1 — error handling)

1. Send a voice note with heavy background noise or while whispering very quietly

**Expected**: Bot replies with something like "I couldn't quite understand that voice note — could you try again or type it instead?"

### Scenario 5: Long Voice Note (P1 — duration limit)

1. Send a voice note longer than 3 minutes (or forward a long audio clip)

**Expected**: Bot replies with a friendly message explaining the voice note is too long and suggesting a shorter message or typing.

### Scenario 6: Transcription Service Down (P1 — fallback)

1. Temporarily set an invalid `OPENAI_API_KEY` in `.env`
2. Send a voice note

**Expected**: Bot replies with a fallback message asking the user to type instead. Does NOT silently drop the message.

3. Restore the correct API key and restart

### Scenario 7: Transcription Confirmation (P2)

1. Send a voice note saying: "Put dentist appointment on Friday at 2 PM"

**Expected**: Bot response includes the transcribed text (so you can verify it heard "Friday at 2 PM" correctly) and creates the calendar event.

## Verification Checklist

- [ ] Voice note → calendar query works
- [ ] Voice note → grocery list action works
- [ ] Short voice notes (<2 seconds) work
- [ ] Unclear audio gets friendly error
- [ ] Long audio (>3 min) gets duration warning
- [ ] API errors get friendly fallback
- [ ] Transcribed text appears in conversation logs
- [ ] Bot response time under 15 seconds
