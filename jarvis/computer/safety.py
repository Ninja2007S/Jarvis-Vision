from __future__ import annotations

import time


class ComputerSafety:

    def __init__(
        self,
        armed: bool = False,
    ):

        self.armed = armed

        self.last_action = 0.0

        self.minimum_interval = 0.15

    def arm(self) -> None:
        self.armed = True

    def disarm(self) -> None:
        self.armed = False

    def can_execute(
        self,
        action: str,
    ) -> bool:

        if not self.armed:
            return False

        now = time.time()

        if (
            now - self.last_action
            < self.minimum_interval
        ):
            return False

        self.last_action = now

        return True