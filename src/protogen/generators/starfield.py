from __future__ import annotations

import random

from PIL import Image, ImageDraw

from protogen.generators import ProceduralGenerator


class StarfieldGenerator(ProceduralGenerator):
    """3D starfield flying outward from center."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._star_count = params.get("star_count", 50)
        self._speed = params.get("speed", 1.0)
        self._color = tuple(params.get("color", [0, 255, 255]))
        # Stars: [x, y, z] in 3D space, z goes from far (1.0) to near (0.01)
        self._stars: list[list[float]] = [
            [random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.1, 1.0)]
            for _ in range(self._star_count)
        ]
        self._last_t = 0.0

    def render(self, t: float) -> Image.Image:
        img = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        dt = t - self._last_t if self._last_t > 0 else 1.0 / 30
        self._last_t = t

        cx, cy = self.width / 2, self.height / 2
        r, g, b = self._color

        for star in self._stars:
            # Move star closer (decrease z)
            star[2] -= self._speed * dt * 0.5
            if star[2] <= 0.01:
                star[0] = random.uniform(-1, 1)
                star[1] = random.uniform(-1, 1)
                star[2] = 1.0

            # Project 3D -> 2D
            sx = int(cx + star[0] / star[2] * cx)
            sy = int(cy + star[1] / star[2] * cy)

            if 0 <= sx < self.width and 0 <= sy < self.height:
                # Brightness and size based on distance
                brightness = max(0.2, 1.0 - star[2])
                size = max(1, int((1.0 - star[2]) * 3))
                cr = int(r * brightness)
                cg = int(g * brightness)
                cb = int(b * brightness)
                if size <= 1:
                    draw.point((sx, sy), fill=(cr, cg, cb))
                else:
                    draw.ellipse(
                        [sx - size // 2, sy - size // 2,
                         sx + size // 2, sy + size // 2],
                        fill=(cr, cg, cb),
                    )

        return img
