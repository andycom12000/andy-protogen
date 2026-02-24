from __future__ import annotations

import asyncio
import logging

import numpy as np
from PIL import Image

from protogen.animation import AnimationEngine
from protogen.blink_controller import BlinkController
from protogen.display.base import DisplayBase
from protogen.expression import Expression, ExpressionType
from protogen.expression_store import ExpressionStore

logger = logging.getLogger(__name__)


class ExpressionManager:
    def __init__(
        self,
        display: DisplayBase,
        store: ExpressionStore,
        blink_interval_min: float = 3.0,
        blink_interval_max: float = 6.0,
        transition_duration_ms: int = 0,
    ) -> None:
        self._display = display
        self._store = store
        self.current_name: str | None = None
        self._animation = AnimationEngine(display)
        self._animation_task: asyncio.Task | None = None
        self._transition_duration_ms = transition_duration_ms
        self._blink = BlinkController(
            store, self._animation, display,
            get_current_name=lambda: self.current_name,
            interval_min=blink_interval_min,
            interval_max=blink_interval_max,
        )

    @property
    def expression_names(self) -> list[str]:
        return self._store.names

    @property
    def blink_enabled(self) -> bool:
        return self._blink.enabled

    def set_expression(self, name: str) -> None:
        expr = self._store.get(name)
        if expr is None:
            return

        old_frame = getattr(self._display, "last_frame", None)
        self._stop_animation()
        self.current_name = name

        if expr.type == ExpressionType.STATIC and expr.image:
            new_frame = expr.image
        elif expr.type == ExpressionType.ANIMATION and expr.frames:
            new_frame = expr.frames[0]
        else:
            return

        if old_frame is not None and self._transition_duration_ms > 0:
            self._animation_task = asyncio.create_task(
                self._play_transition(old_frame, new_frame, expr)
            )
        else:
            self._show_expression(expr)

    async def _play_transition(
        self,
        old_frame: Image.Image,
        new_frame: Image.Image,
        target_expr: Expression,
    ) -> None:
        fps = 20
        duration_s = self._transition_duration_ms / 1000.0
        total_frames = max(1, int(duration_s * fps))
        interval = 1.0 / fps

        old_arr = np.array(old_frame.convert("RGB"), dtype=np.float32)
        new_arr = np.array(new_frame.convert("RGB"), dtype=np.float32)
        diff = new_arr - old_arr
        blend_buf = np.empty_like(old_arr)

        for i in range(1, total_frames + 1):
            alpha = i / total_frames
            np.multiply(diff, alpha, out=blend_buf)
            np.add(old_arr, blend_buf, out=blend_buf)
            self._display.show_image(
                Image.fromarray(blend_buf.astype(np.uint8), "RGB")
            )
            await asyncio.sleep(interval)

        self._show_expression(target_expr)

    def _show_expression(self, expr: Expression) -> None:
        if expr.type == ExpressionType.STATIC and expr.image:
            self._display.show_image(expr.image)
        elif expr.type == ExpressionType.ANIMATION and expr.frames:
            self._animation_task = asyncio.create_task(
                self._animation.play(expr.frames, fps=expr.fps, loop=expr.loop)
            )

    def toggle_blink(self) -> bool:
        return self._blink.toggle()

    def get_thumbnail(self, name: str) -> bytes | None:
        return self._store.get_thumbnail(name)

    def _stop_animation(self) -> None:
        self._animation.stop()
        if self._animation_task is not None:
            self._animation_task.cancel()
            self._animation_task = None
