import numpy as np
from PIL import Image

from protogen.display.base import DisplayBase


class HUB75Display(DisplayBase):
    """Real HUB75 display driver using Adafruit PioMatter. RPi 5 only."""

    def __init__(self, width: int = 128, height: int = 32, n_addr_lines: int = 4):
        super().__init__(width, height)
        import adafruit_blinka_raspberry_pi5_piomatter as piomatter

        self._framebuffer = np.zeros((height, width, 3), dtype=np.uint8)
        self._matrix = piomatter.PioMatter(
            colorspace=piomatter.Colorspace.RGB888Packed,
            pinout=piomatter.Pinout.AdafruitMatrixBonnet,
            framebuffer=self._framebuffer,
            geometry=piomatter.Geometry(
                width=width,
                height=height,
                n_addr_lines=n_addr_lines,
                rotation=piomatter.Orientation.Normal,
            ),
        )
        self.brightness = 100
        self._brightness_lut = np.arange(256, dtype=np.uint8)
        self.last_image: Image.Image | None = None

    def _refresh(self) -> None:
        """Re-render the current image to the framebuffer."""
        if self.last_image is None:
            return
        arr = np.asarray(self.last_image, dtype=np.uint8)
        if self.brightness < 100:
            arr = self._brightness_lut[arr]
        self._framebuffer[:] = arr
        self._matrix.show()

    def show_image(self, image: Image.Image) -> None:
        if image.mode != "RGB" or image.size != (self.width, self.height):
            image = image.convert("RGB").resize((self.width, self.height))
        self.last_image = image
        self._refresh()

    def clear(self) -> None:
        self._framebuffer[:] = 0
        self._matrix.show()

    def set_brightness(self, value: int) -> None:
        self.brightness = max(0, min(100, value))
        self._brightness_lut = np.array(
            [min(255, i * self.brightness // 100) for i in range(256)],
            dtype=np.uint8,
        )
        self._refresh()
