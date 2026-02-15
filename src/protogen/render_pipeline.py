from __future__ import annotations

from PIL import Image

from protogen.display.base import DisplayBase


class RenderPipeline(DisplayBase):
    """Display wrapper that tracks the last frame and applies optional effects.

    Sits between the expression system and the hardware display.
    For now, effects are a placeholder (Batch 3 will add EffectBase).
    """

    def __init__(self, display: DisplayBase) -> None:
        super().__init__(display.width, display.height)
        self._display = display
        self.last_frame: Image.Image | None = None

    def show_image(self, image: Image.Image) -> None:
        self.last_frame = image
        self._display.show_image(image)

    def clear(self) -> None:
        self.last_frame = None
        self._display.clear()

    def set_brightness(self, value: int) -> None:
        self._display.set_brightness(value)

    @property
    def brightness(self) -> int:
        return self._display.brightness
