from __future__ import annotations

from protogen.display.base import DisplayBase
from protogen.expression import Expression, ExpressionType


class ExpressionManager:
    def __init__(self, display: DisplayBase, expressions: dict[str, Expression]) -> None:
        self._display = display
        self._expressions = expressions
        self._names = sorted(expressions.keys())
        self._current_index = 0
        self.current_name: str | None = None

    @property
    def expression_names(self) -> list[str]:
        return list(self._names)

    def set_expression(self, name: str) -> None:
        if name not in self._expressions:
            return
        expr = self._expressions[name]
        self.current_name = name
        self._current_index = self._names.index(name)

        if expr.type == ExpressionType.STATIC and expr.image:
            self._display.show_image(expr.image)

    def next_expression(self) -> None:
        self._current_index = (self._current_index + 1) % len(self._names)
        self.set_expression(self._names[self._current_index])

    def prev_expression(self) -> None:
        self._current_index = (self._current_index - 1) % len(self._names)
        self.set_expression(self._names[self._current_index])
