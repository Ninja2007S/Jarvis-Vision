from __future__ import annotations

import mss
import numpy as np
import cv2


class ScreenCapture:

    def __init__(self):
        self.sct = mss.mss()

    def capture(
        self,
        monitor: int = 1,
    ):

        monitor_info = self.sct.monitors[
            monitor
        ]

        screenshot = self.sct.grab(
            monitor_info
        )

        frame = np.array(
            screenshot
        )

        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGRA2BGR
        )

        return frame