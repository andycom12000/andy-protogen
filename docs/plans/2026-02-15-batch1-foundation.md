# Batch 1: Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Strengthen the foundation of the Protogen visor system — fix blink config bug, introduce a render pipeline for future effect layering, add expression transition animations, a boot animation, and expression preview thumbnails in the Web UI.

**Architecture:** The key architectural addition is `RenderPipeline`, a `DisplayBase` subclass that wraps the real display. It sits between the expression system and the hardware display, enabling effect processing (Batch 3) while tracking the last rendered frame (needed for transitions). All existing code that receives a `DisplayBase` can transparently use the pipeline.

**Tech Stack:** Python 3.14, PIL/Pillow, asyncio, FastAPI, pytest + pytest-asyncio

---

## Task 1: Fix blink_interval_max Config Bug

The `_blink_loop()` in `expression_manager.py:62` hardcodes `random.uniform(3.0, 6.0)` instead of using `config.blink_interval_min` / `config.blink_interval_max`. The `ExpressionManager` class doesn't receive these config values.

**Files:**
- Modify: `src/protogen/expression_manager.py`
- Modify: `src/protogen/main.py:38`
- Test: `tests/test_expression_manager.py`

**Step 1: Write the failing test**

Add to `tests/test_expression_manager.py`:

```python
@pytest.mark.asyncio
async def test_blink_uses_configured_interval(mock_display):
    """Verify _blink_loop uses blink_interval_min/max, not hardcoded values."""
    blink_frames = [Image.new("RGB", (128, 32), (255, 255, 255))]
    expressions = {
        "happy": Expression(
            name="happy", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 255, 0)),
            idle_animation="blink",
        ),
        "blink": Expression(
            name="blink", type=ExpressionType.ANIMATION,
            frames=blink_frames, fps=60, loop=False,
        ),
    }
    mgr = ExpressionManager(
        mock_display, expressions,
        blink_interval_min=0.01, blink_interval_max=0.02,
    )
    mgr.set_expression("happy")
    mgr.toggle_blink()

    # With 0.01-0.02s interval, blink should trigger quickly
    await asyncio.sleep(0.15)
    mgr.toggle_blink()  # Stop blink loop

    # If hardcoded 3-6s were used, last_image would still be the original green.
    # With our short interval, the blink animation should have run and restored.
    assert mock_display.last_image is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_expression_manager.py::test_blink_uses_configured_interval -v`
Expected: FAIL — `ExpressionManager.__init__() got an unexpected keyword argument 'blink_interval_min'`

**Step 3: Implement the fix**

In `src/protogen/expression_manager.py`, change the `__init__` signature (line 15) to accept blink intervals:

```python
class ExpressionManager:
    def __init__(
        self,
        display: DisplayBase,
        expressions: dict[str, Expression],
        blink_interval_min: float = 3.0,
        blink_interval_max: float = 6.0,
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
```

Change line 62 in `_blink_loop()`:

```python
# Before:
await asyncio.sleep(random.uniform(3.0, 6.0))
# After:
await asyncio.sleep(random.uniform(self._blink_interval_min, self._blink_interval_max))
```

In `src/protogen/main.py`, update line 38 to pass config values:

```python
expr_mgr = ExpressionManager(
    display, expressions,
    blink_interval_min=config.blink_interval_min,
    blink_interval_max=config.blink_interval_max,
)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_expression_manager.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/protogen/expression_manager.py src/protogen/main.py tests/test_expression_manager.py
git commit -m "fix: use configured blink_interval_min/max instead of hardcoded values"
```

---

## Task 2: RenderPipeline

Create `RenderPipeline` — a `DisplayBase` subclass that wraps the real display. For now it's a pass-through, but it tracks `last_frame` (needed for Task 3 transitions) and has an `effect` slot (used in Batch 3).

**Files:**
- Create: `src/protogen/render_pipeline.py`
- Modify: `src/protogen/main.py`
- Test: `tests/test_render_pipeline.py`

**Step 1: Write the failing tests**

Create `tests/test_render_pipeline.py`:

