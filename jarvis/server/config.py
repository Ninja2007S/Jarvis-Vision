"""Configuration for the Jarvis core.

Reads .env at the project root without pulling in a dependency for it.
Real environment variables always win over the file.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIR = ROOT / "client"


def _load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_env_file()


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.environ.get("JARVIS_MODEL", "qwen2.5:3b-instruct")
JARVIS_NAME = os.environ.get("JARVIS_NAME", "Jarvis")
OPERATOR_NAME = os.environ.get("OPERATOR_NAME", "sir")

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = _int("PORT", 8200)
HISTORY_TURNS = _int("HISTORY_TURNS", 12)

# Ears: faster-whisper model size. This machine has no CUDA GPU (Intel Iris
# Xe is integrated), so this always runs on CPU. "small.en" is the sweet
# spot on a 13th-gen i5; try "base.en" if replies feel slow to start, or
# "medium.en" if you want fewer mis-hears and can spare the extra second.
STT_MODEL = os.environ.get("JARVIS_STT_MODEL", "small.en")

# Voice: path to a Piper .onnx voice model (its .onnx.json must sit next to
# it). Download one from https://huggingface.co/rhasspy/piper-voices — see
# README for the exact free command.
TTS_MODEL_PATH = os.environ.get("JARVIS_TTS_MODEL", str(ROOT / "models" / "en_US-lessac-medium.onnx"))

# Voice: the standalone Piper executable (not the Python package — its
# piper-phonemize dependency has no prebuilt wheel for a lot of Windows +
# newer-Python combinations). A free binary download, no compiling — see
# README for the exact link and where to unzip it.
import platform as _platform  # noqa: E402 - kept local, only used for this one default

_PIPER_BIN_NAME = "piper.exe" if _platform.system() == "Windows" else "piper"
PIPER_BIN = os.environ.get("JARVIS_PIPER_BIN", str(ROOT / "piper" / _PIPER_BIN_NAME))