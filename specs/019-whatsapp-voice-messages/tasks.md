# Tasks: WhatsApp Voice Message Support

**Input**: Design documents from `/specs/019-whatsapp-voice-messages/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not requested — no test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Add dependencies and infrastructure needed for voice transcription

- [x] T001 Add `openai` SDK to `requirements.txt`
- [x] T002 Add `ffmpeg` installation to `Dockerfile` (apt-get install ffmpeg in the existing RUN layer)
- [x] T003 Add `OPENAI_API_KEY` config variable to `src/config.py` (load from environment, same pattern as other API keys)

---

## Phase 2: User Story 1 — Voice Note as Text Input (Priority: P1) MVP

**Goal**: Transcribe voice notes and process them through the existing Claude tool loop, identical to typed messages

**Independent Test**: Send a voice note saying "what's on my calendar today" via WhatsApp and verify the bot responds with calendar events within 15 seconds

### Implementation for User Story 1

- [x] T004 [US1] Create `src/transcribe.py` with: (1) `transcribe_voice_note(audio_bytes: bytes) -> str` that converts OGG/Opus to MP3 via ffmpeg subprocess, sends to OpenAI GPT-4o Mini Transcribe API, returns transcribed text. (2) `get_audio_duration(audio_bytes: bytes) -> float` that uses ffprobe to check duration in seconds. (3) Constants: `MAX_DURATION_SECONDS = 180`. Handle errors gracefully — return empty string on transcription failure.
- [x] T005 [US1] Update `src/whatsapp.py` `extract_message()`: add `elif msg_type == "audio"` branch (before the existing `"unsupported"` catch-all) that returns `{"phone": phone, "name": name, "type": "audio", "media_id": msg["audio"]["id"], "mime_type": msg["audio"].get("mime_type", "audio/ogg")}`. Update the docstring to include "audio" as a supported type.
- [x] T006 [US1] Update `src/app.py` `receive_message()`: add `elif parsed["type"] == "audio"` branch (before the existing `"unsupported"` branch) that calls `background_tasks.add_task(_process_voice_and_reply, phone, parsed)`. Create `_process_voice_and_reply(phone, parsed)` async function that: (1) downloads audio via `download_media(parsed["media_id"])`, (2) checks duration via `get_audio_duration()` — if >180s, sends "That voice note is a bit long for me (3 min max). Could you send a shorter one or type it out?", (3) calls `transcribe_voice_note(audio_bytes)` — if empty/failed, sends "I couldn't quite understand that voice note — could you try again or type it instead?", (4) constructs message text as `[Voice: "{transcribed_text}"] {transcribed_text}`, (5) calls `handle_message(phone, text)` and sends reply via `send_message()`. Import `transcribe_voice_note`, `get_audio_duration` from `src.transcribe` and `download_media` from `src.whatsapp`.

**Checkpoint**: Voice notes are transcribed and processed through the full Claude tool loop. Bot responds to voice commands identically to typed messages.

---

## Phase 3: User Story 2 — Transcription Confirmation (Priority: P2)

**Goal**: Users see what the bot heard so they can catch misheard words

**Independent Test**: Send a voice note and verify the bot's response includes the transcribed text

### Implementation for User Story 2

- [x] T007 [US2] The `[Voice: "..."]` prefix added in T006 already provides transcription visibility to Claude. Add a system prompt instruction in `src/assistant.py` SYSTEM_PROMPT: after rule 11f, add rule `11g. **Voice notes:** When a message starts with [Voice: "..."], the text in quotes is what was transcribed from a voice note. Always briefly confirm what you heard in your response (e.g., "I heard you want to...") so the user can catch any transcription errors. If the transcribed text seems garbled or nonsensical, ask the user to resend or type instead.`

**Checkpoint**: Bot responses to voice notes always include a brief confirmation of what was heard.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Deploy, validate, and document

- [x] T008 Push `.env` with `OPENAI_API_KEY` to NUC via `./scripts/nuc.sh env`
- [x] T009 Deploy to NUC via `./scripts/nuc.sh deploy` and verify Docker build succeeds (ffmpeg installed, openai imported)
- [x] T010 Run quickstart.md Scenario 1 (basic voice note) and Scenario 2 (actionable command) against production
- [x] T011 Update `CLAUDE.md` Active Technologies section to mention openai SDK and ffmpeg for voice transcription

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup (T001-T003)
- **User Story 2 (Phase 3)**: Depends on US1 (T007 modifies assistant.py system prompt, but requires T006's voice flow to be working)
- **Polish (Phase 4)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: T004 → T005 → T006 (sequential — transcribe module, then webhook extraction, then routing)
- **User Story 2 (P2)**: T007 depends on T006 (the `[Voice: "..."]` prefix must exist)

### Parallel Opportunities

- T001, T002, T003 (Setup) can all run in parallel — different files
- T004 and T005 can run in parallel — different files (`transcribe.py` vs `whatsapp.py`)
- T006 depends on both T004 and T005

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001-T003: Setup (deps + config)
2. Complete T004-T006: Transcription pipeline
3. **STOP and VALIDATE**: Send a voice note, verify response
4. Deploy if ready — voice notes are working

### Incremental Delivery

1. T001-T003 → Dependencies installed
2. T004-T006 → Voice notes transcribed and processed (MVP)
3. T007 → Transcription confirmation in responses
4. T008-T011 → Deploy, validate, document

---

## Notes

- Only 3 source files are modified: `whatsapp.py`, `app.py`, `assistant.py`
- One new file created: `src/transcribe.py`
- Infrastructure changes: `Dockerfile` (ffmpeg), `requirements.txt` (openai), `.env` (OPENAI_API_KEY)
- Total: 11 tasks across 4 phases
