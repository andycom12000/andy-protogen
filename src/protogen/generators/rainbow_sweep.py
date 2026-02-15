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

        # Mask: non-black pixels
        mask = rgb_arr.max(axis=2) > 0
        if not mask.any():
            return frame

        # Compute brightness from original (max of RGB channels)
        brightness = rgb_arr.max(axis=2).astype(np.float32) / 255.0

        # Hue sweeps across x-axis and shifts over time
        hue = (self._x_grid * 360 + t * self._speed * 120) % 360

        # HSV to RGB conversion (S=1, V=brightness)
        h60 = hue / 60.0
        sector = h60.astype(np.int32) % 6
        f = h60 - np.floor(h60)
        v = brightness
        p = np.zeros_like(v)
        q = v * (1.0 - f)
        u = v * f  # t in standard HSV formula, renamed to avoid shadowing

        out = np.zeros_like(rgb_arr, dtype=np.float32)
        for i, (r, g, b) in enumerate([
            (v, u, p), (q, v, p), (p, v, u), (p, q, v), (u, p, v), (v, p, q)
        ]):
            s = sector == i
            out[:, :, 0][s] = r[s]
            out[:, :, 1][s] = g[s]
            out[:, :, 2][s] = b[s]

        result = (out * 255).clip(0, 255).astype(np.uint8)
        # Keep black pixels black
        result[~mask] = 0
        return Image.fromarray(result, "RGB")
