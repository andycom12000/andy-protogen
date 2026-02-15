import pytest
from PIL import Image

from protogen.generators import ProceduralGenerator, GENERATORS


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


# --- Plasma ---

from protogen.generators.plasma import PlasmaGenerator


def test_plasma_renders():
    """Plasma generator produces colorful frames."""
    gen = PlasmaGenerator(128, 32, {"speed": 1.0})
    frame = gen.render(1.0)
    assert frame.size == (128, 32)
    pixels = list(frame.getdata())
    non_black = [p for p in pixels if p != (0, 0, 0)]
    assert len(non_black) > 0


def test_plasma_default_params():
    gen = PlasmaGenerator(128, 32, {})
    frame = gen.render(0.5)
    assert frame.size == (128, 32)


# --- Scrolling Text ---

from protogen.generators.scrolling_text import ScrollingTextGenerator


def test_scrolling_text_renders():
    """Scrolling text generator produces non-black frames with text."""
    gen = ScrollingTextGenerator(128, 32, {"text": "HELLO", "color": [0, 255, 255]})
    frame = gen.render(0.5)
    assert frame.size == (128, 32)
    pixels = list(frame.getdata())
    non_black = [p for p in pixels if p != (0, 0, 0)]
    assert len(non_black) > 0


def test_scrolling_text_set_text():
    """set_text updates the displayed text."""
    gen = ScrollingTextGenerator(128, 32, {"text": "A"})
    gen.set_text("NEW TEXT")
    assert gen._text == "NEW TEXT"


def test_scrolling_text_default_params():
    gen = ScrollingTextGenerator(128, 32, {})
    frame = gen.render(0.0)
    assert frame.size == (128, 32)
