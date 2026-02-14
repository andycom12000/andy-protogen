"""Shared test fixtures."""
import pytest
from protogen.display.mock import MockDisplay


@pytest.fixture
def mock_display():
    return MockDisplay(width=128, height=32)
