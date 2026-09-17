"""Hands — acting phase.

Run with `python -m hands.app`. Every gesture from the foundation phase
now drives a real action on the PC:

    pointer position     moves the cursor (smoothed)
    pinch start -> end    mouse click (hold and move while pinching = drag)
    fist                  clutch — freezes the cursor so you can reposition
                          your hand without dragging the mouse across the
                          screen, the same way you'd lift a real mouse
    peace + vertical move scrolls, proportional to how far you move
    open_palm + swipe     left/right switches windows, up opens the task
                          view, down shows the desktop

Starts DISARMED — tracking and the debug overlay run, but nothing touches
your actual mouse or keyboard, so you can watch what it's about to do
before it does it. Press `a` to arm it. Dragging your real mouse to a
screen corner kills all synthetic input instantly (pyautogui's failsafe).

Controls:
    q       quit
    m       toggle mirroring
    a       arm / disarm actions
"""

from __future__ import annotations

import logging
import time

import cv2

from . import actions, config
from .gestures import Stabilizer, classify
from .motion import SwipeDetector
from .mouse import CursorSmoother
from .tracker import HandTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("jarvis.hands")

_BONES = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]

_GESTURE_COLOR = {
    "pinch": (255, 209, 102),
    "point": (143, 188, 216),
    "open_palm": (150, 220, 150),
    "fist": (201, 139, 118),
    "peace": (200, 170, 230),
    "thumbs_up": (255, 255, 150),
    "unknown": (120, 120, 120),
}

SCROLL_SENSITIVITY = 40  # pointer-delta-to-scroll-ticks multiplier


class Controller:
    """Owns all the per-hand state that has to persist between frames:
    cursor smoothing, whether a pinch is currently held, the scroll
    baseline, and swipe history. One instance per session — not per hand,
    since only the primary (first-seen) hand drives OS actions."""

    def __init__(self) -> None:
        self.armed = False
        self.cursor = CursorSmoother()
        self.swipes = SwipeDetector()
        self.pinching = False
        self.peace_baseline_y: float | None = None

    def release_if_needed(self) -> None:
        """Safety net: if the hand vanishes mid-drag, don't leave the
        mouse button stuck down."""
        if self.pinching and self.armed:
            actions.mouse_up()
        self.pinching = False
        self.cursor.reset()
        self.swipes.reset()
        self.peace_baseline_y = None

    def act(self, gesture) -> str:
        """Apply one frame's gesture. Returns a short label for the overlay."""
        name = gesture.name
        note = name

        if name == "fist":
            # Clutch: freeze the cursor, drop any scroll/swipe state, but
            # don't release a mid-drag pinch just because the hand closed —
            # fist and pinch are mutually exclusive gestures already.
            self.peace_baseline_y = None
            self.swipes.reset()
            return "fist (clutch)"

        sx, sy = self.cursor.update(*gesture.pointer)
        if self.armed:
            actions.move_cursor(sx, sy)

        if name == "pinch" and not self.pinching:
            self.pinching = True
            if self.armed:
                actions.mouse_down()
            note = "pinch -> click/drag start"
        elif name != "pinch" and self.pinching:
            self.pinching = False
            if self.armed:
                actions.mouse_up()
            note = "pinch released"

        if name == "peace":
            if self.peace_baseline_y is None:
                self.peace_baseline_y = gesture.pointer[1]
            else:
                delta = self.peace_baseline_y - gesture.pointer[1]  # up = positive
                ticks = int(delta * SCROLL_SENSITIVITY)
                if ticks and self.armed:
                    actions.scroll(ticks)
                if ticks:
                    note = f"scroll {ticks:+d}"
                self.peace_baseline_y = gesture.pointer[1]
        else:
            self.peace_baseline_y = None

        if name == "open_palm":
            swipe = self.swipes.update(gesture.pointer)
            if swipe:
                note = f"swipe {swipe.direction}"
                if self.armed:
                    if swipe.direction == "left":
                        actions.switch_window(forward=False)
                    elif swipe.direction == "right":
                        actions.switch_window(forward=True)
                    elif swipe.direction == "up":
                        actions.task_view()
                    elif swipe.direction == "down":
                        actions.show_desktop()
        else:
            self.swipes.reset()

        return note


def _draw_hand(frame, hand, label: str) -> None:
    h, w = frame.shape[:2]
    color = _GESTURE_COLOR.get(label.split()[0], (200, 200, 200))
    pixels = [(int(p[0] * w), int(p[1] * h)) for p in hand.points]

    for a, b in _BONES:
        cv2.line(frame, pixels[a], pixels[b], color, 2, cv2.LINE_AA)
    for x, y in pixels:
        cv2.circle(frame, (x, y), 3, color, -1, cv2.LINE_AA)

    label_pos = (pixels[0][0] - 20, pixels[0][1] + 30)
    cv2.putText(frame, label, label_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)


def main() -> None:
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        log.error("Couldn't open camera index %d. Try a different JARVIS_CAMERA_INDEX.", config.CAMERA_INDEX)
        return

    tracker = HandTracker()
    stabilizer = Stabilizer(config.STABLE_FRAMES)
    controller = Controller()
    mirror = config.MIRROR

    log.info("hands online, DISARMED — press a to arm, q to quit")

    last_time = time.time()
    fps = 0.0
    had_hand = False

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                log.warning("lost the camera feed")
                break

            if mirror:
                frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hands = tracker.process(rgb)

            if hands:
                had_hand = True
                primary = hands[0]
                gesture = classify(primary)
                settled, changed = stabilizer.update(gesture.name)
                if changed:
                    log.info("gesture -> %s", settled)
                note = controller.act(gesture)
                _draw_hand(frame, primary, note)

                for extra in hands[1:]:
                    _draw_hand(frame, extra, classify(extra).name)
            elif had_hand:
                had_hand = False
                controller.release_if_needed()
                log.info("hand lost — released and reset")

            now = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - last_time, 1e-6))
            last_time = now
            status = "ARMED" if controller.armed else "disarmed"
            cv2.putText(
                frame, f"{fps:0.0f} fps  |  {len(hands)} hand(s)  |  {status}",
                (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (150, 220, 150) if controller.armed else (180, 190, 200), 1, cv2.LINE_AA,
            )

            cv2.imshow("Jarvis — hands", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("m"):
                mirror = not mirror
                log.info("mirror: %s", mirror)
            if key == ord("a"):
                controller.armed = not controller.armed
                log.info("armed: %s", controller.armed)

    finally:
        controller.release_if_needed()
        cap.release()
        tracker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
