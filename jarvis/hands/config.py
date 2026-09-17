"""JARVIS hand-tracking and camera configuration."""

from __future__ import annotations

import os


# ============================================================
# CAMERA
# ============================================================

CAMERA_INDEX = int(
    os.environ.get(
        "JARVIS_CAMERA_INDEX",
        "0",
    )
)

# Higher quality camera capture.
FRAME_WIDTH = int(
    os.environ.get(
        "JARVIS_FRAME_WIDTH",
        "1280",
    )
)

FRAME_HEIGHT = int(
    os.environ.get(
        "JARVIS_FRAME_HEIGHT",
        "720",
    )
)

CAMERA_FPS = int(
    os.environ.get(
        "JARVIS_CAMERA_FPS",
        "30",
    )
)


# ============================================================
# MIRROR
# ============================================================

MIRROR = True


# ============================================================
# HAND TRACKING
# ============================================================

MAX_HANDS = 2

DETECTION_CONFIDENCE = 0.55

TRACKING_CONFIDENCE = 0.55

# Gesture stabilizer.
STABLE_FRAMES = 2