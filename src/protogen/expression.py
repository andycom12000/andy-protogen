from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PIL import Image


class ExpressionType(Enum):
    STATIC = "static"
    ANIMATION = "animation"


@dataclass
class Expression:
    name: str
    type: ExpressionType
    image: Image.Image | None = None
    frames: list[Image.Image] = field(default_factory=list)
    fps: int = 12
    loop: bool = True
    idle_animation: str | None = None
    next_expression: str | None = None


def load_expressions(expressions_dir: str | Path) -> dict[str, Expression]:
    expressions_dir = Path(expressions_dir)
    manifest_path = expressions_dir / "manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    result: dict[str, Expression] = {}
    for name, data in manifest["expressions"].items():
        expr_type = ExpressionType(data["type"])

        if expr_type == ExpressionType.STATIC:
            img_path = expressions_dir / data["file"]
            image = Image.open(img_path).convert("RGB")
            result[name] = Expression(
                name=name,
                type=expr_type,
                image=image,
                idle_animation=data.get("idle_animation"),
            )
        elif expr_type == ExpressionType.ANIMATION:
            frames_dir = expressions_dir / data["frames_dir"]
            frame_files = sorted(frames_dir.glob("frame_*.png"))
            frames = [Image.open(f).convert("RGB") for f in frame_files]
            result[name] = Expression(
                name=name,
                type=expr_type,
                frames=frames,
                fps=data.get("fps", 12),
                loop=data.get("loop", True),
                next_expression=data.get("next"),
            )

    return result
