"""Tests for WebSocket message handling via FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from protogen.commands import Command, InputEvent
from protogen.inputs.web import _create_app


@pytest.fixture
def ws_app():
    """Create a test FastAPI app for WebSocket testing."""
    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy", "sad"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 80,
    )
    return app, commands


def test_ws_set_expression(ws_app):
    """Send set action and verify SET_EXPRESSION command is generated."""
    app, commands = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "set", "name": "happy"})
    assert len(commands) == 1
    assert commands[0].event == InputEvent.SET_EXPRESSION
    assert commands[0].value == "happy"


def test_ws_brightness(ws_app):
    """Send brightness action and verify SET_BRIGHTNESS command."""
    app, commands = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "brightness", "value": 50})
    assert len(commands) == 1
    assert commands[0].event == InputEvent.SET_BRIGHTNESS
    assert commands[0].value == 50


def test_ws_toggle_blink(ws_app):
    """Send toggle_blink action and verify TOGGLE_BLINK command."""
    app, commands = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "toggle_blink"})
    assert len(commands) == 1
    assert commands[0].event == InputEvent.TOGGLE_BLINK
    assert commands[0].value is None


def test_ws_set_effect(ws_app):
    """Send set_effect action and verify SET_EFFECT command."""
    app, commands = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "set_effect", "name": "matrix_rain"})
    assert len(commands) == 1
    assert commands[0].event == InputEvent.SET_EFFECT
    assert commands[0].value == "matrix_rain"


def test_ws_clear_effect(ws_app):
    """Send clear_effect action and verify CLEAR_EFFECT command."""
    app, commands = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "clear_effect"})
    assert len(commands) == 1
    assert commands[0].event == InputEvent.CLEAR_EFFECT
    assert commands[0].value is None


def test_ws_set_text(ws_app):
    """Send set_text action and verify both SET_TEXT and SET_EFFECT commands."""
    app, commands = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "set_text", "text": "HELLO"})
    assert len(commands) == 2
    assert commands[0].event == InputEvent.SET_TEXT
    assert commands[0].value == "HELLO"
    assert commands[1].event == InputEvent.SET_EFFECT
    assert commands[1].value == "scrolling_text"


def test_ws_ping_no_command(ws_app):
    """Send ping action and verify no command is generated."""
    app, commands = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "ping"})
    assert len(commands) == 0


def test_ws_update_effect_params(ws_app):
    """Send update_effect_params action and verify SET_EFFECT_WITH_PARAMS command."""
    app, commands = ws_app
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({
            "action": "update_effect_params",
            "name": "matrix_rain",
            "params": {"speed": 2.0, "density": 0.5},
        })
    assert len(commands) == 1
    assert commands[0].event == InputEvent.SET_EFFECT_WITH_PARAMS
    assert commands[0].value == {
        "name": "matrix_rain",
        "params": {"speed": 2.0, "density": 0.5},
    }
