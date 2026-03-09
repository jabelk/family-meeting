"""Voice note transcription — OGG/Opus → MP3 → OpenAI Whisper API."""

import logging
import subprocess
import tempfile
from pathlib import Path

from openai import AsyncOpenAI

from src.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

MAX_DURATION_SECONDS = 180  # 3 minutes

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


def get_audio_duration(audio_bytes: bytes) -> float:
    """Get duration of audio in seconds using ffprobe."""
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                tmp_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return float(result.stdout.strip()) if result.stdout.strip() else 0.0
    except (subprocess.TimeoutExpired, ValueError):
        logger.warning("Could not determine audio duration")
        return 0.0
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _convert_ogg_to_mp3(audio_bytes: bytes) -> bytes:
    """Convert OGG/Opus audio to MP3 using ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
        ogg_file.write(audio_bytes)
        ogg_path = ogg_file.name

    mp3_path = ogg_path.replace(".ogg", ".mp3")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                ogg_path,
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "4",
                mp3_path,
                "-y",
                "-loglevel",
                "error",
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        return Path(mp3_path).read_bytes()
    finally:
        Path(ogg_path).unlink(missing_ok=True)
        Path(mp3_path).unlink(missing_ok=True)


async def transcribe_voice_note(audio_bytes: bytes) -> str:
    """Transcribe voice note audio to text via OpenAI.

    Returns transcribed text, or empty string on failure.
    """
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not configured — cannot transcribe voice note")
        return ""

    try:
        mp3_bytes = _convert_ogg_to_mp3(audio_bytes)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.error("ffmpeg conversion failed: %s", e)
        return ""

    try:
        # Write MP3 to temp file for the OpenAI API
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(mp3_bytes)
            mp3_path = f.name

        client = _get_client()
        with open(mp3_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file,
            )
        return transcript.text.strip()
    except Exception as e:
        logger.error("Transcription failed: %s", e)
        return ""
    finally:
        Path(mp3_path).unlink(missing_ok=True)
