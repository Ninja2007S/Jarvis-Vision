from __future__ import annotations

from dataclasses import dataclass
import math
import time

import cv2
import numpy as np


# ============================================================
# JARVIS HOLOGRAPHIC RENDERER
#
# Camera-native holographic AR layer.
#
# IMPORTANT:
#   Gesture recognition happens outside this class.
#
#   PEACE
#       -> enters CREATE MODE
#
#   PEACE -> PINCH
#       -> creates a NEW virtual object
#
#   NORMAL PINCH
#       -> grabs an EXISTING object only
#
#   EMPTY-SPACE PINCH
#       -> does NOTHING
#
#   POINT
#       -> selects / targets
#
#   TWO-HAND PINCH
#       -> scale + rotate + move
#
# This renderer accepts either:
#
#   pixel coordinates:
#       (640, 360)
#
# OR normalized coordinates:
#       (0.50, 0.50)
#
# It automatically converts normalized coordinates to pixels.
# ============================================================


# ============================================================
# PERFORMANCE
# ============================================================

# Do NOT use full-frame blending for every line.
# That was the major source of lag in the previous renderer.

ENABLE_GLOW = True

# Number of objects rendered normally.
MAX_OBJECTS = 20


# ============================================================
# INTERACTION
# ============================================================

DRAG_SPEED = 1.20

MIN_SCALE = 0.35
MAX_SCALE = 4.50

CREATE_COOLDOWN = 0.35

KEY_PRESS_COOLDOWN = 0.22

# Increased hit area for easier selection.
OBJECT_HIT_RADIUS = 125.0

DEFAULT_OBJECT_SCALE = 1.0

IDLE_ROTATION_SPEED = 18.0


# ============================================================
# KEYBOARD
# ============================================================

KEYBOARD_WIDTH = 470
KEYBOARD_HEIGHT = 175

KEYBOARD_X = 0.72
KEYBOARD_Y = 0.72

KEY_WIDTH = 39
KEY_HEIGHT = 27

KEY_GAP = 4


# ============================================================
# COLORS - BGR
# ============================================================

CYAN = (255, 235, 80)
BRIGHT_CYAN = (255, 255, 180)

LIGHT_CYAN = (220, 255, 230)

BLUE = (255, 120, 50)

PURPLE = (255, 100, 210)

GREEN = (100, 255, 120)

YELLOW = (100, 255, 255)

RED = (80, 100, 255)

WHITE = (245, 255, 255)

DARK = (20, 35, 45)

BLACK = (0, 0, 0)


# ============================================================
# DATA
# ============================================================

@dataclass
class HologramObject:
    id: int
    object_type: str
    x: float
    y: float

    scale: float = 1.0
    rotation: float = 0.0

    selected: bool = False
    grabbed: bool = False

    created_at: float = 0.0
    phase: float = 0.0


# ============================================================
# VIRTUAL KEYBOARD
# ============================================================

