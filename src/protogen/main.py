from __future__ import annotations

import asyncio
import io
import signal
from pathlib import Path

from PIL import Image

from protogen.commands import InputEvent
from protogen.config import Config
from protogen.expression import load_expressions, load_effects
from protogen.expression_manager import ExpressionManager
from protogen.input_manager import InputManager
from protogen.boot_animation import play_boot_animation
from protogen.generators import register_generators, GENERATORS, FrameEffect
from protogen.render_pipeline import RenderPipeline
from protogen.system_monitor import SystemMonitor


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
    register_generators()
    display = create_display(config)
    display.set_brightness(config.display.brightness)

    expressions = load_expressions(config.expressions_dir)
    effects = load_effects(config.expressions_dir)
    pipeline = RenderPipeline(display)
    expr_mgr = ExpressionManager(
        pipeline, expressions,
        blink_interval_min=config.blink_interval_min,
        blink_interval_max=config.blink_interval_max,
        transition_duration_ms=config.transition_duration_ms,
    )
    input_mgr = InputManager()

    def make_effect_thumbnail(name: str) -> bytes | None:
        effect = effects.get(name)
        if effect is None:
            return None
        gen_cls = GENERATORS.get(effect.generator_name)
        if gen_cls is None:
            return None
        gen = gen_cls(display.width, display.height, effect.generator_params)
        if isinstance(gen, FrameEffect):
            # Use a cyan sample frame so the transform is visible
            sample = Image.new("RGB", (display.width, display.height), (0, 200, 200))
            img = gen.apply(sample, 0.5)
        else:
            img = gen.render(0.0)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    system_monitor = SystemMonitor()

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
            get_thumbnail=expr_mgr.get_thumbnail,
            effect_names=sorted(effects.keys()),
            get_active_effect=lambda: pipeline.active_effect_name,
            get_effect_thumbnail=make_effect_thumbnail,
            get_display_fps=lambda: pipeline.get_fps(),
            system_monitor=system_monitor,
        ))

    # 播放開機動畫
    await play_boot_animation(display, duration=2.0)

    # 設定預設表情
    expr_mgr.set_expression(config.default_expression)

    # 命令處理迴圈
    async def handle_commands():
        while True:
            cmd = await input_mgr.get()
            if cmd.event == InputEvent.SET_EXPRESSION:
                expr_mgr.set_expression(cmd.value)
            elif cmd.event == InputEvent.SET_BRIGHTNESS:
                display.set_brightness(cmd.value)
            elif cmd.event == InputEvent.SET_TEXT:
                pipeline.set_effect_text(cmd.value)
            elif cmd.event == InputEvent.TOGGLE_BLINK:
                expr_mgr.toggle_blink()
            elif cmd.event == InputEvent.SET_EFFECT:
                effect = effects.get(cmd.value)
                if effect is not None:
                    pipeline.set_effect(effect.generator_name, effect.generator_params, effect.fps)
            elif cmd.event == InputEvent.CLEAR_EFFECT:
                pipeline.clear_effect()

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
        pipeline.run_effect_loop(),
    )


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
