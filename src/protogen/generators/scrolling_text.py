from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from protogen.generators import ProceduralGenerator


class ScrollingTextGenerator(ProceduralGenerator):
    """Horizontal scrolling text from right to left."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._text = params.get("text", "PROTOGEN")
        self._speed = params.get("speed", 50.0)  # pixels per second
        self._color = tuple(params.get("color", [0, 255, 255]))
        self._font = ImageFont.load_default()
        self._render_text_image()

    def _render_text_image(self) -> None:
        """Pre-render the full text into a wide image for scrolling."""
        bbox = self._font.getbbox(self._text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        # Add padding: full screen width on each side for smooth scroll
        total_w = tw + self.width * 2
        self._text_img = Image.new("RGB", (total_w, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(self._text_img)
        y = (self.height - th) // 2
        draw.text((self.width, y), self._text, fill=self._color, font=self._font)
        self._total_width = total_w

    def set_text(self, text: str) -> None:
        """Update the scrolling text dynamically."""
        self._text = text
        self._render_text_image()

    def render(self, t: float) -> Image.Image:
        offset = int(t * self._speed) % self._total_width
        # Crop a window from the pre-rendered text image
        return self._text_img.crop((offset, 0, offset + self.width, self.height))
