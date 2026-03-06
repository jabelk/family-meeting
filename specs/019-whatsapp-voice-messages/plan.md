# Implementation Plan: WhatsApp Voice Message Support

**Branch**: `019-whatsapp-voice-messages` | **Date**: 2026-03-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/019-whatsapp-voice-messages/spec.md`

## Summary

Add voice note transcription to the WhatsApp bot so family members can speak instead of typing. Voice notes (OGG/Opus) are downloaded via the existing `download_media()` function, converted to MP3 with ffmpeg, transcribed via OpenAI's GPT-4o Mini Transcribe API (~$0.90/month), and fed into the existing Claude tool loop as text. Three files change: `whatsapp.py` (extract audio messages), `app.py` (route audio to transcription), and a new `transcribe.py` module.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK (existing), openai SDK (new — for Whisper transcription only), ffmpeg (new — apt package in Docker)
**Storage**: N/A — transcribed text flows through existing conversation pipeline
**Testing**: Not requested
**Target Platform**: Linux server (Docker on NUC, Ubuntu 24.04)
**Project Type**: Web service (existing FastAPI app)
**Performance Goals**: Voice notes transcribed and responded to within 15 seconds total
**Constraints**: NUC has limited resources; cloud transcription avoids local CPU load
**Scale/Scope**: 2 family members, ~10-20 voice notes/day max

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Uses OpenAI Whisper API (existing service) rather than building custom STT. ffmpeg is a standard tool, not custom code. |
| II. Mobile-First Access | PASS | Voice notes are a native mobile interaction — this makes the bot more mobile-friendly, not less. |
| III. Simplicity & Low Friction | PASS | Zero user-facing setup. Users just send voice notes as they normally would in WhatsApp. |
| IV. Structured Output | PASS | Bot responses remain the same structured format — only the input method changes. |
| V. Incremental Value | PASS | Feature is fully standalone. Works immediately without any other feature. Does not break any existing functionality. |

All gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/019-whatsapp-voice-messages/
├── plan.md              # This file
├── research.md          # STT service comparison
├── data-model.md        # Voice note entity
├── quickstart.md        # Validation scenarios
└── tasks.md             # Task breakdown (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── app.py               # MODIFY: route audio messages to transcription
├── whatsapp.py          # MODIFY: extract audio message type + media_id
├── transcribe.py        # NEW: download → convert → transcribe pipeline
├── config.py            # MODIFY: add OPENAI_API_KEY config
└── assistant.py         # NO CHANGE: receives text from transcription

Dockerfile               # MODIFY: add ffmpeg apt package
requirements.txt         # MODIFY: add openai SDK
```

**Structure Decision**: Existing single-project structure. New `src/transcribe.py` module encapsulates all transcription logic (download, convert, API call). Keeps `whatsapp.py` and `app.py` changes minimal.

## Key Design Decisions

### 1. OpenAI GPT-4o Mini Transcribe over local Whisper
- Cloud API at $0.003/min ≈ $0.90/month at expected volume
- No NUC CPU impact (already running FastAPI + sidecar + tunnel + n8n)
- 1-3 second latency vs 5-10 seconds local
- Docker image stays small (no 500MB model download)

### 2. ffmpeg for OGG→MP3 conversion
- WhatsApp sends OGG/Opus; OpenAI Whisper API prefers MP3
- ffmpeg is a standard apt package, ~30MB in Docker
- Conversion takes <100ms for a 30-second clip
- Alternative: pydub (wraps ffmpeg anyway, adds dependency)

### 3. Transcription confirmation (US2) via prefix
- Prepend transcribed text to the user message as `[Voice: "transcribed text"]`
- This flows through Claude naturally — Claude sees it as context
- Claude can reference the original words in its response
- No separate confirmation step needed

### 4. Max duration: 3 minutes
- Check audio duration before transcribing
- WhatsApp voice notes are typically <30 seconds
- 3-minute limit prevents abuse/accidents (forwarded podcasts, etc.)
- Reply with friendly message if exceeded
