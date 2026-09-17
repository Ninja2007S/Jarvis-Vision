"""Voice.

Calls the standalone Piper executable directly rather than importing the
`piper-tts` Python package — its `piper-phonemize` dependency is a compiled
C++ extension with no prebuilt wheel for a lot of Windows + newer-Python
combinations, which is exactly what broke here. Shelling out to the real
binary sidesteps that entirely: same free engine, no Python packaging to
fight, and it isn't tied to whatever Python version happens to be running
the core.

Splitting replies sentence by sentence, as before, is what lets the first
sentence start speaking while the model is still writing the second.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Iterator

from . import config

log = logging.getLogger("jarvis.voice")

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

_sample_rate_cache: int | None = None


def is_configured() -> bool:
    """Whether both the Piper binary and a voice model are actually where
    config expects them."""
    return Path(config.PIPER_BIN).exists() and Path(config.TTS_MODEL_PATH).exists()


def sample_rate() -> int:
    """Piper's voice models ship a companion .onnx.json with the sample
    rate baked in — reading that is simpler and faster than asking the
    binary, and it's the same file the voice download step already fetches."""
    global _sample_rate_cache
    if _sample_rate_cache is None:
        config_path = Path(str(config.TTS_MODEL_PATH) + ".json")
        data = json.loads(config_path.read_text(encoding="utf-8"))
        _sample_rate_cache = int(data["audio"]["sample_rate"])
    return _sample_rate_cache


def sentences(text: str) -> Iterator[str]:
    """Split a finished reply into speakable chunks."""
    for piece in _SENTENCE_BOUNDARY.split(text.strip()):
        piece = piece.strip()
        if piece:
            yield piece


def split_ready(buffer: str) -> tuple[list[str], str]:
    """Peel complete sentences off the front of a growing buffer.

    Used while the reply is still streaming in: called after every fragment,
    it returns whatever sentences are now finished (to synthesize and speak
    immediately) plus whatever incomplete tail to keep accumulating.
    """
    matches = list(_SENTENCE_BOUNDARY.finditer(buffer))
    if not matches:
        return [], buffer
    boundary = matches[-1].end()
    ready = [s.strip() for s in _SENTENCE_BOUNDARY.split(buffer[:boundary]) if s.strip()]
    return ready, buffer[boundary:]


def synthesize(text: str) -> bytes:
    """Raw 16-bit mono PCM audio for one chunk of text, at sample_rate()
    Hz. Blocking — call via a thread."""
    result = subprocess.run(
        [
            config.PIPER_BIN,
            "--model", str(config.TTS_MODEL_PATH),
            "--output_raw",
        ],
        input=text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"piper exited {result.returncode}: {result.stderr.decode('utf-8', 'replace')[:300]}")
    return result.stdout