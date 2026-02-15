from __future__ import annotations

from PIL import Image

from protogen.generators import ProceduralGenerator


class PlasmaGenerator(ProceduralGenerator):
    """Flowing plasma effect with overlapping sine waves (stub)."""

    def render(self, t: float) -> Image.Image:
        return Image.new("RGB", (self.width, self.height), (0, 0, 0))
