from __future__ import annotations

import asyncio
import logging
import random
from typing import Callable

from protogen.animation import AnimationEngine
from protogen.expression import ExpressionType
from protogen.expression_store import ExpressionStore

logger = logging.getLogger(__name__)


class BlinkController:
    """Periodic idle blink animation controller."""

    def __init__(
        self,
        store: ExpressionStore,
        animation: AnimationEngine,
        display,
        get_current_name: Callable[[], str | None],
        interval_min: float = 3.0,
        interval_max: float = 6.0,
    ) -> None:
        self._store = store
        self._animation = animation
        self._display = display
        self._get_current_name = get_current_name
        self._enabled = False
        self._task: asyncio.Task | None = None
        self._interval_min = interval_min
        self._interval_max = interval_max

    @property
    def enabled(self) -> bool:
        return self._enabled

    def toggle(self) -> bool:
        self._enabled = not self._enabled
        if self._enabled:
            self._task = asyncio.create_task(self._loop())
        else:
            if self._task is not None:
                self._task.cancel()
                self._task = None
        return self._enabled

    async def _loop(self) -> None:
        try:
            while self._enabled:
                await asyncio.sleep(
                    random.uniform(self._interval_min, self._interval_max)
                )
                if not self._enabled:
                    break

                name = self._get_current_name()
                if name is None:
                    continue
                expr = self._store.get(name)
                if expr is None or expr.type != ExpressionType.STATIC:
                    continue
                if expr.idle_animation is None:
                    continue

                blink_expr = self._store.get(expr.idle_animation)
                if blink_expr is None or not blink_expr.frames:
                    continue

                await self._animation.play(
                    blink_expr.frames, fps=blink_expr.fps, loop=False
                )

                if self._enabled and expr.image:
                    self._display.show_image(expr.image)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("blink loop crashed")
