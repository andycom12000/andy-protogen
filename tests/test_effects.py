import asyncio

import pytest
from PIL import Image

from protogen.render_pipeline import RenderPipeline
from protogen.generators import ProceduralGenerator, GENERATORS, register_generators


class DummyEffect(ProceduralGenerator):
    def render(self, t: float) -> Image.Image:
        return Image.new("RGB", (self.width, self.height), (0, 50, 0))


@pytest.fixture(autouse=True)
def setup_generators():
    register_generators()
    GENERATORS["__test_effect__"] = DummyEffect
    yield
    GENERATORS.pop("__test_effect__", None)


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
