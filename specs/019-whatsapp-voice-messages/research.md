# Research: WhatsApp Voice Message Support

**Feature**: 019-whatsapp-voice-messages
**Date**: 2026-03-06

## Decision 1: Speech-to-Text Service

**Decision**: OpenAI GPT-4o Mini Transcribe API

**Rationale**: Best balance of cost ($0.003/min ≈ $0.90/month), simplicity (10-15 lines of code), accuracy (excellent for conversational English), and zero NUC resource impact. At 10-20 voice notes/day of ~30 seconds each, monthly cost is under $1.

**Alternatives considered**:

| Option | Cost/month | Latency (30s clip) | Docker impact | Rejected because |
|--------|-----------|---------------------|---------------|------------------|
| OpenAI GPT-4o Transcribe | $1.80 | 1-3 sec | Minimal | 2x cost for marginal accuracy gain |
| Local faster-whisper (small) | $0 | 5-10 sec | +500MB image | NUC CPU load, larger Docker image, more code to maintain |
| Local faster-whisper (base) | $0 | 3-6 sec | +300MB image | Same concerns, slightly less accurate |
| Google Cloud STT | $5.76-8.06 | 1-3 sec | Minimal | 4-8x more expensive than OpenAI |
| Claude API audio input | N/A | N/A | None | Not supported — Claude Messages API does not accept audio content blocks |

## Decision 2: Audio Format Conversion

**Decision**: ffmpeg subprocess call (OGG/Opus → MP3)

**Rationale**: WhatsApp sends voice notes as OGG/Opus. OpenAI Whisper API officially supports OGG but has known issues with Opus codec in OGG containers. Converting to MP3 with ffmpeg is reliable, fast (<100ms), and ffmpeg is a standard apt package (~30MB in Docker).

**Alternatives considered**:
- **pydub**: Python wrapper around ffmpeg. Adds a pip dependency for no benefit — subprocess call to ffmpeg is simpler and has fewer moving parts.
- **Send OGG directly**: Risky — Opus-in-OGG format may fail. Not worth debugging intermittent failures.
- **Convert to WAV**: Works but produces larger files (10x). MP3 is smaller and well-supported.

## Decision 3: Transcription Confirmation (US2)

**Decision**: Prefix the transcribed text in the message sent to Claude as `[Voice: "transcribed text"]`

**Rationale**: Claude naturally sees the transcribed text as part of the conversation context and can reference it in responses. This requires zero additional code in the assistant — the transcription becomes the message text. Claude can quote the original words if it wants to confirm understanding.

**Alternatives considered**:
- **Separate confirmation message**: Send "I heard: ..." then wait for user OK before processing. Adds friction — violates Constitution III (Simplicity & Low Friction). Users would need to reply "yes" for every voice note.
- **Show transcription only on errors**: Hard to detect transcription confidence reliably. Better to always show what was heard.

## Decision 4: Maximum Audio Duration

**Decision**: 3-minute limit, checked via ffprobe before transcription

**Rationale**: Family voice notes are typically <30 seconds. 3-minute cap prevents accidental processing of forwarded podcasts, songs, or long recordings. ffprobe (bundled with ffmpeg) can check duration in <50ms without decoding the full file.

**Alternatives considered**:
- **No limit**: Risk of processing 10-minute forwarded audio at $0.03+ per note. Low risk at family scale but bad practice.
- **1-minute limit**: Too restrictive. Erin might occasionally send a longer note explaining a complex situation.
- **File size limit**: Less intuitive than duration. A 3-minute OGG/Opus file is only ~300KB anyway.
