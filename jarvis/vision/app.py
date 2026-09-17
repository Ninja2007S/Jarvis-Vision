from __future__ import annotations

import time

import cv2

from ..hands.tracker import HandTracker

from .camera import Camera
from .controller import VisionController
from .detector import ObjectDetector
from .ar_bridge import ARBridge
from .hologram_renderer import HologramRenderer


# ============================================================
# DISPLAY
# ============================================================

WINDOW_NAME = "JARVIS Vision"

DISPLAY_WIDTH = 1100
DISPLAY_HEIGHT = 825


# ============================================================
# DRAW HAND
# ============================================================

def draw_hand(
    frame,
    hand,
    gesture,
    width: int,
    height: int,
) -> None:

    if hand is None:
        return

    points = hand.points

    if len(points) < 21:
        return

    connections = [

        # Thumb
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),

        # Index
        (0, 5),
        (5, 6),
        (6, 7),
        (7, 8),

        # Middle
        (0, 9),
        (9, 10),
        (10, 11),
        (11, 12),

        # Ring
        (0, 13),
        (13, 14),
        (14, 15),
        (15, 16),

        # Pinky
        (0, 17),
        (17, 18),
        (18, 19),
        (19, 20),

        # Palm
        (5, 9),
        (9, 13),
        (13, 17),
    ]

    gesture_name = str(
        gesture
    ).lower()

    # ========================================================
    # SKELETON
    # ========================================================

    for a, b in connections:

        x1, y1 = HandTracker.get_pixel_point(
            hand,
            a,
            width,
            height,
        )

        x2, y2 = HandTracker.get_pixel_point(
            hand,
            b,
            width,
            height,
        )

        cv2.line(
            frame,
            (int(x1), int(y1)),
            (int(x2), int(y2)),
            (80, 180, 255),
            2,
            cv2.LINE_AA,
        )

    # ========================================================
    # LANDMARKS
    # ========================================================

    for i in range(len(points)):

        x, y = HandTracker.get_pixel_point(
            hand,
            i,
            width,
            height,
        )

        radius = (
            7
            if i == 8
            else 4
        )

        cv2.circle(
            frame,
            (int(x), int(y)),
            radius,
            (255, 255, 255),
            -1,
            cv2.LINE_AA,
        )

    # ========================================================
    # INDEX
    # ========================================================

    ix, iy = (
        HandTracker.get_index_fingertip(
            hand,
            width,
            height,
        )
    )

    ix = int(ix)
    iy = int(iy)

    # ========================================================
    # THUMB
    # ========================================================

    tx, ty = HandTracker.get_pixel_point(
        hand,
        4,
        width,
        height,
    )

    tx = int(tx)
    ty = int(ty)

    # ========================================================
    # PINCH MIDPOINT
    # ========================================================

    px = int(
        (tx + ix) * 0.5
    )

    py = int(
        (ty + iy) * 0.5
    )

    # ========================================================
    # INTERACTION VISUAL
    # ========================================================

    if gesture_name == "pinch":

        cv2.line(
            frame,
            (tx, ty),
            (ix, iy),
            (0, 255, 120),
            2,
            cv2.LINE_AA,
        )

        cv2.circle(
            frame,
            (px, py),
            17,
            (0, 255, 120),
            2,
            cv2.LINE_AA,
        )

        cv2.circle(
            frame,
            (px, py),
            4,
            (0, 255, 120),
            -1,
            cv2.LINE_AA,
        )

    elif gesture_name == "peace":

        cv2.circle(
            frame,
            (ix, iy),
            14,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        cv2.circle(
            frame,
            (ix, iy),
            4,
            (0, 255, 0),
            -1,
            cv2.LINE_AA,
        )

    elif gesture_name == "point":

        cv2.circle(
            frame,
            (ix, iy),
            16,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.circle(
            frame,
            (ix, iy),
            4,
            (0, 255, 255),
            -1,
            cv2.LINE_AA,
        )

        # Crosshair makes the actual interaction
        # coordinate extremely obvious.

        cv2.line(
            frame,
            (ix - 22, iy),
            (ix + 22, iy),
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )

        cv2.line(
            frame,
            (ix, iy - 22),
            (ix, iy + 22),
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )

    else:

        cv2.circle(
            frame,
            (ix, iy),
            10,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    # ========================================================
    # LABEL
    # ========================================================

    label_x = (
        px
        if gesture_name == "pinch"
        else ix
    )

    label_y = (
        py
        if gesture_name == "pinch"
        else iy
    )

    cv2.putText(
        frame,
        f"{hand.handedness}: {gesture_name.upper()}",
        (
            max(10, label_x - 90),
            max(25, label_y - 22),
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (0, 255, 255),
        1,
        cv2.LINE_AA,
    )


# ============================================================
# DRAW PHYSICAL OBJECT
# ============================================================

def draw_object(
    frame,
    obj,
    selected=False,
    targeted=False,
) -> None:

    box = obj.box

    x1 = int(box.x1)
    y1 = int(box.y1)

    x2 = int(box.x2)
    y2 = int(box.y2)

    label_lower = obj.label.lower()

    if selected:

        color = (
            0,
            255,
            0,
        )

        thickness = 4

    elif targeted:

        color = (
            0,
            255,
            255,
        )

        thickness = 3

    elif label_lower == "person":

        color = (
            120,
            120,
            180,
        )

        thickness = 1

    else:

        color = (
            100,
            220,
            255,
        )

        thickness = 2

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        color,
        thickness,
        cv2.LINE_AA,
    )

    label = (
        f"{obj.label} "
        f"{obj.confidence:.2f}"
    )

    if selected:

        label = (
            "SELECTED: "
            + label
        )

    elif targeted:

        label = (
            "TARGET: "
            + label
        )

    cv2.putText(
        frame,
        label,
        (
            x1,
            max(25, y1 - 10),
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        1,
        cv2.LINE_AA,
    )


# ============================================================
# HUD
# ============================================================

def draw_hud(
    frame,
    controller,
    fps,
    hologram_count,
    create_mode=False,
    keyboard_visible=False,
) -> None:

    height, width = frame.shape[:2]

    state = controller.state

    # ========================================================
    # HEADER
    # ========================================================

    cv2.putText(
        frame,
        "JARVIS",
        (18, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (100, 220, 255),
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        f"{fps:.0f} FPS",
        (18, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (100, 255, 150),
        1,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        f"{width}x{height}",
        (18, 69),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
        (150, 220, 255),
        1,
        cv2.LINE_AA,
    )

    # ========================================================
    # HOLOGRAM STATUS
    # ========================================================

    right_x = width - 185

    cv2.putText(
        frame,
        f"HOLO {hologram_count}",
        (right_x, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (0, 255, 255),
        1,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        f"OBJ {len(state.objects)}",
        (right_x, 48),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (100, 220, 255),
        1,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        f"HANDS {len(state.hands)}",
        (right_x, 67),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (100, 220, 255),
        1,
        cv2.LINE_AA,
    )

    keyboard_status = (
        "KEYBOARD ON"
        if keyboard_visible
        else "KEYBOARD OFF"
    )

    cv2.putText(
        frame,
        keyboard_status,
        (right_x, 87),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.32,
        (180, 220, 255),
        1,
        cv2.LINE_AA,
    )

    # ========================================================
    # GESTURE
    # ========================================================

    gesture_text = "NONE"

    if state.hands:

        gesture_text = str(
            state.hands[0].get(
                "gesture",
                "unknown",
            )
        ).upper()

    cv2.putText(
        frame,
        f"GESTURE {gesture_text}",
        (18, height - 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (0, 255, 255),
        1,
        cv2.LINE_AA,
    )

    # ========================================================
    # TARGET
    # ========================================================

    target = controller.current_target

    if target is not None:

        cv2.putText(
            frame,
            f"TARGET {target.label}",
            (18, height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )

    # ========================================================
    # SELECTED
    # ========================================================

    selected = controller.selected_object

    if selected is not None:

        cv2.putText(
            frame,
            f"PHYSICAL {selected.label}",
            (
                width // 2 - 80,
                height - 20,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (0, 255, 120),
            1,
            cv2.LINE_AA,
        )

    # ========================================================
    # CREATE MODE
    # ========================================================

    if create_mode:

        cv2.putText(
            frame,
            "CREATE MODE",
            (
                width // 2 - 80,
                28,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

    # ========================================================
    # VISION STATUS
    # ========================================================

    cv2.circle(
        frame,
        (width - 20, 110),
        4,
        (0, 255, 120),
        -1,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        "VISION",
        (width - 82, 114),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
        (150, 255, 180),
        1,
        cv2.LINE_AA,
    )


# ============================================================
# CONTROLLER HAND STATE
# ============================================================

def get_hand_state(
    controller,
    handedness,
):

    wanted = str(
        handedness
    ).lower()

    for hand_state in controller.state.hands:

        current = str(
            hand_state.get(
                "handedness",
                "",
            )
        ).lower()

        if current == wanted:
            return hand_state

    return None


# ============================================================
# MEDIAPIPE HAND BY SIDE
# ============================================================

def get_hand_by_side(
    hands,
    side,
):

    wanted = str(
        side
    ).lower()

    for hand in hands:

        current = str(
            getattr(
                hand,
                "handedness",
                "",
            )
        ).lower()

        if current == wanted:
            return hand

    return None


# ============================================================
# LIVE INTERACTION POINTER
# ============================================================

def get_interaction_pointer(
    hand,
    width: int,
    height: int,
):
    """
    ALWAYS return the real index fingertip in PIXELS.

    Never return hand.points[8] directly.

    MediaPipe:
        0.0 -> 1.0 normalized

    Renderer:
        actual camera pixel coordinates
    """

    if hand is None:
        return None

    if len(hand.points) < 9:
        return None

    return HandTracker.get_index_fingertip(
        hand,
        width,
        height,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    # ========================================================
    # CAMERA
    # ========================================================

    camera = Camera()

    # ========================================================
    # YOLO
    # ========================================================

    detector = ObjectDetector(
        model_name="yolo11n.pt",

        # Higher confidence removes many false positives.
        confidence=0.35,

        # Run YOLO less frequently.
        detection_interval=3,

        # Smaller inference size improves responsiveness.
        image_size=512,
    )

    # ========================================================
    # MEDIAPIPE
    # ========================================================

    hand_tracker = HandTracker()

    # ========================================================
    # CONTROLLER
    # ========================================================

    controller = VisionController(
        stable_frames=3,
        pinch_release_frames=4,
    )

    # ========================================================
    # HOLOGRAM
    # ========================================================

    holograms = HologramRenderer()

    # ========================================================
    # AR BRIDGE
    # ========================================================

    ar_bridge = ARBridge()

    controller.subscribe(
        ar_bridge.handle_event
    )

    # ========================================================
    # DEBUG EVENTS
    # ========================================================

    def on_vision_event(event):

        print(
            f"[VISION EVENT] "
            f"{event.type}: "
            f"{event.data}"
        )

    controller.subscribe(
        on_vision_event
    )

    # ========================================================
    # CAMERA START
    # ========================================================

    camera.start()

    # ========================================================
    # WINDOW
    # ========================================================

    cv2.namedWindow(
        WINDOW_NAME,
        cv2.WINDOW_NORMAL,
    )

    cv2.resizeWindow(
        WINDOW_NAME,
        DISPLAY_WIDTH,
        DISPLAY_HEIGHT,
    )

    # ========================================================
    # STARTUP
    # ========================================================

    print()
    print("=" * 72)
    print("                    JARVIS VISION ONLINE")
    print("=" * 72)

    print("Camera:             ACTIVE")
    print("Capture:            1280 x 720")
    print("Display:            1100 x 825")
    print("YOLO:               ACTIVE")
    print("MediaPipe:          ACTIVE")
    print("Gesture engine:     ACTIVE")
    print("Hologram engine:    ACTIVE")

    print()
    print("ONE-HAND HOLOGRAM")

    print("  POINT              -> TARGET")
    print("  PINCH SELECTED     -> GRAB")
    print("  PINCH + MOVE       -> MOVE")
    print("  RELEASE            -> DROP")

    print()
    print("CREATE")

    print("  PEACE              -> CREATE MODE")
    print("  PEACE + PINCH      -> MATERIALIZE")
    print("  PINCH + MOVE       -> MOVE NEW OBJECT")
    print("  RELEASE            -> DROP")

    print()
    print("IMPORTANT")

    print("  EMPTY-SPACE PINCH  -> NOTHING")
    print("  PERSON             -> NOT SELECTABLE")

    print()
    print("TWO-HAND")

    print("  PINCH BOTH HANDS   -> SCALE / ROTATE / MOVE")
    print("  RELEASE            -> LOCK RESULT")

    print()
    print("KEYBOARD")

    print("  POINT              -> HOVER KEY")
    print("  PINCH KEY          -> TYPE")
    print("  K                  -> TOGGLE KEYBOARD")

    print()
    print("TEST")

    print("  N                  -> ARM CREATE MODE")
    print("  C                  -> CANCEL CREATE MODE")

    print()
    print("Browser camera should remain CLOSED.")
    print("Press Q to quit.")

    print("=" * 72)

    # ========================================================
    # FPS
    # ========================================================

    last_time = time.perf_counter()

    fps = 0.0

    # ========================================================
    # MAIN LOOP
    # ========================================================

    try:

        while True:

            # =================================================
            # CAMERA
            # =================================================

            packet = camera.read()

            if packet is None:
                continue

            frame = packet.frame.copy()

            height, width = frame.shape[:2]

            # =================================================
            # YOLO
            # =================================================

            objects = detector.detect(
                frame
            )

            controller.update_objects(
                objects=objects,
                width=width,
                height=height,
            )

            # =================================================
            # MEDIAPIPE
            # =================================================

            frame_rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            hands = hand_tracker.process(
                frame_rgb
            )

            controller.update_hands(
                hands
            )

            # =================================================
            # FIND HANDS
            # =================================================

            right_hand = get_hand_by_side(
                hands,
                "Right",
            )

            left_hand = get_hand_by_side(
                hands,
                "Left",
            )

            # =================================================
            # RIGHT GESTURE
            # =================================================

            right_state = get_hand_state(
                controller,
                "Right",
            )

            right_gesture = (
                str(
                    right_state.get(
                        "gesture",
                        "unknown",
                    )
                ).lower()
                if right_state is not None
                else "unknown"
            )

            # =================================================
            # LEFT GESTURE
            # =================================================

            left_state = get_hand_state(
                controller,
                "Left",
            )

            left_gesture = (
                str(
                    left_state.get(
                        "gesture",
                        "unknown",
                    )
                ).lower()
                if left_state is not None
                else "unknown"
            )

            # =================================================
            # PRIMARY HAND
            # =================================================

            active_hand_name = (
                controller.active_hand
            )

            if (
                active_hand_name is not None
                and
                active_hand_name.lower() == "right"
                and
                right_hand is not None
            ):

                primary_hand = right_hand
                primary_gesture = right_gesture

            elif (
                active_hand_name is not None
                and
                active_hand_name.lower() == "left"
                and
                left_hand is not None
            ):

                primary_hand = left_hand
                primary_gesture = left_gesture

            elif right_hand is not None:

                primary_hand = right_hand
                primary_gesture = right_gesture

            elif left_hand is not None:

                primary_hand = left_hand
                primary_gesture = left_gesture

            else:

                primary_hand = None
                primary_gesture = "unknown"

            # =================================================
            # PRIMARY POINTER
            #
            # THIS IS NOW DEFINITIVELY PIXELS.
            # =================================================

            first_pointer = get_interaction_pointer(
                primary_hand,
                width,
                height,
            )

            # =================================================
            # SECONDARY HAND
            # =================================================

            if primary_hand is right_hand:

                secondary_hand = left_hand
                secondary_gesture = left_gesture

            elif primary_hand is left_hand:

                secondary_hand = right_hand
                secondary_gesture = right_gesture

            else:

                secondary_hand = None
                secondary_gesture = "unknown"

            # =================================================
            # SECOND POINTER
            # =================================================

            second_pointer = get_interaction_pointer(
                secondary_hand,
                width,
                height,
            )

            # =================================================
            # PHYSICAL TARGET
            # =================================================

            physical_target_exists = (
                controller.current_target is not None
            )

            # =================================================
            # HOLOGRAM UPDATE
            # =================================================

            holograms.update(
                pointer=first_pointer,
                gesture=primary_gesture,
                physical_target_exists=(
                    physical_target_exists
                ),
                second_pointer=second_pointer,
                second_gesture=secondary_gesture,
            )

            # =================================================
            # DRAW PHYSICAL OBJECTS
            # =================================================

            selected_object = (
                controller.selected_object
            )

            target_object = (
                controller.current_target
            )

            for obj in objects:

                is_selected = (
                    selected_object is not None
                    and
                    selected_object.id == obj.id
                )

                is_targeted = (
                    target_object is not None
                    and
                    target_object.id == obj.id
                )

                draw_object(
                    frame,
                    obj,
                    selected=is_selected,
                    targeted=is_targeted,
                )

            # =================================================
            # DRAW HANDS
            # =================================================

            for hand in hands:

                hand_state = get_hand_state(
                    controller,
                    hand.handedness,
                )

                gesture_for_hand = (
                    str(
                        hand_state.get(
                            "gesture",
                            "unknown",
                        )
                    ).lower()
                    if hand_state is not None
                    else "unknown"
                )

                draw_hand(
                    frame,
                    hand,
                    gesture_for_hand,
                    width,
                    height,
                )

            # =================================================
            # HOLOGRAM RENDER
            # =================================================

            holograms.render(
                frame,
                pointer=first_pointer,
                gesture=primary_gesture,
            )

            # =================================================
            # FPS
            # =================================================

            now = time.perf_counter()

            instant_fps = (
                1.0
                /
                max(
                    now - last_time,
                    1e-6,
                )
            )

            fps = (
                fps * 0.90
                +
                instant_fps * 0.10
            )

            last_time = now

            # =================================================
            # HUD
            # =================================================

            draw_hud(
                frame,
                controller,
                fps,
                len(holograms.objects),
                create_mode=(
                    holograms.create_mode
                ),
                keyboard_visible=(
                    holograms.keyboard.visible
                ),
            )

            # =================================================
            # DISPLAY
            # =================================================

            cv2.imshow(
                WINDOW_NAME,
                frame,
            )

            # =================================================
            # KEYBOARD
            # =================================================

            key = cv2.waitKey(1) & 0xFF

            # -------------------------------------------------
            # QUIT
            # -------------------------------------------------

            if key in (
                ord("q"),
                ord("Q"),
            ):

                break

            # -------------------------------------------------
            # TOGGLE KEYBOARD
            # -------------------------------------------------

            if key in (
                ord("k"),
                ord("K"),
            ):

                holograms.keyboard.visible = (
                    not holograms.keyboard.visible
                )

                print(
                    "[JARVIS] Virtual keyboard:",
                    (
                        "ON"
                        if holograms.keyboard.visible
                        else "OFF"
                    ),
                )

            # -------------------------------------------------
            # MANUAL CREATE
            # -------------------------------------------------

            if key in (
                ord("n"),
                ord("N"),
            ):

                holograms.enter_create_mode()

                print(
                    "[JARVIS] CREATE MODE armed"
                )

            # -------------------------------------------------
            # CANCEL
            # -------------------------------------------------

            if key in (
                ord("c"),
                ord("C"),
            ):

                holograms.exit_create_mode()

                print(
                    "[JARVIS] CREATE MODE cancelled"
                )

    finally:

        try:

            hand_tracker.close()

        except Exception:

            pass

        camera.stop()

        cv2.destroyAllWindows()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()