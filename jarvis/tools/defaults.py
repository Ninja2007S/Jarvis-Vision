from __future__ import annotations

from .registry import ToolRegistry

from ..computer.apps import (
    open_application,
)


def create_default_registry():

    registry = ToolRegistry()

    registry.register(
        name="open_application",
        description=(
            "Open an approved Windows application."
        ),
        function=open_application,
    )

    return registry