# Phase 3: Architecture Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 拆分 ExpressionManager 為獨立元件（ExpressionStore + BlinkController），RenderPipeline 改用組合模式，改善依賴注入。

**Architecture:** ExpressionManager 目前承擔三種職責：表情資料管理、動畫播放/交叉淡化、眨眼控制。將資料管理抽為 ExpressionStore、眨眼抽為 BlinkController，ExpressionManager 保留為門面（facade）負責動畫/轉場邏輯並協調子元件。RenderPipeline 改為不繼承 DisplayBase，透過組合持有 display 實例。

**Tech Stack:** Python 3.14, PIL/Pillow, NumPy, asyncio, pytest

**Design Decision — 為何不抽 AnimationController：** 動畫播放/交叉淡化與表情切換邏輯緊密耦合（需追蹤 current_name、管理 animation_task、讀取 last_frame），強行拆分會產生大量回呼和循環依賴。ExpressionManager 抽走 Store 和 Blink 後約 ~80 行，規模適當。

---

## 現有架構摘要

```
ExpressionManager (184 lines) — 三個職責：
├── 資料管理：expressions dict, _names, expression_names, get_thumbnail
├── 動畫控制：set_expression, _play_transition, _show_expression, _stop_animation
└── 眨眼控制：toggle_blink, _blink_loop, _blink_enabled/task/interval

RenderPipeline(DisplayBase) — 繼承 DisplayBase ABC
├── 包裝 display 實例，追蹤 last_frame
├── 效果合成（procedural generators）
└── FPS 追蹤（EMA）

main.py — 建立元件、處理命令
```

## 目標架構

```
ExpressionStore (new) — 純資料查詢
├── expressions dict, names, get(), get_thumbnail()

BlinkController (new) — 眨眼邏輯
├── toggle(), enabled, _loop()
├── 依賴：ExpressionStore, AnimationEngine, display, get_current_name callback

ExpressionManager (refactored) — 門面 + 動畫控制
├── 持有 ExpressionStore, BlinkController
├── set_expression, _play_transition, _show_expression
├── 委派 expression_names → store.names
├── 委派 toggle_blink → blink.toggle()
├── 委派 get_thumbnail → store.get_thumbnail()

RenderPipeline (no inheritance) — 組合模式
├── 不再繼承 DisplayBase
├── 持有 display 實例，委派所有 display 方法
```

---

### Task 1: Extract ExpressionStore

**Files:**
- Create: `src/protogen/expression_store.py`
- Create: `tests/test_expression_store.py`

**Step 1: Write ExpressionStore tests**

```python
# tests/test_expression_store.py
import io

import pytest
from PIL import Image

from protogen.expression import Expression, ExpressionType
from protogen.expression_store import ExpressionStore


@pytest.fixture
def sample_store():
    return ExpressionStore({
        "happy": Expression(
            name="happy", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 255, 0)),
        ),
        "sad": Expression(
            name="sad", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 0, 255)),
        ),
        "blink": Expression(
            name="blink", type=ExpressionType.ANIMATION,
            frames=[Image.new("RGB", (128, 32), (255, 255, 255))],
            fps=15, loop=False, hidden=True,
        ),
    })


def test_names_excludes_hidden(sample_store):
    assert sample_store.names == ["happy", "sad"]


def test_get_existing(sample_store):
    expr = sample_store.get("happy")
    assert expr is not None
    assert expr.name == "happy"


def test_get_hidden(sample_store):
    """Hidden expressions are still accessible via get()."""
    expr = sample_store.get("blink")
    assert expr is not None


def test_get_nonexistent(sample_store):
    assert sample_store.get("nonexistent") is None


def test_get_thumbnail_static(sample_store):
    data = sample_store.get_thumbnail("happy")
    assert data is not None
    assert data[:4] == b'\x89PNG'


def test_get_thumbnail_animation(sample_store):
    data = sample_store.get_thumbnail("blink")
    assert data is not None
    img = Image.open(io.BytesIO(data))
    assert img.getpixel((0, 0)) == (255, 255, 255)


def test_get_thumbnail_nonexistent(sample_store):
    assert sample_store.get_thumbnail("nonexistent") is None
```

**Step 2: Run tests — should FAIL (module not found)**

Run: `python -m pytest tests/test_expression_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'protogen.expression_store'`

**Step 3: Implement ExpressionStore**

