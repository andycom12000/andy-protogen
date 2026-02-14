import numpy as np
from PIL import Image

from protogen.display.base import DisplayBase


class MockDisplay(DisplayBase):
    """Mock display that stores the last shown image for testing,
    and optionally renders to a pygame window."""

    def __init__(self, width: int = 128, height: int = 32, scale: int = 8, use_pygame: bool = False):
        super().__init__(width, height)
        self.scale = scale
        self.brightness = 100
        self.last_image: Image.Image | None = None
        self.use_pygame = use_pygame
        self._screen = None

        if self.use_pygame:
            import pygame
            pygame.init()
            self._screen = pygame.display.set_mode((width * scale, height * scale))
            pygame.display.set_caption("Protogen Mock Display")

    def show_image(self, image: Image.Image) -> None:
        self.last_image = image.convert("RGB").resize((self.width, self.height))
        if self.use_pygame and self._screen is not None:
            import pygame
            arr = np.array(self.last_image)
            # Apply brightness
            arr = (arr * self.brightness / 100).astype(np.uint8)
            surface = pygame.surfarray.make_surface(np.transpose(arr, (1, 0, 2)))
            scaled = pygame.transform.scale(surface, (self.width * self.scale, self.height * self.scale))
            self._screen.blit(scaled, (0, 0))
            pygame.display.flip()

    def clear(self) -> None:
        self.show_image(Image.new("RGB", (self.width, self.height), (0, 0, 0)))

    def set_brightness(self, value: int) -> None:
        self.brightness = max(0, min(100, value))
