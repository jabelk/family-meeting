# Feature Specification: WhatsApp Voice Message Support

**Feature Branch**: `019-whatsapp-voice-messages`
**Created**: 2026-03-05
**Status**: Draft
**Input**: User description: "WhatsApp voice message support — transcribe voice notes from WhatsApp so users can speak instead of typing. Currently voice notes are dropped with a 'send as text' reply. Users (especially Erin) should be able to hold the mic button, speak their request, and have the bot understand it the same as a typed message."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Voice Note as Text Input (Priority: P1)

As a family member, I want to send a voice note via WhatsApp and have the bot understand and respond to it just like a typed message, so I can interact hands-free while cooking, driving, or wrangling kids.

**Why this priority**: This is the entire feature. Erin frequently has her hands full (meal prep, holding Zoey, driving) and voice notes are the fastest way to communicate. Without this, she must stop what she's doing and type — or her message is silently lost.

**Independent Test**: Send a voice note saying "what's on my calendar today" and verify the bot responds with today's calendar events, identical to typing the same question.

**Acceptance Scenarios**:

1. **Given** a family member sends a voice note via WhatsApp, **When** the bot receives it, **Then** the spoken content is transcribed and processed as if the user had typed that text
2. **Given** a voice note contains a request like "add milk to the grocery list," **When** the bot processes it, **Then** the action is performed (milk added to list) and a confirmation is sent back
3. **Given** a voice note is very short (under 2 seconds, e.g., "yes"), **When** the bot receives it, **Then** it still transcribes and responds correctly
4. **Given** a voice note is long (over 60 seconds), **When** the bot receives it, **Then** it transcribes the full content and responds appropriately

---

### User Story 2 - Transcription Confirmation (Priority: P2)

As a family member, I want to see what the bot heard before it acts on my voice note, so I can catch any misheard words — especially for names, amounts, or calendar times.

**Why this priority**: Transcription errors can lead to wrong calendar entries, wrong grocery items, or wrong budget amounts. Showing what was heard builds trust and prevents silent mistakes. Secondary because the bot is useful even without this confirmation.

**Independent Test**: Send a voice note and verify the bot's reply includes a brief quote of the transcribed text alongside the normal response.

**Acceptance Scenarios**:

1. **Given** a family member sends a voice note, **When** the bot responds, **Then** the response includes a short indicator of the transcribed text (e.g., a quoted line at the top)
2. **Given** the transcription is clearly garbled or very low confidence, **When** the bot processes it, **Then** it asks the user to confirm or resend rather than acting on bad input

---

### Edge Cases

- What happens when the voice note is inaudible (background noise, whispering, wind)? The bot should reply that it couldn't understand the audio and ask the user to try again or type instead.
- What happens when the voice note is in a language other than English? The bot should transcribe as best it can; the family speaks English so this is unlikely but should not crash.
- What happens when WhatsApp sends an audio file that isn't a voice note (e.g., a forwarded song or podcast clip)? The bot should attempt transcription — if it's speech, it works; if it's music/noise, it falls back to the "couldn't understand" response.
- What happens when the transcription service is unavailable or errors out? The bot should reply with a friendly fallback message asking the user to type instead, rather than silently dropping the message.
- What happens when the voice note is extremely long (5+ minutes)? The bot should process up to a reasonable limit (e.g., 3 minutes of audio) and inform the user if the note was truncated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept voice note messages from WhatsApp and convert the spoken audio to text
- **FR-002**: System MUST process the transcribed text through the same message handling pipeline as typed messages (same tools, same context, same conversation history)
- **FR-003**: System MUST include the transcribed text in the conversation log so it is preserved for debugging (same as typed messages)
- **FR-004**: System MUST handle transcription failures gracefully by replying with a helpful message asking the user to try again or type instead
- **FR-005**: System MUST support standard WhatsApp voice note formats (OGG/Opus audio)
- **FR-006**: System MUST enforce a maximum audio duration limit to prevent excessive processing costs, rejecting notes longer than the limit with a friendly message

### Key Entities

- **Voice Note**: An audio message received via WhatsApp, identified by a media ID. Contains spoken content that must be downloaded, transcribed, and processed. Key attributes: sender phone number, media ID, audio format, duration.
- **Transcription**: The text output from converting a voice note to text. Becomes the input to the existing message handling pipeline, replacing what would normally be typed text.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Voice notes are transcribed and responded to within 15 seconds of receipt (including download, transcription, and Claude processing time)
- **SC-002**: 90% of clearly spoken English voice notes are transcribed accurately enough for the bot to perform the correct action
- **SC-003**: Zero silent drops — every voice note receives either a normal response or a clear error message
- **SC-004**: Voice note interactions appear in conversation logs identically to typed messages, enabling the same debugging workflow

## Assumptions

- Family members speak English in their voice notes
- WhatsApp voice notes use OGG/Opus format (standard WhatsApp encoding)
- Voice notes from family members are typically under 30 seconds (quick requests, not long monologues)
- The existing message processing pipeline (Claude tool loop) does not need modification — only the input method changes
- A speech-to-text service with sufficient accuracy for conversational English is available and affordable at the family's low message volume (~20-50 messages/day total, subset being voice)
- The 3-minute maximum duration is sufficient for any reasonable family request
