from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> tuple[float, float]:
        return (
            (self.x1 + self.x2) / 2,
            (self.y1 + self.y2) / 2,
        )

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclass
class DetectedObject:
    id: int
    label: str
    confidence: float
    box: BoundingBox

    attributes: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class VisionState:
    timestamp: float

    objects: list[DetectedObject] = field(
        default_factory=list
    )

    hands: list[dict[str, Any]] = field(
        default_factory=list
    )

    text: list[str] = field(
        default_factory=list
    )

    scene_description: str | None = None

    camera_width: int = 0
    camera_height: int = 0

    @property
    def object_count(self) -> int:
        return len(self.objects)

    def find(self, label: str) -> list[DetectedObject]:
        label = label.lower()

        return [
            obj
            for obj in self.objects
            if obj.label.lower() == label
        ]