from __future__ import annotations

import asyncio
from typing import Protocol

from protogen.commands import Command


class InputSource(Protocol):
    async def run(self, put: asyncio.coroutines) -> None: ...


class InputManager:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Command] = asyncio.Queue()
        self._sources: list[InputSource] = []

    def add_source(self, source: InputSource) -> None:
        self._sources.append(source)

    async def put(self, cmd: Command) -> None:
        await self._queue.put(cmd)

    async def get(self) -> Command:
        return await self._queue.get()

    async def run_all(self) -> None:
        tasks = [
            asyncio.create_task(source.run(self.put))
            for source in self._sources
        ]
        await asyncio.gather(*tasks)