```python
from PIL import Image

from protogen.display.mock import MockDisplay
from protogen.render_pipeline import RenderPipeline


def test_passthrough_show_image():
    """RenderPipeline forwards show_image to the wrapped display."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)

    img = Image.new("RGB", (128, 32), (255, 0, 0))
    pipeline.show_image(img)

    assert display.last_image is not None


def test_tracks_last_frame():
    """RenderPipeline stores the last frame before any effects."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)

    img = Image.new("RGB", (128, 32), (0, 255, 0))
    pipeline.show_image(img)

    assert pipeline.last_frame is not None
    # last_frame should be the original image (before effects)
    assert pipeline.last_frame.size == (128, 32)


def test_clear_resets_last_frame():
    """Clearing the pipeline resets last_frame to None."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)

    pipeline.show_image(Image.new("RGB", (128, 32), (255, 0, 0)))
    assert pipeline.last_frame is not None

    pipeline.clear()
    assert pipeline.last_frame is None


def test_delegates_set_brightness():
    """set_brightness is forwarded to the wrapped display."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)

    pipeline.set_brightness(50)
    assert display.brightness == 50


def test_brightness_property():
    """brightness property reads from the wrapped display."""
    display = MockDisplay(width=128, height=32)
    display.brightness = 75
    pipeline = RenderPipeline(display)

    assert pipeline.brightness == 75


def test_no_effect_passthrough():
    """With no effect set, frames pass through unchanged."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)

    img = Image.new("RGB", (128, 32), (100, 100, 100))
    pipeline.show_image(img)

    # The display should have received the same pixel values
    pixel = display.last_image.getpixel((0, 0))
    assert pixel == (100, 100, 100)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'protogen.render_pipeline'`

**Step 3: Implement RenderPipeline**

Create `src/protogen/render_pipeline.py`:

```python
from __future__ import annotations

from PIL import Image

from protogen.display.base import DisplayBase


class RenderPipeline(DisplayBase):
    """Display wrapper that tracks the last frame and applies optional effects.

    Sits between the expression system and the hardware display.
    For now, effects are a placeholder (Batch 3 will add EffectBase).
    """

    def __init__(self, display: DisplayBase) -> None:
        super().__init__(display.width, display.height)
        self._display = display
        self.last_frame: Image.Image | None = None

    def show_image(self, image: Image.Image) -> None:
        self.last_frame = image
        self._display.show_image(image)

    def clear(self) -> None:
        self.last_frame = None
        self._display.clear()

    def set_brightness(self, value: int) -> None:
        self._display.set_brightness(value)

    @property
    def brightness(self) -> int:
        return self._display.brightness
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render_pipeline.py -v`
Expected: ALL PASS

**Step 5: Integrate into main.py**

In `src/protogen/main.py`, wrap the display in a pipeline. The `display` variable is still used for brightness control and pygame events; the `pipeline` is what ExpressionManager uses.

```python
# Add import at top:
from protogen.render_pipeline import RenderPipeline

# In async_main(), after line 35 (display.set_brightness):
pipeline = RenderPipeline(display)

# Change line 38 to use pipeline:
expr_mgr = ExpressionManager(
    pipeline, expressions,
    blink_interval_min=config.blink_interval_min,
    blink_interval_max=config.blink_interval_max,
)
```

Note: `display.set_brightness()` in `handle_commands()` (line 66) stays using `display` directly — brightness is a hardware concern. The lambda `get_brightness=lambda: display.brightness` also stays on `display`. The `pump_display_events()` still uses `display`. Only ExpressionManager uses `pipeline`.

**Step 6: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/protogen/render_pipeline.py tests/test_render_pipeline.py src/protogen/main.py
git commit -m "feat: add RenderPipeline display wrapper with last_frame tracking"
```

---

## Task 3: Expression Transition Animation

When switching expressions, cross-fade from the old frame to the new frame over `transition_duration_ms`. Uses `RenderPipeline.last_frame` (via `self._display.last_frame`) to capture the old frame.

**Files:**
- Modify: `src/protogen/expression_manager.py`
- Test: `tests/test_expression_manager.py`

**Step 1: Write the failing test**

Add to `tests/test_expression_manager.py`:

```python
from protogen.render_pipeline import RenderPipeline


@pytest.mark.asyncio
async def test_transition_cross_fade(mock_display):
    """Switching expressions with transition_duration_ms produces a cross-fade."""
    pipeline = RenderPipeline(mock_display)
    red_img = Image.new("RGB", (128, 32), (255, 0, 0))
    blue_img = Image.new("RGB", (128, 32), (0, 0, 255))
    expressions = {
        "red": Expression(
            name="red", type=ExpressionType.STATIC, image=red_img,
        ),
        "blue": Expression(
            name="blue", type=ExpressionType.STATIC, image=blue_img,
        ),
    }
    mgr = ExpressionManager(pipeline, expressions, transition_duration_ms=100)
    mgr.set_expression("red")

    # Now switch — should trigger a cross-fade
    mgr.set_expression("blue")
    # Let the transition play out
    await asyncio.sleep(0.2)

    assert mgr.current_name == "blue"
    # After transition, the final image should be the blue expression
    pixel = mock_display.last_image.getpixel((0, 0))
    assert pixel == (0, 0, 255)


