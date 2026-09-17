"""Language core.

Thin async wrapper around a locally running Ollama server. Everything is
streamed token by token so the interface can start speaking (Phase 2) before
the model has finished thinking.

This module knows nothing about websockets, audio, or vision. Later phases
swap the model or add tool calling here without touching anything else.
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Iterable

import httpx

from . import config


class LLMUnavailable(RuntimeError):
    """Raised when the local model server cannot be reached."""


async def is_online() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{config.OLLAMA_HOST}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


async def installed_models() -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{config.OLLAMA_HOST}/api/tags")
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError:
        return []
    return [m.get("name", "") for m in data.get("models", [])]


async def stream_reply(messages: Iterable[dict]) -> AsyncIterator[str]:
    """Yield reply fragments from the model as they are generated."""

    payload = {
        "model": config.MODEL,
        "messages": list(messages),
        "stream": True,
        "options": {
            "temperature": 0.6,
            "top_p": 0.9,
            # Short, spoken-length answers. Phase 2 reads these aloud.
            "num_predict": 400,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0)) as client:
            async with client.stream(
                "POST", f"{config.OLLAMA_HOST}/api/chat", json=payload
            ) as response:
                if response.status_code != 200:
                    body = (await response.aread()).decode("utf-8", "replace")
                    raise LLMUnavailable(f"Model server returned {response.status_code}: {body[:200]}")

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("error"):
                        raise LLMUnavailable(str(event["error"]))
                    fragment = event.get("message", {}).get("content")
                    if fragment:
                        yield fragment
                    if event.get("done"):
                        break
    except httpx.HTTPError as exc:
        raise LLMUnavailable(f"Cannot reach the model server at {config.OLLAMA_HOST}") from exc
