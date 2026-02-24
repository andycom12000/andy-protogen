# Phase 1: Quick Fixes + Blink Expansion — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix code quality issues (Pillow deprecation, type errors, encapsulation violations), add parameter validation, improve logging, and generate per-expression blink animations for angry/crying/shocked/very_angry.

**Architecture:** Incremental fixes to existing modules — no new modules introduced. Each task is independent except Task 7-8 (blink generation depends on script changes before manifest updates).

**Tech Stack:** Python 3.14, Pillow, pytest, pytest-asyncio, NumPy

---

### Task 1: Fix Pillow `getdata()` deprecation warnings in tests

**Files:**
- Modify: `tests/test_procedural.py:51,73,94,115`
- Modify: `tests/test_boot_animation.py:19,27`

**Step 1: Write verification test to confirm deprecation warning exists**

Run: `pytest tests/test_procedural.py tests/test_boot_animation.py -W error::DeprecationWarning -v 2>&1 | head -30`
Expected: Tests FAIL with `DeprecationWarning` about `getdata()`

**Step 2: Replace `getdata()` with `getpixel()`-based or `np.asarray()` checks**

In `tests/test_procedural.py`, replace all 4 occurrences of the pattern:
```python
    pixels = list(frame.getdata())
    non_black = [p for p in pixels if p != (0, 0, 0)]
    assert len(non_black) > 0
```
with:
```python
    arr = np.asarray(frame)
    assert arr.any()  # at least one non-zero pixel
```

Add `import numpy as np` at the top of the file (after existing imports).

In `tests/test_boot_animation.py`, replace both occurrences:

Line 19 pattern:
```python
    pixels = list(frame.getdata())
    non_black = [p for p in pixels if p != (0, 0, 0)]
    assert len(non_black) > 0
```
with:
```python
    arr = np.asarray(frame)
    assert arr.any()
```

Line 27 pattern:
```python
    pixels = list(frame.getdata())
    non_black = [p for p in pixels if p != (0, 0, 0)]
    assert len(non_black) == 0
```
with:
```python
    arr = np.asarray(frame)
    assert not arr.any()
```

Add `import numpy as np` at the top of the file (after existing imports).

**Step 3: Run tests to verify no deprecation warnings**

Run: `pytest tests/test_procedural.py tests/test_boot_animation.py -W error::DeprecationWarning -v`
Expected: All tests PASS, no deprecation warnings

**Step 4: Fix deprecated `Image.BILINEAR` in generate_placeholder_faces.py**

In `scripts/generate_placeholder_faces.py`, replace all occurrences of `Image.BILINEAR` with `Image.Resampling.BILINEAR` (lines 52 and 365).

**Step 5: Commit**

```bash
git add tests/test_procedural.py tests/test_boot_animation.py scripts/generate_placeholder_faces.py
git commit -m "fix: replace deprecated Pillow getdata() and Image.BILINEAR usage"
```

---

### Task 2: Fix `InputSource` Protocol type annotation

**Files:**
- Modify: `src/protogen/input_manager.py:10`
- Test: `tests/test_input_manager.py` (existing — verify no regression)

**Step 1: Write a type-checking smoke test**

No new test file needed — the fix is a type annotation correction. Verify existing tests pass.

Run: `pytest tests/ -v -k "input" 2>&1 | head -20`
Expected: See what input-related tests exist

**Step 2: Fix the type annotation**

In `src/protogen/input_manager.py`, change line 10 from:
```python
    async def run(self, put: asyncio.coroutines) -> None: ...
```
to:
```python
    async def run(self, put: Callable[[Command], Awaitable[None]]) -> None: ...
```

Also add the necessary imports. Change line 1-6 from:
```python
from __future__ import annotations

import asyncio
from typing import Protocol

from protogen.commands import Command
```
to:
```python
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Protocol

from protogen.commands import Command
```

**Step 3: Run all tests to verify no regression**