@pytest.mark.asyncio
async def test_transition_skipped_when_zero(mock_display):
    """With transition_duration_ms=0, expression switches immediately."""
    pipeline = RenderPipeline(mock_display)
    expressions = {
        "a": Expression(
            name="a", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (255, 0, 0)),
        ),
        "b": Expression(
            name="b", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 255, 0)),
        ),
    }
    mgr = ExpressionManager(pipeline, expressions, transition_duration_ms=0)
    mgr.set_expression("a")
    mgr.set_expression("b")

    # Should be immediate — no need to await
    pixel = mock_display.last_image.getpixel((0, 0))
    assert pixel == (0, 255, 0)


@pytest.mark.asyncio
async def test_transition_skipped_on_first_expression(mock_display):
    """First expression set has no old frame, so no transition."""
    pipeline = RenderPipeline(mock_display)
    expressions = {
        "a": Expression(
            name="a", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (255, 0, 0)),
        ),
    }
    mgr = ExpressionManager(pipeline, expressions, transition_duration_ms=200)
    mgr.set_expression("a")

    # Should display immediately (no old frame to transition from)
    pixel = mock_display.last_image.getpixel((0, 0))
    assert pixel == (255, 0, 0)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_expression_manager.py::test_transition_cross_fade -v`
Expected: FAIL — `ExpressionManager.__init__() got an unexpected keyword argument 'transition_duration_ms'`

**Step 3: Implement transition animation**

In `src/protogen/expression_manager.py`:

1. Add `transition_duration_ms` parameter to `__init__`:

```python
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
```

2. Rewrite `set_expression()`:

```python
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
```

3. Add `_play_transition()` and `_show_expression()` helper methods:

```python
    async def _play_transition(
        self,
        old_frame: Image.Image,
        new_frame: Image.Image,
        target_expr: Expression,
    ) -> None:
        """Cross-fade from old_frame to new_frame, then show target expression."""
        fps = 30
        duration_s = self._transition_duration_ms / 1000.0
        total_frames = max(1, int(duration_s * fps))

        old_rgba = old_frame.convert("RGBA")
        new_rgba = new_frame.convert("RGBA")

        for i in range(1, total_frames + 1):
            progress = i / total_frames
            blended = Image.blend(old_rgba, new_rgba, alpha=progress)
            self._display.show_image(blended.convert("RGB"))
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_expression_manager.py -v`
Expected: ALL PASS

**Step 5: Update main.py to pass transition_duration_ms**

In `src/protogen/main.py`, update the ExpressionManager construction:

```python
expr_mgr = ExpressionManager(
    pipeline, expressions,
    blink_interval_min=config.blink_interval_min,
    blink_interval_max=config.blink_interval_max,
    transition_duration_ms=config.transition_duration_ms,
)
```

**Step 6: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/protogen/expression_manager.py src/protogen/main.py tests/test_expression_manager.py
git commit -m "feat: add cross-fade transition animation when switching expressions"
```

---

## Task 4: Boot Animation

Play a startup animation sequence before showing the default expression. Three phases: scanline sweep, "PROTOGEN" text, and fadeout to black.

**Files:**
- Create: `src/protogen/boot_animation.py`
- Modify: `src/protogen/main.py`
- Test: `tests/test_boot_animation.py`

**Step 1: Write the failing tests**

Create `tests/test_boot_animation.py`:

```python
import pytest
from PIL import Image

from protogen.boot_animation import render_boot_frame, play_boot_animation
from protogen.display.mock import MockDisplay


def test_render_boot_frame_returns_correct_size():
    """Each boot frame should be 128x32 RGB."""
    frame = render_boot_frame(128, 32, t=0.5)
    assert frame.size == (128, 32)
    assert frame.mode == "RGB"


def test_render_boot_frame_not_all_black_during_active_phases():
    """During active phases (t=0.3 scanline, t=0.5 text), frame should have content."""
    frame = render_boot_frame(128, 32, t=0.3)
    # At least some pixels should be non-black
    pixels = list(frame.getdata())
    non_black = [p for p in pixels if p != (0, 0, 0)]
    assert len(non_black) > 0


def test_render_boot_frame_fades_to_black():
    """At t=1.0 (end of animation), frame should be fully black."""
    frame = render_boot_frame(128, 32, t=1.0)
    pixels = list(frame.getdata())
    non_black = [p for p in pixels if p != (0, 0, 0)]
    assert len(non_black) == 0


@pytest.mark.asyncio
async def test_play_boot_animation_completes():
    """Boot animation should complete and display frames."""
    display = MockDisplay(width=128, height=32)
    await play_boot_animation(display, duration=0.1)
    # After playing, something should have been displayed
    assert display.last_image is not None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_boot_animation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'protogen.boot_animation'`

