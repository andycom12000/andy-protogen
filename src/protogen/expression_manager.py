from __future__ import annotations

import asyncio
import io
import logging
import random

import numpy as np
from PIL import Image

from protogen.animation import AnimationEngine
from protogen.display.base import DisplayBase
from protogen.expression import Expression, ExpressionType

logger = logging.getLogger(__name__)


class ExpressionManager:
    def __init__(
        self,
        display: DisplayBase,
        expressions: dict[str, Expression],
        blink_interval_min: float = 3.0,
        blink_interval_max: float = 6.0,
        transition_duration_ms: int = 0,
    ) -> None:
        self._display = display
        self._expressions = expressions
        self._names = sorted(expressions.keys())
        self.current_name: str | None = None
        self._animation = AnimationEngine(display)
        self._animation_task: asyncio.Task | None = None
        self._blink_enabled: bool = False
        self._blink_task: asyncio.Task | None = None
        self._blink_interval_min = blink_interval_min
        self._blink_interval_max = blink_interval_max
        self._transition_duration_ms = transition_duration_ms

    @property
    def expression_names(self) -> list[str]:
        return list(self._names)

    @property
    def blink_enabled(self) -> bool:
        return self._blink_enabled

    def set_expression(self, name: str) -> None:
        if name not in self._expressions:
            return

        # Capture old frame for transition (if display tracks it)
        old_frame = getattr(self._display, "last_frame", None)

        self._stop_animation()

        expr = self._expressions[name]
        self.current_name = name

        # Determine the new expression's first frame
        if expr.type == ExpressionType.STATIC and expr.image:
            new_frame = expr.image
        elif expr.type == ExpressionType.ANIMATION and expr.frames:
            new_frame = expr.frames[0]
        else:
            return

        # Cross-fade transition if we have an old frame and duration > 0
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
        """Cross-fade from old_frame to new_frame, then show target expression."""
        fps = 20
        duration_s = self._transition_duration_ms / 1000.0
        total_frames = max(1, int(duration_s * fps))

        # Pre-compute diff in RGB space (float32, one-time cost)
        old_arr = np.array(old_frame.convert("RGB"), dtype=np.float32)
        new_arr = np.array(new_frame.convert("RGB"), dtype=np.float32)
        diff = new_arr - old_arr

        for i in range(1, total_frames + 1):
            alpha = i / total_frames
            blended = (old_arr + diff * alpha).clip(0, 255).astype(np.uint8)
            self._display.show_image(Image.fromarray(blended, "RGB"))
            await asyncio.sleep(1.0 / fps)

        # After transition completes, show the target expression normally
        self._show_expression(target_expr)

    def _show_expression(self, expr: Expression) -> None:
        """Display an expression immediately (no transition)."""
        if expr.type == ExpressionType.STATIC and expr.image:
            self._display.show_image(expr.image)
        elif expr.type == ExpressionType.ANIMATION and expr.frames:
            self._animation_task = asyncio.create_task(
                self._animation.play(expr.frames, fps=expr.fps, loop=expr.loop)
            )

    def toggle_blink(self) -> bool:
        self._blink_enabled = not self._blink_enabled
        if self._blink_enabled:
            self._blink_task = asyncio.create_task(self._blink_loop())
        else:
            if self._blink_task is not None:
                self._blink_task.cancel()
                self._blink_task = None
        return self._blink_enabled

    async def _blink_loop(self) -> None:
        try:
            while self._blink_enabled:
                await asyncio.sleep(random.uniform(self._blink_interval_min, self._blink_interval_max))
                if not self._blink_enabled:
                    break

                if self.current_name is None:
                    continue
                current_expr = self._expressions.get(self.current_name)
                if current_expr is None:
                    continue
                if current_expr.type != ExpressionType.STATIC:
                    continue
                if current_expr.idle_animation is None:
                    continue

                blink_expr = self._expressions.get(current_expr.idle_animation)
                if blink_expr is None or not blink_expr.frames:
                    continue

                await self._animation.play(
                    blink_expr.frames, fps=blink_expr.fps, loop=False
                )

                if self._blink_enabled and current_expr.image:
                    self._display.show_image(current_expr.image)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("blink loop crashed")

    def get_thumbnail(self, name: str) -> bytes | None:
        """Return PNG bytes for the expression's preview image."""
        expr = self._expressions.get(name)
        if expr is None:
            return None

        img = None
        if expr.type == ExpressionType.STATIC and expr.image:
            img = expr.image
        elif expr.type == ExpressionType.ANIMATION and expr.frames:
            img = expr.frames[0]

        if img is None:
            return None

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _stop_animation(self) -> None:
        self._animation.stop()
        if self._animation_task is not None:
            self._animation_task.cancel()
            self._animation_task = None