Run: `pytest tests/ -v`
Expected: All 85 tests PASS

**Step 4: Commit**

```bash
git add src/protogen/input_manager.py
git commit -m "fix: correct InputSource Protocol type annotation"
```

---

### Task 3: Fix RenderPipeline private attribute access

**Files:**
- Modify: `src/protogen/generators/__init__.py:32-52` (add `set_base_frame` to `FrameEffect`)
- Modify: `src/protogen/render_pipeline.py:91` (use public setter)

**Step 1: Write failing test for the public setter**

Add to `tests/test_procedural.py`:
```python
def test_frame_effect_set_base_frame():
    """FrameEffect exposes set_base_frame() public method."""
    from protogen.generators import FrameEffect

    class DummyEffect(FrameEffect):
        def apply(self, frame, t):
            return frame

    effect = DummyEffect(128, 32, {})
    new_frame = Image.new("RGB", (128, 32), (255, 0, 0))
    effect.set_base_frame(new_frame)
    rendered = effect.render(0.0)
    assert rendered.getpixel((0, 0)) == (255, 0, 0)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_procedural.py::test_frame_effect_set_base_frame -v`
Expected: FAIL with `AttributeError: 'DummyEffect' object has no attribute 'set_base_frame'`

**Step 3: Add `set_base_frame()` to FrameEffect**

In `src/protogen/generators/__init__.py`, add method to `FrameEffect` class after line 37:
```python
    def set_base_frame(self, frame: Image.Image) -> None:
        """Update the base frame used by this effect."""
        self._base_frame = frame
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_procedural.py::test_frame_effect_set_base_frame -v`
Expected: PASS

**Step 5: Update RenderPipeline to use public setter**

In `src/protogen/render_pipeline.py`, change line 91 from:
```python
                        self._effect._base_frame = self.last_frame
```
to:
```python
                        self._effect.set_base_frame(self.last_frame)
```

**Step 6: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add src/protogen/generators/__init__.py src/protogen/render_pipeline.py tests/test_procedural.py
git commit -m "refactor: add FrameEffect.set_base_frame() public method"
```

---

### Task 4: Add parameter validation

**Files:**
- Modify: `src/protogen/config.py` (brightness validation in `__post_init__`)
- Modify: `src/protogen/expression.py` (manifest structure validation)
- Test: `tests/test_config.py` (new file)
- Modify: `tests/test_expression.py` (add validation tests)

**Step 1: Write failing test for brightness validation**

Create `tests/test_config.py`:
```python
import pytest
from protogen.config import DisplayConfig


def test_brightness_clamped_to_valid_range():
    """Brightness is clamped to 0-100."""
    cfg = DisplayConfig(brightness=150)
    assert cfg.brightness == 100

    cfg2 = DisplayConfig(brightness=-10)
    assert cfg2.brightness == 0


def test_brightness_valid_values_unchanged():
    """Valid brightness values pass through unchanged."""
    cfg = DisplayConfig(brightness=50)
    assert cfg.brightness == 50
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — brightness 150 is stored as-is, not clamped

**Step 3: Add `__post_init__` to DisplayConfig**

In `src/protogen/config.py`, add after the `DisplayConfig` class fields (after line 14):
```python
    def __post_init__(self) -> None:
        self.brightness = max(0, min(100, self.brightness))
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Write failing test for manifest validation**

Add to `tests/test_expression.py`:
```python
def test_load_expressions_skips_invalid_entry(tmp_path):
    """Entries with missing required fields are skipped."""
    manifest = {
        "expressions": {
            "good": {"type": "static", "file": "base/good.png"},
            "bad_no_type": {"file": "base/bad.png"},
            "bad_no_file": {"type": "static"},
        },
        "effects": {},
        "default": "good",
    }
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    base = tmp_path / "base"
    base.mkdir()
    img = Image.new("RGB", (128, 32), (0, 0, 0))
    img.save(base / "good.png")

    result = load_expressions(tmp_path)
    assert "good" in result
    assert "bad_no_type" not in result
    assert "bad_no_file" not in result