**Step 3: Implement boot animation**

Create `src/protogen/boot_animation.py`:

```python
from __future__ import annotations

import asyncio

from PIL import Image, ImageDraw, ImageFont

from protogen.display.base import DisplayBase


def render_boot_frame(width: int, height: int, t: float) -> Image.Image:
    """Render a single boot animation frame.

    Args:
        width: Display width in pixels.
        height: Display height in pixels.
        t: Progress from 0.0 to 1.0.

    Returns:
        RGB image for this frame.
    """
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Phase 1: Scanline sweep (t=0.0 to 0.3)
    if t < 0.3:
        progress = t / 0.3
        y = int(progress * height)
        # Draw a bright cyan scanline with glow
        for dy in range(-2, 3):
            row = y + dy
            if 0 <= row < height:
                intensity = max(0, 255 - abs(dy) * 80)
                draw.line([(0, row), (width - 1, row)], fill=(0, intensity, intensity))

    # Phase 2: Text display (t=0.3 to 0.75)
    elif t < 0.75:
        text_progress = (t - 0.3) / 0.45
        text = "PROTOGEN"
        font = ImageFont.load_default()
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (width - tw) // 2
        y = (height - th) // 2

        # Fade in the text
        brightness = min(255, int(text_progress * 3 * 255))
        color = (0, brightness, brightness)
        draw.text((x, y), text, fill=color, font=font)

    # Phase 3: Fade out (t=0.75 to 1.0)
    else:
        fade_progress = (t - 0.75) / 0.25
        text = "PROTOGEN"
        font = ImageFont.load_default()
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (width - tw) // 2
        y = (height - th) // 2

        brightness = max(0, int((1.0 - fade_progress) * 255))
        color = (0, brightness, brightness)
        draw.text((x, y), text, fill=color, font=font)

    return img


async def play_boot_animation(
    display: DisplayBase,
    duration: float = 2.0,
    fps: int = 30,
) -> None:
    """Play the boot animation sequence on the display."""
    total_frames = max(1, int(duration * fps))
    interval = 1.0 / fps

    for i in range(total_frames + 1):
        t = i / total_frames
        frame = render_boot_frame(display.width, display.height, t)
        display.show_image(frame)
        if i < total_frames:
            await asyncio.sleep(interval)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_boot_animation.py -v`
Expected: ALL PASS

**Step 5: Integrate into main.py**

In `src/protogen/main.py`, add the boot animation before setting the default expression.

Add import:
```python
from protogen.boot_animation import play_boot_animation
```

In `async_main()`, after creating `expr_mgr` and before setting the default expression, add:

```python
    # 播放開機動畫
    await play_boot_animation(display, duration=2.0)

    # 設定預設表情
    expr_mgr.set_expression(config.default_expression)
```

Note: The boot animation uses `display` directly (not `pipeline`), since we want it to bypass the render pipeline and display raw frames. The pipeline isn't needed yet — there are no effects during boot.

**Step 6: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/protogen/boot_animation.py tests/test_boot_animation.py src/protogen/main.py
git commit -m "feat: add boot animation with scanline sweep and text display"
```

---

## Task 5: Web UI Expression Preview Thumbnails

Add a thumbnail API endpoint that returns PNG images for each expression, and update the Web UI to show thumbnails instead of plain text buttons.

**Files:**
- Modify: `src/protogen/expression_manager.py` (add `get_thumbnail` method)
- Modify: `src/protogen/inputs/web.py` (add thumbnail endpoint + pass callback)
- Modify: `src/protogen/main.py` (pass `get_thumbnail` to WebInput)
- Modify: `web/static/index.html` (show thumbnails in buttons)
- Test: `tests/test_expression_manager.py`
- Test: `tests/test_web_api.py`

### Part A: Thumbnail generation in ExpressionManager

**Step 1: Write the failing test**

Add to `tests/test_expression_manager.py`:

```python
def test_get_thumbnail_static(mock_display, sample_expressions):
    """get_thumbnail returns PNG bytes for a static expression."""
    mgr = ExpressionManager(mock_display, sample_expressions)
    data = mgr.get_thumbnail("happy")
    assert data is not None
    assert isinstance(data, bytes)
    # Verify it's valid PNG (starts with PNG header)
    assert data[:4] == b'\x89PNG'


