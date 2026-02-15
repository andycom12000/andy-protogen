from __future__ import annotations

import numpy as np
from PIL import Image

from protogen.generators import FrameEffect


class RainbowSweepEffect(FrameEffect):
    """Recolors non-black pixels with a sweeping rainbow based on x-position."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._speed = params.get("speed", 1.0)
        # Pre-compute x coordinate grid (0..1) for hue mapping
        self._x_grid = np.tile(
            np.linspace(0, 1, width, endpoint=False, dtype=np.float32), (height, 1)
        )

    def update_params(self, params: dict) -> None:
        super().update_params(params)
        if "speed" in params:
            self._speed = params["speed"]

    def apply(self, frame: Image.Image, t: float) -> Image.Image:
        rgb_arr = np.array(frame)

        # Mask & brightness: single max call
        channel_max = rgb_arr.max(axis=2)
        mask = channel_max > 0
        if not mask.any():
            return frame

        brightness = channel_max.astype(np.float32) * (1.0 / 255.0)

        # Hue sweeps across x-axis and shifts over time
        hue = (self._x_grid * 360 + t * self._speed * 120) % 360

        # HSV to RGB conversion (S=1, V=brightness) using np.choose
        h60 = hue / 60.0
        sector = h60.astype(np.int32) % 6
        f = h60 - np.floor(h60)
        v = brightness
        p = np.zeros_like(v)
        q = v * (1.0 - f)
        u = v * f  # t in standard HSV formula, renamed to avoid shadowing

        # np.choose: select R, G, B per sector in one vectorized call
        r = np.choose(sector, [v, q, p, p, u, v])
        g = np.choose(sector, [u, v, v, q, p, p])
        b = np.choose(sector, [p, p, u, v, v, q])

        result = np.empty_like(rgb_arr)
        result[:, :, 0] = (r * 255).clip(0, 255)
        result[:, :, 1] = (g * 255).clip(0, 255)
        result[:, :, 2] = (b * 255).clip(0, 255)

        # Keep black pixels black
        result[~mask] = 0
        return Image.fromarray(result.astype(np.uint8), "RGB")
