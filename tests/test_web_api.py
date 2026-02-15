import io

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from protogen.commands import Command, InputEvent
from protogen.inputs.web import _create_app
from protogen.system_monitor import SystemMonitor


def _make_png(color: tuple) -> bytes:
    img = Image.new("RGB", (128, 32), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def web_app():
    """Create a test FastAPI app with thumbnail and effect callbacks."""
    red_png = _make_png((255, 0, 0))
    green_png = _make_png((0, 255, 0))

    def get_thumbnail(name: str) -> bytes | None:
        if name == "happy":
            return red_png
        return None

    def get_effect_thumbnail(name: str) -> bytes | None:
        if name == "matrix_rain":
            return green_png
        return None

    commands = []
    active_effect = [None]

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy", "sad"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 80,
        get_thumbnail=get_thumbnail,
        effect_names=["matrix_rain", "starfield", "plasma", "scrolling_text"],
        get_active_effect=lambda: active_effect[0],
        get_effect_thumbnail=get_effect_thumbnail,
        get_display_fps=lambda: 30.0,
        system_monitor=SystemMonitor(),
    )
    return app, commands, active_effect


def test_thumbnail_endpoint_returns_png(web_app):
    app, _, _ = web_app
    client = TestClient(app)
    response = client.get("/api/expressions/happy/thumbnail")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:4] == b'\x89PNG'


def test_thumbnail_endpoint_404_for_unknown(web_app):
    app, _, _ = web_app
    client = TestClient(app)
    response = client.get("/api/expressions/nonexistent/thumbnail")
    assert response.status_code == 404


def test_text_endpoint(web_app):
    app, commands, _ = web_app
    client = TestClient(app)
    response = client.post("/api/text", json={"text": "Hello!"})
    assert response.status_code == 200
    assert len(commands) == 2
    assert commands[0].event == InputEvent.SET_TEXT
    assert commands[0].value == "Hello!"
    assert commands[1].event == InputEvent.SET_EFFECT
    assert commands[1].value == "scrolling_text"


def test_effects_list_endpoint(web_app):
    app, _, _ = web_app
    client = TestClient(app)
    response = client.get("/api/effects")
    assert response.status_code == 200
    data = response.json()
    assert "effects" in data
    assert "matrix_rain" in data["effects"]
    assert len(data["effects"]) == 4


def test_set_effect_endpoint(web_app):
    app, commands, _ = web_app
    client = TestClient(app)
    response = client.post("/api/effect/matrix_rain")
    assert response.status_code == 200
    assert len(commands) == 1
    assert commands[0].event == InputEvent.SET_EFFECT
    assert commands[0].value == "matrix_rain"


def test_clear_effect_endpoint(web_app):
    app, commands, _ = web_app
    client = TestClient(app)
    response = client.post("/api/effect/clear")
    assert response.status_code == 200
    assert len(commands) == 1
    assert commands[0].event == InputEvent.CLEAR_EFFECT


def test_state_includes_effect(web_app):
    app, _, active_effect = web_app
    client = TestClient(app)
    active_effect[0] = "starfield"
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert data["active_effect"] == "starfield"


def test_effect_thumbnail_endpoint(web_app):
    app, _, _ = web_app
    client = TestClient(app)
    response = client.get("/api/effects/matrix_rain/thumbnail")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:4] == b'\x89PNG'

    # Unknown effect returns 404
    response = client.get("/api/effects/nonexistent/thumbnail")
    assert response.status_code == 404


def test_system_status_endpoint(web_app):
    app, _, active_effect = web_app
    active_effect[0] = "plasma"
    client = TestClient(app)
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    # Should contain system metrics keys
    assert "cpu_temp" in data
    assert "cpu_usage" in data
    assert "memory_used" in data
    assert "uptime" in data
    assert "wifi_signal" in data
    # Should contain display state keys
    assert "display_fps" in data
    assert data["display_fps"] == 30.0
    assert "current_expression" in data
    assert data["current_expression"] == "happy"
    assert "current_effect" in data
    assert data["current_effect"] == "plasma"
    assert "brightness" in data
    assert data["brightness"] == 80


def test_system_status_without_monitor():
    """System status endpoint works with monitor=None."""
    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 100,
        get_display_fps=lambda: 0.0,
        system_monitor=None,
    )
    client = TestClient(app)
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["cpu_temp"] is None
    assert data["display_fps"] == 0.0