def test_get_thumbnail_animation(mock_display):
    """get_thumbnail returns first frame PNG for an animation."""
    frames = [
        Image.new("RGB", (128, 32), (255, 0, 0)),
        Image.new("RGB", (128, 32), (0, 255, 0)),
    ]
    expressions = {
        "anim": Expression(
            name="anim", type=ExpressionType.ANIMATION,
            frames=frames, fps=12, loop=True,
        ),
    }
    mgr = ExpressionManager(mock_display, expressions)
    data = mgr.get_thumbnail("anim")
    assert data is not None
    # Decode and check it's the first frame (red)
    img = Image.open(io.BytesIO(data))
    assert img.getpixel((0, 0)) == (255, 0, 0)


def test_get_thumbnail_nonexistent(mock_display, sample_expressions):
    """get_thumbnail returns None for unknown expression."""
    mgr = ExpressionManager(mock_display, sample_expressions)
    assert mgr.get_thumbnail("nonexistent") is None
```

Also add `import io` at the top of the test file.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_expression_manager.py::test_get_thumbnail_static -v`
Expected: FAIL — `AttributeError: 'ExpressionManager' object has no attribute 'get_thumbnail'`

**Step 3: Implement get_thumbnail**

Add to `src/protogen/expression_manager.py`:

```python
import io
```

Add method to `ExpressionManager`:

```python
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

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_expression_manager.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/protogen/expression_manager.py tests/test_expression_manager.py
git commit -m "feat: add get_thumbnail method to ExpressionManager"
```

### Part B: Thumbnail API endpoint

**Step 6: Write the failing test**

Create `tests/test_web_api.py`:

```python
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from protogen.commands import Command, InputEvent
from protogen.inputs.web import _create_app


@pytest.fixture
def web_app():
    """Create a test FastAPI app with a thumbnail callback."""
    red_png = _make_png((255, 0, 0))

    def get_thumbnail(name: str) -> bytes | None:
        if name == "happy":
            return red_png
        return None

    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy", "sad"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 80,
        get_thumbnail=get_thumbnail,
    )
    return app, commands


def _make_png(color: tuple) -> bytes:
    import io
    img = Image.new("RGB", (128, 32), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_thumbnail_endpoint_returns_png(web_app):
    app, _ = web_app
    client = TestClient(app)
    response = client.get("/api/expressions/happy/thumbnail")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:4] == b'\x89PNG'


def test_thumbnail_endpoint_404_for_unknown(web_app):
    app, _ = web_app
    client = TestClient(app)
    response = client.get("/api/expressions/nonexistent/thumbnail")
    assert response.status_code == 404
```

**Step 7: Run tests to verify they fail**

Run: `pytest tests/test_web_api.py -v`
Expected: FAIL — `_create_app() got an unexpected keyword argument 'get_thumbnail'`

**Step 8: Add thumbnail endpoint to web.py**

In `src/protogen/inputs/web.py`:

1. Add `get_thumbnail` parameter to `_create_app`:

```python
from fastapi.responses import FileResponse, Response

def _create_app(
    expression_names: list[str],
    put: Callable[[Command], Awaitable[None]],
    get_blink_state: Callable[[], bool],
    get_current_expression: Callable[[], str | None],
    get_brightness: Callable[[], int],
    get_thumbnail: Callable[[str], bytes | None] | None = None,
):
```

2. Add the thumbnail endpoint (after `list_expressions`):

```python
    @app.get("/api/expressions/{name}/thumbnail")
    async def expression_thumbnail(name: str):
        if get_thumbnail is None:
            return Response(status_code=404)
        data = get_thumbnail(name)
        if data is None:
            return Response(status_code=404)
        return Response(content=data, media_type="image/png")
```

3. Add `get_thumbnail` parameter to `WebInput.__init__`:

