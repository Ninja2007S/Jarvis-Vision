from __future__ import annotations

from .objects import VisionState


def vision_to_dict(
    state: VisionState,
) -> dict:

    objects = []

    for obj in state.objects:
        objects.append(
            {
                "id": obj.id,
                "label": obj.label,
                "confidence": round(
                    obj.confidence,
                    3,
                ),
                "box": {
                    "x1": obj.box.x1,
                    "y1": obj.box.y1,
                    "x2": obj.box.x2,
                    "y2": obj.box.y2,
                },
            }
        )

    return {
        "timestamp": state.timestamp,
        "camera": {
            "width": state.camera_width,
            "height": state.camera_height,
        },
        "objects": objects,
        "hands": state.hands,
        "text": state.text,
        "scene_description": (
            state.scene_description
        ),
    }