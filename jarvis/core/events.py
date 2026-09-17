from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(
        default_factory=dict
    )


Handler = Callable[
    [Event],
    Awaitable[None],
]


class EventBus:

    def __init__(self) -> None:
        self._handlers: dict[
            str,
            list[Handler],
        ] = {}

    def subscribe(
        self,
        event_type: str,
        handler: Handler,
    ) -> None:

        self._handlers.setdefault(
            event_type,
            [],
        ).append(handler)

    async def publish(
        self,
        event: Event,
    ) -> None:

        handlers = self._handlers.get(
            event.type,
            [],
        )

        if not handlers:
            return

        await asyncio.gather(
            *[
                handler(event)
                for handler in handlers
            ]
        )