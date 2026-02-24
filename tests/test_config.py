import pytest
from protogen.config import DisplayConfig


def test_brightness_clamped_to_valid_range():
    """Brightness is clamped to 0-100."""
    cfg = DisplayConfig(brightness=150)
    assert cfg.brightness == 100

    cfg2 = DisplayConfig(brightness=-10)
    assert cfg2.brightness == 0


def test_brightness_valid_values_unchanged():
    """Valid brightness values pass through unchanged."""
    cfg = DisplayConfig(brightness=50)
    assert cfg.brightness == 50
