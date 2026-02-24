from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Protocol

from protogen.commands import Command

logger = logging.getLogger(__name__)


class InputSource(Protocol):
    async def run(self, put: Callable[[Command], Awaitable[None]]) -> None: ...


class InputManager:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Command] = asyncio.Queue()
        self._sources: list[InputSource] = []

    def add_source(self, source: InputSource) -> None:
        self._sources.append(source)
        logger.info("registered input source: %s", type(source).__name__)

    async def put(self, cmd: Command) -> None:
        await self._queue.put(cmd)

    async def get(self) -> Command:
        return await self._queue.get()

    async def run_all(self) -> None:
        logger.info("starting %d input sources", len(self._sources))
        tasks = [
            asyncio.create_task(source.run(self.put))
            for source in self._sources
        ]
        await asyncio.gather(*tasks)
