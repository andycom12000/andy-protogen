from pathlib import Path

from protogen.expression import Expression, ExpressionType, load_expressions


def test_expression_static(tmp_path):
    from PIL import Image

    base_dir = tmp_path / "base"
    base_dir.mkdir()
    img = Image.new("RGB", (128, 32), (0, 255, 0))
    img.save(base_dir / "happy.png")

    manifest = {
        "expressions": {
            "happy": {
                "type": "static",
                "file": "base/happy.png",
            }
        },
        "default": "happy",
    }
    import json
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    expressions = load_expressions(tmp_path)
    assert "happy" in expressions
    assert expressions["happy"].type == ExpressionType.STATIC
    assert expressions["happy"].image is not None
    assert expressions["happy"].image.size == (128, 32)


def test_expression_animation(tmp_path):
    from PIL import Image

    anim_dir = tmp_path / "animations" / "blink"
    anim_dir.mkdir(parents=True)
    for i in range(3):
        img = Image.new("RGB", (128, 32), (i * 80, 0, 0))
        img.save(anim_dir / f"frame_{i:02d}.png")

    manifest = {
        "expressions": {
            "blink": {
                "type": "animation",
                "frames_dir": "animations/blink",
                "fps": 12,
                "loop": False,
            }
        },
        "default": "blink",
    }
    import json
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    expressions = load_expressions(tmp_path)
    assert "blink" in expressions
    assert expressions["blink"].type == ExpressionType.ANIMATION
    assert len(expressions["blink"].frames) == 3
