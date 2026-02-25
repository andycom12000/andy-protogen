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


def test_update_effect_params_endpoint(web_app):
    app, commands, _ = web_app
    client = TestClient(app)
    response = client.post(
        "/api/effect/matrix_rain/params",
        json={"speed": 2.0, "density": 0.5},
    )
    assert response.status_code == 200
    assert len(commands) == 1
    assert commands[0].event == InputEvent.SET_EFFECT_WITH_PARAMS
    assert commands[0].value == {
        "name": "matrix_rain",
        "params": {"speed": 2.0, "density": 0.5},
    }


def test_preview_returns_jpeg():
    """Preview endpoint returns JPEG when a frame is available."""
    frame = Image.new("RGB", (128, 32), (255, 0, 0))
    buf = io.BytesIO()
    frame.save(buf, format="JPEG", quality=60)
    jpeg_bytes = buf.getvalue()
    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 100,
        get_display_fps=lambda: 30.0,
        get_jpeg=lambda quality=60: jpeg_bytes,
    )
    client = TestClient(app)
    response = client.get("/api/preview")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "no-store"
    assert response.content[:2] == b'\xff\xd8'


def test_preview_no_frame_returns_204():
    """Preview endpoint returns 204 when get_jpeg returns None."""
    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 100,
        get_display_fps=lambda: 30.0,
        get_jpeg=lambda quality=60: None,
    )
    client = TestClient(app)
    response = client.get("/api/preview")
    assert response.status_code == 204


def test_preview_no_callback_returns_204(web_app):
    """Preview endpoint returns 204 when get_jpeg callback is not provided."""
    app, _, _ = web_app
    client = TestClient(app)
    response = client.get("/api/preview")
    assert response.status_code == 204


def test_preview_stream_returns_mjpeg():
    """Preview stream endpoint returns multipart MJPEG content."""
    frame = Image.new("RGB", (128, 32), (255, 0, 0))
    buf = io.BytesIO()
    frame.save(buf, format="JPEG", quality=60)
    jpeg_bytes = buf.getvalue()
    call_count = [0]

    class _StopStream(Exception):
        """Raised to terminate the infinite stream in tests."""

    def get_jpeg(quality=60):
        call_count[0] += 1
        if call_count[0] > 2:
            raise _StopStream
        return jpeg_bytes

    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 100,
        get_display_fps=lambda: 30.0,
        get_jpeg=get_jpeg,
    )
    # The MJPEG generator is infinite; raise_server_exceptions=False
    # lets the test terminate when get_jpeg raises _StopStream.
    client = TestClient(app, raise_server_exceptions=False)
    with client.stream("GET", "/api/preview/stream") as response:
        assert response.status_code == 200
        content_type = response.headers["content-type"]
        assert "multipart/x-mixed-replace" in content_type
        response.read()
    # get_jpeg was called, confirming the generator invoked it
    assert call_count[0] > 0
    # Verify JPEG bytes are well-formed (would be in the stream)
    assert jpeg_bytes[:2] == b"\xff\xd8"


def test_preview_stream_no_jpeg_returns_204():
    """Preview stream returns 204 when get_jpeg is not provided."""
    commands = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    app = _create_app(
        expression_names=["happy"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 100,
        get_display_fps=lambda: 30.0,
    )
    client = TestClient(app)
    response = client.get("/api/preview/stream")
    assert response.status_code == 204
