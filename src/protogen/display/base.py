from abc import ABC, abstractmethod

from PIL import Image


class DisplayBase(ABC):
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    @abstractmethod
    def show_image(self, image: Image.Image) -> None:
        """Push an image to the display."""

    @abstractmethod
    def clear(self) -> None:
        """Clear the display."""

    @abstractmethod
    def set_brightness(self, value: int) -> None:
        """Set brightness (0-100)."""
