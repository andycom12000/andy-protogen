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
    """During active phases (t=0.15 scanline, t=0.5 text), frame should have content."""
    frame = render_boot_frame(128, 32, t=0.5)
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
