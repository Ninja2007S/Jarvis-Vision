from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MultimodalContext:

    user_text: str = ""

    scene_description: str = ""

    selected_object: str | None = None

    visible_objects: list[str] = field(
        default_factory=list
    )

    detected_text: str = ""

    active_gesture: str | None = None

    pointer_x: float | None = None
    pointer_y: float | None = None

    def build_prompt_context(self) -> str:

        parts = []

        if self.scene_description:
            parts.append(
                "SCENE:\n"
                + self.scene_description
            )

        if self.visible_objects:
            parts.append(
                "VISIBLE OBJECTS:\n"
                + ", ".join(
                    self.visible_objects
                )
            )

        if self.selected_object:
            parts.append(
                "USER SELECTED:\n"
                + self.selected_object
            )

        if self.detected_text:
            parts.append(
                "VISIBLE TEXT:\n"
                + self.detected_text
            )

        if self.active_gesture:
            parts.append(
                "HAND GESTURE:\n"
                + self.active_gesture
            )

        return "\n\n".join(parts)