```

Add `import json` to the imports if not already present.

**Step 6: Run test to verify it fails**

Run: `pytest tests/test_expression.py::test_load_expressions_skips_invalid_entry -v`
Expected: FAIL with `KeyError`

**Step 7: Add validation to load_expressions**

In `src/protogen/expression.py`, wrap the expression loading in `load_expressions()` with try/except. Change the loop body (lines 35-58) to:
```python
    for name, data in manifest.get("expressions", {}).items():
        try:
            expr_type = ExpressionType(data["type"])
        except (KeyError, ValueError):
            continue

        if expr_type == ExpressionType.STATIC:
            file_path = data.get("file")
            if file_path is None:
                continue
            img_path = expressions_dir / file_path
            if not img_path.exists():
                continue
            image = Image.open(img_path).convert("RGB")
            result[name] = Expression(
                name=name,
                type=expr_type,
                image=image,
                idle_animation=data.get("idle_animation"),
            )
        elif expr_type == ExpressionType.ANIMATION:
            frames_dir_name = data.get("frames_dir")
            if frames_dir_name is None:
                continue
            frames_dir = expressions_dir / frames_dir_name
            if not frames_dir.exists():
                continue
            frame_files = sorted(frames_dir.glob("frame_*.png"))
            frames = [Image.open(f).convert("RGB") for f in frame_files]
            result[name] = Expression(
                name=name,
                type=expr_type,
                frames=frames,
                fps=data.get("fps", 12),
                loop=data.get("loop", True),
                next_expression=data.get("next"),
            )
```

**Step 8: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 9: Commit**

```bash
git add src/protogen/config.py src/protogen/expression.py tests/test_config.py tests/test_expression.py
git commit -m "feat: add parameter validation for brightness and manifest entries"
```

---

### Task 5: Merge WebSocket dual-command patterns

**Files:**
- Modify: `src/protogen/inputs/web.py:142-154`
- Modify: `src/protogen/commands.py` (add `SET_EFFECT_WITH_PARAMS` event)
- Modify: `src/protogen/main.py:117-122` (handle new event)
- Modify: `tests/test_web_api.py` (update test expectations)

**Step 1: Write failing test for merged command**

Add to `tests/test_web_api.py`:
```python
def test_update_effect_params_sends_single_command(web_app):
    """update_effect_params via REST sends a single merged command."""
    client, commands = web_app
    client.post("/api/expression/happy")
    commands.clear()

    client.put("/api/effects/breathe/params", json={"period": 5.0})
    effect_cmds = [c for c in commands if c.event == InputEvent.SET_EFFECT_WITH_PARAMS]
    assert len(effect_cmds) == 1
    assert effect_cmds[0].value == {"name": "breathe", "params": {"period": 5.0}}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_api.py::test_update_effect_params_sends_single_command -v`
Expected: FAIL — `InputEvent` has no `SET_EFFECT_WITH_PARAMS`

**Step 3: Add new event to commands.py**

In `src/protogen/commands.py`, add after line 13:
```python
    SET_EFFECT_WITH_PARAMS = "set_effect_with_params"
```

**Step 4: Update web.py WebSocket handler**

In `src/protogen/inputs/web.py`, change lines 152-154 from:
```python
                elif action == "update_effect_params":
                    await put(Command(event=InputEvent.SET_EFFECT, value=data["name"]))
                    await put(Command(event=InputEvent.SET_EFFECT_PARAMS, value=data.get("params", {})))
```
to:
```python
                elif action == "update_effect_params":
                    await put(Command(
                        event=InputEvent.SET_EFFECT_WITH_PARAMS,
                        value={"name": data["name"], "params": data.get("params", {})},
                    ))
