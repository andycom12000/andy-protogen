from dataclasses import dataclass
from enum import Enum


class InputEvent(Enum):
    SET_EXPRESSION = "set"
    SET_BRIGHTNESS = "brightness"
    TOGGLE_ANIMATION = "toggle_anim"
    TOGGLE_BLINK = "toggle_blink"


@dataclass(frozen=True)
class Command:
    event: InputEvent
    value: str | int | None = None
