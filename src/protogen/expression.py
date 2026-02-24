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
    for name, data in manifest.get("expressions", {}).items():
        try:
            expr_type = ExpressionType(data["type"])
        except (KeyError, ValueError):
            continue

        if expr_type == ExpressionType.STATIC:
            file_path = data.get("file")
            if file_path is None:
                continue
            img_path = expressions_dir / file_path
            if not img_path.exists():
                continue
            image = Image.open(img_path).convert("RGB")
            result[name] = Expression(
                name=name,
                type=expr_type,
                image=image,
                idle_animation=data.get("idle_animation"),
            )
        elif expr_type == ExpressionType.ANIMATION:
            frames_dir_name = data.get("frames_dir")
            if frames_dir_name is None:
                continue
            frames_dir = expressions_dir / frames_dir_name
            if not frames_dir.exists():
                continue
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


@dataclass
class Effect:
    name: str
    generator_name: str
    generator_params: dict = field(default_factory=dict)
    fps: int = 20


def load_effects(expressions_dir: str | Path) -> dict[str, Effect]:
    expressions_dir = Path(expressions_dir)
    manifest_path = expressions_dir / "manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    result: dict[str, Effect] = {}
    for name, data in manifest.get("effects", {}).items():
        result[name] = Effect(
            name=name,
            generator_name=data["generator"],
            generator_params=data.get("params", {}),
            fps=data.get("fps", 20),
        )
    return result
