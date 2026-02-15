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


@dataclass(frozen=True)
class Command:
    event: InputEvent
    value: str | int | None = None
