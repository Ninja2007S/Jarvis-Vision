from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence


# ============================================================
# CONFIGURATION
# ============================================================

PINCH_START_RATIO = 0.34
PINCH_RELEASE_RATIO = 0.52

FINGER_CURL_THRESHOLD = 1.10

POINTING_MIN_INDEX_EXTENSION = 0.012

STABLE_FRAMES = 2


# ============================================================
# GESTURE DATA
# ============================================================

@dataclass
class Gesture:
    name: str
    pointer: tuple[float, float] | None = None
    pinch_distance: float = 0.0
    handedness: str | None = None


# ============================================================
# HAND COMPATIBILITY
# ============================================================

def _extract_points(hand_or_points: Any):
    """
    Accept either:

        Hand object

    or:

        raw landmark list / numpy array
    """

    if hand_or_points is None:
        return None

    if hasattr(
        hand_or_points,
        "points",
    ):
        return hand_or_points.points

    return hand_or_points


def _extract_handedness(
    hand_or_points: Any,
    handedness: str | None,
) -> str | None:

    if handedness is not None:
        return handedness

    value = getattr(
        hand_or_points,
        "handedness",
        None,
    )

    if value is None:
        return None

    return str(value)


# ============================================================
# GEOMETRY
# ============================================================

def distance(
    a: Sequence[float],
    b: Sequence[float],
) -> float:

    dx = float(a[0]) - float(b[0])
    dy = float(a[1]) - float(b[1])

    dz = 0.0

    try:
        if len(a) > 2 and len(b) > 2:
            dz = (
                float(a[2]) -
                float(b[2])
            )
    except Exception:
        dz = 0.0

    return math.sqrt(
        dx * dx +
        dy * dy +
        dz * dz
    )


def midpoint(
    a: Sequence[float],
    b: Sequence[float],
) -> tuple[float, float]:

    return (
        (
            float(a[0]) +
            float(b[0])
        ) / 2.0,

        (
            float(a[1]) +
            float(b[1])
        ) / 2.0,
    )


def hand_scale(
    points: Sequence[Sequence[float]],
) -> float:

    if points is None:
        return 1.0

    try:
        if len(points) < 10:
            return 1.0
    except Exception:
        return 1.0

    scale = distance(
        points[0],
        points[9],
    )

    return max(
        scale,
        1e-6,
    )


# ============================================================
# PINCH
# ============================================================

def pinch_ratio(
    points: Sequence[Sequence[float]],
) -> float:

    if points is None:
        return 999.0

    try:
        if len(points) < 9:
            return 999.0
    except Exception:
        return 999.0

    return (
        distance(
            points[4],
            points[8],
        )
        /
        hand_scale(points)
    )


# ============================================================
# FINGER EXTENSION
# ============================================================

def finger_extension_ratio(
    points: Sequence[Sequence[float]],
    tip_index: int,
    pip_index: int,
) -> float:

    if points is None:
        return 0.0

    try:
        if len(points) <= max(
            tip_index,
            pip_index,
        ):
            return 0.0
    except Exception:
        return 0.0

    wrist = points[0]
    tip = points[tip_index]
    pip = points[pip_index]

    wrist_to_tip = distance(
        wrist,
        tip,
    )

    wrist_to_pip = distance(
        wrist,
        pip,
    )

    if wrist_to_pip <= 1e-6:
        return 0.0

    return (
        wrist_to_tip /
        wrist_to_pip
    )


def finger_curl_ratio(
    points: Sequence[Sequence[float]],
    tip_index: int,
    pip_index: int,
) -> float:

    return finger_extension_ratio(
        points,
        tip_index,
        pip_index,
    )


def finger_is_curled(
    points: Sequence[Sequence[float]],
    tip_index: int,
    pip_index: int,
) -> bool:

    return (
        finger_curl_ratio(
            points,
            tip_index,
            pip_index,
        )
        <
        FINGER_CURL_THRESHOLD
    )


