from dataclasses import dataclass
from enum import Enum


class InputEvent(Enum):
    SET_EXPRESSION = "set"
    SET_BRIGHTNESS = "brightness"
    TOGGLE_ANIMATION = "toggle_anim"
    TOGGLE_BLINK = "toggle_blink"
    SET_TEXT = "set_text"
    SET_EFFECT = "set_effect"
    CLEAR_EFFECT = "clear_effect"
    SET_EFFECT_PARAMS = "set_effect_params"


@dataclass(frozen=True)
class Command:
    event: InputEvent
    value: str | int | dict | None = None
