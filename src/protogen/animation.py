from __future__ import annotations

import asyncio

from PIL import Image

from protogen.display.base import DisplayBase
from protogen.generators import ProceduralGenerator


class AnimationEngine:
    def __init__(self, display: DisplayBase) -> None:
        self._display = display
        self._running = False

    def stop(self) -> None:
        self._running = False

    async def play(self, frames: list[Image.Image], fps: int = 12, loop: bool = False) -> None:
        if not frames:
            return
        self._running = True
        interval = 1.0 / fps

        while self._running:
            for frame in frames:
                if not self._running:
                    return
                self._display.show_image(frame)
                await asyncio.sleep(interval)
            if not loop:
                break

    async def play_procedural(self, generator: ProceduralGenerator, fps: int = 30) -> None:
        """Render procedural frames in a loop."""
        self._running = True
        interval = 1.0 / fps
        t = 0.0

        while self._running:
            frame = generator.render(t)
            self._display.show_image(frame)
            await asyncio.sleep(interval)
            t += interval