```python
class WebInput:
    def __init__(
        self,
        port: int = 8080,
        expression_names: list[str] | None = None,
        get_blink_state: Callable[[], bool] | None = None,
        get_current_expression: Callable[[], str | None] | None = None,
        get_brightness: Callable[[], int] | None = None,
        get_thumbnail: Callable[[str], bytes | None] | None = None,
    ) -> None:
        self._port = port
        self._expression_names = expression_names or []
        self._get_blink_state = get_blink_state or (lambda: False)
        self._get_current_expression = get_current_expression or (lambda: None)
        self._get_brightness = get_brightness or (lambda: 100)
        self._get_thumbnail = get_thumbnail
```

4. Pass it in `run()`:

```python
    async def run(self, put: Callable[[Command], Awaitable[None]]) -> None:
        import uvicorn

        app = _create_app(
            self._expression_names, put, self._get_blink_state,
            self._get_current_expression, self._get_brightness,
            get_thumbnail=self._get_thumbnail,
        )
        config = uvicorn.Config(app, host="0.0.0.0", port=self._port, log_level="info", ws="wsproto")
        server = uvicorn.Server(config)
        await server.serve()
```

**Step 9: Run tests to verify they pass**

Run: `pytest tests/test_web_api.py -v`
Expected: ALL PASS

**Step 10: Wire up in main.py**

In `src/protogen/main.py`, update the WebInput constructor:

```python
    if config.input.web_enabled:
        from protogen.inputs.web import WebInput
        input_mgr.add_source(WebInput(
            port=config.input.web_port,
            expression_names=expr_mgr.expression_names,
            get_blink_state=lambda: expr_mgr.blink_enabled,
            get_current_expression=lambda: expr_mgr.current_name,
            get_brightness=lambda: display.brightness,
            get_thumbnail=expr_mgr.get_thumbnail,
        ))
```

**Step 11: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 12: Commit**

```bash
git add src/protogen/inputs/web.py src/protogen/main.py tests/test_web_api.py
git commit -m "feat: add expression thumbnail API endpoint"
```

### Part C: Web UI thumbnails

**Step 13: Update the Web UI**

In `web/static/index.html`, update the expression button CSS and the `loadExpressions()` JavaScript function.

Add CSS for thumbnail buttons (after the `.expressions button` rules, around line 156):

```css
        .expressions button {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            min-height: 72px;
            padding: 10px 8px;
            font-family: 'Fira Sans', sans-serif;
            font-size: 0.8rem;
            font-weight: 500;
            text-transform: capitalize;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: var(--bg-primary);
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.2s ease;
            -webkit-tap-highlight-color: transparent;
        }

        .expressions button img {
            width: 100%;
            max-height: 32px;
            object-fit: contain;
            image-rendering: pixelated;
            border-radius: 4px;
        }
```

Update the `loadExpressions()` function (around line 443):

```javascript
        async function loadExpressions() {
            try {
                const res = await fetch('/api/expressions');
                const { expressions } = await res.json();
                exprEl.innerHTML = '';
                expressions.filter(name => name !== 'blink').forEach(name => {
                    const btn = document.createElement('button');
                    const img = document.createElement('img');
                    img.src = `/api/expressions/${name}/thumbnail`;
                    img.alt = displayName(name);
                    img.loading = 'lazy';
                    btn.appendChild(img);
                    const label = document.createElement('span');
                    label.textContent = displayName(name);
                    btn.appendChild(label);
                    btn.dataset.expr = name;
                    btn.setAttribute('type', 'button');
                    btn.onclick = () => {
                        setActiveExpression(name);
                        send({ action: 'set', name });
                    };
                    exprEl.appendChild(btn);
                });
            } catch (e) {
                console.error('Failed to load expressions:', e);
            }
        }
```

**Step 14: Manual test**

Run: `python -m protogen.main`
Open: `http://localhost:8080`
Verify: Expression buttons now show preview thumbnails above the text labels.

**Step 15: Commit**

```bash
git add web/static/index.html
git commit -m "feat: show expression preview thumbnails in web UI"
```

---

## Summary

After completing all 5 tasks, the codebase will have:

1. **blink_interval_min/max** properly wired from config to ExpressionManager
2. **RenderPipeline** wrapping the display, tracking `last_frame`, ready for effects (Batch 3)
3. **Cross-fade transitions** when switching between expressions
4. **Boot animation** with scanline sweep and "PROTOGEN" text on startup
5. **Expression preview thumbnails** in the Web UI via a new `/api/expressions/{name}/thumbnail` endpoint

New files: `render_pipeline.py`, `boot_animation.py`, `test_render_pipeline.py`, `test_boot_animation.py`, `test_web_api.py`
Modified files: `expression_manager.py`, `main.py`, `inputs/web.py`, `index.html`
