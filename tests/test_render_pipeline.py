from PIL import Image

from protogen.display.mock import MockDisplay
from protogen.generators import register_generators
from protogen.render_pipeline import RenderPipeline

register_generators()


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


def test_get_fps_initial_zero():
    """get_fps returns 0.0 when no frames have been shown."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)
    assert pipeline.get_fps() == 0.0


def test_get_fps_after_frames():
    """get_fps returns a positive value after multiple show_image calls."""
    import time
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)

    img = Image.new("RGB", (128, 32), (0, 0, 0))
    for _ in range(5):
        pipeline.show_image(img)
        time.sleep(0.01)

    fps = pipeline.get_fps()
    assert fps > 0.0


def test_get_fps_single_frame_zero():
    """get_fps returns 0.0 with only one frame (no interval to measure)."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)

    pipeline.show_image(Image.new("RGB", (128, 32), (0, 0, 0)))
    assert pipeline.get_fps() == 0.0


def test_pending_text_applied_on_set_effect():
    """Text set before effect is created gets applied to the new effect."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)

    # Simulate the command order: SET_TEXT then SET_EFFECT
    pipeline.set_effect_text("HELLO WORLD")
    pipeline.set_effect("scrolling_text", {})

    assert pipeline._effect is not None
    assert pipeline._effect._text == "HELLO WORLD"
    assert pipeline._pending_text is None


def test_pending_text_cleared_after_apply():
    """Pending text is consumed after being applied to the effect."""
    display = MockDisplay(width=128, height=32)
    pipeline = RenderPipeline(display)

    pipeline.set_effect_text("TEST")
    pipeline.set_effect("scrolling_text", {})

    # Create a second effect — should NOT carry over old text
    pipeline.set_effect("scrolling_text", {})
    assert pipeline._effect._text == "PROTOGEN"  # default
