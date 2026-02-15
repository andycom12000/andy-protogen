from __future__ import annotations

import numpy as np
from PIL import Image

from protogen.generators import ProceduralGenerator


class StarfieldGenerator(ProceduralGenerator):
    """3D starfield flying outward from center."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._star_count = params.get("star_count", 50)
        self._speed = params.get("speed", 1.0)
        self._color = np.array(params.get("color", [0, 255, 255]), dtype=np.float32)
        # Star state as NumPy arrays
        rng = np.random.default_rng()
        self._sx = rng.uniform(-1, 1, self._star_count).astype(np.float32)
        self._sy = rng.uniform(-1, 1, self._star_count).astype(np.float32)
        self._sz = rng.uniform(0.1, 1.0, self._star_count).astype(np.float32)
        self._last_t = 0.0
        self._rng = rng
        # Reusable framebuffer
        self._framebuf = np.zeros((height, width, 3), dtype=np.uint8)

    def update_params(self, params: dict) -> None:
        super().update_params(params)
        if "speed" in params:
            self._speed = params["speed"]
        if "color" in params:
            self._color = np.array(params["color"], dtype=np.float32)

    def render(self, t: float) -> Image.Image:
        dt = t - self._last_t if self._last_t > 0 else 1.0 / 30
        self._last_t = t

        # Clear framebuffer
        self._framebuf[:] = 0

        # Vectorized z update
        self._sz -= self._speed * dt * 0.5

        # Find stars that need reset
        dead = self._sz <= 0.01
        n_dead = dead.sum()
        if n_dead > 0:
            self._sx[dead] = self._rng.uniform(-1, 1, n_dead).astype(np.float32)
            self._sy[dead] = self._rng.uniform(-1, 1, n_dead).astype(np.float32)
            self._sz[dead] = 1.0

        cx = self.width / 2
        cy = self.height / 2

        # Vectorized projection
        inv_z = 1.0 / self._sz
        px = (cx + self._sx * inv_z * cx).astype(np.int32)
        py = (cy + self._sy * inv_z * cy).astype(np.int32)

        # Brightness and size
        one_minus_z = 1.0 - self._sz
        brightness = np.maximum(0.2, one_minus_z)
        sizes = np.maximum(1, (one_minus_z * 3).astype(np.int32))

        # Visibility mask
        visible = (px >= 0) & (px < self.width) & (py >= 0) & (py < self.height)

        # Draw visible stars
        fb = self._framebuf
        color = self._color
        for i in np.where(visible)[0]:
            br = brightness[i]
            cr = int(color[0] * br)
            cg = int(color[1] * br)
            cb = int(color[2] * br)
            x, y, sz = int(px[i]), int(py[i]), int(sizes[i])
            if sz <= 1:
                fb[y, x] = (cr, cg, cb)
            else:
                # Draw square block approximation
                half = sz // 2
                x0 = max(0, x - half)
                y0 = max(0, y - half)
                x1 = min(self.width, x + half + 1)
                y1 = min(self.height, y + half + 1)
                fb[y0:y1, x0:x1] = (cr, cg, cb)

        return Image.fromarray(self._framebuf, "RGB")
