from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np

from ..hands import config


@dataclass
class CameraFrame:

    frame: np.ndarray

    timestamp: float

    width: int

    height: int


class Camera:

    def __init__(
        self,
        index: int | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: int = 30,
    ) -> None:

        self.index = (
            config.CAMERA_INDEX
            if index is None
            else index
        )

        self.width = (
            config.FRAME_WIDTH
            if width is None
            else width
        )

        self.height = (
            config.FRAME_HEIGHT
            if height is None
            else height
        )

        self.fps = fps

        self._capture = None

        self._thread = None

        self._lock = threading.Lock()

        self._latest = None

        self._running = False

    # ========================================================
    # START
    # ========================================================

    def start(self):

        if self._running:

            return

        # ----------------------------------------------------
        # DIRECTSHOW
        # ----------------------------------------------------

        self._capture = cv2.VideoCapture(
            self.index,
            cv2.CAP_DSHOW,
        )

        if not self._capture.isOpened():

            raise RuntimeError(
                f"Could not open camera index {self.index}"
            )

        # ----------------------------------------------------
        # MJPEG
        # ----------------------------------------------------
        #
        # Many USB webcams deliver substantially better
        # high-resolution performance when explicitly asked
        # for MJPEG instead of raw YUYV.
        #

        try:

            self._capture.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter_fourcc(
                    *"MJPG"
                ),
            )

        except Exception:

            pass

        # ----------------------------------------------------
        # RESOLUTION
        # ----------------------------------------------------

        self._capture.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.width,
        )

        self._capture.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.height,
        )

        # ----------------------------------------------------
        # FPS
        # ----------------------------------------------------

        self._capture.set(
            cv2.CAP_PROP_FPS,
            self.fps,
        )

        # ----------------------------------------------------
        # LOW BUFFER
        # ----------------------------------------------------

        try:

            self._capture.set(
                cv2.CAP_PROP_BUFFERSIZE,
                1,
            )

        except Exception:

            pass

        # ----------------------------------------------------
        # CAMERA AUTOFOCUS
        # ----------------------------------------------------

        try:

            self._capture.set(
                cv2.CAP_PROP_AUTOFOCUS,
                1,
            )

        except Exception:

            pass

        self._running = True

        self._thread = threading.Thread(
            target=self._capture_loop,
            name="jarvis-camera",
            daemon=True,
        )

        self._thread.start()

    # ========================================================
    # CAPTURE LOOP
    # ========================================================

    def _capture_loop(self):

        assert self._capture is not None

        while self._running:

            ok, frame = (
                self._capture.read()
            )

            if not ok:

                time.sleep(
                    0.01
                )

                continue

            # ------------------------------------------------
            # MIRROR
            # ------------------------------------------------

            if config.MIRROR:

                frame = cv2.flip(
                    frame,
                    1,
                )

            packet = CameraFrame(

                frame=frame,

                timestamp=time.time(),

                width=frame.shape[1],

                height=frame.shape[0],
            )

            with self._lock:

                self._latest = packet

    # ========================================================
    # READ
    # ========================================================

    def read(self):

        with self._lock:

            return self._latest

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self._running = False

        if self._thread:

            self._thread.join(
                timeout=1.0
            )

        if self._capture:

            self._capture.release()

        self._capture = None

        self._thread = None

        self._latest = None

    # ========================================================
    # CONTEXT MANAGER
    # ========================================================

    def __enter__(self):

        self.start()

        return self

    def __exit__(
        self,
        *_args,
    ):

        self.stop()