from __future__ import annotations

import asyncio
import time
from collections import deque

import numpy as np
from PIL import Image

from protogen.display.base import DisplayBase
from protogen.generators import ProceduralGenerator, FrameEffect, GENERATORS


class RenderPipeline(DisplayBase):
    """Display wrapper that tracks the last frame and composites effects.

    Sits between the expression system and the hardware display.
    Effects are rendered as an independent overlay and composited
    with the expression frame using pixel-wise max (lighter).
    """

    def __init__(self, display: DisplayBase) -> None:
        super().__init__(display.width, display.height)
        self._display = display
        self.last_frame: Image.Image | None = None
        self._effect: ProceduralGenerator | None = None
        self._effect_name: str | None = None
        self._effect_fps: int = 20
        self._effect_frame: Image.Image | None = None
        self._frame_times: deque[float] = deque(maxlen=30)
        self._pending_text: str | None = None
        self._black_frame = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        self._last_base_id: int | None = None

    @property
    def active_effect_name(self) -> str | None:
        return self._effect_name

    def set_effect(self, name: str, params: dict, fps: int = 20) -> None:
        gen_cls = GENERATORS.get(name)
        if gen_cls is None:
            return
        self._effect = gen_cls(self.width, self.height, params)
        self._effect_name = name
        self._effect_fps = fps
        self._effect_frame = None
        self._last_base_id = None
        if self._pending_text is not None and hasattr(self._effect, "set_text"):
            self._effect.set_text(self._pending_text)
            self._pending_text = None

    def update_effect_params(self, params: dict) -> None:
        if self._effect is not None:
            self._effect.update_params(params)

    def clear_effect(self) -> None:
        self._effect = None
        self._effect_name = None
        self._effect_frame = None
        self._last_base_id = None
        # Re-display pure expression frame
        if self.last_frame is not None:
            self._display.show_image(self.last_frame)

    def set_effect_text(self, text: str) -> None:
        self._pending_text = text
        if self._effect is not None and hasattr(self._effect, "set_text"):
            self._effect.set_text(text)

    async def run_effect_loop(self) -> None:
        start = time.monotonic()
        while True:
            if self._effect is not None:
                t = time.monotonic() - start
                if isinstance(self._effect, FrameEffect) and self.last_frame is not None:
                    # Only update _base_frame when the expression frame changes
                    frame_id = id(self.last_frame)
                    if frame_id != self._last_base_id:
                        self._effect._base_frame = self.last_frame
                        self._last_base_id = frame_id
                self._effect_frame = self._effect.render(t)
                self._push_composited()
            await asyncio.sleep(1.0 / self._effect_fps)

    def _push_composited(self) -> None:
        if self._effect_frame is None:
            return
        if isinstance(self._effect, FrameEffect):
            self._display.show_image(self._effect_frame)
            return
        base = self.last_frame
        if base is None:
            base = self._black_frame
        # NumPy pixel-wise max instead of ImageChops.lighter
        base_arr = np.asarray(base)
        effect_arr = np.asarray(self._effect_frame)
        composited_arr = np.maximum(base_arr, effect_arr)
        self._display.show_image(Image.fromarray(composited_arr, "RGB"))

    def get_fps(self) -> float:
        if len(self._frame_times) < 2:
            return 0.0
        elapsed = self._frame_times[-1] - self._frame_times[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._frame_times) - 1) / elapsed

    def show_image(self, image: Image.Image) -> None:
        self._frame_times.append(time.monotonic())
        self.last_frame = image
        if self._effect is not None and self._effect_frame is not None:
            self._push_composited()
        else:
            self._display.show_image(image)

    def clear(self) -> None:
        self.last_frame = None
        self._display.clear()

    def set_brightness(self, value: int) -> None:
        self._display.set_brightness(value)

    @property
    def brightness(self) -> int:
        return self._display.brightness
