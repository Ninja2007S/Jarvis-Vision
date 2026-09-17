"""Ears.

faster-whisper on CPU, int8-quantized. Your machine has an Intel Iris Xe
integrated GPU — no CUDA — so this deliberately never tries the GPU path;
asking it to would just fail slowly. On a 13th-gen i5 the "small.en" model
transcribes a five-second clip in well under a second, which is what makes
push-to-talk feel instant rather than laggy.

The model loads once, lazily, on first use, so the core still starts up
immediately even if the model files haven't finished downloading yet.
"""

from __future__ import annotations

import io
import logging
import wave

import numpy as np

from . import config

log = logging.getLogger("jarvis.ears")

_model = None


def _load_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        log.info("loading whisper model %s on cpu ...", config.STT_MODEL)
        _model = WhisperModel(config.STT_MODEL, device="cpu", compute_type="int8")
        log.info("whisper model ready")
    return _model


def pcm16_to_wav_bytes(pcm: bytes, sample_rate: int) -> bytes:
    """Wrap raw 16-bit mono PCM in a WAV header, for saving/debugging only."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return buffer.getvalue()


def transcribe(pcm: bytes, sample_rate: int) -> str:
    """Turn raw 16-bit mono PCM audio into text. Blocking — call via a thread."""
    if not pcm:
        return ""

    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

    if sample_rate != 16000:
        # The client is asked to send 16kHz already; this is a safety net,
        # not the primary path, so simple linear resampling is good enough.
        duration = len(audio) / sample_rate
        target_len = int(duration * 16000)
        audio = np.interp(
            np.linspace(0, len(audio), target_len, endpoint=False),
            np.arange(len(audio)),
            audio,
        ).astype(np.float32)

    model = _load_model()
    segments, _info = model.transcribe(
        audio,
        language="en",
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        beam_size=1,
    )
    return "".join(segment.text for segment in segments).strip()
