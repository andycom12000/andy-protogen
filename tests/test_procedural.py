import asyncio

import pytest
from PIL import Image

from protogen.generators import ProceduralGenerator, GENERATORS
from protogen.expression import Expression, ExpressionType
from protogen.expression_manager import ExpressionManager
from protogen.render_pipeline import RenderPipeline


class DummyGenerator(ProceduralGenerator):
    """Test generator that fills with a solid color based on time."""

    def render(self, t: float) -> Image.Image:
        brightness = min(255, int(t * 100) % 256)
        return Image.new("RGB", (self.width, self.height), (brightness, 0, 0))


@pytest.fixture(autouse=True)
def register_test_generator():
    """Register the dummy generator for tests."""
    from protogen.generators import register_generators

    register_generators()
    GENERATORS["__test_dummy__"] = DummyGenerator
    yield
    GENERATORS.pop("__test_dummy__", None)


def test_procedural_generator_abc():
    """ProceduralGenerator subclass can be instantiated and renders frames."""
    gen = DummyGenerator(128, 32, {})
    frame = gen.render(0.5)
    assert frame.size == (128, 32)
    assert frame.mode == "RGB"


def test_generators_registry_exists():
    """GENERATORS registry is a dict mapping names to generator classes."""
    assert isinstance(GENERATORS, dict)


@pytest.mark.asyncio
async def test_expression_manager_plays_procedural(mock_display):
    """ExpressionManager can play a procedural expression."""
    pipeline = RenderPipeline(mock_display)
    expressions = {
        "test_proc": Expression(
            name="test_proc",
            type=ExpressionType.PROCEDURAL,
            generator_name="__test_dummy__",
            generator_params={},
            fps=30,
            loop=True,
        ),
    }
    mgr = ExpressionManager(pipeline, expressions)
    mgr.set_expression("test_proc")

    # Let it render a few frames
    await asyncio.sleep(0.15)

    assert mgr.current_name == "test_proc"
    assert mock_display.last_image is not None


def test_procedural_thumbnail(mock_display):
    """get_thumbnail returns a rendered frame for procedural expressions."""
    expressions = {
        "test_proc": Expression(
            name="test_proc",
            type=ExpressionType.PROCEDURAL,
            generator_name="__test_dummy__",
            generator_params={},
            fps=30,
            loop=True,
        ),
    }
    mgr = ExpressionManager(mock_display, expressions)
    data = mgr.get_thumbnail("test_proc")
    assert data is not None
    assert data[:4] == b'\x89PNG'


# --- Matrix Rain ---

from protogen.generators.matrix_rain import MatrixRainGenerator


def test_matrix_rain_renders():
    """Matrix rain generator produces non-black frames."""
    gen = MatrixRainGenerator(128, 32, {"color": [0, 255, 70], "speed": 1.0, "density": 0.3})
    frame = gen.render(1.0)
    assert frame.size == (128, 32)
    assert frame.mode == "RGB"
    # After 1 second, some pixels should be non-black
    pixels = list(frame.getdata())
    non_black = [p for p in pixels if p != (0, 0, 0)]
    assert len(non_black) > 0


def test_matrix_rain_default_params():
    """Matrix rain works with empty params (uses defaults)."""
    gen = MatrixRainGenerator(128, 32, {})
    frame = gen.render(0.5)
    assert frame.size == (128, 32)


# --- Starfield ---

from protogen.generators.starfield import StarfieldGenerator


def test_starfield_renders():
    """Starfield generator produces non-black frames."""
    gen = StarfieldGenerator(128, 32, {"star_count": 40, "speed": 1.0})
    frame = gen.render(1.0)
    assert frame.size == (128, 32)
    pixels = list(frame.getdata())
    non_black = [p for p in pixels if p != (0, 0, 0)]
    assert len(non_black) > 0


def test_starfield_default_params():
    gen = StarfieldGenerator(128, 32, {})
    frame = gen.render(0.5)
    assert frame.size == (128, 32)
