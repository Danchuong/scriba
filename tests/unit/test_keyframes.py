"""Tests for the CSS @keyframes preset system."""

from __future__ import annotations

import pytest

from scriba.animation.extensions.keyframes import (
    KEYFRAME_PRESETS,
    generate_keyframe_styles,
    get_animation_class,
)


class TestGenerateSingle:
    def test_single_preset_emits_style_block(self) -> None:
        result = generate_keyframe_styles("scene1", {"rotate"})
        assert "<style>" in result
        assert "</style>" in result
        assert "@keyframes scene1-rotate" in result

    def test_pulse_preset(self) -> None:
        result = generate_keyframe_styles("s1", {"pulse"})
        assert "@keyframes s1-pulse" in result
        assert "scale(1.15)" in result


class TestGenerateMultiple:
    def test_two_presets_both_present(self) -> None:
        result = generate_keyframe_styles("sc", {"rotate", "pulse"})
        assert "@keyframes sc-rotate" in result
        assert "@keyframes sc-pulse" in result

    def test_output_is_deterministic(self) -> None:
        """Presets are sorted by name for stable output."""
        r1 = generate_keyframe_styles("x", {"rotate", "pulse", "trail"})
        r2 = generate_keyframe_styles("x", {"trail", "rotate", "pulse"})
        assert r1 == r2


class TestScoping:
    def test_name_includes_scene_id(self) -> None:
        result = generate_keyframe_styles("my-scene", {"fade-loop"})
        assert "@keyframes my-scene-fade-loop" in result

    def test_different_scenes_produce_different_names(self) -> None:
        r1 = generate_keyframe_styles("a", {"rotate"})
        r2 = generate_keyframe_styles("b", {"rotate"})
        assert "a-rotate" in r1
        assert "b-rotate" in r2
        assert "a-rotate" not in r2


class TestUnknownPreset:
    def test_unknown_preset_ignored(self) -> None:
        result = generate_keyframe_styles("s1", {"nonexistent"})
        assert result == ""

    def test_mixed_known_unknown(self) -> None:
        result = generate_keyframe_styles("s1", {"rotate", "nonexistent"})
        assert "@keyframes s1-rotate" in result
        assert "nonexistent" not in result


class TestEmptyInput:
    def test_empty_set_returns_empty_string(self) -> None:
        assert generate_keyframe_styles("s1", set()) == ""


class TestAllPresets:
    def test_all_five_presets_valid(self) -> None:
        all_names = set(KEYFRAME_PRESETS.keys())
        assert all_names == {"rotate", "pulse", "orbit", "fade-loop", "trail"}
        result = generate_keyframe_styles("s", all_names)
        for name in all_names:
            assert f"@keyframes s-{name}" in result


class TestDeduplication:
    def test_set_naturally_deduplicates(self) -> None:
        """Sets can't hold duplicates, so this verifies the contract."""
        presets: set[str] = {"rotate", "rotate"}
        result = generate_keyframe_styles("s1", presets)
        assert result.count("@keyframes s1-rotate") == 1


class TestAnimationClass:
    def test_returns_expected_class(self) -> None:
        assert get_animation_class("s1", "pulse") == "scriba-anim-pulse"

    def test_class_is_independent_of_scene(self) -> None:
        assert get_animation_class("a", "rotate") == get_animation_class("b", "rotate")
