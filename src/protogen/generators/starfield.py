from __future__ import annotations

from PIL import Image

from protogen.generators import ProceduralGenerator


class StarfieldGenerator(ProceduralGenerator):
    """3D starfield flying outward from center (stub)."""

    def render(self, t: float) -> Image.Image:
        return Image.new("RGB", (self.width, self.height), (0, 0, 0))
