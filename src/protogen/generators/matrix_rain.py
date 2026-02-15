from __future__ import annotations

import random

from PIL import Image, ImageDraw

from protogen.generators import ProceduralGenerator


class MatrixRainGenerator(ProceduralGenerator):
    """Matrix-style falling code rain effect."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._color = tuple(params.get("color", [0, 255, 70]))
        self._speed = params.get("speed", 1.0)
        self._density = params.get("density", 0.3)

        # Column state: each column has a drop position (float)
        self._col_w = 4  # ~4px per character column
        self._cell_h = 5  # approx character height in pixels
        self._num_cols = width // self._col_w
        self._drops: list[float] = [
            random.uniform(-height, 0) for _ in range(self._num_cols)
        ]
        self._last_t = 0.0

    def update_params(self, params: dict) -> None:
        super().update_params(params)
        if "speed" in params:
            self._speed = params["speed"]
        if "density" in params:
            self._density = params["density"]
        if "color" in params:
            self._color = tuple(params["color"])

    def render(self, t: float) -> Image.Image:
        img = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        dt = t - self._last_t if self._last_t > 0 else 1.0 / 30
        self._last_t = t

        r, g, b = self._color
        trail_len = 6

        for i, drop_y in enumerate(self._drops):
            # Advance drop position
            self._drops[i] += self._speed * dt * 30

            x = i * self._col_w
            head_y = int(self._drops[i]) % (self.height + self._cell_h * trail_len)

            # Draw trail (fading tail)
            for j in range(trail_len):
                y = head_y - j * self._cell_h
                if 0 <= y < self.height:
                    if j == 0:
                        # Head: bright white
                        draw.rectangle(
                            [x, y, x + self._col_w - 1, y + self._cell_h - 1],
                            fill=(255, 255, 255),
                        )
                    else:
                        # Trail: fading color
                        fade = max(0, 1.0 - j / trail_len)
                        cr = int(r * fade)
                        cg = int(g * fade)
                        cb = int(b * fade)
                        draw.rectangle(
                            [x, y, x + self._col_w - 1, y + self._cell_h - 1],
                            fill=(cr, cg, cb),
                        )

            # Reset drop when it goes off screen
            if head_y > self.height + self._cell_h * trail_len:
                if random.random() < self._density:
                    self._drops[i] = random.uniform(-self._cell_h * 4, 0)

        return img
