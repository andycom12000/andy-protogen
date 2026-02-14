from dataclasses import dataclass
from enum import Enum


class InputEvent(Enum):
    NEXT_EXPRESSION = "next"
    PREV_EXPRESSION = "prev"
    SET_EXPRESSION = "set"
    SET_BRIGHTNESS = "brightness"
    TOGGLE_ANIMATION = "toggle_anim"


@dataclass(frozen=True)
class Command:
    event: InputEvent
    value: str | int | None = None
