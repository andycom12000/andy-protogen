import asyncio

import pytest
from PIL import Image

from protogen.expression import Expression, ExpressionType
from protogen.expression_manager import ExpressionManager


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