def finger_extended(
    points: Sequence[Sequence[float]],
    tip_index: int,
    pip_index: int,
) -> bool:

    if points is None:
        return False

    try:
        if len(points) <= max(
            tip_index,
            pip_index,
        ):
            return False
    except Exception:
        return False

    ratio = finger_extension_ratio(
        points,
        tip_index,
        pip_index,
    )

    if ratio >= FINGER_CURL_THRESHOLD:
        return True

    try:
        tip = points[tip_index]
        pip = points[pip_index]

        vertical_extension = (
            float(pip[1]) -
            float(tip[1])
        )

        return (
            ratio >= 1.02
            and
            vertical_extension
            >= POINTING_MIN_INDEX_EXTENSION
        )

    except Exception:
        return False


# ============================================================
# PINCH GEOMETRY
# ============================================================

def valid_pinch_geometry(
    points: Sequence[Sequence[float]],
) -> bool:

    if points is None:
        return False

    try:
        if len(points) < 21:
            return False
    except Exception:
        return False

    middle_curled = finger_is_curled(
        points,
        12,
        10,
    )

    ring_curled = finger_is_curled(
        points,
        16,
        14,
    )

    pinky_curled = finger_is_curled(
        points,
        20,
        18,
    )

    return (
        int(middle_curled)
        +
        int(ring_curled)
        +
        int(pinky_curled)
    ) >= 2


# ============================================================
# PEACE
# ============================================================

def is_peace_sign(
    points: Sequence[Sequence[float]],
) -> bool:

    if points is None:
        return False

    try:
        if len(points) < 21:
            return False
    except Exception:
        return False

    index_extended = finger_extended(
        points,
        8,
        6,
    )

    middle_extended = finger_extended(
        points,
        12,
        10,
    )

    ring_curled = finger_is_curled(
        points,
        16,
        14,
    )

    pinky_curled = finger_is_curled(
        points,
        20,
        18,
    )

    return (
        index_extended
        and
        middle_extended
        and
        ring_curled
        and
        pinky_curled
    )


# ============================================================
# PINCH DETECTION
# ============================================================

def is_pinch(
    points: Sequence[Sequence[float]],
    previous_name: str | None = None,
) -> bool:

    if points is None:
        return False

    try:
        if len(points) < 21:
            return False
    except Exception:
        return False

    if not valid_pinch_geometry(points):
        return False

    ratio = pinch_ratio(points)

    previous = (
        str(previous_name).lower()
        if previous_name is not None
        else ""
    )

    if previous == "pinch":
        return ratio <= PINCH_RELEASE_RATIO

    return ratio <= PINCH_START_RATIO


# ============================================================
# POINTER
# ============================================================

def get_index_pointer(
    points: Sequence[Sequence[float]],
) -> tuple[float, float] | None:

    if points is None:
        return None

    try:
        if len(points) < 9:
            return None

        return (
            float(points[8][0]),
            float(points[8][1]),
        )

    except Exception:
        return None


def get_pinch_pointer(
    points: Sequence[Sequence[float]],
) -> tuple[float, float] | None:

    return get_index_pointer(points)


# ============================================================
# CLASSIFY
# ============================================================