```

Also update the REST endpoint for effect params. Find the PUT handler for effect params and update it similarly to send a single merged command.

**Step 5: Handle new event in main.py**

In `src/protogen/main.py`, add after line 122 (`pipeline.update_effect_params(cmd.value)`):
```python
            elif cmd.event == InputEvent.SET_EFFECT_WITH_PARAMS:
                effect = effects.get(cmd.value["name"])
                if effect is not None:
                    pipeline.set_effect(effect.generator_name, effect.generator_params, effect.fps)
                    pipeline.update_effect_params(cmd.value.get("params", {}))
```

**Step 6: Update existing test expectations**

In `tests/test_web_api.py`, update `test_update_effect_params_endpoint` to expect the new merged command format.

**Step 7: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 8: Commit**

```bash
git add src/protogen/commands.py src/protogen/inputs/web.py src/protogen/main.py tests/test_web_api.py
git commit -m "refactor: merge SET_EFFECT + SET_EFFECT_PARAMS into single command"
```

---

### Task 6: Add logging to core components

**Files:**
- Modify: `src/protogen/display/base.py` (no logging needed — abstract)
- Modify: `src/protogen/display/mock.py` (add logger)
- Modify: `src/protogen/input_manager.py` (add logger)
- Modify: `src/protogen/animation.py` (add logger)
- Modify: `src/protogen/render_pipeline.py` (add logger)
- Modify: `src/protogen/expression.py` (add logger)
- Modify: `src/protogen/config.py` (add logger)

**Step 1: Add logging to display/mock.py**

Add at top of file:
```python
import logging

logger = logging.getLogger(__name__)
```

Add log calls:
- In `__init__`: `logger.info("MockDisplay initialised (%dx%d, scale=%d)", width, height, scale)`
- In `set_brightness`: `logger.debug("brightness set to %d", value)`

**Step 2: Add logging to input_manager.py**

Add at top:
```python
import logging

logger = logging.getLogger(__name__)
```

Add log calls:
- In `add_source`: `logger.info("registered input source: %s", type(source).__name__)`
- In `run_all`: `logger.info("starting %d input sources", len(self._sources))`

**Step 3: Add logging to animation.py**

Add at top:
```python
import logging

logger = logging.getLogger(__name__)
```

Add log calls:
- In `play`: `logger.debug("playing animation: %d frames, fps=%d, loop=%s", len(frames), fps, loop)`

**Step 4: Add logging to render_pipeline.py**

Add at top:
```python
import logging

logger = logging.getLogger(__name__)
```

Add log calls:
- In `set_effect`: `logger.info("effect set: %s (fps=%d)", name, fps)`
- In `clear_effect`: `logger.info("effect cleared")`

**Step 5: Add logging to expression.py**

Add at top:
```python
import logging

logger = logging.getLogger(__name__)
```

Add log calls:
- In `load_expressions`: `logger.info("loaded %d expressions from %s", len(result), expressions_dir)`
- On skip: `logger.warning("skipping invalid expression: %s", name)`

**Step 6: Add logging to config.py**

Add at top:
```python
import logging

