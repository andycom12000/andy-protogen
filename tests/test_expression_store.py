import io

import pytest
from PIL import Image

from protogen.expression import Expression, ExpressionType
from protogen.expression_store import ExpressionStore


@pytest.fixture
def sample_store():
    return ExpressionStore({
        "happy": Expression(
            name="happy", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 255, 0)),
        ),
        "sad": Expression(
            name="sad", type=ExpressionType.STATIC,
            image=Image.new("RGB", (128, 32), (0, 0, 255)),
        ),
        "blink": Expression(
            name="blink", type=ExpressionType.ANIMATION,
            frames=[Image.new("RGB", (128, 32), (255, 255, 255))],
            fps=15, loop=False, hidden=True,
        ),
    })


def test_names_excludes_hidden(sample_store):
    assert sample_store.names == ["happy", "sad"]


def test_get_existing(sample_store):
    expr = sample_store.get("happy")
    assert expr is not None
    assert expr.name == "happy"


def test_get_hidden(sample_store):
    """Hidden expressions are still accessible via get()."""
    expr = sample_store.get("blink")
    assert expr is not None


def test_get_nonexistent(sample_store):
    assert sample_store.get("nonexistent") is None


def test_get_thumbnail_static(sample_store):
    data = sample_store.get_thumbnail("happy")
    assert data is not None
    assert data[:4] == b'\x89PNG'


def test_get_thumbnail_animation(sample_store):
    data = sample_store.get_thumbnail("blink")
    assert data is not None
    img = Image.open(io.BytesIO(data))
    assert img.getpixel((0, 0)) == (255, 255, 255)


def test_get_thumbnail_nonexistent(sample_store):
    assert sample_store.get_thumbnail("nonexistent") is None