```python
# src/protogen/expression_store.py
from __future__ import annotations

import io
import logging

from PIL import Image

from protogen.expression import Expression, ExpressionType

logger = logging.getLogger(__name__)


class ExpressionStore:
    """Expression data store — loading, querying, and index management."""

    def __init__(self, expressions: dict[str, Expression]) -> None:
        self._expressions = expressions
        self._names = sorted(
            name for name, expr in expressions.items() if not expr.hidden
        )

    @property
    def names(self) -> list[str]:
        return list(self._names)

    def get(self, name: str) -> Expression | None:
        return self._expressions.get(name)

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
```

**Step 4: Run tests — should PASS**

Run: `python -m pytest tests/test_expression_store.py -v`
Expected: 7 passed

**Step 5: Run full test suite — no regressions**

Run: `python -m pytest -v`
Expected: All existing tests pass (purely additive change)

**Step 6: Commit**

```
git add src/protogen/expression_store.py tests/test_expression_store.py
git commit -m "refactor: extract ExpressionStore from ExpressionManager"
```

---

### Task 2: Extract BlinkController

**Files:**
- Create: `src/protogen/blink_controller.py`
- Create: `tests/test_blink_controller.py`

**Step 1: Write BlinkController tests**

```python
# tests/test_blink_controller.py
import asyncio

import pytest
from PIL import Image

from protogen.animation import AnimationEngine
from protogen.expression import Expression, ExpressionType
from protogen.expression_store import ExpressionStore
from protogen.blink_controller import BlinkController


@pytest.fixture
def blink_fixtures(mock_display):
    store = ExpressionStore({
        "happy": Expression(
            name="happy", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 255, 0)),
            idle_animation="blink",
        ),
        "blink": Expression(
            name="blink", type=ExpressionType.ANIMATION,
            frames=[Image.new("RGB", (128, 32), (255, 255, 255))],
            fps=60, loop=False, hidden=True,
        ),
        "no_blink": Expression(
            name="no_blink", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (255, 0, 0)),
        ),
    })
    animation = AnimationEngine(mock_display)
    return store, animation, mock_display


def test_toggle_on_off(blink_fixtures):
    store, animation, display = blink_fixtures
    ctrl = BlinkController(
        store, animation, display,
        get_current_name=lambda: "happy",
    )
    assert not ctrl.enabled
    assert ctrl.toggle() is True
    assert ctrl.enabled
    assert ctrl.toggle() is False
    assert not ctrl.enabled


@pytest.mark.asyncio
async def test_blink_triggers(blink_fixtures):
    store, animation, display = blink_fixtures
    ctrl = BlinkController(
        store, animation, display,
        get_current_name=lambda: "happy",
        interval_min=0.01, interval_max=0.02,
    )
    ctrl.toggle()
    await asyncio.sleep(0.15)
    ctrl.toggle()  # stop
    # Blink should have triggered — display shows something
    assert display.last_image is not None


@pytest.mark.asyncio
async def test_blink_skips_no_idle_animation(blink_fixtures):
    """Expressions without idle_animation don't blink."""
    store, animation, display = blink_fixtures
    ctrl = BlinkController(
        store, animation, display,
        get_current_name=lambda: "no_blink",
        interval_min=0.01, interval_max=0.02,
    )
    display.show_image(Image.new("RGB", (128, 32), (255, 0, 0)))
    original_image = display.last_image

    ctrl.toggle()
    await asyncio.sleep(0.1)
    ctrl.toggle()

    # Image should remain unchanged (no blink played)
    assert display.last_image.getpixel((0, 0)) == (255, 0, 0)
```

**Step 2: Run tests — should FAIL**

Run: `python -m pytest tests/test_blink_controller.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'protogen.blink_controller'`

**Step 3: Implement BlinkController**

```python
# src/protogen/blink_controller.py
from __future__ import annotations

import asyncio
import logging
import random
from typing import Callable

from PIL import Image

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
```

**Step 4: Run tests — should PASS**

Run: `python -m pytest tests/test_blink_controller.py -v`
Expected: 3 passed

**Step 5: Run full test suite — no regressions**

Run: `python -m pytest -v`
Expected: All tests pass (purely additive)

**Step 6: Commit**

```
git add src/protogen/blink_controller.py tests/test_blink_controller.py
git commit -m "refactor: extract BlinkController from ExpressionManager"
```

---