logger = logging.getLogger(__name__)
```

Add in `Config.load()`:
- `logger.info("loaded config from %s", path)`

**Step 7: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS (logging doesn't change behavior)

**Step 8: Commit**

```bash
git add src/protogen/display/mock.py src/protogen/input_manager.py src/protogen/animation.py src/protogen/render_pipeline.py src/protogen/expression.py src/protogen/config.py
git commit -m "feat: add structured logging to core components"
```

---

### Task 7: Generate per-expression blink animations

**Files:**
- Modify: `scripts/generate_placeholder_faces.py`

This task adds 4 new blink frame generators: `generate_angry_blink_frames`, `generate_crying_blink_frames`, `generate_shocked_blink_frames`, `generate_very_angry_blink_frames`.

**Step 1: Add `generate_angry_blink_frames()`**

Add after `generate_blink_frames()` (after line 372):

```python
def generate_angry_blink_frames(base_img: Image.Image, n_frames: int = 7):
    """Generate blink animation for angry expression.

    Uses flatter red oval eyes that squish vertically to close.
    """
    frames = []
    close_amounts = [0.0, 0.33, 0.66, 1.0, 0.66, 0.33, 0.0]

    for close in close_amounts:
        if close <= 0.0:
            frames.append(base_img.copy())
            continue

        frame = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(frame)

        if close >= 1.0:
            _draw_closed_eye(draw, *LEFT_EYE, color=RED)
            _draw_closed_eye(draw, *RIGHT_EYE, color=RED)
        else:
            squished_ry = max(1, int(5 * (1 - close)))
            if squished_ry < 2:
                _draw_closed_eye(draw, *LEFT_EYE, color=RED)
                _draw_closed_eye(draw, *RIGHT_EYE, color=RED)
            else:
                _draw_default_eye(draw, *LEFT_EYE, color=RED, is_left=True, rx=12, ry=squished_ry)
                _draw_default_eye(draw, *RIGHT_EYE, color=RED, is_left=False, rx=12, ry=squished_ry)
            # Angry brow lines (same as angry expression)
            lx, ly = LEFT_EYE
            rcx, rcy = RIGHT_EYE
            draw.line([(lx - 12, ly - 9), (lx + 12, ly - 5)], fill=RED, width=2)
            draw.line([(rcx - 12, rcy - 5), (rcx + 12, rcy - 9)], fill=RED, width=2)

        _draw_nose_dots(draw, color=RED)
        _draw_mouth_zigzag_angry(draw, color=RED)
        frames.append(frame)
    return frames
```

**Step 2: Add `generate_very_angry_blink_frames()`**

```python
def generate_very_angry_blink_frames(base_img: Image.Image, n_frames: int = 7):
    """Generate blink animation for very_angry expression.

    Uses egg-shaped red eyes cut by heavy brows, squishing to close.
    Mirrors left half to right for perfect symmetry.
    """
    frames = []
    close_amounts = [0.0, 0.33, 0.66, 1.0, 0.66, 0.33, 0.0]

    for close in close_amounts:
        if close <= 0.0:
            frames.append(base_img.copy())
            continue

        frame = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(frame)

        if close >= 1.0:
            _draw_closed_eye(draw, *LEFT_EYE, color=RED)
            _draw_closed_eye(draw, *RIGHT_EYE, color=RED)
        else:
            squished_ry = max(1, int(8 * (1 - close)))
            for (cx, cy), is_left in [(LEFT_EYE, True), (RIGHT_EYE, False)]:
                if squished_ry < 2:
                    _draw_closed_eye(draw, cx, cy, color=RED)
                else:
                    _draw_default_eye(draw, cx, cy, color=RED, is_left=is_left,
                                      rx=10, ry=squished_ry,
                                      angle=-12 if is_left else 12)
                # Heavy brow mask + line (same as very_angry)
                brow_y_outer = cy - 6
                brow_y_inner = cy - 1
                if is_left:
                    pts_mask = [(cx - 15, cy - 14), (cx + 15, cy - 14),
                                (cx + 15, brow_y_inner), (cx - 15, brow_y_outer)]
                    draw.polygon(pts_mask, fill=BG)
                    draw.line([(cx - 13, brow_y_outer), (cx + 13, brow_y_inner)],
                              fill=RED, width=3)
                else:
                    pts_mask = [(cx - 15, cy - 14), (cx + 15, cy - 14),
                                (cx - 15, brow_y_inner + 2), (cx + 15, brow_y_outer + 2)]
                    draw.polygon(pts_mask, fill=BG)
                    draw.line([(cx - 13, brow_y_inner), (cx + 13, brow_y_outer)],
                              fill=RED, width=3)

        _draw_nose_dots(draw, color=RED)
        # Wider zigzag mouth (same as very_angry)
        pts = [
            (50, 29), (53, 27), (56, 29), (59, 26), (62, 28),
            (64, 22), (66, 28), (69, 26), (72, 29), (75, 27), (78, 29),
        ]
        draw.line(pts, fill=RED, width=1)
        # Mirror for symmetry
        left_half = frame.crop((0, 0, 64, 32))
        right_half = left_half.transpose(Image.FLIP_LEFT_RIGHT)
        frame.paste(right_half, (64, 0))
        frames.append(frame)
    return frames
