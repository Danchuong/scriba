"""Tests for scriba.animation.detector — ~12 cases."""

from __future__ import annotations

import pytest

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.errors import NestedAnimationError, UnclosedAnimationError


class TestHappyPath:
    """Basic detection scenarios."""

    def test_single_animation_block(self) -> None:
        source = r"\begin{animation}" "\nsome content\n" r"\end{animation}"
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 1
        assert blocks[0].kind == "animation"
        assert blocks[0].start == 0
        assert blocks[0].end == len(source)
        assert blocks[0].raw == source

    def test_multiple_animation_blocks(self) -> None:
        a = r"\begin{animation}" "\nfirst\n" r"\end{animation}"
        b = r"\begin{animation}" "\nsecond\n" r"\end{animation}"
        source = a + "\n\nSome text in between.\n\n" + b
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 2
        assert "first" in blocks[0].raw
        assert "second" in blocks[1].raw

    def test_with_options(self) -> None:
        source = r'\begin{animation}[id=foo, label="bar"]' "\ncontent\n" r"\end{animation}"
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 1
        assert blocks[0].metadata is not None
        assert blocks[0].metadata["options_raw"] == 'id=foo, label="bar"'

    def test_options_only_id(self) -> None:
        source = r"\begin{animation}[id=my-scene]" "\ncontent\n" r"\end{animation}"
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 1
        assert blocks[0].metadata["options_raw"] == "id=my-scene"

    def test_empty_options(self) -> None:
        source = r"\begin{animation}[]" "\ncontent\n" r"\end{animation}"
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 1
        # Empty brackets → options_raw is None
        assert blocks[0].metadata["options_raw"] is None


class TestEdgeCases:
    """Edge and error cases."""

    def test_trailing_text_on_begin_line(self) -> None:
        source = r"\begin{animation}[id=x] % trailing comment" "\ncontent\n" r"\end{animation}"
        # The regex only captures up to the ], trailing text is part of raw
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 1
        assert "trailing comment" in blocks[0].raw

    def test_nested_begin_raises(self) -> None:
        source = (
            r"\begin{animation}" "\n"
            r"\begin{animation}" "\n"
            r"\end{animation}" "\n"
            r"\end{animation}"
        )
        with pytest.raises(NestedAnimationError) as exc_info:
            detect_animation_blocks(source)
        assert "E1003" in str(exc_info.value)

    def test_unclosed_environment(self) -> None:
        source = r"\begin{animation}" "\nno closing tag"
        with pytest.raises(UnclosedAnimationError) as exc_info:
            detect_animation_blocks(source)
        assert "E1001" in str(exc_info.value)

    def test_inside_lstlisting_not_matched(self) -> None:
        source = (
            r"\begin{lstlisting}" "\n"
            r"\begin{animation}" "\n"
            r"\end{animation}" "\n"
            r"\end{lstlisting}"
        )
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 0

    def test_empty_animation(self) -> None:
        source = r"\begin{animation}" r"\end{animation}"
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 1
        assert blocks[0].raw == source

    def test_no_animation_in_source(self) -> None:
        source = "Just some plain text with no environments."
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 0

    def test_block_offsets_correct(self) -> None:
        prefix = "Some prefix text.\n"
        animation = r"\begin{animation}" "\nbody\n" r"\end{animation}"
        source = prefix + animation
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 1
        assert blocks[0].start == len(prefix)
        assert blocks[0].end == len(source)
        assert source[blocks[0].start : blocks[0].end] == animation
