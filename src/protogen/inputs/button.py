from __future__ import annotations

import asyncio
from typing import Callable, Awaitable

from protogen.commands import Command, InputEvent


class ButtonInput:
    """GPIO button input using gpiod. RPi only."""

    def __init__(self, pin: int = 17, debounce_ms: int = 200) -> None:
        self._pin = pin
        self._debounce = debounce_ms / 1000.0

    async def run(self, put: Callable[[Command], Awaitable[None]]) -> None:
        import gpiod
        from gpiod.line import Bias, Direction, Edge

        chip = gpiod.Chip("/dev/gpiochip0")
        request = chip.request_lines(
            config={
                self._pin: gpiod.LineSettings(
                    direction=Direction.INPUT,
                    bias=Bias.PULL_UP,
                    edge_detection=Edge.FALLING,
                    debounce_period=self._debounce,
                )
            }
        )

        while True:
            if request.wait_edge_events(timeout=0.1):
                request.read_edge_events()
                await put(Command(event=InputEvent.TOGGLE_BLINK))
                await asyncio.sleep(self._debounce)
            await asyncio.sleep(0.01)
