from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image


class ProceduralGenerator(ABC):
    """Base class for procedural expression generators."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        self.width = width
        self.height = height
        self.params = params

    @abstractmethod
    def render(self, t: float) -> Image.Image:
        """Render a frame at time t (seconds since start).

        Returns:
            RGB image of size (width, height).
        """


# Registry of generator name -> class.
# Generators register themselves when their modules are imported.
GENERATORS: dict[str, type[ProceduralGenerator]] = {}


def register_generators() -> None:
    """Import all generator modules to populate the registry."""
    from protogen.generators.matrix_rain import MatrixRainGenerator
    from protogen.generators.starfield import StarfieldGenerator
    from protogen.generators.plasma import PlasmaGenerator
    from protogen.generators.scrolling_text import ScrollingTextGenerator

    GENERATORS["matrix_rain"] = MatrixRainGenerator
    GENERATORS["starfield"] = StarfieldGenerator
    GENERATORS["plasma"] = PlasmaGenerator
    GENERATORS["scrolling_text"] = ScrollingTextGenerator
