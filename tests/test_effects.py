import asyncio

import numpy as np
import pytest
from PIL import Image

from protogen.render_pipeline import RenderPipeline
from protogen.generators import (
    ProceduralGenerator, FrameEffect, GENERATORS, register_generators,
)


class DummyEffect(ProceduralGenerator):
    def render(self, t: float) -> Image.Image:
        return Image.new("RGB", (self.width, self.height), (0, 50, 0))


class DummyFrameEffect(FrameEffect):
    """Halves pixel values — simple testable transform."""
    def apply(self, frame: Image.Image, t: float) -> Image.Image:
        arr = np.array(frame, dtype=np.float32)
        arr *= 0.5
        return Image.fromarray(arr.astype(np.uint8), "RGB")


@pytest.fixture(autouse=True)
def setup_generators():
    register_generators()
    GENERATORS["__test_effect__"] = DummyEffect
    GENERATORS["__test_frame_effect__"] = DummyFrameEffect
    yield
    GENERATORS.pop("__test_effect__", None)
    GENERATORS.pop("__test_frame_effect__", None)


# --- Existing overlay pipeline tests ---

def test_pipeline_set_effect(mock_display):
    pipeline = RenderPipeline(mock_display)
    pipeline.set_effect("__test_effect__", {})
    assert pipeline.active_effect_name == "__test_effect__"


def test_pipeline_clear_effect(mock_display):
    pipeline = RenderPipeline(mock_display)
    pipeline.set_effect("__test_effect__", {})
    pipeline.clear_effect()
    assert pipeline.active_effect_name is None


@pytest.mark.asyncio
async def test_pipeline_composites_effect_with_expression(mock_display):
    pipeline = RenderPipeline(mock_display)
    pipeline.set_effect("__test_effect__", {})
    task = asyncio.create_task(pipeline.run_effect_loop())
    red_frame = Image.new("RGB", (128, 32), (100, 0, 0))
    pipeline.show_image(red_frame)
    await asyncio.sleep(0.15)
    assert mock_display.last_image is not None
    pixel = mock_display.last_image.getpixel((0, 0))
    assert pixel == (100, 50, 0)  # lighter of (100,0,0) and (0,50,0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def test_pipeline_no_effect_passes_through(mock_display):
    pipeline = RenderPipeline(mock_display)
    frame = Image.new("RGB", (128, 32), (255, 0, 0))
    pipeline.show_image(frame)
    assert mock_display.last_image.getpixel((0, 0)) == (255, 0, 0)


# --- FrameEffect pipeline integration ---

@pytest.mark.asyncio
async def test_frame_effect_transforms_directly(mock_display):
    """FrameEffect should transform the base frame, not use lighter compositing."""
    pipeline = RenderPipeline(mock_display)
    cyan_frame = Image.new("RGB", (128, 32), (0, 200, 100))
    pipeline.show_image(cyan_frame)
    pipeline.set_effect("__test_frame_effect__", {})
    task = asyncio.create_task(pipeline.run_effect_loop())
    await asyncio.sleep(0.15)
    assert mock_display.last_image is not None
    pixel = mock_display.last_image.getpixel((0, 0))
    # DummyFrameEffect halves: (0, 200, 100) -> (0, 100, 50)
    assert pixel == (0, 100, 50)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def test_frame_effect_render_delegates_to_apply():
    """render() should call apply() with the stored _base_frame."""
    effect = DummyFrameEffect(128, 32, {})
    base = Image.new("RGB", (128, 32), (100, 100, 100))
    effect._base_frame = base
    result = effect.render(0.0)
    pixel = result.getpixel((0, 0))
    assert pixel == (50, 50, 50)


# --- BreatheEffect ---

def test_breathe_at_peak():
    from protogen.generators.breathe import BreatheEffect
    effect = BreatheEffect(128, 32, {"period": 4.0, "amplitude": 0.5})
    frame = Image.new("RGB", (128, 32), (200, 200, 200))
    # At t = period/4, sin(2*pi*t/period) = sin(pi/2) = 1.0 → factor = 1.0
    result = effect.apply(frame, 1.0)
    pixel = result.getpixel((0, 0))
    assert pixel == (200, 200, 200)


def test_breathe_at_trough():
    from protogen.generators.breathe import BreatheEffect
    effect = BreatheEffect(128, 32, {"period": 4.0, "amplitude": 0.5})
    frame = Image.new("RGB", (128, 32), (200, 200, 200))
    # At t = 3*period/4, sin(2*pi*t/period) = sin(3*pi/2) = -1.0 → factor = 0.5
    result = effect.apply(frame, 3.0)
    pixel = result.getpixel((0, 0))
    assert pixel == (100, 100, 100)


