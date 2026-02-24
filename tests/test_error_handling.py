"""Tests for error handling in expression and effect loading."""

import json

import pytest
from PIL import Image

from protogen.expression import load_effects, load_expressions


def _write_manifest(directory, manifest_data):
    """Helper to write manifest.json to the given directory."""
    with open(directory / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)


def _create_valid_png(path):
    """Helper to create a valid 1x1 PNG at the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1, 1), (255, 0, 0))
    img.save(path)


# ---------------------------------------------------------------------------
# load_expressions error paths
# ---------------------------------------------------------------------------


class TestLoadExpressionsInvalidManifestJson:
    """Invalid JSON in manifest.json raises JSONDecodeError (uncaught)."""

    def test_invalid_json_raises(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text("{invalid json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_expressions(tmp_path)


class TestLoadExpressionsMissingTypeKey:
    """Expression entry with no 'type' key is skipped."""

    def test_missing_type_key_skipped(self, tmp_path):
        _write_manifest(tmp_path, {
            "expressions": {
                "no_type": {"file": "some.png"},
            },
        })

        result = load_expressions(tmp_path)
        assert "no_type" not in result
        assert len(result) == 0


class TestLoadExpressionsInvalidType:
    """Expression entry with unknown type value is skipped."""

    def test_invalid_type_skipped(self, tmp_path):
        _write_manifest(tmp_path, {
            "expressions": {
                "bad_type": {"type": "hologram"},
            },
        })

        result = load_expressions(tmp_path)
        assert "bad_type" not in result
        assert len(result) == 0


class TestLoadExpressionsStaticMissingFileKey:
    """Static expression with no 'file' key is skipped."""

    def test_missing_file_key_skipped(self, tmp_path):
        _write_manifest(tmp_path, {
            "expressions": {
                "no_file": {"type": "static"},
            },
        })

        result = load_expressions(tmp_path)
        assert "no_file" not in result
        assert len(result) == 0


class TestLoadExpressionsStaticMissingFile:
    """Static expression referencing a non-existent file is skipped."""

    def test_nonexistent_file_skipped(self, tmp_path):
        _write_manifest(tmp_path, {
            "expressions": {
                "ghost": {"type": "static", "file": "does_not_exist.png"},
            },
        })

        result = load_expressions(tmp_path)
        assert "ghost" not in result
        assert len(result) == 0


class TestLoadExpressionsAnimationMissingFramesDirKey:
    """Animation expression with no 'frames_dir' key is skipped."""

    def test_missing_frames_dir_key_skipped(self, tmp_path):
        _write_manifest(tmp_path, {
            "expressions": {
                "no_frames": {"type": "animation"},
            },
        })

        result = load_expressions(tmp_path)
        assert "no_frames" not in result
        assert len(result) == 0


class TestLoadExpressionsAnimationNonexistentFramesDir:
    """Animation expression with non-existent frames_dir is skipped."""

    def test_nonexistent_frames_dir_skipped(self, tmp_path):
        _write_manifest(tmp_path, {
            "expressions": {
                "missing_dir": {
                    "type": "animation",
                    "frames_dir": "nonexistent_dir",
                },
            },
        })

        result = load_expressions(tmp_path)
        assert "missing_dir" not in result
        assert len(result) == 0


class TestLoadExpressionsInvalidSkippedValidLoaded:
    """Invalid entries are skipped while valid entries still load correctly."""

    def test_mixed_valid_and_invalid(self, tmp_path):
        # Create valid static image
        _create_valid_png(tmp_path / "images" / "good.png")

        # Create valid animation frames
        anim_dir = tmp_path / "anim" / "wave"
        anim_dir.mkdir(parents=True)
        for i in range(2):
            img = Image.new("RGB", (1, 1), (0, i * 128, 0))
            img.save(anim_dir / f"frame_{i:02d}.png")

        _write_manifest(tmp_path, {
            "expressions": {
                "valid_static": {
                    "type": "static",
                    "file": "images/good.png",
                },
                "bad_no_type": {
                    "file": "images/good.png",
                },
                "bad_type": {
                    "type": "unknown",
                },
                "bad_no_file": {
                    "type": "static",
                },
                "bad_missing_png": {
                    "type": "static",
                    "file": "images/nope.png",
                },
                "valid_anim": {
                    "type": "animation",
                    "frames_dir": "anim/wave",
                    "fps": 10,
                },
                "bad_no_frames_dir": {
                    "type": "animation",
                },
                "bad_frames_dir_missing": {
                    "type": "animation",
                    "frames_dir": "anim/gone",
                },
            },
        })

        result = load_expressions(tmp_path)

        # Valid entries loaded
        assert "valid_static" in result
        assert result["valid_static"].image is not None
        assert "valid_anim" in result
        assert len(result["valid_anim"].frames) == 2

        # All invalid entries skipped
        assert "bad_no_type" not in result
        assert "bad_type" not in result
        assert "bad_no_file" not in result
        assert "bad_missing_png" not in result
        assert "bad_no_frames_dir" not in result
        assert "bad_frames_dir_missing" not in result

        assert len(result) == 2


class TestLoadExpressionsEmptyManifest:
    """Manifest with no 'expressions' key returns empty dict."""

    def test_empty_manifest(self, tmp_path):
        _write_manifest(tmp_path, {})

        result = load_expressions(tmp_path)
        assert result == {}


# ---------------------------------------------------------------------------
# load_effects error paths
# ---------------------------------------------------------------------------


class TestLoadEffectsMissingGeneratorKey:
    """Effect entry without 'generator' key raises KeyError (uncaught)."""

    def test_missing_generator_raises(self, tmp_path):
        _write_manifest(tmp_path, {
            "effects": {
                "bad_effect": {"params": {"color": "red"}},
            },
        })

        with pytest.raises(KeyError):
            load_effects(tmp_path)


class TestLoadEffectsValidEntry:
    """Valid effect entries load correctly (sanity check)."""

    def test_valid_effect_loads(self, tmp_path):
        _write_manifest(tmp_path, {
            "effects": {
                "sparkle": {
                    "generator": "sparkle_gen",
                    "params": {"intensity": 0.5},
                    "fps": 30,
                },
            },
        })

        result = load_effects(tmp_path)
        assert "sparkle" in result
        assert result["sparkle"].generator_name == "sparkle_gen"
        assert result["sparkle"].generator_params == {"intensity": 0.5}
        assert result["sparkle"].fps == 30


class TestLoadEffectsEmptyManifest:
    """Manifest with no 'effects' key returns empty dict."""

    def test_empty_effects(self, tmp_path):
        _write_manifest(tmp_path, {})

        result = load_effects(tmp_path)
        assert result == {}


class TestLoadEffectsDefaults:
    """Effect entries use default values for optional keys."""

    def test_defaults_applied(self, tmp_path):
        _write_manifest(tmp_path, {
            "effects": {
                "minimal": {
                    "generator": "test_gen",
                },
            },
        })

        result = load_effects(tmp_path)
        assert result["minimal"].generator_params == {}
        assert result["minimal"].fps == 20