class VirtualKeyboard:

    def __init__(self):

        self.visible = True

        self.text = ""

        self.last_key = None

        self.last_press = 0.0

        self.x = KEYBOARD_X
        self.y = KEYBOARD_Y

        self.scale = 0.78

        self.hover_key = None

        self.dragging = False

    # ========================================================
    # BOUNDS
    # ========================================================

    def bounds(self, width, height):

        w = KEYBOARD_WIDTH * self.scale
        h = KEYBOARD_HEIGHT * self.scale

        cx = width * self.x
        cy = height * self.y

        x1 = int(cx - w / 2)
        y1 = int(cy - h / 2)

        x2 = int(cx + w / 2)
        y2 = int(cy + h / 2)

        return x1, y1, x2, y2

    # ========================================================
    # ROWS
    # ========================================================

    def rows(self):

        return [
            [
                "1", "2", "3", "4", "5",
                "6", "7", "8", "9", "0",
            ],
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
            list("ZXCVBNM"),
            [
                "SPACE",
                "BACK",
                "ENTER",
            ],
        ]

    # ========================================================
    # KEY RECTANGLE
    # ========================================================

    def key_rect(
        self,
        row,
        col,
        total,
        x1,
        y1,
    ):

        gap = KEY_GAP * self.scale

        key_height = KEY_HEIGHT * self.scale

        if row == 4:

            widths = [120, 70, 75]

            width = widths[col] * self.scale

            current_x = x1 + gap

            for i in range(col):

                current_x += (
                    widths[i] * self.scale
                    + gap
                )

        else:

            width = KEY_WIDTH * self.scale

            current_x = (
                x1
                + gap
                + col * (
                    width + gap
                )
            )

        current_y = (
            y1
            + 32 * self.scale
            + row * (
                key_height + gap
            )
        )

        return (
            int(current_x),
            int(current_y),
            int(current_x + width),
            int(current_y + key_height),
        )

    # ========================================================
    # KEY AT POSITION
    # ========================================================

    def key_at(
        self,
        px,
        py,
        width,
        height,
    ):

        if not self.visible:
            return None

        x1, y1, _, _ = self.bounds(
            width,
            height,
        )

        for row_index, row in enumerate(self.rows()):

            for col_index, key in enumerate(row):

                rx1, ry1, rx2, ry2 = self.key_rect(
                    row_index,
                    col_index,
                    len(row),
                    x1,
                    y1,
                )

                if (
                    rx1 <= px <= rx2
                    and
                    ry1 <= py <= ry2
                ):
                    return key

        return None

    # ========================================================
    # PRESS
    # ========================================================

    def press(self, key):

        if key is None:
            return

        now = time.time()

        if (
            now - self.last_press
            < KEY_PRESS_COOLDOWN
        ):
            return

        self.last_press = now
        self.last_key = key

        if key == "SPACE":

            self.text += " "

        elif key == "BACK":

            self.text = self.text[:-1]

        elif key == "ENTER":

            self.text += "\n"

        else:

            self.text += key

        self.text = self.text[-40:]

    # ========================================================
    # DRAW
    # ========================================================

    def draw(
        self,
        frame,
        pointer=None,
        gesture="unknown",
    ):

        if not self.visible:
            return

        height, width = frame.shape[:2]

        x1, y1, x2, y2 = self.bounds(
            width,
            height,
        )

        # ----------------------------------------------------
        # Glass background.
        # ----------------------------------------------------

        overlay = frame[
            max(0, y1):min(height, y2),
            max(0, x1):min(width, x2),
        ]

        if overlay.size:

            tint = np.full_like(
                overlay,
                (20, 70, 85),
            )

            cv2.addWeighted(
                overlay,
                0.72,
                tint,
                0.28,
                0,
                overlay,
            )

        # ----------------------------------------------------
        # Frame.
        # ----------------------------------------------------

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            CYAN,
            1,
        )

        cv2.rectangle(
            frame,
            (x1 + 3, y1 + 3),
            (x2 - 3, y2 - 3),
            (120, 180, 190),
            1,
        )

        # ----------------------------------------------------
        # Header.
        # ----------------------------------------------------

        cv2.putText(
            frame,
            "JARVIS // HOLOGRAPHIC INPUT",
            (
                x1 + 12,
                y1 + int(20 * self.scale),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38 * self.scale,
            BRIGHT_CYAN,
            1,
            cv2.LINE_AA,
        )

        # ----------------------------------------------------
        # Text display.
        # ----------------------------------------------------

        display_text = self.text[-28:]

        cv2.rectangle(
            frame,
            (
                x1 + 10,
                y1 + int(25 * self.scale),
            ),
            (
                x2 - 10,
                y1 + int(52 * self.scale),
            ),
            (15, 40, 50),
            1,
        )

        cv2.putText(
            frame,
            display_text,
            (
                x1 + 15,
                y1 + int(44 * self.scale),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42 * self.scale,
            WHITE,
            1,
            cv2.LINE_AA,
        )

        # ----------------------------------------------------
        # Keys.
        # ----------------------------------------------------

        rows = self.rows()

        self.hover_key = None

        if pointer is not None:

            self.hover_key = self.key_at(
                pointer[0],
                pointer[1],
                width,
                height,
            )

        for row_index, row in enumerate(rows):

            for col_index, key in enumerate(row):

                rx1, ry1, rx2, ry2 = self.key_rect(
                    row_index,
                    col_index,
                    len(row),
                    x1,
                    y1,
                )

                hovered = (
                    key == self.hover_key
                )

                fill = (
                    (80, 120, 130)
                    if hovered
                    else (30, 65, 75)
                )

                cv2.rectangle(
                    frame,
                    (rx1, ry1),
                    (rx2, ry2),
                    fill,
                    -1,
                )

                cv2.rectangle(
                    frame,
                    (rx1, ry1),
                    (rx2, ry2),
                    (
                        BRIGHT_CYAN
                        if hovered
                        else CYAN
                    ),
                    1,
                )

                font_scale = (
                    0.32
                    if len(key) <= 2
                    else 0.22
                )

                text_size = cv2.getTextSize(
                    key,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    1,
                )[0]

                tx = (
                    rx1
                    + (
                        rx2 - rx1
                        - text_size[0]
                    ) // 2
                )

                ty = (
                    ry1
                    + (
                        ry2 - ry1
                        + text_size[1]
                    ) // 2
                )

                cv2.putText(
                    frame,
                    key,
                    (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    WHITE,
                    1,
                    cv2.LINE_AA,
                )

        if (
            gesture == "pinch"
            and self.hover_key
        ):

            cv2.putText(
                frame,
                f"PRESS // {self.hover_key}",
                (
                    x1 + 8,
                    y2 - 8,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.30,
                BRIGHT_CYAN,
                1,
                cv2.LINE_AA,
            )


# ============================================================
# MAIN RENDERER
# ============================================================

class HologramRenderer:

    def __init__(self):

        self.objects = []

        self.next_id = 1

        self.selected_id = None
        self.pointed_id = None
        self.grabbed_id = None

        self.create_mode = False

        self.create_type_index = 0

        self.create_types = [
            "cube",
            "sphere",
            "pyramid",
            "diamond",
            "ring",
        ]

        self.drag_pointer = None

        self.two_hand_active = False

        self.two_hand_distance = None
        self.two_hand_angle = None
        self.two_hand_scale = None
        self.two_hand_rotation = None

        self.last_gesture = "unknown"
        self.last_pointer = None

        self.last_create_time = 0.0

        self.keyboard = VirtualKeyboard()

        self.width = 1280
        self.height = 720

        self.started_at = time.time()

        # ====================================================
        # IMPORTANT:
        #
        # Startup objects bypass creation cooldown.
        # ====================================================

        self.create(
            "cube",
            0.23,
            0.32,
            scale=1.25,
            bypass_cooldown=True,
        )

        self.create(
            "sphere",
            0.50,
            0.32,
            scale=1.15,
            bypass_cooldown=True,
        )

        self.create(
            "pyramid",
            0.77,
            0.32,
            scale=1.20,
            bypass_cooldown=True,
        )

    # ========================================================
    # COORDINATE NORMALIZATION
    #
    # This is VERY important.
    #
    # MediaPipe may provide:
    #
    #   0.0 -> 1.0
    #
    # while the renderer works in:
    #
    #   pixels
    #
    # This function accepts both.
    # ========================================================

    def normalize_pointer(
        self,
        pointer,
    ):

        if pointer is None:
            return None

        try:

            x = float(pointer[0])
            y = float(pointer[1])

        except Exception:

            return None

        # ----------------------------------------------------
        # Normalized coordinates.
        # ----------------------------------------------------

        if (
            -0.05 <= x <= 1.05
            and
            -0.05 <= y <= 1.05
        ):

            # If values are clearly normalized,
            # convert them to pixels.
            if (
                abs(x) <= 1.0
                and
                abs(y) <= 1.0
            ):

                x *= self.width
                y *= self.height

        # ----------------------------------------------------
        # Clamp.
        # ----------------------------------------------------

        x = max(
            0.0,
            min(
                float(self.width - 1),
                x,
            ),
        )

        y = max(
            0.0,
            min(
                float(self.height - 1),
                y,
            ),
        )

        return x, y

    # ========================================================
    # CREATE
    # ========================================================

    def create(
        self,
        object_type,
        x,
        y,
        scale=DEFAULT_OBJECT_SCALE,
        bypass_cooldown=False,
    ):

        now = time.time()

        if (
            not bypass_cooldown
            and
            now - self.last_create_time
            < CREATE_COOLDOWN
        ):

            return None

        # ----------------------------------------------------
        # Accept either normalized or pixel coordinates.
        # ----------------------------------------------------

        if (
            0.0 <= float(x) <= 1.0
            and
            0.0 <= float(y) <= 1.0
        ):

            normalized_x = float(x)
            normalized_y = float(y)

        else:

            normalized_x = (
                float(x)
                /
                max(1, self.width)
            )

            normalized_y = (
                float(y)
                /
                max(1, self.height)
            )

        obj = HologramObject(
            id=self.next_id,
            object_type=object_type,
            x=max(
                0.03,
                min(
                    0.97,
                    normalized_x,
                ),
            ),
            y=max(
                0.08,
                min(
                    0.90,
                    normalized_y,
                ),
            ),
            scale=max(
                MIN_SCALE,
                min(
                    MAX_SCALE,
                    float(scale),
                ),
            ),
            rotation=0.0,
            selected=False,
            grabbed=False,
            created_at=now,
            phase=self.next_id * 0.83,
        )

        self.next_id += 1

        self.objects.append(obj)

        # Protect against accidental unlimited growth.
        if len(self.objects) > MAX_OBJECTS:

            removable = [
                item
                for item in self.objects
                if not item.selected
                and not item.grabbed
            ]

            if removable:

                oldest = min(
                    removable,
                    key=lambda item: item.created_at,
                )

                self.objects.remove(oldest)

        self.last_create_time = now

        return obj

    # ========================================================
    # FIND OBJECT
    # ========================================================

    def find_at(self, pointer):

        pointer = self.normalize_pointer(
            pointer
        )

        if pointer is None:
            return None

        px = pointer[0]
        py = pointer[1]

        best = None
        best_distance = float("inf")

        # Selected object gets priority.
        ordered = sorted(
            self.objects,
            key=lambda obj: (
                0 if obj.selected else 1,
                -obj.id,
            ),
        )

        for obj in ordered:

            ox = obj.x * self.width
            oy = obj.y * self.height

            radius = (
                OBJECT_HIT_RADIUS
                *
                max(
                    0.75,
                    obj.scale,
                )
            )

            distance_value = math.hypot(
                px - ox,
                py - oy,
            )

            if (
                distance_value <= radius
                and
                distance_value < best_distance
            ):

                best = obj
                best_distance = distance_value

        return best

    # ========================================================
    # SELECT
    # ========================================================

    def select(self, obj):

        for item in self.objects:

            item.selected = (
                item is obj
            )

        self.selected_id = (
            obj.id
            if obj is not None
            else None
        )

    # ========================================================
    # POINT SELECTION
    # ========================================================

    def update_point_selection(
        self,
        pointer,
    ):

        pointer = self.normalize_pointer(
            pointer
        )

        obj = self.find_at(pointer)

        self.pointed_id = (
            obj.id
            if obj is not None
            else None
        )

        return obj

    # ========================================================
    # START GRAB
    # ========================================================

    def start_grab(self, pointer):

        pointer = self.normalize_pointer(
            pointer
        )

        if pointer is None:
            return None

        obj = None

        # ----------------------------------------------------
        # If something is already selected, use it.
        # ----------------------------------------------------

        if self.selected_id is not None:

            for item in self.objects:

                if item.id == self.selected_id:

                    obj = item
                    break

        # ----------------------------------------------------
        # Otherwise find under pointer.
        # ----------------------------------------------------

        if obj is None:

            obj = self.find_at(
                pointer
            )

        # ----------------------------------------------------
        # CRITICAL:
        #
        # Empty-space pinch DOES NOT create.
        # ----------------------------------------------------

        if obj is None:

            return None

        self.select(obj)

        obj.grabbed = True

        self.grabbed_id = obj.id

        self.drag_pointer = pointer

        return obj

    # ========================================================
    # UPDATE GRAB
    # ========================================================

    def update_grab(self, pointer):

        pointer = self.normalize_pointer(
            pointer
        )

        if (
            self.grabbed_id is None
            or
            pointer is None
        ):

            return

        obj = None

        for item in self.objects:

            if item.id == self.grabbed_id:

                obj = item
                break

        if obj is None:
            return

        if self.drag_pointer is None:

            self.drag_pointer = pointer
            return

        dx = (
            pointer[0]
            -
            self.drag_pointer[0]
        )

        dy = (
            pointer[1]
            -
            self.drag_pointer[1]
        )

        obj.x += (
            dx
            /
            self.width
            *
            DRAG_SPEED
        )

        obj.y += (
            dy
            /
            self.height
            *
            DRAG_SPEED
        )

        obj.x = max(
            0.03,
            min(
                0.97,
                obj.x,
            ),
        )

        obj.y = max(
            0.08,
            min(
                0.90,
                obj.y,
            ),
        )

        self.drag_pointer = pointer

    # ========================================================
    # RELEASE
    # ========================================================

    def release_grab(self):

        for obj in self.objects:

            obj.grabbed = False

        self.grabbed_id = None

        self.drag_pointer = None

    # ========================================================
    # CREATE MODE
    # ========================================================

    def enter_create_mode(self):

        self.create_mode = True

    def exit_create_mode(self):

        self.create_mode = False

    # ========================================================
    # CREATE FROM GESTURE
    # ========================================================

    def create_from_gesture(self, pointer):

        pointer = self.normalize_pointer(
            pointer
        )

        if pointer is None:
            return None

        now = time.time()

        if (
            now - self.last_create_time
            < CREATE_COOLDOWN
        ):

            return None

        object_type = (
            self.create_types[
                self.create_type_index
            ]
        )

        obj = self.create(
            object_type,
            pointer[0],
            pointer[1],
            scale=1.25,
            bypass_cooldown=False,
        )

        if obj is None:
            return None

        self.select(obj)

        obj.grabbed = True

        self.grabbed_id = obj.id

        self.drag_pointer = pointer

        self.create_type_index = (
            self.create_type_index + 1
        ) % len(self.create_types)

        return obj

    # ========================================================
    # TWO HAND START
    # ========================================================

    def start_two_hands(
        self,
        pointer,
        second_pointer,
    ):

        pointer = self.normalize_pointer(
            pointer
        )

        second_pointer = self.normalize_pointer(
            second_pointer
        )

        if (
            pointer is None
            or
            second_pointer is None
        ):

            return

        obj = None

        if self.selected_id is not None:

            for item in self.objects:

                if item.id == self.selected_id:

                    obj = item
                    break

        if obj is None:

            obj = self.find_at(
                pointer
            )

        if obj is None:

            obj = self.find_at(
                second_pointer
            )

        if obj is None:
            return

        self.select(obj)

        dx = (
            second_pointer[0]
            -
            pointer[0]
        )

        dy = (
            second_pointer[1]
            -
            pointer[1]
        )

        self.two_hand_distance = max(
            math.hypot(dx, dy),
            1.0,
        )

        self.two_hand_angle = math.atan2(
            dy,
            dx,
        )

        self.two_hand_scale = obj.scale
        self.two_hand_rotation = obj.rotation

        self.two_hand_active = True

    # ========================================================
    # TWO HAND UPDATE
    # ========================================================

    def update_two_hands(
        self,
        pointer,
        second_pointer,
    ):

        if (
            not self.two_hand_active
            or
            pointer is None
            or
            second_pointer is None
        ):

            return

        if self.selected_id is None:
            return

        pointer = self.normalize_pointer(
            pointer
        )

        second_pointer = self.normalize_pointer(
            second_pointer
        )

        if (
            pointer is None
            or
            second_pointer is None
        ):

            return

        obj = None

        for item in self.objects:

            if item.id == self.selected_id:

                obj = item
                break

        if obj is None:
            return

        dx = (
            second_pointer[0]
            -
            pointer[0]
        )

        dy = (
            second_pointer[1]
            -
            pointer[1]
        )

        current_distance = max(
            math.hypot(dx, dy),
            1.0,
        )

        current_angle = math.atan2(
            dy,
            dx,
        )

        scale_ratio = (
            current_distance
            /
            max(
                1.0,
                self.two_hand_distance,
            )
        )

        obj.scale = max(
            MIN_SCALE,
            min(
                MAX_SCALE,
                self.two_hand_scale
                *
                scale_ratio,
            ),
        )

        angle_delta = (
            current_angle
            -
            self.two_hand_angle
        )

        # Keep rotation stable across ±PI.
        while angle_delta > math.pi:
            angle_delta -= 2 * math.pi

        while angle_delta < -math.pi:
            angle_delta += 2 * math.pi

        obj.rotation = (
            self.two_hand_rotation
            +
            math.degrees(
                angle_delta
            )
        )

        midpoint_x = (
            pointer[0]
            +
            second_pointer[0]
        ) * 0.5

        midpoint_y = (
            pointer[1]
            +
            second_pointer[1]
        ) * 0.5

        obj.x = max(
            0.03,
            min(
                0.97,
                midpoint_x
                /
                self.width,
            ),
        )

        obj.y = max(
            0.08,
            min(
                0.90,
                midpoint_y
                /
                self.height,
            ),
        )

    # ========================================================
    # STOP TWO HANDS
    # ========================================================

    def stop_two_hands(self):

        self.two_hand_active = False

        self.two_hand_distance = None
        self.two_hand_angle = None
        self.two_hand_scale = None
        self.two_hand_rotation = None

    # ========================================================
    # KEYBOARD
    # ========================================================

    def process_keyboard(
        self,
        pointer,
        gesture,
    ):

        if not self.keyboard.visible:
            return

        pointer = self.normalize_pointer(
            pointer
        )

        if pointer is None:
            return

        key = self.keyboard.key_at(
            pointer[0],
            pointer[1],
            self.width,
            self.height,
        )

        if (
            gesture == "pinch"
            and
            key is not None
        ):

            self.keyboard.press(key)

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        pointer=None,
        gesture="unknown",
        second_pointer=None,
        second_gesture="unknown",
        physical_target_exists=False,
    ):

        gesture = (
            gesture.lower()
            if gesture
            else "unknown"
        )

        second_gesture = (
            second_gesture.lower()
            if second_gesture
            else "unknown"
        )

        pointer = self.normalize_pointer(
            pointer
        )

        second_pointer = self.normalize_pointer(
            second_pointer
        )

        # ====================================================
        # KEYBOARD
        # ====================================================

        self.process_keyboard(
            pointer,
            gesture,
        )

        # ====================================================
        # TWO HANDS
        # ====================================================

        two_hands = (
            pointer is not None
            and
            second_pointer is not None
            and
            gesture == "pinch"
            and
            second_gesture == "pinch"
        )

        if two_hands:

            if not self.two_hand_active:

                self.start_two_hands(
                    pointer,
                    second_pointer,
                )

            self.update_two_hands(
                pointer,
                second_pointer,
            )

            self.last_gesture = gesture
            self.last_pointer = pointer

            return

        if self.two_hand_active:

            self.stop_two_hands()

        # ====================================================
        # PEACE
        # ====================================================

        if gesture == "peace":

            self.enter_create_mode()

            # Do not keep an old object grabbed.
            self.release_grab()

            self.last_gesture = gesture
            self.last_pointer = pointer

            return

        # ====================================================
        # PINCH
        # ====================================================

        if gesture == "pinch":

            # ------------------------------------------------
            # CREATE MODE:
            #
            # Peace happened first.
            # Now pinch creates an object.
            # ------------------------------------------------

            if (
                self.create_mode
                and
                self.grabbed_id is None
            ):

                self.create_from_gesture(
                    pointer
                )

            # ------------------------------------------------
            # NORMAL PINCH:
            #
            # Existing objects only.
            # ------------------------------------------------

            elif self.grabbed_id is None:

                self.start_grab(
                    pointer
                )

            # ------------------------------------------------
            # CONTINUE DRAG.
            # ------------------------------------------------

            else:

                self.update_grab(
                    pointer
                )

        # ====================================================
        # RELEASE
        # ====================================================

        elif (
            self.last_gesture == "pinch"
            and
            gesture != "pinch"
        ):

            self.release_grab()

            # If an object was created, creation mode ends
            # when the user releases it.
            self.exit_create_mode()

        # ====================================================
        # POINT
        # ====================================================

        elif gesture == "point":

            obj = self.update_point_selection(
                pointer
            )

            if obj is not None:

                self.select(obj)

        # ====================================================
        # OTHER
        # ====================================================

        else:

            self.update_point_selection(
                pointer
            )

        self.last_gesture = gesture
        self.last_pointer = pointer

    # ========================================================
    # FAST HOLOGRAM LINE
    #
    # IMPORTANT:
    #
    # Previous version copied the ENTIRE frame for every line.
    # That caused major lag.
    #
    # This version draws directly.
    # ========================================================

    def _line(
        self,
        frame,
        p1,
        p2,
        color=CYAN,
        thickness=1,
    ):

        # ----------------------------------------------------
        # Optional tiny glow.
        #
        # Only draw a local line, not a full frame blend.
        # ----------------------------------------------------

        if ENABLE_GLOW:

            glow_thickness = max(
                2,
                thickness + 2,
            )

            cv2.line(
                frame,
                p1,
                p2,
                color,
                glow_thickness,
                cv2.LINE_AA,
            )

        cv2.line(
            frame,
            p1,
            p2,
            color,
            thickness,
            cv2.LINE_AA,
        )

        if thickness <= 1:

            cv2.line(
                frame,
                p1,
                p2,
                BRIGHT_CYAN,
                1,
                cv2.LINE_AA,
            )

    # ========================================================
    # PROJECT 3D POINT
    # ========================================================

    def _project(
        self,
        x,
        y,
        z,
        cx,
        cy,
        size,
        rotation,
    ):

        yaw = math.radians(
            rotation
        )

        cos_y = math.cos(yaw)
        sin_y = math.sin(yaw)

        x2 = (
            x * cos_y
            -
            z * sin_y
        )

        z2 = (
            x * sin_y
            +
            z * cos_y
        )

        pitch = math.radians(18.0)

        cos_x = math.cos(pitch)
        sin_x = math.sin(pitch)

        y2 = (
            y * cos_x
            -
            z2 * sin_x
        )

        z3 = (
            y * sin_x
            +
            z2 * cos_x
        )

        camera_distance = 4.0

        perspective = (
            camera_distance
            /
            max(
                0.5,
                camera_distance + z3,
            )
        )

        px = (
            cx
            +
            x2
            *
            size
            *
            perspective
        )

        py = (
            cy
            +
            y2
            *
            size
            *
            perspective
        )

        return int(px), int(py)

    # ========================================================
    # CUBE
    # ========================================================

    def _draw_cube(
        self,
        frame,
        obj,
        color,
    ):

        cx = obj.x * self.width
        cy = obj.y * self.height

        size = 70 * obj.scale

        vertices = []

        for z in (-1.0, 1.0):

            for y in (-1.0, 1.0):

                for x in (-1.0, 1.0):

                    vertices.append(
                        self._project(
                            x,
                            y,
                            z,
                            cx,
                            cy,
                            size,
                            obj.rotation,
                        )
                    )

        edges = [
            (0, 1),
            (1, 3),
            (3, 2),
            (2, 0),

            (4, 5),
            (5, 7),
            (7, 6),
            (6, 4),

            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        ]

        for a, b in edges:

            self._line(
                frame,
                vertices[a],
                vertices[b],
                color,
                2,
            )

        # Inner cube.

        inner = []

        for z in (-0.55, 0.55):

            for y in (-0.55, 0.55):

                for x in (-0.55, 0.55):

                    inner.append(
                        self._project(
                            x,
                            y,
                            z,
                            cx,
                            cy,
                            size * 0.55,
                            -obj.rotation * 1.4,
                        )
                    )

        for a, b in edges:

            self._line(
                frame,
                inner[a],
                inner[b],
                BLUE,
                1,
            )

    # ========================================================
    # SPHERE
    # ========================================================

    def _draw_sphere(
        self,
        frame,
        obj,
        color,
    ):

        cx = obj.x * self.width
        cy = obj.y * self.height

        radius = 70 * obj.scale

        # Fewer lines = much better FPS.

        for latitude in range(
            -60,
            61,
            30,
        ):

            lat = math.radians(latitude)

            ring_radius = math.cos(lat)
            ring_y = math.sin(lat)

            previous = None

            for longitude in range(
                0,
                361,
                24,
            ):

                lon = math.radians(
                    longitude + obj.rotation
                )

                x = (
                    ring_radius
                    *
                    math.cos(lon)
                )

                z = (
                    ring_radius
                    *
                    math.sin(lon)
                )

                point = self._project(
                    x,
                    ring_y,
                    z,
                    cx,
                    cy,
                    radius,
                    0,
                )

                if previous is not None:

                    self._line(
                        frame,
                        previous,
                        point,
                        color,
                        1,
                    )

                previous = point

        for longitude in range(
            0,
            180,
            45,
        ):

            previous = None

            for latitude in range(
                -90,
                91,
                15,
            ):

                lat = math.radians(latitude)

                lon = math.radians(
                    longitude + obj.rotation
                )

                x = (
                    math.cos(lat)
                    *
                    math.cos(lon)
                )

                y = math.sin(lat)

                z = (
                    math.cos(lat)
                    *
                    math.sin(lon)
                )

                point = self._project(
                    x,
                    y,
                    z,
                    cx,
                    cy,
                    radius,
                    0,
                )

                if previous is not None:

                    self._line(
                        frame,
                        previous,
                        point,
                        BLUE,
                        1,
                    )

                previous = point

    # ========================================================
    # PYRAMID
    # ========================================================

    def _draw_pyramid(
        self,
        frame,
        obj,
        color,
    ):

        cx = obj.x * self.width
        cy = obj.y * self.height

        size = 80 * obj.scale

        base = []

        for angle in (
            45,
            135,
            225,
            315,
        ):

            rad = math.radians(
                angle + obj.rotation
            )

            base.append(
                self._project(
                    math.cos(rad),
                    0.65,
                    math.sin(rad),
                    cx,
                    cy,
                    size,
                    0,
                )
            )

        apex = self._project(
            0,
            -1.15,
            0,
            cx,
            cy,
            size,
            0,
        )

        for i in range(4):

            self._line(
                frame,
                base[i],
                base[(i + 1) % 4],
                color,
                2,
            )

            self._line(
                frame,
                base[i],
                apex,
                BRIGHT_CYAN,
                2,
            )

        center = self._project(
            0,
            0.2,
            0,
            cx,
            cy,
            size,
            0,
        )

        for point in base:

            self._line(
                frame,
                point,
                center,
                BLUE,
                1,
            )

    # ========================================================
    # DIAMOND
    # ========================================================

    def _draw_diamond(
        self,
        frame,
        obj,
        color,
    ):

        cx = obj.x * self.width
        cy = obj.y * self.height

        size = 80 * obj.scale

        points = [
            self._project(
                0, -1.2, 0,
                cx, cy, size,
                obj.rotation,
            ),
            self._project(
                -1.0, 0, 0,
                cx, cy, size,
                obj.rotation,
            ),
            self._project(
                0, 1.2, 0,
                cx, cy, size,
                obj.rotation,
            ),
            self._project(
                1.0, 0, 0,
                cx, cy, size,
                obj.rotation,
            ),
            self._project(
                0, 0, -0.9,
                cx, cy, size,
                obj.rotation,
            ),
            self._project(
                0, 0, 0.9,
                cx, cy, size,
                obj.rotation,
            ),
        ]

        edges = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),

            (0, 4),
            (4, 2),

            (2, 5),
            (5, 0),

            (1, 4),
            (4, 3),

            (1, 5),
            (5, 3),
        ]

        for a, b in edges:

            self._line(
                frame,
                points[a],
                points[b],
                color,
                2,
            )

    # ========================================================
    # RING
    # ========================================================

    def _draw_ring(
        self,
        frame,
        obj,
        color,
    ):

        cx = obj.x * self.width
        cy = obj.y * self.height

        radius = 65 * obj.scale

        tube = 0.22

        # Reduced resolution for FPS.

        for tube_angle in range(
            0,
            360,
            45,
        ):

            previous = None

            for main_angle in range(
                0,
                361,
                18,
            ):

                u = math.radians(
                    main_angle + obj.rotation
                )

                v = math.radians(
                    tube_angle
                )

                r = (
                    1.0
                    +
                    tube * math.cos(v)
                )

                x = r * math.cos(u)
                y = tube * math.sin(v)
                z = r * math.sin(u)

                point = self._project(
                    x,
                    y,
                    z,
                    cx,
                    cy,
                    radius,
                    0,
                )

                if previous is not None:

                    self._line(
                        frame,
                        previous,
                        point,
                        color,
                        1,
                    )

                previous = point

        for main_angle in range(
            0,
            360,
            45,
        ):

            previous = None

            for tube_angle in range(
                0,
                361,
                18,
            ):

                u = math.radians(
                    main_angle + obj.rotation
                )

                v = math.radians(
                    tube_angle
                )

                r = (
                    1.0
                    +
                    tube * math.cos(v)
                )

                x = r * math.cos(u)
                y = tube * math.sin(v)
                z = r * math.sin(u)

                point = self._project(
                    x,
                    y,
                    z,
                    cx,
                    cy,
                    radius,
                    0,
                )

                if previous is not None:

                    self._line(
                        frame,
                        previous,
                        point,
                        BLUE,
                        1,
                    )

                previous = point

    # ========================================================
    # OBJECT DISPATCH
    # ========================================================

    def _draw_object(
        self,
        frame,
        obj,
    ):

        elapsed = (
            time.time()
            -
            obj.created_at
        )

        animated_rotation = (
            obj.rotation
            +
            elapsed
            *
            IDLE_ROTATION_SPEED
        )

        original_rotation = obj.rotation

        obj.rotation = animated_rotation

        color = (
            BRIGHT_CYAN
            if obj.selected
            else CYAN
        )

        if obj.object_type == "cube":

            self._draw_cube(
                frame,
                obj,
                color,
            )

        elif obj.object_type == "sphere":

            self._draw_sphere(
                frame,
                obj,
                color,
            )

        elif obj.object_type == "pyramid":

            self._draw_pyramid(
                frame,
                obj,
                color,
            )

        elif obj.object_type == "diamond":

            self._draw_diamond(
                frame,
                obj,
                color,
            )

        elif obj.object_type == "ring":

            self._draw_ring(
                frame,
                obj,
                color,
            )

        # ----------------------------------------------------
        # Scan ring.
        # ----------------------------------------------------

        cx = int(
            obj.x * self.width
        )

        cy = int(
            obj.y * self.height
        )

        scan_phase = elapsed * 2.0

        scan_radius = (
            55
            *
            obj.scale
            *
            (
                0.75
                +
                0.25
                *
                math.sin(scan_phase)
            )
        )

        cv2.ellipse(
            frame,
            (cx, cy),
            (
                int(scan_radius),
                int(
                    scan_radius * 0.30
                ),
            ),
            animated_rotation,
            0,
            360,
            BLUE,
            1,
            cv2.LINE_AA,
        )

        # ----------------------------------------------------
        # Selected marker.
        # ----------------------------------------------------

        if obj.selected:

            marker_radius = int(
                92 * obj.scale
            )

            cv2.ellipse(
                frame,
                (cx, cy),
                (
                    marker_radius,
                    int(
                        marker_radius * 0.75
                    ),
                ),
                animated_rotation,
                0,
                360,
                BRIGHT_CYAN,
                2,
                cv2.LINE_AA,
            )

            cv2.circle(
                frame,
                (cx, cy),
                5,
                WHITE,
                -1,
                cv2.LINE_AA,
            )

        # ----------------------------------------------------
        # Grab brackets.
        # ----------------------------------------------------

        if obj.grabbed:

            r = int(
                105 * obj.scale
            )

            bracket = 18

            points = [
                (cx - r, cy - r),
                (cx + r, cy - r),
                (cx + r, cy + r),
                (cx - r, cy + r),
            ]

            for px, py in points:

                x_direction = (
                    bracket
                    if px < cx
                    else -bracket
                )

                y_direction = (
                    bracket
                    if py < cy
                    else -bracket
                )

                cv2.line(
                    frame,
                    (px, py),
                    (
                        px + x_direction,
                        py,
                    ),
                    GREEN,
                    2,
                    cv2.LINE_AA,
                )

                cv2.line(
                    frame,
                    (px, py),
                    (
                        px,
                        py + y_direction,
                    ),
                    GREEN,
                    2,
                    cv2.LINE_AA,
                )

        obj.rotation = original_rotation

    # ========================================================
    # POINTER
    # ========================================================

    def draw_pointer(
        self,
        frame,
        pointer,
        gesture,
    ):

        pointer = self.normalize_pointer(
            pointer
        )

        if pointer is None:
            return

        px = int(pointer[0])
        py = int(pointer[1])

        if gesture == "pinch":

            color = RED

        elif gesture == "peace":

            color = PURPLE

        elif gesture == "point":

            color = BRIGHT_CYAN

        else:

            color = WHITE

        # Target ring.

        cv2.circle(
            frame,
            (px, py),
            18,
            color,
            1,
            cv2.LINE_AA,
        )

        cv2.circle(
            frame,
            (px, py),
            4,
            color,
            -1,
            cv2.LINE_AA,
        )

        # Crosshair.

        cv2.line(
            frame,
            (px - 24, py),
            (px - 8, py),
            color,
            1,
            cv2.LINE_AA,
        )

        cv2.line(
            frame,
            (px + 8, py),
            (px + 24, py),
            color,
            1,
            cv2.LINE_AA,
        )

        cv2.line(
            frame,
            (px, py - 24),
            (px, py - 8),
            color,
            1,
            cv2.LINE_AA,
        )

        cv2.line(
            frame,
            (px, py + 8),
            (px, py + 24),
            color,
            1,
            cv2.LINE_AA,
        )

    # ========================================================
    # CREATE MODE
    # ========================================================

    def draw_create_mode(
        self,
        frame,
    ):

        if not self.create_mode:
            return

        height, width = frame.shape[:2]

        text = "CREATE MODE"

        text_size = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            1,
        )[0]

        x = (
            width - text_size[0]
        ) // 2

        y = 45

        cv2.rectangle(
            frame,
            (
                x - 14,
                y - 23,
            ),
            (
                x + text_size[0] + 14,
                y + 8,
            ),
            DARK,
            -1,
        )

        cv2.rectangle(
            frame,
            (
                x - 14,
                y - 23,
            ),
            (
                x + text_size[0] + 14,
                y + 8,
            ),
            PURPLE,
            1,
        )

        cv2.putText(
            frame,
            text,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            PURPLE,
            1,
            cv2.LINE_AA,
        )

    # ========================================================
    # STATUS
    # ========================================================

    def draw_status(
        self,
        frame,
        gesture="unknown",
    ):

        height, width = frame.shape[:2]

        status = (
            f"GESTURE // "
            f"{gesture.upper()}"
        )

        if self.grabbed_id is not None:

            status += (
                "   |   GRABBING"
            )

        elif self.two_hand_active:

            status += (
                "   |   TWO-HAND 3D CONTROL"
            )

        elif self.selected_id is not None:

            status += (
                "   |   OBJECT SELECTED"
            )

        if self.create_mode:

            status += (
                "   |   CREATE MODE"
            )

        # ----------------------------------------------------
        # Pointer diagnostic.
        # ----------------------------------------------------

        if self.last_pointer is not None:

            status += (
                f"   |   P:"
                f"{int(self.last_pointer[0])},"
                f"{int(self.last_pointer[1])}"
            )

        cv2.putText(
            frame,
            status,
            (
                18,
                height - 18,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            BRIGHT_CYAN,
            1,
            cv2.LINE_AA,
        )

    # ========================================================
    # OBJECT LABEL
    # ========================================================

    def draw_object_labels(
        self,
        frame,
    ):

        for obj in self.objects:

            if not obj.selected:
                continue

            cx = int(
                obj.x * self.width
            )

            cy = int(
                obj.y * self.height
            )

            label = (
                f"OBJ {obj.id} // "
                f"{obj.object_type.upper()}"
            )

            cv2.putText(
                frame,
                label,
                (
                    cx - 55,
                    cy - 115,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                BRIGHT_CYAN,
                1,
                cv2.LINE_AA,
            )

    # ========================================================
    # RENDER
    # ========================================================

    def render(
        self,
        frame,
        pointer=None,
        second_pointer=None,
        gesture="unknown",
        second_gesture="unknown",
    ):

        self.height, self.width = (
            frame.shape[:2]
        )

        # ----------------------------------------------------
        # Draw virtual objects.
        # ----------------------------------------------------

        for obj in list(self.objects):

            self._draw_object(
                frame,
                obj,
            )

        # ----------------------------------------------------
        # Labels.
        # ----------------------------------------------------

        self.draw_object_labels(
            frame
        )

        # ----------------------------------------------------
        # Keyboard.
        # ----------------------------------------------------

        self.keyboard.draw(
            frame,
            pointer=pointer,
            gesture=gesture,
        )

        # ----------------------------------------------------
        # Main pointer.
        # ----------------------------------------------------

        self.draw_pointer(
            frame,
            pointer,
            gesture,
        )

        # ----------------------------------------------------
        # Second pointer.
        # ----------------------------------------------------

        if second_pointer is not None:

            self.draw_pointer(
                frame,
                second_pointer,
                second_gesture,
            )

        # ----------------------------------------------------
        # Create mode.
        # ----------------------------------------------------

        self.draw_create_mode(
            frame
        )

        # ----------------------------------------------------
        # Status.
        # ----------------------------------------------------

        self.draw_status(
            frame,
            gesture,
        )