```

**Step 3: Add `generate_crying_blink_frames()`**

```python
def generate_crying_blink_frames(base_img: Image.Image, n_frames: int = 7):
    """Generate blink animation for crying expression.

    Uses teardrop outline eyes that squish vertically to close.
    Teardrops persist through all frames.
    """
    frames = []
    close_amounts = [0.0, 0.33, 0.66, 1.0, 0.66, 0.33, 0.0]

    for close in close_amounts:
        if close <= 0.0:
            frames.append(base_img.copy())
            continue

        frame = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(frame)

        if close >= 1.0:
            _draw_closed_eye(draw, *LEFT_EYE)
            _draw_closed_eye(draw, *RIGHT_EYE)
        else:
            squished_ry = max(1, int(6 * (1 - close)))
            for ecx, ecy in [LEFT_EYE, RIGHT_EYE]:
                if squished_ry < 2:
                    _draw_closed_eye(draw, ecx, ecy)
                else:
                    rx = 8
                    draw.ellipse([ecx - rx, ecy - squished_ry, ecx + rx, ecy + squished_ry],
                                 outline=CYAN, width=2)

        # Teardrops always visible (even when eyes closed)
        bright = (100, 255, 240)
        for ecx, ecy in [LEFT_EYE, RIGHT_EYE]:
            draw.line([(ecx - 3, ecy + 7), (ecx - 3, ecy + 13)], fill=bright, width=2)
            draw.line([(ecx + 3, ecy + 7), (ecx + 3, ecy + 11)], fill=bright, width=2)

        _draw_nose_dots(draw)
        _draw_mouth_zigzag_frown(draw)
        frames.append(frame)
    return frames
```

**Step 4: Add `generate_shocked_blink_frames()`**

```python
def generate_shocked_blink_frames(base_img: Image.Image, n_frames: int = 7):
    """Generate blink animation for shocked expression.

    Uses large round eyes that shrink to close.
    """
    frames = []
    close_amounts = [0.0, 0.33, 0.66, 1.0, 0.66, 0.33, 0.0]

    for close in close_amounts:
        if close <= 0.0:
            frames.append(base_img.copy())
            continue

        frame = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(frame)

        if close >= 1.0:
            _draw_closed_eye(draw, *LEFT_EYE)
            _draw_closed_eye(draw, *RIGHT_EYE)
        else:
            squished_r = max(1, int(10 * (1 - close)))
            for ecx, ecy in [LEFT_EYE, RIGHT_EYE]:
                if squished_r < 2:
                    _draw_closed_eye(draw, ecx, ecy)
                else:
                    draw.ellipse([ecx - 10, ecy - squished_r, ecx + 10, ecy + squished_r],
                                 fill=CYAN)

        _draw_nose_dots(draw)
        # Upper half egg mouth (same as shocked)
        draw.chord([48, 22, 80, 38], 180, 360, fill=CYAN)
        draw.ellipse([55, 19, 63, 29], fill=BG)
        draw.ellipse([57, 19, 65, 29], fill=CYAN)
        draw.ellipse([65, 19, 73, 29], fill=BG)
        draw.ellipse([63, 19, 71, 29], fill=CYAN)
        frames.append(frame)
    return frames
