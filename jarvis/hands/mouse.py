"""Smooth normalized hand coordinates."""

from __future__ import annotations


SMOOTHING = 0.18


class CursorSmoother:
    """
    Exponential pointer smoother.

    smoothing:
        0.0 = follow immediately
        1.0 = extremely slow

    Internally this uses:

        current += (target - current) * alpha

    where:

        alpha = 1 - smoothing
    """

    def __init__(
        self,
        smoothing: float = SMOOTHING,
    ) -> None:

        self._smoothing = max(
            0.0,
            min(
                0.95,
                float(smoothing),
            ),
        )

        self._alpha = 1.0 - self._smoothing

        self._x: float | None = None
        self._y: float | None = None

    def update(
        self,
        x: float,
        y: float,
    ) -> tuple[float, float]:

        x = max(
            0.0,
            min(1.0, float(x)),
        )

        y = max(
            0.0,
            min(1.0, float(y)),
        )

        if self._x is None:
            self._x = x
            self._y = y

            return (
                self._x,
                self._y,
            )

        self._x += (
            x - self._x
        ) * self._alpha

        self._y += (
            y - self._y
        ) * self._alpha

        return (
            self._x,
            self._y,
        )

    def reset(self) -> None:
        self._x = None
        self._y = None

    @property
    def value(
        self,
    ) -> tuple[float, float] | None:

        if self._x is None:
            return None

        return (
            self._x,
            self._y,
        )