from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class Tool:

    name: str
    description: str
    function: Callable[..., Any]


class ToolRegistry:

    def __init__(self):

        self.tools: dict[
            str,
            Tool
        ] = {}

    def register(
        self,
        name: str,
        description: str,
        function: Callable[..., Any],
    ):

        self.tools[name] = Tool(
            name=name,
            description=description,
            function=function,
        )

    def get(
        self,
        name: str,
    ) -> Tool | None:

        return self.tools.get(name)

    def list(self):

        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self.tools.values()
        ]

    def execute(
        self,
        name: str,
        **kwargs,
    ):

        tool = self.get(name)

        if tool is None:
            raise ValueError(
                f"Unknown tool: {name}"
            )

        return tool.function(
            **kwargs
        )