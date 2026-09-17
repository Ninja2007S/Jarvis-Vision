"""
Jarvis core — Phase 2.

Adds ears and a voice to the Phase 1 socket.

Protocol, client to server:
    {"type": "say",         "text": "..."}   a typed turn
    {"type": "voice_start"}                  push-to-talk pressed
    <binary frames>                          raw 16-bit mono PCM, 16kHz
    {"type": "voice_end"}                    push-to-talk released
    {"type": "reset"}                        clear the conversation
    {"type": "ping"}                         keepalive

Vision protocol:
    /ws/vision

    JSON messages from the vision client are forwarded to ar_bridge.
"""

from __future__ import annotations

import asyncio
import json
import logging

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState

from ..vision.ar_bridge import ar_bridge

from . import config, ears, llm, voice
from .session import Session


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
)

log = logging.getLogger("jarvis")


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title=f"{config.JARVIS_NAME} core",
    version="0.2.0",
)


# ---------------------------------------------------------------------------
# Audio configuration
# ---------------------------------------------------------------------------

SAMPLE_RATE_IN = 16000


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/healthz")
async def healthz() -> dict:
    online = await llm.is_online()

    models = (
        await llm.installed_models()
        if online
        else []
    )

    return {
        "core": "up",
        "model_server": "up" if online else "down",
        "model": config.MODEL,
        "model_installed": config.MODEL in models,
        "installed_models": models,
        "tts_configured": voice.is_configured(),
    }


# ---------------------------------------------------------------------------
# Text-to-speech
# ---------------------------------------------------------------------------

async def _speak(
    socket: WebSocket,
    text: str,
    tts_ok: bool,
) -> bool:
    """
    Synthesize one sentence and stream it back.

    Returns whether TTS is still usable for the current turn.
    """

    if not tts_ok or not text.strip():
        return tts_ok

    try:
        pcm = await asyncio.to_thread(
            voice.synthesize,
            text,
        )

        await socket.send_json(
            {
                "type": "audio",
                "sample_rate": voice.sample_rate(),
            }
        )

        await socket.send_bytes(pcm)

        return True

    except Exception as exc:
        log.warning(
            "voice synthesis unavailable: %s",
            exc,
        )

        return False


# ===========================================================================
# JARVIS VOICE / TEXT WEBSOCKET
# ===========================================================================

