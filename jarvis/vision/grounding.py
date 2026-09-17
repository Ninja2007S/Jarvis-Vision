from __future__ import annotations

from .hand_fusion import (
    find_pointing_target,
)
from .objects import DetectedObject


def point_inside(
    x: float,
    y: float,
    obj: DetectedObject,
) -> bool:

    box = obj.box

    return (
        box.x1 <= x <= box.x2
        and box.y1 <= y <= box.y2
    )


def find_pointed_object(
    pointer: tuple[float, float],
    objects: list[DetectedObject],
) -> DetectedObject | None:

    x, y = pointer

    return find_pointing_target(
        pointer_x=x,
        pointer_y=y,
        objects=objects,
    )