from __future__ import annotations

import time
from typing import Any, Callable

from ..hands.gestures import (
    Stabilizer,
    classify,
)

from .hand_fusion import (
    create_pointing_target,
)

from .objects import (
    DetectedObject,
    VisionState,
)


class VisionController:

    # ========================================================
    # Selection configuration
    # ========================================================

    NON_SELECTABLE_LABELS = {
        "person",
        "people",
        "face",
    }

    # YOLO detections below this confidence are not allowed
    # to become interaction targets.
    MIN_SELECTION_CONFIDENCE = 0.40

    # Pointer must move this much in normalized coordinates
    # before another vision.pointing event is emitted.
    #
    # 0.012 = approximately 7.7 px at 640x480.
    POINTER_EVENT_THRESHOLD = 0.012

    # Target must remain present for this many detections
    # before becoming the active target.
    TARGET_CONFIRM_FRAMES = 1

    # Keep target alive for a few frames when YOLO temporarily
    # misses it.
    TARGET_LOCK_FRAMES = 4

    def __init__(
        self,
        stable_frames: int = 3,
        pinch_release_frames: int = 4,
    ) -> None:

        self.stable_frames = max(
            1,
            stable_frames,
        )

        self.pinch_release_frames = max(
            1,
            pinch_release_frames,
        )

        # ====================================================
        # Objects
        # ====================================================

        self.objects: list[
            DetectedObject
        ] = []

        self.camera_width = 0
        self.camera_height = 0

        # ====================================================
        # Pointer
        # ====================================================

        self.pointer: tuple[
            float,
            float,
        ] | None = None

        # ====================================================
        # Target / selection
        # ====================================================

        self.current_target: (
            DetectedObject | None
        ) = None

        self.selected_object: (
            DetectedObject | None
        ) = None

        self._target_candidate_id: (
            int | None
        ) = None

        self._target_candidate_frames = 0

        self._target_lock_frames = 0

        # ====================================================
        # Pointer event throttling
        # ====================================================

        self._last_emitted_pointer_x: (
            float | None
        ) = None

        self._last_emitted_pointer_y: (
            float | None
        ) = None

        self._last_emitted_target_id: (
            int | None
        ) = None

        # ====================================================
        # Active hand
        # ====================================================

        self.active_hand: str | None = None

        self._candidate_hand: str | None = None

        self._candidate_hand_frames = 0

        # ====================================================
        # Gestures
        # ====================================================

        self._last_gesture: dict[
            str,
            str,
        ] = {}

        self._gesture_stabilizers: dict[
            str,
            Stabilizer,
        ] = {}

        # ====================================================
        # Pinch state
        # ====================================================

        self._pinching: dict[
            str,
            bool,
        ] = {}

        self._pinch_release_count: dict[
            str,
            int,
        ] = {}

        # ====================================================
        # Missing hands
        # ====================================================

        self._missing_hand_frames: dict[
            str,
            int,
        ] = {}

        # ====================================================
        # Subscribers
        # ====================================================

        self._subscribers: list[
            Callable[[Any], None]
        ] = []

        # ====================================================
        # Object event throttling
        # ====================================================

        self._last_object_event_signature = None

        self._last_object_event_time = 0.0

        # ====================================================
        # Vision state
        # ====================================================

        self.state = VisionState(
            timestamp=time.time()
        )

    # ========================================================
    # Events
    # ========================================================

    def subscribe(
        self,
        callback: Callable[[Any], None],
    ) -> None:

        self._subscribers.append(
            callback
        )

    def set_event_callback(
        self,
        callback,
    ) -> None:

        self._subscribers = [callback]

    def _emit(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:

        payload = data or {}

        event = type(
            "VisionEvent",
            (),
            {
                "type": event_type,
                "data": payload,
            },
        )()

        for callback in list(
            self._subscribers
        ):

            try:
                callback(event)

            except TypeError:

                # Compatibility with older
                # callback(event_type, data)
                try:
                    callback(
                        event_type,
                        payload,
                    )

                except Exception:
                    pass

            except Exception:
                pass

    # ========================================================
    # Objects
    # ========================================================

    def update_objects(
        self,
        objects: list[DetectedObject],
        width: int,
        height: int,
    ) -> None:

        self.objects = objects

        self.camera_width = width
        self.camera_height = height

        self.state.objects = objects
        self.state.camera_width = width
        self.state.camera_height = height
        self.state.timestamp = time.time()

        self._emit_objects_if_changed()

        # ----------------------------------------------------
        # Refresh selected object reference
        # ----------------------------------------------------

        if self.selected_object is not None:

            selected_id = (
                self.selected_object.id
            )

            replacement = next(
                (
                    obj
                    for obj in objects
                    if obj.id == selected_id
                ),
                None,
            )

            if replacement is not None:

                self.selected_object = (
                    replacement
                )

        # ----------------------------------------------------
        # Refresh target reference
        # ----------------------------------------------------

        if self.current_target is not None:

            target_id = (
                self.current_target.id
            )

            replacement = next(
                (
                    obj
                    for obj in objects
                    if obj.id == target_id
                ),
                None,
            )

            if replacement is not None:

                self.current_target = (
                    replacement
                )

    def _emit_objects_if_changed(
        self,
    ) -> None:

        signature = tuple(
            sorted(
                (
                    obj.id,
                    obj.label,
                    round(
                        obj.confidence,
                        1,
                    ),
                )
                for obj in self.objects
            )
        )

        now = time.time()

        # Don't spam identical object lists.
        if (
            signature
            == self._last_object_event_signature
            and now
            - self._last_object_event_time
            < 0.75
        ):
            return

        self._last_object_event_signature = (
            signature
        )

        self._last_object_event_time = now

        self._emit(
            "vision.object_detected",
            {
                "count": len(self.objects),
                "objects": [
                    {
                        "id": obj.id,
                        "label": obj.label,
                        "confidence": obj.confidence,
                    }
                    for obj in self.objects
                ],
            },
        )

    # ========================================================
    # Selectable objects
    # ========================================================

    def _get_selectable_objects(
        self,
    ) -> list[DetectedObject]:

        selectable: list[
            DetectedObject
        ] = []

        for obj in self.objects:

            label = str(
                getattr(
                    obj,
                    "label",
                    "",
                )
            ).strip().lower()

            confidence = float(
                getattr(
                    obj,
                    "confidence",
                    0.0,
                )
            )

            # Never allow people to be selected.
            if label in self.NON_SELECTABLE_LABELS:
                continue

            # Reject weak YOLO detections.
            if (
                confidence
                < self.MIN_SELECTION_CONFIDENCE
            ):
                continue

            selectable.append(obj)

        return selectable

    # ========================================================
    # Hands
    # ========================================================

    def update_hands(
        self,
        hands: list,
    ) -> None:

        seen: set[str] = set()

        state_hands = []

        for hand in hands:

            handedness = hand.handedness

            seen.add(handedness)

            if (
                handedness
                not in self._gesture_stabilizers
            ):

                self._gesture_stabilizers[
                    handedness
                ] = Stabilizer(
                    self.stable_frames
                )

            previous = self._last_gesture.get(
                handedness
            )

            raw_gesture = classify(
                hand,
                previous_name=previous,
            )

            raw_name = raw_gesture.name

            stabilizer = (
                self._gesture_stabilizers[
                    handedness
                ]
            )

            settled, changed = (
                stabilizer.update(
                    raw_name
                )
            )

            # During startup, use raw gesture.
            gesture_name = (
                settled
                if settled is not None
                else raw_name
            )

            previous_name = (
                self._last_gesture.get(
                    handedness
                )
            )

            self._last_gesture[
                handedness
            ] = gesture_name

            pinch_active = (
                gesture_name == "pinch"
            )

            state_hands.append(
                {
                    "handedness": handedness,
                    "gesture": gesture_name,
                    "raw_gesture": raw_name,
                    "pinch_distance": (
                        raw_gesture.pinch_distance
                    ),
                    "pointer": (
                        raw_gesture.pointer
                    ),
                }
            )

            if (
                previous_name is not None
                and previous_name
                != gesture_name
            ):

                self._emit(
                    "hand.gesture",
                    {
                        "hand": handedness,
                        "previous": previous_name,
                        "current": gesture_name,
                        "raw": raw_name,
                    },
                )

            self._process_hand(
                hand,
                raw_gesture,
                gesture_name,
                pinch_active,
            )

            self._missing_hand_frames[
                handedness
            ] = 0

        # ----------------------------------------------------
        # Missing-hand protection
        # ----------------------------------------------------

        for handedness in list(
            self._missing_hand_frames
        ):

            if handedness in seen:
                continue

            self._missing_hand_frames[
                handedness
            ] += 1

            # Allow several frames of tracking loss.
            if (
                self._missing_hand_frames[
                    handedness
                ]
                <= 8
            ):
                continue

            if (
                self.active_hand
                == handedness
            ):

                self._release_active_hand(
                    handedness
                )

        self.state.hands = state_hands
        self.state.timestamp = time.time()

    # ========================================================
    # Hand processing
    # ========================================================

    def _process_hand(
        self,
        hand,
        gesture,
        gesture_name: str,
        pinch_active: bool,
    ) -> None:

        handedness = hand.handedness

        # ----------------------------------------------------
        # Point
        # ----------------------------------------------------

        if gesture_name == "point":

            if self._activate_hand(
                handedness
            ):

                self._update_pointer(
                    hand,
                    gesture,
                )

            return

        # ----------------------------------------------------
        # Pinch
        # ----------------------------------------------------

        if gesture_name == "pinch":

            # If there is no active hand yet,
            # allow pinch to activate it.
            if self.active_hand is None:

                self._activate_hand(
                    handedness,
                    immediate=True,
                )

            if self.active_hand == handedness:

                self._update_pointer(
                    hand,
                    gesture,
                )

                self._process_pinch(
                    hand,
                    gesture,
                )

            return

        # ----------------------------------------------------
        # Other gestures while pinching
        # ----------------------------------------------------

        if self.active_hand == handedness:

            if self._pinching.get(
                handedness,
                False,
            ):

                # Do NOT instantly release because
                # MediaPipe classified one frame incorrectly.
                self._pinch_release_count[
                    handedness
                ] = (
                    self._pinch_release_count.get(
                        handedness,
                        0,
                    )
                    + 1
                )

                if (
                    self._pinch_release_count[
                        handedness
                    ]
                    >= self.pinch_release_frames
                ):

                    self.release_pinch(
                        handedness
                    )

            elif gesture_name in (
                "open_palm",
                "fist",
                "peace",
                "thumbs_up",
                "unknown",
            ):

                self._release_active_hand(
                    handedness
                )

    # ========================================================
    # Active hand
    # ========================================================

    def _activate_hand(
        self,
        handedness: str,
        immediate: bool = False,
    ) -> bool:

        if self.active_hand == handedness:
            return True

        if self.active_hand is not None:
            return False

        if immediate:

            self.active_hand = handedness

            self._candidate_hand = None
            self._candidate_hand_frames = 0

            self._emit(
                "active_hand_changed",
                {
                    "hand": handedness,
                },
            )

            return True

        if (
            self._candidate_hand
            == handedness
        ):

            self._candidate_hand_frames += 1

        else:

            self._candidate_hand = handedness
            self._candidate_hand_frames = 1

        if (
            self._candidate_hand_frames
            < self.stable_frames
        ):

            return False

        self.active_hand = handedness

        self._candidate_hand = None
        self._candidate_hand_frames = 0

        self._emit(
            "active_hand_changed",
            {
                "hand": handedness,
            },
        )

        return True

    # ========================================================
    # Pointer
    # ========================================================

    def _update_pointer(
        self,
        hand,
        gesture,
    ) -> None:

        if gesture.pointer is None:
            return

        self.pointer = gesture.pointer

        self.state.pointer_x = (
            self.pointer[0]
        )

        self.state.pointer_y = (
            self.pointer[1]
        )

        # ====================================================
        # Only selectable objects participate in targeting.
        # ====================================================

        selectable_objects = (
            self._get_selectable_objects()
        )

        target_state = (
            create_pointing_target(
                pointer_normalized=self.pointer,
                width=self.camera_width,
                height=self.camera_height,
                objects=selectable_objects,
                is_pointing=True,
            )
        )

        new_target = target_state.object

        # ====================================================
        # Target hysteresis
        # ====================================================

        if new_target is None:

            if self._target_lock_frames > 0:

                self._target_lock_frames -= 1

            else:

                self.current_target = None

                self._target_candidate_id = None

                self._target_candidate_frames = 0

        else:

            # ------------------------------------------------
            # Existing target remains under pointer.
            # ------------------------------------------------

            if (
                self.current_target is not None
                and self.current_target.id
                == new_target.id
            ):

                self.current_target = (
                    new_target
                )

                self._target_candidate_id = None

                self._target_candidate_frames = 0

                self._target_lock_frames = (
                    self.TARGET_LOCK_FRAMES
                )

            # ------------------------------------------------
            # Candidate target continues to be seen.
            # ------------------------------------------------

            elif (
                self._target_candidate_id
                == new_target.id
            ):

                self._target_candidate_frames += 1

                if (
                    self._target_candidate_frames
                    >= self.TARGET_CONFIRM_FRAMES
                ):

                    self.current_target = (
                        new_target
                    )

                    self._target_candidate_id = None

                    self._target_candidate_frames = 0

                    self._target_lock_frames = (
                        self.TARGET_LOCK_FRAMES
                    )

            # ------------------------------------------------
            # New candidate target.
            # ------------------------------------------------

            else:

                self._target_candidate_id = (
                    new_target.id
                )

                self._target_candidate_frames = 1

        target = self.current_target

        # ====================================================
        # Event throttling
        # ====================================================

        current_x = float(
            self.pointer[0]
        )

        current_y = float(
            self.pointer[1]
        )

        current_target_id = (
            target.id
            if target is not None
            else None
        )

        previous_x = (
            self._last_emitted_pointer_x
        )

        previous_y = (
            self._last_emitted_pointer_y
        )

        previous_target_id = (
            self._last_emitted_target_id
        )

        if (
            previous_x is None
            or previous_y is None
        ):

            pointer_moved = True

        else:

            dx = abs(
                current_x
                - previous_x
            )

            dy = abs(
                current_y
                - previous_y
            )

            pointer_moved = (
                dx
                >= self.POINTER_EVENT_THRESHOLD
                or dy
                >= self.POINTER_EVENT_THRESHOLD
            )

        target_changed = (
            current_target_id
            != previous_target_id
        )

        # ====================================================
        # Emit only meaningful pointer changes.
        # ====================================================

        if (
            pointer_moved
            or target_changed
        ):

            self._emit(
                "vision.pointing",
                {
                    "hand": hand.handedness,
                    "x": current_x,
                    "y": current_y,
                    "pointing": True,
                    "target": (
                        target.label
                        if target is not None
                        else None
                    ),
                    "target_id": (
                        target.id
                        if target is not None
                        else None
                    ),
                },
            )

            self._last_emitted_pointer_x = (
                current_x
            )

            self._last_emitted_pointer_y = (
                current_y
            )

            self._last_emitted_target_id = (
                current_target_id
            )

    # ========================================================
    # Pinch
    # ========================================================

    def _process_pinch(
        self,
        hand,
        gesture,
    ) -> None:

        handedness = hand.handedness

        already_pinching = (
            self._pinching.get(
                handedness,
                False,
            )
        )

        self._pinch_release_count[
            handedness
        ] = 0

        if already_pinching:
            return

        self._pinching[
            handedness
        ] = True

        self._emit(
            "hand.pinch_start",
            {
                "hand": handedness,
                "pinch_distance": (
                    gesture.pinch_distance
                ),
            },
        )

        # ====================================================
        # Select current target.
        #
        # IMPORTANT:
        # Use exactly the same filtering as _update_pointer().
        # ====================================================

        target = self.current_target

        # If no current target exists, perform one final
        # filtered target lookup.
        if target is None:

            selectable_objects = (
                self._get_selectable_objects()
            )

            target_state = (
                create_pointing_target(
                    pointer_normalized=(
                        gesture.pointer
                    ),
                    width=self.camera_width,
                    height=self.camera_height,
                    objects=selectable_objects,
                    is_pointing=True,
                )
            )

            target = target_state.object

        # ====================================================
        # Physical object selected
        # ====================================================

        if target is not None:

            self.select(target)

        else:

            self._emit(
                "selection_missed",
                {
                    "hand": handedness,
                },
            )

    # ========================================================
    # Selection
    # ========================================================

    def select(
        self,
        obj: DetectedObject,
    ) -> None:

        # Safety check: never allow person selection even if
        # another caller attempts to select it directly.

        label = str(
            getattr(
                obj,
                "label",
                "",
            )
        ).strip().lower()

        confidence = float(
            getattr(
                obj,
                "confidence",
                0.0,
            )
        )

        if label in self.NON_SELECTABLE_LABELS:

            return

        if (
            confidence
            < self.MIN_SELECTION_CONFIDENCE
        ):

            return

        self.selected_object = obj

        self.state.selected_object = (
            obj.label
        )

        self._emit(
            "vision.object_selected",
            {
                "object_id": obj.id,
                "label": obj.label,
                "confidence": obj.confidence,
            },
        )

    def clear_selection(
        self,
    ) -> None:

        self.selected_object = None

        self.state.selected_object = None

    # ========================================================
    # Pinch release
    # ========================================================

    def release_pinch(
        self,
        handedness: str,
    ) -> None:

        if not self._pinching.get(
            handedness,
            False,
        ):
            return

        self._pinching[
            handedness
        ] = False

        self._pinch_release_count[
            handedness
        ] = 0

        self._emit(
            "hand.pinch_end",
            {
                "hand": handedness,
            },
        )

        # Selection intentionally remains active after release.

    # ========================================================
    # Active-hand release
    # ========================================================

    def _release_active_hand(
        self,
        handedness: str,
    ) -> None:

        if self.active_hand != handedness:
            return

        if self._pinching.get(
            handedness,
            False,
        ):

            self.release_pinch(
                handedness
            )

        self._emit(
            "target_lost",
            {
                "object_id": (
                    self.current_target.id
                    if self.current_target
                    else None
                ),
                "label": (
                    self.current_target.label
                    if self.current_target
                    else None
                ),
            },
        )

        self.current_target = None

        self.pointer = None

        self.state.pointer_x = None
        self.state.pointer_y = None

        self.active_hand = None

        self._candidate_hand = None
        self._candidate_hand_frames = 0

        self._target_candidate_id = None
        self._target_candidate_frames = 0

        self._target_lock_frames = 0

        # Reset pointer-event throttling so the next active hand
        # produces an initial pointer event immediately.

        self._last_emitted_pointer_x = None
        self._last_emitted_pointer_y = None
        self._last_emitted_target_id = None

        self._emit(
            "active_hand_released",
            {
                "hand": handedness,
            },
        )

    # ========================================================
    # Public snapshot
    # ========================================================

    def snapshot(
        self,
    ) -> dict[str, Any]:

        target = self.current_target

        selected = self.selected_object

        return {
            "active_hand": self.active_hand,

            "pointer": self.pointer,

            "target": (
                {
                    "id": target.id,
                    "label": target.label,
                    "confidence": target.confidence,
                }
                if target is not None
                else None
            ),

            "selected": (
                {
                    "id": selected.id,
                    "label": selected.label,
                    "confidence": selected.confidence,
                }
                if selected is not None
                else None
            ),

            "object_count": len(
                self.objects
            ),

            "timestamp": time.time(),
        }