def classify(
    hand_or_points: Any,
    handedness: str | None = None,
    previous_name: str | None = None,
) -> Gesture:

    points = _extract_points(
        hand_or_points
    )

    if points is None:
        return Gesture(
            name="unknown",
            pointer=None,
            handedness=handedness,
        )

    try:
        if len(points) < 21:
            return Gesture(
                name="unknown",
                pointer=None,
                handedness=handedness,
            )
    except Exception:
        return Gesture(
            name="unknown",
            pointer=None,
            handedness=handedness,
        )

    actual_handedness = (
        _extract_handedness(
            hand_or_points,
            handedness,
        )
    )

    pointer = get_index_pointer(
        points
    )

    # ========================================================
    # PEACE MUST COME FIRST
    # ========================================================

    if is_peace_sign(points):

        return Gesture(
            name="peace",
            pointer=pointer,
            handedness=actual_handedness,
        )

    # ========================================================
    # PINCH
    # ========================================================

    if is_pinch(
        points,
        previous_name=previous_name,
    ):

        return Gesture(
            name="pinch",
            pointer=pointer,
            pinch_distance=pinch_ratio(
                points
            ),
            handedness=actual_handedness,
        )

    # ========================================================
    # POINT
    # ========================================================

    index_extended = finger_extended(
        points,
        8,
        6,
    )

    middle_curled = finger_is_curled(
        points,
        12,
        10,
    )

    ring_curled = finger_is_curled(
        points,
        16,
        14,
    )

    pinky_curled = finger_is_curled(
        points,
        20,
        18,
    )

    if (
        index_extended
        and
        middle_curled
        and
        ring_curled
        and
        pinky_curled
    ):

        return Gesture(
            name="point",
            pointer=pointer,
            handedness=actual_handedness,
        )

    # ========================================================
    # OPEN HAND
    # ========================================================

    middle_extended = finger_extended(
        points,
        12,
        10,
    )

    ring_extended = finger_extended(
        points,
        16,
        14,
    )

    pinky_extended = finger_extended(
        points,
        20,
        18,
    )

    if (
        index_extended
        and
        middle_extended
        and
        ring_extended
        and
        pinky_extended
    ):

        return Gesture(
            name="open",
            pointer=pointer,
            handedness=actual_handedness,
        )

    # ========================================================
    # UNKNOWN
    # ========================================================

    return Gesture(
        name="unknown",
        pointer=pointer,
        handedness=actual_handedness,
    )


# ============================================================
# STABILIZER
# ============================================================

class Stabilizer:
    """
    Controller-compatible gesture stabilizer.

    IMPORTANT CONTRACT:

        settled, changed = stabilizer.update(...)

    settled:
        Current stable gesture name.

    changed:
        True only when the stable gesture changed.
    """

    def __init__(
        self,
        stable_frames: int = STABLE_FRAMES,
    ) -> None:

        self.stable_frames = max(
            1,
            int(stable_frames),
        )

        self.current: str | None = None
        self.candidate: str | None = None
        self.count = 0

    def update(
        self,
        value: str | Gesture,
    ) -> tuple[str, bool]:

        # ----------------------------------------------------
        # Extract name regardless of input type.
        # ----------------------------------------------------

        if isinstance(
            value,
            Gesture,
        ):

            incoming = value.name

        elif isinstance(
            value,
            str,
        ):

            incoming = value

        else:

            incoming = "unknown"

        incoming = (
            str(incoming)
            .strip()
            .lower()
        )

        # ----------------------------------------------------
        # No previous stable state.
        # ----------------------------------------------------

        if self.current is None:

            if self.candidate == incoming:

                self.count += 1

            else:

                self.candidate = incoming
                self.count = 1

            if (
                self.count >=
                self.stable_frames
            ):

                self.current = incoming

                self.candidate = None
                self.count = 0

                return (
                    self.current,
                    True,
                )

            # Before enough frames, expose incoming
            # so controller still has a usable state.
            return (
                incoming,
                False,
            )

        # ----------------------------------------------------
        # Same as current stable gesture.
        # ----------------------------------------------------

        if incoming == self.current:

            self.candidate = None
            self.count = 0

            return (
                self.current,
                False,
            )

        # ----------------------------------------------------
        # New candidate gesture.
        # ----------------------------------------------------

        if incoming != self.candidate:

            self.candidate = incoming
            self.count = 1

        else:

            self.count += 1

        # ----------------------------------------------------
        # Candidate has become stable.
        # ----------------------------------------------------

        if (
            self.count >=
            self.stable_frames
        ):

            previous = self.current

            self.current = incoming

            self.candidate = None
            self.count = 0

            return (
                self.current,
                self.current != previous,
            )

        # ----------------------------------------------------
        # Still transitioning.
        # ----------------------------------------------------

        return (
            self.current,
            False,
        )

    def reset(self) -> None:

        self.current = None
        self.candidate = None
        self.count = 0


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================

GestureStabilizer = Stabilizer