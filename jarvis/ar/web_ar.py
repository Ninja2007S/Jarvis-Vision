from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

import cv2

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import uvicorn


log = logging.getLogger("jarvis.ar.web")


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"


class WebARBridge:
    """
    Python -> browser WebGL bridge.

    Python owns the physical webcam.

    The browser receives:
        - JPEG camera frames
        - hand pointer
        - gesture
        - virtual object state
        - selection state
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:

        self.host = host
        self.port = port

        self.app = FastAPI(
            title="JARVIS WebGL AR",
        )

        self.app.mount(
            "/static",
            StaticFiles(directory=str(STATIC_DIR)),
            name="static",
        )

        self._clients: set[WebSocket] = set()

        self._loop: asyncio.AbstractEventLoop | None = None

        self._thread: threading.Thread | None = None

        self._started = False

        self._lock = threading.Lock()

        self._latest_frame: bytes | None = None

        self._latest_state: dict[str, Any] = {}

        self._configure_routes()

    # =========================================================
    # ROUTES
    # =========================================================

    def _configure_routes(self) -> None:

        @self.app.get("/")
        async def index():

            return FileResponse(
                STATIC_DIR / "index.html"
            )

        @self.app.get("/health")
        async def health():

            return {
                "status": "ok",
                "clients": len(self._clients),
            }

        @self.app.websocket("/ws/ar")
        async def websocket_endpoint(
            websocket: WebSocket,
        ):

            await websocket.accept()

            self._clients.add(websocket)

            log.info(
                "WebGL AR client connected"
            )

            try:

                await websocket.send_json(
                    {
                        "type": "ar.connected",
                        "data": {
                            "status": "ready",
                            "server": "JARVIS WebGL",
                        },
                    }
                )

                while True:

                    message = await websocket.receive_text()

                    try:

                        payload = json.loads(
                            message
                        )

                    except json.JSONDecodeError:

                        continue

                    await self._handle_browser_message(
                        payload
                    )

            except WebSocketDisconnect:

                pass

            except Exception:

                log.exception(
                    "AR WebSocket error"
                )

            finally:

                self._clients.discard(
                    websocket
                )

                log.info(
                    "WebGL AR client disconnected"
                )

    # =========================================================
    # BROWSER MESSAGE
    # =========================================================

    async def _handle_browser_message(
        self,
        payload: dict[str, Any],
    ) -> None:

        message_type = payload.get(
            "type"
        )

        if message_type == "ar.ready":

            log.info(
                "Browser WebGL scene ready"
            )

        elif message_type == "three.object_selected":

            log.info(
                "3D object selected: %s",
                payload.get("data"),
            )

        elif message_type == "three.object_moved":

            log.debug(
                "3D object moved: %s",
                payload.get("data"),
            )

        elif message_type == "keyboard.input":

            log.info(
                "Keyboard input: %s",
                payload.get("data"),
            )

    # =========================================================
    # START SERVER
    # =========================================================

    def start(self) -> None:

        if self._started:
            return

        self._started = True

        self._thread = threading.Thread(
            target=self._run_server,
            name="jarvis-web-ar",
            daemon=True,
        )

        self._thread.start()

        # Give uvicorn a moment to initialize.
        time.sleep(0.4)

        log.info(
            "JARVIS WebGL AR: http://%s:%d",
            self.host,
            self.port,
        )

    def _run_server(self) -> None:

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
        )

    # =========================================================
    # CLIENT LOOP
    # =========================================================

    def _send_from_thread(
        self,
        message: dict[str, Any],
    ) -> None:

        loop = self._loop

        if loop is None:
            return

        asyncio.run_coroutine_threadsafe(
            self._broadcast(
                message
            ),
            loop,
        )

    async def _broadcast(
        self,
        message: dict[str, Any],
    ) -> None:

        if not self._clients:
            return

        dead: list[WebSocket] = []

        for client in list(
            self._clients
        ):

            try:

                await client.send_json(
                    message
                )

            except Exception:

                dead.append(client)

        for client in dead:

            self._clients.discard(
                client
            )

    # =========================================================
    # CAMERA FRAME
    # =========================================================

    def send_frame(
        self,
        frame,
        quality: int = 65,
    ) -> None:

        if not self._clients:
            return

        try:

            ok, encoded = cv2.imencode(
                ".jpg",
                frame,
                [
                    cv2.IMWRITE_JPEG_QUALITY,
                    quality,
                ],
            )

            if not ok:
                return

            jpeg_bytes = encoded.tobytes()

            packet = {
                "type": "camera.frame",
                "data": base64.b64encode(
                    jpeg_bytes
                ).decode("ascii"),
            }

            self._send_from_thread(
                packet
            )

        except Exception:

            log.exception(
                "Failed to encode camera frame"
            )

    # =========================================================
    # VISION STATE
    # =========================================================

    def send_state(
        self,
        *,
        pointer=None,
        gesture="unknown",
        second_pointer=None,
        second_gesture="unknown",
        objects=None,
        virtual_objects=None,
        create_mode=False,
        selected_id=None,
        grabbed_id=None,
    ) -> None:

        if not self._clients:
            return

        message = {
            "type": "vision.state",
            "data": {
                "pointer": self._point(pointer),
                "gesture": gesture,

                "secondPointer": self._point(
                    second_pointer
                ),

                "secondGesture": second_gesture,

                "objects": (
                    objects
                    if objects is not None
                    else []
                ),

                "virtualObjects": (
                    virtual_objects
                    if virtual_objects is not None
                    else []
                ),

                "createMode": bool(
                    create_mode
                ),

                "selectedId": selected_id,

                "grabbedId": grabbed_id,
            },
        }

        self._send_from_thread(
            message
        )

    # =========================================================
    # POINT
    # =========================================================

    @staticmethod
    def _point(point):

        if point is None:
            return None

        try:

            return {
                "x": float(point[0]),
                "y": float(point[1]),
            }

        except Exception:

            return None

    # =========================================================
    # SHUTDOWN
    # =========================================================

    def stop(self) -> None:

        self._started = False


web_ar = WebARBridge()