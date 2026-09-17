from __future__ import annotations

from dataclasses import dataclass
import math

from .objects import DetectedObject


# ============================================================
# Selection configuration
# ============================================================

# These classes represent people rather than objects the user
# normally wants to manipulate.
NON_SELECTABLE_LABELS = {
    "person",
    "face",
}


# Keep snapping relatively tight.
SNAP_DISTANCE_PX = 28.0


@dataclass
class PointingTarget:
    object: DetectedObject | None

    pointer_x: float
    pointer_y: float

    is_pointing: bool


def normalized_to_pixels(
    x: float,
    y: float,
    width: int,
    height: int,
) -> tuple[float, float]:

    return (
        x * width,
        y * height,
    )


def selectable(
    obj: DetectedObject,
) -> bool:

    label = obj.label.lower().strip()

    return label not in NON_SELECTABLE_LABELS


def point_inside_object(
    x: float,
    y: float,
    obj: DetectedObject,
) -> bool:

    if not selectable(obj):
        return False

    box = obj.box

    return (
        box.x1 <= x <= box.x2
        and box.y1 <= y <= box.y2
    )


def distance_to_box(
    x: float,
    y: float,
    obj: DetectedObject,
) -> float:

    box = obj.box

    dx = max(
        box.x1 - x,
        0.0,
        x - box.x2,
    )

    dy = max(
        box.y1 - y,
        0.0,
        y - box.y2,
    )

    return math.sqrt(
        dx * dx + dy * dy
    )


def box_area(
    obj: DetectedObject,
) -> float:

    width = max(
        1.0,
        obj.box.x2 - obj.box.x1,
    )

    height = max(
        1.0,
        obj.box.y2 - obj.box.y1,
    )

    return width * height


def target_score(
    pointer_x: float,
    pointer_y: float,
    obj: DetectedObject,
) -> float:

    """
    Lower is better.

    Distance matters most.

    Area is a secondary factor so that a giant person/background
    region does not beat a small object.
    """

    distance = distance_to_box(
        pointer_x,
        pointer_y,
        obj,
    )

    area = box_area(obj)

    # Prevent extremely large objects from dominating.
    area_penalty = min(
        100.0,
        math.sqrt(area) * 0.015,
    )

    confidence_bonus = (
        obj.confidence * 8.0
    )

    return (
        distance
        + area_penalty
        - confidence_bonus
    )


def find_pointing_target(
    pointer_x: float,
    pointer_y: float,
    objects: list[DetectedObject],
) -> DetectedObject | None:

    selectable_objects = [
        obj
        for obj in objects
        if selectable(obj)
    ]

    if not selectable_objects:
        return None

    # --------------------------------------------------------
    # First: objects directly underneath the pointer.
    # --------------------------------------------------------

    containing = [
        obj
        for obj in selectable_objects
        if point_inside_object(
            pointer_x,
            pointer_y,
            obj,
        )
    ]

    if containing:

        containing.sort(
            key=lambda obj: target_score(
                pointer_x,
                pointer_y,
                obj,
            )
        )

        return containing[0]

    # --------------------------------------------------------
    # Second: tight snapping around the pointer.
    # --------------------------------------------------------

    nearby = []

    for obj in selectable_objects:

        distance = distance_to_box(
            pointer_x,
            pointer_y,
            obj,
        )

        if distance <= SNAP_DISTANCE_PX:

            nearby.append(
                (
                    distance,
                    obj,
                )
            )

    if not nearby:
        return None

    nearby.sort(
        key=lambda item: (
            item[0],
            box_area(item[1]),
            -item[1].confidence,
        )
    )

    return nearby[0][1]


def create_pointing_target(
    pointer_normalized: tuple[float, float],
    width: int,
    height: int,
    objects: list[DetectedObject],
    is_pointing: bool = True,
) -> PointingTarget:

    px, py = normalized_to_pixels(
        pointer_normalized[0],
        pointer_normalized[1],
        width,
        height,
    )

    target = None

    if is_pointing:

        target = find_pointing_target(
            px,
            py,
            objects,
        )

    return PointingTarget(
        object=target,
        pointer_x=px,
        pointer_y=py,
        is_pointing=is_pointing,
    )