```

**Step 5: Update `main()` to generate new blink frames**

In `scripts/generate_placeholder_faces.py`, add after the existing blink frame generation (after line 512):

```python
    # Generate per-expression blink animations
    blink_generators = {
        "angry_blink": (generate_angry_blink_frames, "angry"),
        "very_angry_blink": (generate_very_angry_blink_frames, "very_angry"),
        "crying_blink": (generate_crying_blink_frames, "crying"),
        "shocked_blink": (generate_shocked_blink_frames, "shocked"),
    }
    for blink_name, (gen_func, base_expr) in blink_generators.items():
        anim_dir = OUT_DIR / "animations" / blink_name
        anim_dir.mkdir(parents=True, exist_ok=True)
        blink_frames = gen_func(generated_images[base_expr])
        for i, frame in enumerate(blink_frames):
            frame.save(anim_dir / f"frame_{i:02d}.png")
        print(f"Generated: {len(blink_frames)} {blink_name} frames")
```

**Step 6: Run the script to generate frames**

Run: `python scripts/generate_placeholder_faces.py`
Expected: Output shows generation of 7 frames each for angry_blink, very_angry_blink, crying_blink, shocked_blink

**Step 7: Verify generated frames exist**

Run: `ls expressions/animations/angry_blink/ expressions/animations/very_angry_blink/ expressions/animations/crying_blink/ expressions/animations/shocked_blink/`
Expected: Each directory contains `frame_00.png` through `frame_06.png`

**Step 8: Commit**

```bash
git add scripts/generate_placeholder_faces.py expressions/animations/
git commit -m "art: generate per-expression blink animations for angry/crying/shocked/very_angry"
```

---

### Task 8: Update manifest.json with new blink definitions

**Files:**
- Modify: `expressions/manifest.json`

**Step 1: Add 4 new blink animation entries to manifest**

In `expressions/manifest.json`, add these entries inside the `"expressions"` object (after the existing `"blink"` entry at line 42):

```json
    "angry_blink": {
      "type": "animation",
      "frames_dir": "animations/angry_blink",
      "fps": 15,
      "loop": false
    },
    "very_angry_blink": {
      "type": "animation",
      "frames_dir": "animations/very_angry_blink",
      "fps": 15,
      "loop": false
    },
    "crying_blink": {
      "type": "animation",
      "frames_dir": "animations/crying_blink",
      "fps": 15,
      "loop": false
    },
    "shocked_blink": {
      "type": "animation",
      "frames_dir": "animations/shocked_blink",
      "fps": 15,
      "loop": false
    },
```

**Step 2: Add `idle_animation` to the 4 static expressions**

Change `angry` entry from:
```json
    "angry": {
      "type": "static",
      "file": "base/angry.png"
    },
```
to:
```json
    "angry": {
      "type": "static",
      "file": "base/angry.png",
      "idle_animation": "angry_blink"
    },
```

Change `crying` entry from:
```json
    "crying": {
      "type": "static",
      "file": "base/crying.png"
    },
```
to:
```json
    "crying": {
      "type": "static",
      "file": "base/crying.png",
      "idle_animation": "crying_blink"
    },
```

Change `shocked` entry from:
```json
    "shocked": {
      "type": "static",
      "file": "base/shocked.png"
    },
```
to:
```json
    "shocked": {
      "type": "static",
      "file": "base/shocked.png",
      "idle_animation": "shocked_blink"
    },
```

Change `very_angry` entry from:
```json
    "very_angry": {
      "type": "static",
      "file": "base/very_angry.png"
    },
```
to:
```json
    "very_angry": {
      "type": "static",
      "file": "base/very_angry.png",
      "idle_animation": "very_angry_blink"
    },
```

**Step 3: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add expressions/manifest.json
git commit -m "feat: add per-expression blink animations for angry/crying/shocked/very_angry"
```

---

### Final Verification

**Run full test suite with deprecation warnings as errors:**

```bash
pytest tests/ -W error::DeprecationWarning -v
```

Expected: All tests PASS, no warnings.
