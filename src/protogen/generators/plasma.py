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

    def update_params(self, params: dict) -> None:
        super().update_params(params)
        if "speed" in params:
            self._speed = params["speed"]

    def render(self, t: float) -> Image.Image:
        st = t * self._speed

        # Combine multiple sine waves for plasma effect
        v1 = np.sin(self._x * 10 + st)
        v2 = np.sin(self._y * 10 + st * 0.7)
        v3 = np.sin((self._x + self._y) * 8 + st * 1.3)
        v4 = np.sin(
            np.sqrt(((self._x - 0.5) ** 2 + (self._y - 0.5) ** 2) * 100) + st * 0.5
        )

        v = (v1 + v2 + v3 + v4) / 4.0  # Range: -1 to 1
        v = (v + 1.0) / 2.0  # Normalize to 0-1

        if self._palette == "rainbow":
            # HSV-like rainbow mapping
            h = (v * 360).astype(np.float32)
            r = np.clip(np.abs((h / 60) % 6 - 3) - 1, 0, 1)
            g = np.clip(2 - np.abs((h / 60) % 6 - 2), 0, 1)
            b = np.clip(2 - np.abs((h / 60) % 6 - 4), 0, 1)
            rgb = np.stack([
                (r * 255).astype(np.uint8),
                (g * 255).astype(np.uint8),
                (b * 255).astype(np.uint8),
            ], axis=-1)
        else:
            # Cyan palette
            r = (v * 0.1 * 255).astype(np.uint8)
            g = (v * 0.8 * 255).astype(np.uint8)
            b = (v * 255).astype(np.uint8)
            rgb = np.stack([r, g, b], axis=-1)

        return Image.fromarray(rgb, "RGB")
