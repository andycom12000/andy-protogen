from __future__ import annotations

import numpy as np
from PIL import Image

from protogen.generators import ProceduralGenerator


class MatrixRainGenerator(ProceduralGenerator):
    """Matrix-style falling code rain effect."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._color = np.array(params.get("color", [0, 255, 70]), dtype=np.float32)
        self._speed = params.get("speed", 1.0)
        self._density = params.get("density", 0.3)

        # Column state
        self._col_w = 4  # ~4px per character column
        self._cell_h = 5  # approx character height in pixels
        self._num_cols = width // self._col_w
        rng = np.random.default_rng()
        self._drops = rng.uniform(-height, 0, self._num_cols).astype(np.float32)
        self._last_t = 0.0
        self._rng = rng
        # Reusable framebuffer
        self._framebuf = np.zeros((height, width, 3), dtype=np.uint8)
        # Pre-compute trail fade colors (index 0 = head = white, 1..trail_len-1 = fading)
        self._trail_len = 6
        self._trail_colors = self._build_trail_colors()

    def _build_trail_colors(self) -> np.ndarray:
        """Pre-compute trail colors as uint8 array (trail_len, 3)."""
        trail = np.zeros((self._trail_len, 3), dtype=np.uint8)
        trail[0] = (255, 255, 255)  # head: bright white
        for j in range(1, self._trail_len):
            fade = max(0.0, 1.0 - j / self._trail_len)
            trail[j] = (self._color * fade).astype(np.uint8)
        return trail

    def update_params(self, params: dict) -> None:
        super().update_params(params)
        if "speed" in params:
            self._speed = params["speed"]
        if "density" in params:
            self._density = params["density"]
        if "color" in params:
            self._color = np.array(params["color"], dtype=np.float32)
            self._trail_colors = self._build_trail_colors()

    def render(self, t: float) -> Image.Image:
        dt = t - self._last_t if self._last_t > 0 else 1.0 / 30
        self._last_t = t

        # Clear framebuffer
        self._framebuf[:] = 0

        # Vectorized drop advance
        self._drops += self._speed * dt * 30

        fb = self._framebuf
        col_w = self._col_w
        cell_h = self._cell_h
        trail_len = self._trail_len
        wrap = self.height + cell_h * trail_len
        trail_colors = self._trail_colors
        h = self.height

        for i in range(self._num_cols):
            head_y = int(self._drops[i]) % wrap
            x0 = i * col_w
            x1 = x0 + col_w

            for j in range(trail_len):
                y = head_y - j * cell_h
                if 0 <= y < h:
                    y1 = min(y + cell_h, h)
                    fb[y:y1, x0:x1] = trail_colors[j]

            # Reset drop when it goes off screen
            if head_y > wrap:
                if self._rng.random() < self._density:
                    self._drops[i] = self._rng.uniform(-cell_h * 4, 0)

        return Image.fromarray(self._framebuf, "RGB")
