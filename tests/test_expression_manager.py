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
