from __future__ import annotations

import asyncio
import logging
import random

from protogen.animation import AnimationEngine
from protogen.display.base import DisplayBase
from protogen.expression import Expression, ExpressionType

logger = logging.getLogger(__name__)


class ExpressionManager:
    def __init__(self, display: DisplayBase, expressions: dict[str, Expression]) -> None:
        self._display = display
        self._expressions = expressions
        self._names = sorted(expressions.keys())
        self.current_name: str | None = None
        self._animation = AnimationEngine(display)
        self._animation_task: asyncio.Task | None = None
        self._blink_enabled: bool = False
        self._blink_task: asyncio.Task | None = None

    @property
    def expression_names(self) -> list[str]:
        return list(self._names)

    @property
    def blink_enabled(self) -> bool:
        return self._blink_enabled

    def set_expression(self, name: str) -> None:
        if name not in self._expressions:
            return
        # 停止正在播放的動畫
        self._stop_animation()

        expr = self._expressions[name]
        self.current_name = name

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
                await asyncio.sleep(random.uniform(3.0, 6.0))
                if not self._blink_enabled:
                    break

                # 只在靜態表情且有 idle_animation 時觸發
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

                # 播放眨眼動畫
                await self._animation.play(
                    blink_expr.frames, fps=blink_expr.fps, loop=False
                )

                # 動畫結束後恢復靜態圖
                if self._blink_enabled and current_expr.image:
                    self._display.show_image(current_expr.image)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("blink loop crashed")

    def _stop_animation(self) -> None:
        self._animation.stop()
        if self._animation_task is not None:
            self._animation_task.cancel()
            self._animation_task = None
