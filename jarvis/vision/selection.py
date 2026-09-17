from __future__ import annotations

import time


class SelectionManager:

    def __init__(self) -> None:
        self.selected_id: int | None = None
        self.selected_at: float | None = None

    def select(
        self,
        object_id: int,
    ) -> None:

        self.selected_id = object_id
        self.selected_at = time.time()

    def clear(self) -> None:

        self.selected_id = None
        self.selected_at = None

    def is_selected(
        self,
        object_id: int,
    ) -> bool:

        return (
            self.selected_id == object_id
        )