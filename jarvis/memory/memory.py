from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class MemoryItem:

    text: str
    category: str
    created_at: str


class Memory:

    def __init__(self):

        self.items: list[
            MemoryItem
        ] = []

    def add(
        self,
        text: str,
        category: str = "general",
    ):

        self.items.append(
            MemoryItem(
                text=text,
                category=category,
                created_at=(
                    datetime.now()
                    .isoformat()
                ),
            )
        )

    def search(
        self,
        query: str,
        limit: int = 5,
    ):

        query_words = set(
            query.lower().split()
        )

        scored = []

        for item in self.items:

            words = set(
                item.text.lower().split()
            )

            score = len(
                query_words & words
            )

            if score > 0:
                scored.append(
                    (score, item)
                )

        scored.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        return [
            item
            for _, item
            in scored[:limit]
        ]