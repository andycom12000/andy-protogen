"""Boundary condition and edge case tests."""

import pytest
from PIL import Image

from protogen.config import Config, DisplayConfig
from protogen.display.mock import MockDisplay
from protogen.expression import Expression, ExpressionType
from protogen.expression_manager import ExpressionManager
from protogen.expression_store import ExpressionStore


# ---- Config.load() from YAML ----

def test_config_load_from_yaml(tmp_path):
    """Config.load() parses YAML values correctly."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        "display:\n  brightness: 60\n  mock: true\ndefault_expression: angry\n",
        encoding="utf-8",
    )
    config = Config.load(yaml_file)
    assert config.display.brightness == 60
    assert config.display.mock is True
    assert config.default_expression == "angry"


# ---- Config.load() missing file returns defaults ----

def test_config_load_missing_file_returns_defaults(tmp_path):
    """Config.load() returns default values when the file doesn't exist."""
    config = Config.load(tmp_path / "nonexistent.yaml")
    assert config.display.brightness == 80
    assert config.display.mock is False
    assert config.default_expression == "happy"


# ---- Config.load() empty YAML ----

def test_config_load_empty_yaml(tmp_path):
    """Config.load() returns defaults when given an empty YAML file."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("", encoding="utf-8")
    config = Config.load(yaml_file)
    assert config.display.brightness == 80


# ---- DisplayConfig brightness boundary parametrized ----

@pytest.mark.parametrize("input_val,expected", [
    (-1, 0),
    (0, 0),
    (50, 50),
    (100, 100),
    (101, 100),
    (999, 100),
])
def test_display_config_brightness_boundary(input_val, expected):
    """DisplayConfig.__post_init__ clamps brightness to [0, 100]."""
    cfg = DisplayConfig(brightness=input_val)
    assert cfg.brightness == expected


# ---- MockDisplay brightness boundary ----

@pytest.mark.parametrize("input_val,expected", [
    (-10, 0),
    (0, 0),
    (50, 50),
    (100, 100),
    (200, 100),
])
def test_mock_display_brightness_boundary(input_val, expected):
    """MockDisplay.set_brightness clamps to [0, 100]."""
    display = MockDisplay(width=128, height=32)
    display.set_brightness(input_val)
    assert display.brightness == expected


# ---- Empty ExpressionStore ----

def test_empty_expression_store():
    """ExpressionStore with an empty dict has no names, get returns None."""
    store = ExpressionStore({})
    assert store.names == []
    assert store.get("anything") is None
    assert store.get_thumbnail("anything") is None


# ---- ExpressionManager with empty store ----

def test_expression_manager_empty_store(mock_display):
    """set_expression on a nonexistent name is a no-op."""
    store = ExpressionStore({})
    mgr = ExpressionManager(mock_display, store)
    mgr.set_expression("nonexistent")
    assert mgr.current_name is None
    assert mock_display.last_image is None


# ---- Animation expression with empty frames list ----

def test_expression_store_animation_no_frames():
    """get_thumbnail returns None for an animation with no frames."""
    store = ExpressionStore({
        "empty_anim": Expression(
            name="empty_anim",
            type=ExpressionType.ANIMATION,
            frames=[],
            fps=15,
            loop=True,
        ),
    })
    assert store.get_thumbnail("empty_anim") is None


# ---- ExpressionManager set_expression with empty-frames animation ----

def test_expression_manager_empty_frames_animation(mock_display):
    """set_expression with an animation that has no frames is a no-op."""
    store = ExpressionStore({
        "empty_anim": Expression(
            name="empty_anim",
            type=ExpressionType.ANIMATION,
            frames=[],
            fps=15,
            loop=True,
        ),
    })
    mgr = ExpressionManager(mock_display, store)
    mgr.set_expression("empty_anim")
    # current_name is set but no image is shown because frames list is empty
    assert mgr.current_name == "empty_anim"
    assert mock_display.last_image is None


# ---- Static expression with no image ----

def test_expression_manager_static_no_image(mock_display):
    """set_expression with a static expression that has no image is a no-op."""
    store = ExpressionStore({
        "no_img": Expression(
            name="no_img",
            type=ExpressionType.STATIC,
            image=None,
        ),
    })
    mgr = ExpressionManager(mock_display, store)
    mgr.set_expression("no_img")
    # current_name is set but no image is shown because image is None
    assert mgr.current_name == "no_img"
    assert mock_display.last_image is None
