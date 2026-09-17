from __future__ import annotations

"""JARVIS MediaPipe Hand Tracker.

Uses MediaPipe Tasks HandLandmarker in VIDEO mode.

Coordinate conventions
----------------------

Hand.points:
    normalized MediaPipe coordinates
    x = 0.0 -> 1.0
    y = 0.0 -> 1.0

get_index_fingertip():
    pixel coordinates

IMPORTANT:
    Interaction code should use pixel_index_fingertip()
    or HandTracker.get_index_fingertip().
"""

import logging
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from . import config


log = logging.getLogger("jarvis.hands.tracker")


# ============================================================
# MODEL
# ============================================================

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/"
    "hand_landmarker.task"
)

MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "hand_landmarker.task"
)


# ============================================================
# LANDMARK INDICES
# ============================================================

WRIST = 0

THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4

INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8

MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12

RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16

PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20


# ============================================================
# HAND
# ============================================================

@dataclass
class Hand:

    points: np.ndarray

    handedness: str

    def point(
        self,
        index: int,
    ) -> np.ndarray:

        return self.points[index]

    def index_fingertip(self) -> np.ndarray:

        return self.points[INDEX_TIP]

    def pixel_point(
        self,
        index: int,
        width: int,
        height: int,
    ) -> tuple[float, float]:

        if len(self.points) <= index:
            return 0.0, 0.0

        point = self.points[index]

        x = float(point[0]) * float(width)
        y = float(point[1]) * float(height)

        x = max(
            0.0,
            min(float(width - 1), x),
        )

        y = max(
            0.0,
            min(float(height - 1), y),
        )

        return x, y

    def pixel_index_fingertip(
        self,
        width: int,
        height: int,
    ) -> tuple[float, float]:

        return self.pixel_point(
            INDEX_TIP,
            width,
            height,
        )


# ============================================================
# MODEL DOWNLOAD
# ============================================================

def _ensure_model() -> Path:

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not MODEL_PATH.exists():

        log.info(
            "Downloading MediaPipe hand landmark model..."
        )

        urllib.request.urlretrieve(
            MODEL_URL,
            MODEL_PATH,
        )

        log.info(
            "Hand landmark model saved to %s",
            MODEL_PATH,
        )

    return MODEL_PATH


# ============================================================
# TRACKER
# ============================================================

class HandTracker:

    def __init__(self) -> None:

        model_path = _ensure_model()

        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(
                model_asset_path=str(model_path)
            ),
            num_hands=config.MAX_HANDS,
            min_hand_detection_confidence=(
                config.DETECTION_CONFIDENCE
            ),
            min_tracking_confidence=(
                config.TRACKING_CONFIDENCE
            ),
            running_mode=vision.RunningMode.VIDEO,
        )

        self._landmarker = (
            vision.HandLandmarker.create_from_options(
                options
            )
        )

        self._start = time.perf_counter()

        self._last_timestamp_ms = -1

        log.info(
            "MediaPipe HandLandmarker ready | "
            "hands=%d | detection=%.2f | tracking=%.2f",
            config.MAX_HANDS,
            config.DETECTION_CONFIDENCE,
            config.TRACKING_CONFIDENCE,
        )

    # ========================================================
    # PROCESS
    # ========================================================

    def process(
        self,
        frame_rgb: np.ndarray,
    ) -> list[Hand]:

        if frame_rgb is None:
            return []

        if frame_rgb.size == 0:
            return []

        if frame_rgb.ndim != 3:
            return []

        try:

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=frame_rgb,
            )

        except Exception:

            log.exception(
                "Could not create MediaPipe image"
            )

            return []

        timestamp_ms = int(
            (
                time.perf_counter()
                -
                self._start
            )
            * 1000
        )

        if (
            timestamp_ms
            <=
            self._last_timestamp_ms
        ):

            timestamp_ms = (
                self._last_timestamp_ms
                + 1
            )

        self._last_timestamp_ms = timestamp_ms

        try:

            result = (
                self._landmarker.detect_for_video(
                    mp_image,
                    timestamp_ms,
                )
            )

        except Exception:

            log.exception(
                "MediaPipe hand detection failed"
            )

            return []

        hands: list[Hand] = []

        for i, landmarks in enumerate(
            result.hand_landmarks
        ):

            if len(landmarks) < 21:
                continue

            points = np.array(
                [
                    [
                        float(landmark.x),
                        float(landmark.y),
                        float(landmark.z),
                    ]
                    for landmark in landmarks
                ],
                dtype=np.float32,
            )

            label = "Right"

            if i < len(result.handedness):

                categories = result.handedness[i]

                if categories:

                    category = categories[0]

                    if category.category_name:

                        label = (
                            category.category_name
                        )

            hands.append(
                Hand(
                    points=points,
                    handedness=label,
                )
            )

        return hands

    # ========================================================
    # INDEX FINGERTIP PIXELS
    # ========================================================

    @staticmethod
    def get_index_fingertip(
        hand: Hand,
        width: int,
        height: int,
    ) -> tuple[float, float]:

        if hand is None:
            return 0.0, 0.0

        if len(hand.points) <= INDEX_TIP:
            return 0.0, 0.0

        point = hand.points[INDEX_TIP]

        x = float(point[0]) * float(width)
        y = float(point[1]) * float(height)

        x = max(
            0.0,
            min(float(width - 1), x),
        )

        y = max(
            0.0,
            min(float(height - 1), y),
        )

        return x, y

    # ========================================================
    # GENERIC PIXEL LANDMARK
    # ========================================================

    @staticmethod
    def get_pixel_point(
        hand: Hand,
        landmark_index: int,
        width: int,
        height: int,
    ) -> tuple[float, float]:

        if hand is None:
            return 0.0, 0.0

        if (
            landmark_index < 0
            or landmark_index >= len(hand.points)
        ):
            return 0.0, 0.0

        point = hand.points[landmark_index]

        x = float(point[0]) * float(width)
        y = float(point[1]) * float(height)

        x = max(
            0.0,
            min(float(width - 1), x),
        )

        y = max(
            0.0,
            min(float(height - 1), y),
        )

        return x, y

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self) -> None:

        try:

            self._landmarker.close()

        except Exception:

            log.exception(
                "Failed to close MediaPipe HandLandmarker"
            )