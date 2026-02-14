import asyncio

import pytest
from PIL import Image

from protogen.animation import AnimationEngine


@pytest.mark.asyncio
async def test_play_oneshot(mock_display):
    frames = [Image.new("RGB", (128, 32), (i * 80, 0, 0)) for i in range(3)]
    engine = AnimationEngine(mock_display)

    await engine.play(frames, fps=60, loop=False)

    # 最後一幀應該被顯示
    assert mock_display.last_image is not None


@pytest.mark.asyncio
async def test_play_loop_can_be_stopped(mock_display):
    frames = [Image.new("RGB", (128, 32), (0, 255, 0))]
    engine = AnimationEngine(mock_display)

    task = asyncio.create_task(engine.play(frames, fps=30, loop=True))
    await asyncio.sleep(0.1)
    engine.stop()
    await asyncio.wait_for(task, timeout=1.0)
