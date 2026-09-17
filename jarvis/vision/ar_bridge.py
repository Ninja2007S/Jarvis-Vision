from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any


log = logging.getLogger("jarvis.ar_bridge")


class ARBridge:
    """
    Bridge between VisionController and the /ws/vision WebSocket.

    IMPORTANT:
    main.py owns websocket.accept().
    This class NEVER calls websocket.accept().
    """

    def __init__(self) -> None:

        self._websocket = None

        self._loop: asyncio.AbstractEventLoop | None = None

        self._lock = threading.Lock()

        self._connected = False

    # ============================================================
    # CONNECT
    # ============================================================

    async def connect(
        self,
        websocket,
    ) -> None:
        """
        Register an already-accepted WebSocket.

        websocket.accept() MUST NOT be called here.
        """

        with self._lock:

            self._websocket = websocket
            self._loop = asyncio.get_running_loop()
            self._connected = True

        log.info(
            "AR bridge connected"
        )

    # ============================================================
    # DISCONNECT
    # ============================================================

    def disconnect(
        self,
        websocket=None,
    ) -> None:

        with self._lock:

            if (
                websocket is None
                or websocket is self._websocket
            ):

                self._connected = False
                self._websocket = None
                self._loop = None

        log.info(
            "AR bridge disconnected"
        )

    # ============================================================
    # VISION CONTROLLER EVENTS
    # ============================================================

    def handle_event(
        self,
        event,
    ) -> None:
        """
        Called by VisionController.

        VisionController is synchronous, while the WebSocket
        is asynchronous, so the event is safely scheduled onto
        the asyncio event loop.
        """

        if event is None:
            return

        event_type = getattr(
            event,
            "type",
            "vision.event",
        )

        event_data = getattr(
            event,
            "data",
            {},
        )

        payload = {
            "type": event_type,
            "data": event_data,
        }

        self.send(
            payload
        )

    # ============================================================
    # SEND FROM VISION THREAD
    # ============================================================

    def send(
        self,
        payload: dict[str, Any],
    ) -> None:

        with self._lock:

            websocket = self._websocket
            loop = self._loop
            connected = self._connected

        if not connected:
            return

        if websocket is None:
            return

        if loop is None:
            return

        try:

            future = asyncio.run_coroutine_threadsafe(
                self._send_async(
                    websocket,
                    payload,
                ),
                loop,
            )

            # Do not wait for the result.
            # Vision must never stall waiting for WebSocket I/O.
            future.add_done_callback(
                self._send_done
            )

        except Exception as exc:

            log.debug(
                "AR send scheduling failed: %s",
                exc,
            )

    # ============================================================
    # ASYNC SEND
    # ============================================================

    async def _send_async(
        self,
        websocket,
        payload: dict[str, Any],
    ) -> None:

        try:

            await websocket.send_text(
                json.dumps(
                    payload,
                    default=str,
                )
            )

        except Exception as exc:

            log.debug(
                "AR websocket send failed: %s",
                exc,
            )

            self.disconnect(
                websocket
            )

    # ============================================================
    # FUTURE CALLBACK
    # ============================================================

    @staticmethod
    def _send_done(
        future,
    ) -> None:

        try:

            future.result()

        except Exception:
            # Connection may have disappeared between scheduling
            # and sending. Nothing else needs to happen here.
            pass

    # ============================================================
    # CLIENT → AR BRIDGE
    # ============================================================

    async def handle_message(
        self,
        websocket,
        message_type: str | None,
        payload: dict[str, Any],
    ) -> None:
        """
        Handle messages coming from the AR client.

        This is intentionally lightweight.

        Future AR commands can be added here:
            - virtual object creation
            - object movement
            - keyboard input
            - air drawing
            - UI commands
            - hologram manipulation
        """

        if not message_type:
            return

        # --------------------------------------------------------
        # PING
        # --------------------------------------------------------

        if message_type == "ping":

            try:

                await websocket.send_json(
                    {
                        "type": "pong",
                    }
                )

            except Exception:

                self.disconnect(
                    websocket
                )

            return

        # --------------------------------------------------------
        # AR READY
        # --------------------------------------------------------

        if message_type == "ar.ready":

            log.info(
                "AR client ready: %s",
                payload,
            )

            await self._safe_send_json(
                websocket,
                {
                    "type": "ar.connected",
                    "data": {
                        "status": "ready",
                    },
                },
            )

            return

        # --------------------------------------------------------
        # VIRTUAL OBJECT SELECTED
        # --------------------------------------------------------

        if message_type == "three.object_selected":

            log.info(
                "[AR] virtual object selected: %s",
                payload,
            )

            return

        # --------------------------------------------------------
        # VIRTUAL OBJECT MOVED
        # --------------------------------------------------------

        if message_type == "three.object_moved":

            log.debug(
                "[AR] virtual object moved: %s",
                payload,
            )

            return

        # --------------------------------------------------------
        # AIR DRAWING
        # --------------------------------------------------------

        if message_type == "air_drawing":

            log.debug(
                "[AR] air drawing: %s",
                payload,
            )

            return

        # --------------------------------------------------------
        # VIRTUAL KEYBOARD
        # --------------------------------------------------------

        if message_type == "keyboard.input":

            log.debug(
                "[AR] keyboard input: %s",
                payload,
            )

            return

        # --------------------------------------------------------
        # UNKNOWN MESSAGE
        # --------------------------------------------------------

        log.debug(
            "[AR] unhandled message: %s %s",
            message_type,
            payload,
        )

    # ============================================================
    # SAFE JSON SEND
    # ============================================================

    async def _safe_send_json(
        self,
        websocket,
        payload: dict[str, Any],
    ) -> None:

        try:

            await websocket.send_json(
                payload
            )

        except Exception as exc:

            log.debug(
                "AR response failed: %s",
                exc,
            )

            self.disconnect(
                websocket
            )


# ================================================================
# GLOBAL BRIDGE
# ================================================================

ar_bridge = ARBridge()