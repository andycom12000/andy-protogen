from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Awaitable

from protogen.commands import Command, InputEvent


class WebInput:
    """FastAPI + WebSocket web control interface."""

    def __init__(self, port: int = 8080, expression_names: list[str] | None = None) -> None:
        self._port = port
        self._expression_names = expression_names or []

    async def run(self, put: Callable[[Command], Awaitable[None]]) -> None:
        from fastapi import FastAPI, WebSocket
        from fastapi.responses import FileResponse
        import uvicorn

        app = FastAPI()

        static_dir = Path(__file__).parent.parent.parent.parent / "web" / "static"

        @app.get("/")
        async def index():
            return FileResponse(static_dir / "index.html")

        @app.get("/api/expressions")
        async def list_expressions():
            return {"expressions": self._expression_names}

        @app.post("/api/expression/{name}")
        async def set_expression(name: str):
            await put(Command(event=InputEvent.SET_EXPRESSION, value=name))
            return {"status": "ok"}

        @app.post("/api/next")
        async def next_expression():
            await put(Command(event=InputEvent.NEXT_EXPRESSION))
            return {"status": "ok"}

        @app.post("/api/prev")
        async def prev_expression():
            await put(Command(event=InputEvent.PREV_EXPRESSION))
            return {"status": "ok"}

        @app.post("/api/brightness/{value}")
        async def set_brightness(value: int):
            await put(Command(event=InputEvent.SET_BRIGHTNESS, value=value))
            return {"status": "ok"}

        @app.websocket("/ws")
        async def websocket_endpoint(ws: WebSocket):
            await ws.accept()
            try:
                while True:
                    data = await ws.receive_json()
                    action = data.get("action")
                    if action == "set":
                        await put(Command(event=InputEvent.SET_EXPRESSION, value=data["name"]))
                    elif action == "next":
                        await put(Command(event=InputEvent.NEXT_EXPRESSION))
                    elif action == "prev":
                        await put(Command(event=InputEvent.PREV_EXPRESSION))
                    elif action == "brightness":
                        await put(Command(event=InputEvent.SET_BRIGHTNESS, value=data["value"]))
            except Exception:
                pass

        config = uvicorn.Config(app, host="0.0.0.0", port=self._port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
