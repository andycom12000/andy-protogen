from __future__ import annotations

import numpy as np
from PIL import Image

from protogen.generators import FrameEffect


class ColorShiftEffect(FrameEffect):
    """Rotates the hue of non-black pixels over time."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._speed = params.get("speed", 1.0)

    def apply(self, frame: Image.Image, t: float) -> Image.Image:
        hsv = frame.convert("HSV")
        arr = np.array(hsv)
        rgb_arr = np.array(frame)

        # Only shift non-black pixels (any channel > 0)
        mask = rgb_arr.max(axis=2) > 0
        # Pillow HSV: H is 0-255 (mapped from 0-360)
        offset = int((t * self._speed * 60) % 360 * 255 / 360) & 0xFF
        arr[:, :, 0][mask] = (arr[:, :, 0][mask].astype(np.uint16) + offset).astype(np.uint8)

        return Image.fromarray(arr, "HSV").convert("RGB")