@app.websocket("/ws")
async def websocket_endpoint(
    socket: WebSocket,
) -> None:

    await socket.accept()

    session = Session()

    audio_buffer = bytearray()
    recording = False

    log.info(
        "Jarvis client connected: %s",
        socket.client,
    )

    # -----------------------------------------------------------------------
    # Hello
    # -----------------------------------------------------------------------

    await socket.send_json(
        {
            "type": "hello",
            "name": config.JARVIS_NAME,
            "model": config.MODEL,
            "online": await llm.is_online(),
            "tts_configured": voice.is_configured(),
        }
    )

    # -----------------------------------------------------------------------
    # Handle one complete user turn
    # -----------------------------------------------------------------------

    async def handle_turn(text: str) -> None:

        text = text.strip()

        if not text:
            return

        session.add_user(text)

        await socket.send_json(
            {
                "type": "state",
                "value": "thinking",
            }
        )

        reply_parts: list[str] = []
        pending = ""

        tts_ok = voice.is_configured()

        try:

            async for fragment in llm.stream_reply(
                session.messages()
            ):

                reply_parts.append(fragment)

                # Stream text immediately
                await socket.send_json(
                    {
                        "type": "chunk",
                        "text": fragment,
                    }
                )

                # -----------------------------------------------------------
                # Sentence-level TTS
                # -----------------------------------------------------------

                pending += fragment

                ready, pending = voice.split_ready(
                    pending
                )

                for sentence in ready:

                    await socket.send_json(
                        {
                            "type": "state",
                            "value": "speaking",
                        }
                    )

                    tts_ok = await _speak(
                        socket,
                        sentence,
                        tts_ok,
                    )

        except llm.LLMUnavailable as exc:

            log.warning(
                "language core unavailable: %s",
                exc,
            )

            await socket.send_json(
                {
                    "type": "error",
                    "message": str(exc),
                }
            )

            await socket.send_json(
                {
                    "type": "state",
                    "value": "listening",
                }
            )

            return

        # -------------------------------------------------------------------
        # Speak any remaining text
        # -------------------------------------------------------------------

        if pending.strip():

            await _speak(
                socket,
                pending.strip(),
                tts_ok,
            )

        # -------------------------------------------------------------------
        # Complete reply
        # -------------------------------------------------------------------

        reply = "".join(
            reply_parts
        ).strip()

        session.add_assistant(reply)

        await socket.send_json(
            {
                "type": "done",
                "text": reply,
            }
        )

        await socket.send_json(
            {
                "type": "state",
                "value": "listening",
            }
        )

    # -----------------------------------------------------------------------
    # Main socket loop
    # -----------------------------------------------------------------------

    try:

        while True:

            raw = await socket.receive()

            # ---------------------------------------------------------------
            # Disconnect
            # ---------------------------------------------------------------

            if raw["type"] == "websocket.disconnect":
                break

            # ---------------------------------------------------------------
            # Binary audio frame
            # ---------------------------------------------------------------

            if (
                "bytes" in raw
                and raw["bytes"] is not None
            ):

                if recording:
                    audio_buffer.extend(
                        raw["bytes"]
                    )

                continue

            # ---------------------------------------------------------------
            # Text message
            # ---------------------------------------------------------------

            if (
                "text" not in raw
                or raw["text"] is None
            ):
                continue

            try:

                message = json.loads(
                    raw["text"]
                )

            except json.JSONDecodeError:

                await socket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid JSON message",
                    }
                )

                continue

            kind = message.get("type")

            # ===============================================================
            # PING
            # ===============================================================

            if kind == "ping":

                await socket.send_json(
                    {
                        "type": "pong",
                    }
                )

            # ===============================================================
            # RESET
            # ===============================================================

            elif kind == "reset":

                session.reset()

                await socket.send_json(
                    {
                        "type": "state",
                        "value": "listening",
                    }
                )

            # ===============================================================
            # VOICE START
            # ===============================================================

            elif kind == "voice_start":

                recording = True

                audio_buffer.clear()

                await socket.send_json(
                    {
                        "type": "state",
                        "value": "listening",
                    }
                )

                log.info(
                    "voice recording started"
                )

            # ===============================================================
            # VOICE END
            # ===============================================================

            elif kind == "voice_end":

                recording = False

                await socket.send_json(
                    {
                        "type": "state",
                        "value": "transcribing",
                    }
                )

                clip = bytes(
                    audio_buffer
                )

                audio_buffer.clear()

                # -----------------------------------------------------------
                # Audio diagnostics
                # -----------------------------------------------------------

                samples = (
                    np.frombuffer(
                        clip,
                        dtype=np.int16,
                    )
                    if clip
                    else np.array(
                        [],
                        dtype=np.int16,
                    )
                )

                peak = (
                    int(
                        np.abs(samples).max()
                    )
                    if samples.size
                    else 0
                )

                duration = (
                    samples.size
                    / SAMPLE_RATE_IN
                )

                log.info(
                    "voice_end: captured %d bytes "
                    "(%.2fs), peak amplitude %d/32768",
                    len(clip),
                    duration,
                    peak,
                )

                # -----------------------------------------------------------
                # Transcribe
                # -----------------------------------------------------------

                try:

                    text = await asyncio.to_thread(
                        ears.transcribe,
                        clip,
                        SAMPLE_RATE_IN,
                    )

                except Exception as exc:

                    log.exception(
                        "transcription failed"
                    )

                    await socket.send_json(
                        {
                            "type": "error",
                            "message": (
                                f"Couldn't hear that: {exc}"
                            ),
                        }
                    )

                    await socket.send_json(
                        {
                            "type": "state",
                            "value": "listening",
                        }
                    )

                    continue

                # -----------------------------------------------------------
                # Empty transcription
                # -----------------------------------------------------------

                if not text:

                    await socket.send_json(
                        {
                            "type": "state",
                            "value": "listening",
                        }
                    )

                    continue

                # -----------------------------------------------------------
                # Transcript
                # -----------------------------------------------------------

                await socket.send_json(
                    {
                        "type": "transcript",
                        "text": text,
                    }
                )

                # -----------------------------------------------------------
                # Feed transcript into normal Jarvis pipeline
                # -----------------------------------------------------------

                await handle_turn(text)

            # ===============================================================
            # TYPED MESSAGE
            # ===============================================================

            elif kind == "say":

                await handle_turn(
                    message.get("text") or ""
                )

            # ===============================================================
            # UNKNOWN
            # ===============================================================

            else:

                await socket.send_json(
                    {
                        "type": "error",
                        "message": (
                            f"Unknown message type: {kind}"
                        ),
                    }
                )

    except WebSocketDisconnect:

        log.info(
            "Jarvis client disconnected: %s",
            socket.client,
        )

    except Exception:

        log.exception(
            "Jarvis socket failed"
        )

    finally:

        if (
            socket.client_state
            != WebSocketState.DISCONNECTED
        ):

            try:
                await socket.close()

            except Exception:
                pass


# ===========================================================================
# VISION / AR WEBSOCKET
# ===========================================================================

@app.websocket("/ws/vision")
async def vision_websocket(
    websocket: WebSocket,
) -> None:

    await websocket.accept()

    log.info(
        "Vision client connected: %s",
        websocket.client,
    )

    # Register this vision socket with the bridge
    await ar_bridge.connect(
        websocket
    )

    try:

        while True:

            # ---------------------------------------------------------------
            # Receive vision message
            # ---------------------------------------------------------------

            message = await websocket.receive_text()

            try:

                data = json.loads(
                    message
                )

            except json.JSONDecodeError:

                log.warning(
                    "Invalid AR JSON: %s",
                    message,
                )

                continue

            message_type = data.get(
                "type"
            )

            payload = data.get(
                "data",
                {},
            )

            log.info(
                "[AR] %s %s",
                message_type,
                payload,
            )

            # ---------------------------------------------------------------
            # Forward to AR bridge
            # ---------------------------------------------------------------

            await ar_bridge.handle_message(
                websocket,
                message_type,
                payload,
            )

    except WebSocketDisconnect:

        log.info(
            "Vision client disconnected: %s",
            websocket.client,
        )

    except Exception:

        log.exception(
            "Vision websocket failed"
        )

    finally:

        try:

            ar_bridge.disconnect(
                websocket
            )

        except Exception:

            log.exception(
                "AR bridge disconnect failed"
            )


# ===========================================================================
# STATIC CLIENT
# ===========================================================================

@app.get("/")
async def index() -> FileResponse:

    return FileResponse(
        config.CLIENT_DIR / "index.html"
    )


app.mount(
    "/",
    StaticFiles(
        directory=config.CLIENT_DIR
    ),
    name="client",
)


# ===========================================================================
# RUN
# ===========================================================================

def run() -> None:

    import uvicorn

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level="info",
    )


if __name__ == "__main__":

    run()