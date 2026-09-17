from __future__ import annotations

from .objects import VisionState


def describe_scene(
    state: VisionState,
) -> str:

    if not state.objects:
        return "I do not currently detect any recognizable objects."

    counts: dict[str, int] = {}

    for obj in state.objects:
        counts[obj.label] = (
            counts.get(obj.label, 0) + 1
        )

    parts = []

    for label, count in counts.items():
        if count == 1:
            parts.append(f"one {label}")
        else:
            parts.append(f"{count} {label}s")

    return "I can currently see " + ", ".join(parts) + "."