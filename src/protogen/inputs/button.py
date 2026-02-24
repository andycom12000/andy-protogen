from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Callable, Awaitable

from protogen.commands import Command, InputEvent


class ButtonInput:
    """GPIO button input using gpiod. RPi only.

    GPIO lines are requested eagerly in __init__ so that gpiod
    initialisation happens *before* piomatter on RPi 5.  Requesting
    lines after piomatter causes RP1 PIO xfer_data timeouts.
    """

    def __init__(self, pin: int = 17, debounce_ms: int = 200) -> None:
        import gpiod
        from gpiod.line import Bias, Direction, Edge

        self._pin = pin
        self._debounce = debounce_ms / 1000.0
        self._chip = gpiod.Chip("/dev/gpiochip0")
        self._request = self._chip.request_lines(
            config={
                self._pin: gpiod.LineSettings(
                    direction=Direction.INPUT,
                    bias=Bias.PULL_UP,
                    edge_detection=Edge.FALLING,
                    debounce_period=timedelta(seconds=self._debounce),
                )
            }
        )

    async def run(self, put: Callable[[Command], Awaitable[None]]) -> None:
        loop = asyncio.get_running_loop()
        while True:
            # Block in executor with long timeout — OS-level GPIO interrupt wait
            has_event = await loop.run_in_executor(
                None, self._request.wait_edge_events, 5.0
            )
            if has_event:
                self._request.read_edge_events()
                await put(Command(event=InputEvent.TOGGLE_BLINK))
                await asyncio.sleep(self._debounce)
