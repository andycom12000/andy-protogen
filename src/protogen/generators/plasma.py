from __future__ import annotations

import numpy as np
from PIL import Image

from protogen.generators import ProceduralGenerator


class PlasmaGenerator(ProceduralGenerator):
    """Flowing plasma effect with overlapping sine waves."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._speed = params.get("speed", 1.0)
        self._palette = params.get("palette", "cyan")
        # Pre-compute coordinate grids
        y_coords, x_coords = np.mgrid[0:height, 0:width]
        self._x = x_coords.astype(np.float32) / width
        self._y = y_coords.astype(np.float32) / height
        # Pre-compute radial distance (never changes)
        self._dist = np.sqrt(
            ((self._x - 0.5) ** 2 + (self._y - 0.5) ** 2) * 100,
            dtype=np.float32,
        )
        # Pre-compute static wave inputs
        self._x10 = self._x * 10
        self._y10 = self._y * 10
        self._xy8 = (self._x + self._y) * 8

    def update_params(self, params: dict) -> None:
        super().update_params(params)
        if "speed" in params:
            self._speed = params["speed"]

    def render(self, t: float) -> Image.Image:
        st = t * self._speed

        # Combine multiple sine waves for plasma effect (in-place accumulation)
        v = np.sin(self._x10 + st)
        v += np.sin(self._y10 + st * 0.7)
        v += np.sin(self._xy8 + st * 1.3)
        v += np.sin(self._dist + st * 0.5)

        v *= 0.25  # Range: -1 to 1
        v += 0.5   # Normalize to 0-1

        if self._palette == "rainbow":
            # HSV-like rainbow mapping
            h = v * 6.0  # h/60 pre-scaled
            r = np.clip(np.abs(h % 6 - 3) - 1, 0, 1)
            g = np.clip(2 - np.abs(h % 6 - 2), 0, 1)
            b = np.clip(2 - np.abs(h % 6 - 4), 0, 1)
            rgb = np.empty((self.height, self.width, 3), dtype=np.uint8)
            rgb[:, :, 0] = (r * 255).astype(np.uint8)
            rgb[:, :, 1] = (g * 255).astype(np.uint8)
            rgb[:, :, 2] = (b * 255).astype(np.uint8)
        else:
            # Cyan palette
            rgb = np.empty((self.height, self.width, 3), dtype=np.uint8)
            rgb[:, :, 0] = (v * (0.1 * 255)).astype(np.uint8)
            rgb[:, :, 1] = (v * (0.8 * 255)).astype(np.uint8)
            rgb[:, :, 2] = (v * 255).astype(np.uint8)

        return Image.fromarray(rgb, "RGB")
