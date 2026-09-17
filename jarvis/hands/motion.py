"""Detects deliberate swipes from a short window of pointer positions.

A swipe is a burst of fast, consistent movement in one direction — not the
slow drift of a hand that's just repositioning. Comparing the position now
against the position a handful of frames ago catches that burst without
any trained model: it's a displacement threshold over a fixed window, plus
a cooldown so one swipe doesn't fire five events in a row.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

WINDOW_FRAMES = 6
MIN_DISPLACEMENT = 0.22  # fraction of the frame's width/height, in that window
COOLDOWN_FRAMES = 12  # frames of quiet required before the next swipe can fire


@dataclass
class Swipe:
    direction: str  # "left", "right", "up", "down"


class SwipeDetector:
    def __init__(self) -> None:
        self._history: deque[tuple[float, float]] = deque(maxlen=WINDOW_FRAMES)
        self._cooldown = 0

    def update(self, pointer: tuple[float, float]) -> Swipe | None:
        self._history.append(pointer)

        if self._cooldown > 0:
            self._cooldown -= 1
            return None
        if len(self._history) < WINDOW_FRAMES:
            return None

        x0, y0 = self._history[0]
        x1, y1 = self._history[-1]
        dx, dy = x1 - x0, y1 - y0

        if abs(dx) < MIN_DISPLACEMENT and abs(dy) < MIN_DISPLACEMENT:
            return None

        self._cooldown = COOLDOWN_FRAMES
        self._history.clear()

        if abs(dx) > abs(dy):
            return Swipe("right" if dx > 0 else "left")
        return Swipe("down" if dy > 0 else "up")

    def reset(self) -> None:
        self._history.clear()
