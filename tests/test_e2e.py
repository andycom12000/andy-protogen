"""End-to-end integration tests for the full command pipeline.

Exercises: InputManager -> command processing -> ExpressionManager / RenderPipeline -> Display
"""

import pytest
from PIL import Image

from protogen.commands import Command, InputEvent
from protogen.expression import Expression, ExpressionType, Effect
from protogen.expression_manager import ExpressionManager
from protogen.expression_store import ExpressionStore
from protogen.generators import register_generators, GENERATORS
from protogen.input_manager import InputManager
from protogen.render_pipeline import RenderPipeline

# Ensure generators are registered once for all tests in this module.
register_generators()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(*names: str) -> tuple[ExpressionStore, dict[str, Image.Image]]:
    """Build an ExpressionStore with coloured static expressions.

    Returns the store and a mapping of name -> original image for assertions.
    """
    colours = {
        "happy": (0, 255, 0),
        "sad": (0, 0, 255),
        "angry": (255, 0, 0),
        "surprised": (255, 255, 0),
    }
    expressions: dict[str, Expression] = {}
    images: dict[str, Image.Image] = {}
    for name in names:
        colour = colours.get(name, (128, 128, 128))
        img = Image.new("RGB", (128, 32), colour)
        expressions[name] = Expression(
            name=name,
            type=ExpressionType.STATIC,
            image=img,
        )
        images[name] = img
    return ExpressionStore(expressions), images


def _make_effects() -> dict[str, Effect]:
    """Build a small dictionary of Effect objects for testing."""
    return {
        "matrix_rain": Effect(
            name="matrix_rain",
            generator_name="matrix_rain",
            generator_params={"color": [0, 255, 70], "speed": 1.0, "density": 0.3},
            fps=20,
        ),
        "starfield": Effect(
            name="starfield",
            generator_name="starfield",
            generator_params={"speed": 1.0},
            fps=20,
        ),
    }


async def _process_command(
    cmd: Command,
    expr_mgr: ExpressionManager,
    pipeline: RenderPipeline,
    effects: dict[str, Effect],
    display,
) -> None:
    """Simulate the handle_commands() dispatch from main.py for a single command."""
    if cmd.event == InputEvent.SET_EXPRESSION:
        expr_mgr.set_expression(cmd.value)
    elif cmd.event == InputEvent.SET_BRIGHTNESS:
        display.set_brightness(cmd.value)
    elif cmd.event == InputEvent.TOGGLE_BLINK:
        expr_mgr.toggle_blink()
    elif cmd.event == InputEvent.SET_EFFECT:
        effect = effects.get(cmd.value)
        if effect is not None:
            pipeline.set_effect(
                effect.generator_name, effect.generator_params, effect.fps,
            )
    elif cmd.event == InputEvent.CLEAR_EFFECT:
        pipeline.clear_effect()
    elif cmd.event == InputEvent.SET_TEXT:
        pipeline.set_effect_text(cmd.value)
    elif cmd.event == InputEvent.SET_EFFECT_PARAMS:
        pipeline.update_effect_params(cmd.value)
    elif cmd.event == InputEvent.SET_EFFECT_WITH_PARAMS:
        effect = effects.get(cmd.value["name"])
        if effect is not None:
            pipeline.set_effect(
                effect.generator_name, effect.generator_params, effect.fps,
            )
            pipeline.update_effect_params(cmd.value.get("params", {}))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_expression_through_pipeline(mock_display):
    """PUT SET_EXPRESSION into InputManager, process it, verify display output."""
    store, images = _make_store("happy", "sad")
    pipeline = RenderPipeline(mock_display)
    expr_mgr = ExpressionManager(pipeline, store)
    input_mgr = InputManager()
    effects = _make_effects()

    await input_mgr.put(Command(event=InputEvent.SET_EXPRESSION, value="happy"))

    cmd = await input_mgr.get()
    await _process_command(cmd, expr_mgr, pipeline, effects, mock_display)

    assert expr_mgr.current_name == "happy"
    assert mock_display.last_image is not None
    assert mock_display.last_image.getpixel((0, 0)) == (0, 255, 0)


@pytest.mark.asyncio
async def test_set_brightness_through_pipeline(mock_display):
    """SET_BRIGHTNESS command changes display brightness."""
    store, _ = _make_store("happy")
    pipeline = RenderPipeline(mock_display)
    expr_mgr = ExpressionManager(pipeline, store)
    input_mgr = InputManager()
    effects = _make_effects()

    assert mock_display.brightness == 100  # default

    await input_mgr.put(Command(event=InputEvent.SET_BRIGHTNESS, value=42))

    cmd = await input_mgr.get()
    await _process_command(cmd, expr_mgr, pipeline, effects, mock_display)

    assert mock_display.brightness == 42


