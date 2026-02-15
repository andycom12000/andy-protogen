from __future__ import annotations

import numpy as np
from PIL import Image

from protogen.generators import FrameEffect

_SPEED_FACTOR = 60 * 255 / 360


class ColorShiftEffect(FrameEffect):
    """Rotates the hue of non-black pixels over time."""

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._speed = params.get("speed", 1.0)

    def update_params(self, params: dict) -> None:
        super().update_params(params)
        if "speed" in params:
            self._speed = params["speed"]

    def apply(self, frame: Image.Image, t: float) -> Image.Image:
        # Zero-copy view to check for non-black pixels
        rgb_view = np.asarray(frame)
        mask = rgb_view.max(axis=2) > 0
        if not mask.any():
            return frame

        hsv = frame.convert("HSV")
        arr = np.array(hsv)

        # Pillow HSV: H is 0-255 (mapped from 0-360)
        offset = int((t * self._speed * _SPEED_FACTOR) % 256) & 0xFF
        arr[:, :, 0][mask] = (arr[:, :, 0][mask].astype(np.uint16) + offset).astype(np.uint8)

        return Image.fromarray(arr, "HSV").convert("RGB")
