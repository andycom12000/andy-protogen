from __future__ import annotations

import io
import logging

from PIL import Image

from protogen.expression import Expression, ExpressionType

logger = logging.getLogger(__name__)


class ExpressionStore:
    """Expression data store — loading, querying, and index management."""

    def __init__(self, expressions: dict[str, Expression]) -> None:
        self._expressions = expressions
        self._names = sorted(
            name for name, expr in expressions.items() if not expr.hidden
        )

    @property
    def names(self) -> list[str]:
        return list(self._names)

    def get(self, name: str) -> Expression | None:
        return self._expressions.get(name)

    def get_thumbnail(self, name: str) -> bytes | None:
        """Return PNG bytes for the expression's preview image."""
        expr = self._expressions.get(name)
        if expr is None:
            return None

        img = None
        if expr.type == ExpressionType.STATIC and expr.image:
            img = expr.image
        elif expr.type == ExpressionType.ANIMATION and expr.frames:
            img = expr.frames[0]

        if img is None:
            return None

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
