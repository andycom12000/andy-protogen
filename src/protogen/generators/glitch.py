from __future__ import annotations

import random

import numpy as np
from PIL import Image

from protogen.generators import FrameEffect


class GlitchEffect(FrameEffect):
    """Random glitch distortions — row shifts, channel offsets, color blocks."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._intensity = params.get("intensity", 0.3)
        self._burst_end = 0.0
        self._rng = random.Random()

    def apply(self, frame: Image.Image, t: float) -> Image.Image:
        # Decide whether to trigger a new burst
        if t >= self._burst_end:
            if self._rng.random() < self._intensity * 0.3:
                self._burst_end = t + self._rng.uniform(0.05, 0.25)
            else:
                return frame.copy()

        arr = np.array(frame)
        rng = self._rng

        # Row displacement
        num_rows = rng.randint(1, max(1, self.height // 4))
        for _ in range(num_rows):
            y = rng.randint(0, self.height - 1)
            shift = rng.randint(-self.width // 3, self.width // 3)
            arr[y] = np.roll(arr[y], shift, axis=0)

        # RGB channel offset (50% chance)
        if rng.random() < 0.5:
            channel = rng.randint(0, 2)
            shift = rng.randint(-5, 5)
            arr[:, :, channel] = np.roll(arr[:, :, channel], shift, axis=1)

        # Random color blocks (30% chance)
        if rng.random() < 0.3:
            num_blocks = rng.randint(1, 3)
            for _ in range(num_blocks):
                bx = rng.randint(0, self.width - 1)
                by = rng.randint(0, self.height - 1)
                bw = rng.randint(3, min(20, self.width - bx))
                bh = rng.randint(1, min(4, self.height - by))
                color = [rng.randint(0, 255) for _ in range(3)]
                arr[by:by + bh, bx:bx + bw] = color

        return Image.fromarray(arr, "RGB")
