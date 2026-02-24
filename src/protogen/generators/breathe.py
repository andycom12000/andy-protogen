from __future__ import annotations

import math

import numpy as np
from PIL import Image

from protogen.generators import FrameEffect


class BreatheEffect(FrameEffect):
    """Pulsing brightness effect — makes the expression breathe."""

    _param_attrs = {"period": "_period", "amplitude": "_amplitude"}

    def __init__(self, width: int, height: int, params: dict) -> None:
        super().__init__(width, height, params)
        self._period = params.get("period", 3.0)
        self._amplitude = params.get("amplitude", 0.5)

    def apply(self, frame: Image.Image, t: float) -> Image.Image:
        # factor oscillates between (1 - amplitude) and 1.0
        factor = 1.0 - self._amplitude * (1.0 - math.sin(2 * math.pi * t / self._period)) / 2.0
        # Fixed-point: scale factor to 0-256 range for uint16 multiply + shift
        factor_int = int(factor * 256)
        arr = np.asarray(frame, dtype=np.uint8)
        result = (arr.astype(np.uint16) * factor_int >> 8).astype(np.uint8)
        return Image.fromarray(result, "RGB")
