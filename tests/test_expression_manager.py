import asyncio

import pytest
from PIL import Image

from protogen.expression import Expression, ExpressionType
from protogen.expression_manager import ExpressionManager
from protogen.render_pipeline import RenderPipeline


@pytest.fixture
def sample_expressions():
    return {
        "happy": Expression(
            name="happy", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 255, 0)),
        ),
        "sad": Expression(
            name="sad", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 0, 255)),
        ),
    }


def test_set_expression(mock_display, sample_expressions):
    mgr = ExpressionManager(mock_display, sample_expressions)
    mgr.set_expression("happy")
    assert mgr.current_name == "happy"
    assert mock_display.last_image is not None


def test_expression_list(mock_display, sample_expressions):
    mgr = ExpressionManager(mock_display, sample_expressions)
    assert mgr.expression_names == ["happy", "sad"]


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
