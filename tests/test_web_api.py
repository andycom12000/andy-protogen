import io

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from protogen.commands import Command, InputEvent
from protogen.inputs.web import _create_app


@pytest.fixture
def web_app():
    """Create a test FastAPI app with a thumbnail callback."""
    red_png = _make_png((255, 0, 0))

    def get_thumbnail(name: str) -> bytes | None:
        if name == "happy":
            return red_png
        return None

    commands = []
    texts = []

    async def put(cmd: Command) -> None:
        commands.append(cmd)

    def set_text(text: str) -> None:
        texts.append(text)

    app = _create_app(
        expression_names=["happy", "sad"],
        put=put,
        get_blink_state=lambda: False,
        get_current_expression=lambda: "happy",
        get_brightness=lambda: 80,
        get_thumbnail=get_thumbnail,
        set_text=set_text,
    )
    return app, commands, texts


def _make_png(color: tuple) -> bytes:
    img = Image.new("RGB", (128, 32), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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
    app, commands, texts = web_app
    client = TestClient(app)
    response = client.post("/api/text", json={"text": "Hello!"})
    assert response.status_code == 200
    assert len(commands) == 1
    assert commands[0].event == InputEvent.SET_EXPRESSION
    assert commands[0].value == "scrolling_text"
    assert texts == ["Hello!"]
