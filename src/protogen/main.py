from __future__ import annotations

import asyncio
import signal
from pathlib import Path

from protogen.commands import InputEvent
from protogen.config import Config
from protogen.expression import load_expressions
from protogen.expression_manager import ExpressionManager
from protogen.input_manager import InputManager


def create_display(config: Config):
    if config.display.mock:
        from protogen.display.mock import MockDisplay
        return MockDisplay(
            width=config.display.width,
            height=config.display.height,
            scale=config.display.mock_scale,
            use_pygame=True,
        )
    else:
        from protogen.display.hub75 import HUB75Display
        return HUB75Display(
            width=config.display.width,
            height=config.display.height,
            n_addr_lines=config.display.n_addr_lines,
        )


async def async_main() -> None:
    config = Config.load()
    display = create_display(config)
    display.set_brightness(config.display.brightness)

    expressions = load_expressions(config.expressions_dir)
    expr_mgr = ExpressionManager(display, expressions)
    input_mgr = InputManager()

    # 註冊輸入來源
    if not config.display.mock:
        from protogen.inputs.button import ButtonInput
        input_mgr.add_source(ButtonInput(pin=config.input.button_pin))

    if config.input.web_enabled:
        from protogen.inputs.web import WebInput
        input_mgr.add_source(WebInput(
            port=config.input.web_port,
            expression_names=expr_mgr.expression_names,
            get_blink_state=lambda: expr_mgr.blink_enabled,
            get_current_expression=lambda: expr_mgr.current_name,
            get_brightness=lambda: display.brightness,
        ))

    # 設定預設表情
    expr_mgr.set_expression(config.default_expression)

    # 命令處理迴圈
    async def handle_commands():
        while True:
            cmd = await input_mgr.get()
            if cmd.event == InputEvent.SET_EXPRESSION:
                expr_mgr.set_expression(cmd.value)
            elif cmd.event == InputEvent.NEXT_EXPRESSION:
                expr_mgr.next_expression()
            elif cmd.event == InputEvent.PREV_EXPRESSION:
                expr_mgr.prev_expression()
            elif cmd.event == InputEvent.SET_BRIGHTNESS:
                display.set_brightness(cmd.value)
            elif cmd.event == InputEvent.TOGGLE_BLINK:
                expr_mgr.toggle_blink()

    # pygame 事件迴圈（保持視窗回應）
    async def pump_display_events():
        if hasattr(display, 'pump_events'):
            while True:
                if not display.pump_events():
                    return  # 視窗被關閉
                await asyncio.sleep(1 / 30)

    # 優雅關閉
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: loop.stop())
        except NotImplementedError:
            pass  # Windows 不支援 add_signal_handler

    await asyncio.gather(
        input_mgr.run_all(),
        handle_commands(),
        pump_display_events(),
    )


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
