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


@pytest.mark.asyncio
async def test_toggle_on_off(blink_fixtures):
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

    ctrl.toggle()
    await asyncio.sleep(0.1)
    ctrl.toggle()

    assert display.last_image.getpixel((0, 0)) == (255, 0, 0)