@pytest.mark.asyncio
async def test_toggle_blink_through_pipeline(mock_display):
    """TOGGLE_BLINK command toggles blink state on/off."""
    store, _ = _make_store("happy")
    pipeline = RenderPipeline(mock_display)
    expr_mgr = ExpressionManager(pipeline, store)
    input_mgr = InputManager()
    effects = _make_effects()

    assert expr_mgr.blink_enabled is False

    # Toggle ON
    await input_mgr.put(Command(event=InputEvent.TOGGLE_BLINK))
    cmd = await input_mgr.get()
    await _process_command(cmd, expr_mgr, pipeline, effects, mock_display)
    assert expr_mgr.blink_enabled is True

    # Toggle OFF
    await input_mgr.put(Command(event=InputEvent.TOGGLE_BLINK))
    cmd = await input_mgr.get()
    await _process_command(cmd, expr_mgr, pipeline, effects, mock_display)
    assert expr_mgr.blink_enabled is False


@pytest.mark.asyncio
async def test_set_effect_through_pipeline(mock_display):
    """SET_EFFECT command activates an effect on RenderPipeline."""
    store, _ = _make_store("happy")
    pipeline = RenderPipeline(mock_display)
    expr_mgr = ExpressionManager(pipeline, store)
    input_mgr = InputManager()
    effects = _make_effects()

    assert pipeline.active_effect_name is None

    await input_mgr.put(Command(event=InputEvent.SET_EFFECT, value="matrix_rain"))

    cmd = await input_mgr.get()
    await _process_command(cmd, expr_mgr, pipeline, effects, mock_display)

    assert pipeline.active_effect_name == "matrix_rain"
    assert pipeline._effect is not None


@pytest.mark.asyncio
async def test_clear_effect_through_pipeline(mock_display):
    """CLEAR_EFFECT command removes active effect from RenderPipeline."""
    store, _ = _make_store("happy")
    pipeline = RenderPipeline(mock_display)
    expr_mgr = ExpressionManager(pipeline, store)
    input_mgr = InputManager()
    effects = _make_effects()

    # First, set an expression so the pipeline has a frame to restore
    expr_mgr.set_expression("happy")

    # Set an effect
    await input_mgr.put(Command(event=InputEvent.SET_EFFECT, value="matrix_rain"))
    cmd = await input_mgr.get()
    await _process_command(cmd, expr_mgr, pipeline, effects, mock_display)
    assert pipeline.active_effect_name == "matrix_rain"

    # Now clear it
    await input_mgr.put(Command(event=InputEvent.CLEAR_EFFECT))
    cmd = await input_mgr.get()
    await _process_command(cmd, expr_mgr, pipeline, effects, mock_display)

    assert pipeline.active_effect_name is None
    assert pipeline._effect is None
    # After clearing, the display should show the original expression
    assert mock_display.last_image is not None
    assert mock_display.last_image.getpixel((0, 0)) == (0, 255, 0)


@pytest.mark.asyncio
async def test_multiple_commands_in_sequence(mock_display):
    """Multiple commands processed in order produce the correct final state."""
    store, _ = _make_store("happy", "sad", "angry")
    pipeline = RenderPipeline(mock_display)
    expr_mgr = ExpressionManager(pipeline, store)
    input_mgr = InputManager()
    effects = _make_effects()

    commands = [
        Command(event=InputEvent.SET_EXPRESSION, value="happy"),
        Command(event=InputEvent.SET_BRIGHTNESS, value=75),
        Command(event=InputEvent.SET_EXPRESSION, value="sad"),
        Command(event=InputEvent.TOGGLE_BLINK),
        Command(event=InputEvent.SET_EFFECT, value="starfield"),
        Command(event=InputEvent.SET_EXPRESSION, value="angry"),
        Command(event=InputEvent.SET_BRIGHTNESS, value=30),
        Command(event=InputEvent.CLEAR_EFFECT),
    ]

    for c in commands:
        await input_mgr.put(c)

    for _ in commands:
        cmd = await input_mgr.get()
        await _process_command(cmd, expr_mgr, pipeline, effects, mock_display)

    # Final state verification
    assert expr_mgr.current_name == "angry"
    assert mock_display.brightness == 30
    assert expr_mgr.blink_enabled is True  # toggled once
    assert pipeline.active_effect_name is None  # cleared
    assert mock_display.last_image is not None
    assert mock_display.last_image.getpixel((0, 0)) == (255, 0, 0)


@pytest.mark.asyncio
async def test_set_nonexistent_expression_is_no_op(mock_display):
    """SET_EXPRESSION with an unknown name does not change state."""
    store, _ = _make_store("happy")
    pipeline = RenderPipeline(mock_display)
    expr_mgr = ExpressionManager(pipeline, store)
    input_mgr = InputManager()
    effects = _make_effects()

    # Set initial expression
    expr_mgr.set_expression("happy")
    assert expr_mgr.current_name == "happy"

    # Attempt to set a non-existent expression
    await input_mgr.put(Command(event=InputEvent.SET_EXPRESSION, value="nonexistent"))
    cmd = await input_mgr.get()
    await _process_command(cmd, expr_mgr, pipeline, effects, mock_display)

    # State should remain unchanged
    assert expr_mgr.current_name == "happy"
    assert mock_display.last_image.getpixel((0, 0)) == (0, 255, 0)
