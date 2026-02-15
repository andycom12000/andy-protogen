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


class FrameEffect(ProceduralGenerator):
    """Effect that transforms the base expression frame."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._base_frame: Image.Image = Image.new("RGB", (width, height))

    @abstractmethod
    def apply(self, frame: Image.Image, t: float) -> Image.Image:
        """Apply the effect to a base frame.

        Args:
            frame: The base expression frame to transform.
            t: Time in seconds since effect started.

        Returns:
            Transformed RGB image.
        """

    def render(self, t: float) -> Image.Image:
        return self.apply(self._base_frame, t)


# Registry of generator name -> class.
# Generators register themselves when their modules are imported.
GENERATORS: dict[str, type[ProceduralGenerator]] = {}


def register_generators() -> None:
    """Import all generator modules to populate the registry."""
    from protogen.generators.matrix_rain import MatrixRainGenerator
    from protogen.generators.starfield import StarfieldGenerator
    from protogen.generators.plasma import PlasmaGenerator
    from protogen.generators.scrolling_text import ScrollingTextGenerator
    from protogen.generators.breathe import BreatheEffect
    from protogen.generators.color_shift import ColorShiftEffect
    from protogen.generators.rainbow_sweep import RainbowSweepEffect
    from protogen.generators.glitch import GlitchEffect

    GENERATORS["matrix_rain"] = MatrixRainGenerator
    GENERATORS["starfield"] = StarfieldGenerator
    GENERATORS["plasma"] = PlasmaGenerator
    GENERATORS["scrolling_text"] = ScrollingTextGenerator
    GENERATORS["breathe"] = BreatheEffect
    GENERATORS["color_shift"] = ColorShiftEffect
    GENERATORS["rainbow_sweep"] = RainbowSweepEffect
    GENERATORS["glitch"] = GlitchEffect