def test_breathe_preserves_black():
    from protogen.generators.breathe import BreatheEffect
    effect = BreatheEffect(128, 32, {})
    frame = Image.new("RGB", (128, 32), (0, 0, 0))
    result = effect.apply(frame, 1.5)
    pixel = result.getpixel((0, 0))
    assert pixel == (0, 0, 0)


# --- ColorShiftEffect ---

def test_color_shift_changes_hue():
    from protogen.generators.color_shift import ColorShiftEffect
    effect = ColorShiftEffect(128, 32, {"speed": 1.0})
    frame = Image.new("RGB", (128, 32), (255, 0, 0))  # pure red
    result = effect.apply(frame, 0.0)
    # At t=0, offset should be 0 → color unchanged
    pixel = result.getpixel((0, 0))
    assert pixel[0] > 200  # still mostly red


def test_color_shift_preserves_black():
    from protogen.generators.color_shift import ColorShiftEffect
    effect = ColorShiftEffect(128, 32, {"speed": 1.0})
    # Image with black and non-black pixels
    frame = Image.new("RGB", (128, 32), (0, 0, 0))
    result = effect.apply(frame, 1.0)
    pixel = result.getpixel((0, 0))
    assert pixel == (0, 0, 0)


def test_color_shift_shifts_over_time():
    from protogen.generators.color_shift import ColorShiftEffect
    effect = ColorShiftEffect(128, 32, {"speed": 1.0})
    frame = Image.new("RGB", (128, 32), (255, 0, 0))
    r0 = effect.apply(frame, 0.0)
    r1 = effect.apply(frame, 3.0)  # 3 seconds later
    # Colors should differ after time passes
    p0 = r0.getpixel((0, 0))
    p1 = r1.getpixel((0, 0))
    assert p0 != p1


# --- RainbowSweepEffect ---

def test_rainbow_sweep_recolors():
    from protogen.generators.rainbow_sweep import RainbowSweepEffect
    effect = RainbowSweepEffect(128, 32, {"speed": 1.0})
    frame = Image.new("RGB", (128, 32), (200, 200, 200))
    result = effect.apply(frame, 0.0)
    # Left and right sides should have different hues
    left = result.getpixel((0, 0))
    right = result.getpixel((127, 0))
    assert left != right


def test_rainbow_sweep_preserves_black():
    from protogen.generators.rainbow_sweep import RainbowSweepEffect
    effect = RainbowSweepEffect(128, 32, {"speed": 1.0})
    frame = Image.new("RGB", (128, 32), (0, 0, 0))
    result = effect.apply(frame, 0.5)
    pixel = result.getpixel((64, 16))
    assert pixel == (0, 0, 0)


def test_rainbow_sweep_renders_valid_image():
    from protogen.generators.rainbow_sweep import RainbowSweepEffect
    effect = RainbowSweepEffect(128, 32, {"speed": 1.0})
    frame = Image.new("RGB", (128, 32), (128, 128, 128))
    result = effect.apply(frame, 1.0)
    assert result.size == (128, 32)
    assert result.mode == "RGB"


# --- GlitchEffect ---

def test_glitch_returns_valid_image():
    from protogen.generators.glitch import GlitchEffect
    effect = GlitchEffect(128, 32, {"intensity": 0.3})
    frame = Image.new("RGB", (128, 32), (100, 100, 100))
    result = effect.apply(frame, 0.0)
    assert result.size == (128, 32)
    assert result.mode == "RGB"


def test_glitch_with_burst():
    from protogen.generators.glitch import GlitchEffect
    effect = GlitchEffect(128, 32, {"intensity": 1.0})
    frame = Image.new("RGB", (128, 32), (100, 100, 100))
    # Force a burst by setting rng seed to something that triggers it
    effect._rng.seed(42)
    # Run multiple times — at high intensity, some should differ from original
    results = [effect.apply(frame, t * 0.01) for t in range(20)]
    # At least one result should differ from the original
    original_arr = np.array(frame)
    any_different = any(
        not np.array_equal(np.array(r), original_arr) for r in results
    )
    assert any_different


def test_glitch_preserves_size():
    from protogen.generators.glitch import GlitchEffect
    effect = GlitchEffect(64, 16, {"intensity": 0.5})
    frame = Image.new("RGB", (64, 16), (50, 100, 150))
    result = effect.apply(frame, 0.0)
    assert result.size == (64, 16)