### Task 3: Refactor ExpressionManager to use ExpressionStore + BlinkController

**Files:**
- Modify: `src/protogen/expression_manager.py`
- Modify: `src/protogen/main.py`
- Modify: `tests/test_expression_manager.py`

**Step 1: Update ExpressionManager**

重寫 `expression_manager.py`，改為門面模式。構造函式改接 `ExpressionStore`，內部建立 `BlinkController`。

```python
# src/protogen/expression_manager.py
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
        """Cross-fade from old_frame to new_frame, then show target expression."""
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
```

**Step 2: Update main.py**

在 `async_main()` 中，建立 `ExpressionStore` 並傳給 `ExpressionManager`。

```python
# main.py 修改處：
# 新增 import
from protogen.expression_store import ExpressionStore

# 在 expressions = load_expressions(...) 之後新增：
store = ExpressionStore(expressions)

# 修改 ExpressionManager 建立：
expr_mgr = ExpressionManager(
    pipeline, store,
    blink_interval_min=config.blink_interval_min,
    blink_interval_max=config.blink_interval_max,
    transition_duration_ms=config.transition_duration_ms,
)
```

**Step 3: Update tests**

`tests/test_expression_manager.py` 中所有建立 `ExpressionManager` 的地方，將 `dict` 改為 `ExpressionStore(dict)`。

修改 imports：
```python
from protogen.expression_store import ExpressionStore
```

修改 `sample_expressions` fixture：
```python
@pytest.fixture
def sample_store():
    return ExpressionStore({
        "happy": Expression(
            name="happy", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 255, 0)),
        ),
        "sad": Expression(
            name="sad", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 0, 255)),
        ),
    })
```

所有 `ExpressionManager(display, sample_expressions, ...)` 改為 `ExpressionManager(display, sample_store, ...)`。

每個測試函式的參數也要從 `sample_expressions` 改為 `sample_store`。

同理，各 async test 中直接建立 expressions dict 的地方，也需用 `ExpressionStore(...)` 包裝。

**Step 4: Run full test suite**

Run: `python -m pytest -v`
Expected: All tests pass

**Step 5: Commit**

```
git add src/protogen/expression_manager.py src/protogen/main.py tests/test_expression_manager.py
git commit -m "refactor: ExpressionManager uses ExpressionStore + BlinkController"
```

---

### Task 4: RenderPipeline composition (remove DisplayBase inheritance)

**Files:**
- Modify: `src/protogen/render_pipeline.py`
- Modify: `tests/test_render_pipeline.py`

**Step 1: Remove inheritance, use composition**

```python
# src/protogen/render_pipeline.py — 修改處

# 移除 DisplayBase import（改為只 import 用於 type hint）
# 之前：
class RenderPipeline(DisplayBase):
    def __init__(self, display: DisplayBase) -> None:
        super().__init__(display.width, display.height)
        self._display = display

# 之後：
class RenderPipeline:
    """Display wrapper that tracks the last frame and composites effects."""

    def __init__(self, display: DisplayBase) -> None:
        self.width = display.width
        self.height = display.height
        self._display = display
```

只需修改兩行：
1. `class RenderPipeline(DisplayBase):` → `class RenderPipeline:`
2. `super().__init__(display.width, display.height)` → `self.width = display.width` + `self.height = display.height`

其餘所有方法（`show_image`, `clear`, `set_brightness`, `brightness`）保持不變——它們已經委派給 `self._display`。

**Step 2: Run full test suite**

Run: `python -m pytest -v`
Expected: All tests pass（RenderPipeline 的公開 API 沒有改變，duck typing 確保相容性）

**Step 3: Commit**

```
git add src/protogen/render_pipeline.py
git commit -m "refactor: RenderPipeline uses composition instead of DisplayBase inheritance"
```

---

### Task 5: Final verification and cleanup

**Step 1: Run full test suite**

Run: `python -m pytest -v`
Expected: All tests pass

**Step 2: Verify local startup**

Run: `python -m protogen.main`
Expected: 應用程式正常啟動，Web UI 可存取

**Step 3: Verify module imports are clean**

Run: `python -c "from protogen.expression_store import ExpressionStore; from protogen.blink_controller import BlinkController; print('imports OK')"`
Expected: `imports OK`

**Step 4: Commit (if any cleanup needed)**

```
git commit -m "refactor: Phase 3 architecture refactoring complete"
```
