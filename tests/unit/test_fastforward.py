"""Tests for \\fastforward parsing, validation, and expansion."""

from __future__ import annotations

import warnings

import pytest

# Import directly from submodules to avoid pulling in the full
# AnimationRenderer (which requires primitives, emitter, etc.).
from scriba.animation.parser.ast import FastForwardCommand, FrameIR  # noqa: F401
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.extensions.fastforward import expand_fastforward
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(source: str):
    """Parse animation source and return the AnimationIR."""
    return SceneParser().parse(source)


# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------


class TestFastForwardParsing:
    """Parse valid \\fastforward commands."""

    def test_parse_basic(self):
        """Parse \\fastforward{1000}{sample_every=100, seed=42}."""
        ir = _parse(
            "\\step\n"
            "\\narrate{init}\n"
            "\\fastforward{1000}{sample_every=100, seed=42}\n"
            "\\step\n"
            "\\narrate{done}\n"
        )
        # 1 manual frame + 10 ff frames + 1 manual frame = 12
        assert len(ir.frames) == 12

    def test_parse_with_label(self):
        """Parse with optional label parameter."""
        ir = _parse(
            "\\step\n"
            "\\narrate{init}\n"
            '\\fastforward{500}{sample_every=100, seed=7, label="sa"}\n'
            "\\step\n"
            "\\narrate{done}\n"
        )
        # 1 + 5 + 1 = 7
        assert len(ir.frames) == 7

    def test_parse_with_narrate_template(self):
        """Parse with optional \\narrate{...} template after fastforward."""
        ir = _parse(
            "\\step\n"
            "\\narrate{init}\n"
            "\\fastforward{200}{sample_every=100, seed=1}\n"
            "\\narrate{Iter ${iter}: done.}\n"
            "\\step\n"
            "\\narrate{final}\n"
        )
        # 1 + 2 + 1 = 4
        assert len(ir.frames) == 4
        # Frames 2 and 3 (index 1,2) are the ff frames
        assert ir.frames[1].narrate_body == "Iter ${iter}: done."
        assert ir.frames[2].narrate_body == "Iter ${iter}: done."

    def test_default_narrate_when_no_template(self):
        """When no \\narrate follows, use auto-generated narration."""
        ir = _parse(
            "\\step\n"
            "\\narrate{init}\n"
            "\\fastforward{300}{sample_every=100, seed=1}\n"
            "\\step\n"
            "\\narrate{final}\n"
        )
        # ff frames are index 1,2,3
        assert ir.frames[1].narrate_body == "Iteration 100 / 300 (frame 1)."
        assert ir.frames[2].narrate_body == "Iteration 200 / 300 (frame 2)."
        assert ir.frames[3].narrate_body == "Iteration 300 / 300 (frame 3)."


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------


class TestFastForwardErrors:
    """Error codes E1340-E1348."""

    def test_e1340_total_iters_exceeds_max(self):
        """E1340: total_iters > 10^6."""
        with pytest.raises(ValidationError, match="E1340"):
            _parse(
                "\\step\n"
                "\\narrate{init}\n"
                "\\fastforward{2000000}{sample_every=100000, seed=1}\n"
            )

    def test_e1341_too_many_frames(self):
        """E1341: N > 100 frames."""
        with pytest.raises(ValidationError, match="E1341"):
            _parse(
                "\\step\n"
                "\\narrate{init}\n"
                "\\fastforward{10100}{sample_every=100, seed=1}\n"
            )

    def test_e1342_missing_seed(self):
        """E1342: seed parameter missing."""
        with pytest.raises(ValidationError, match="E1342"):
            _parse(
                "\\step\n"
                "\\narrate{init}\n"
                "\\fastforward{1000}{sample_every=100}\n"
            )

    def test_e1345_fastforward_in_prelude(self):
        """E1345: \\fastforward before first \\step (in prelude)."""
        with pytest.raises(ValidationError, match="E1345"):
            _parse("\\fastforward{1000}{sample_every=100, seed=42}\n")

    def test_e1346_total_iters_zero(self):
        """E1346: total_iters <= 0."""
        with pytest.raises(ValidationError, match="E1346"):
            _parse(
                "\\step\n"
                "\\narrate{init}\n"
                "\\fastforward{0}{sample_every=1, seed=1}\n"
            )

    def test_e1346_total_iters_negative(self):
        """E1346: total_iters negative."""
        with pytest.raises(ValidationError, match="E1346"):
            _parse(
                "\\step\n"
                "\\narrate{init}\n"
                "\\fastforward{-5}{sample_every=1, seed=1}\n"
            )

    def test_e1347_sample_every_zero(self):
        """E1347: sample_every <= 0."""
        with pytest.raises(ValidationError, match="E1347"):
            _parse(
                "\\step\n"
                "\\narrate{init}\n"
                "\\fastforward{1000}{sample_every=0, seed=1}\n"
            )

    def test_e1347_sample_every_negative(self):
        """E1347: sample_every negative."""
        with pytest.raises(ValidationError, match="E1347"):
            _parse(
                "\\step\n"
                "\\narrate{init}\n"
                "\\fastforward{1000}{sample_every=-5, seed=1}\n"
            )

    def test_e1348_single_frame_warning(self):
        """E1348: N=1 emits a warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _parse(
                "\\step\n"
                "\\narrate{init}\n"
                "\\fastforward{100}{sample_every=100, seed=1}\n"
                "\\step\n"
                "\\narrate{done}\n"
            )
            assert any("E1348" in str(warning.message) for warning in w)


# ---------------------------------------------------------------------------
# Expansion tests
# ---------------------------------------------------------------------------


class TestFastForwardExpansion:
    """expand_fastforward() correctness."""

    def test_expand_produces_correct_count(self):
        """N = floor(total_iters / sample_every) frames."""
        cmd = FastForwardCommand(
            line=1, col=1,
            total_iters=1000, sample_every=100, seed=42,
        )
        frames = expand_fastforward(cmd)
        assert len(frames) == 10

    def test_expand_frame_numbering(self):
        """Frame narrate_body contains correct iteration numbers."""
        cmd = FastForwardCommand(
            line=1, col=1,
            total_iters=500, sample_every=100, seed=42,
        )
        frames = expand_fastforward(cmd)
        assert len(frames) == 5
        assert "Iteration 100" in frames[0].narrate_body
        assert "Iteration 500" in frames[4].narrate_body
        assert "(frame 1)" in frames[0].narrate_body
        assert "(frame 5)" in frames[4].narrate_body

    def test_expand_custom_narrate_template(self):
        """Custom narrate template is propagated to all frames."""
        cmd = FastForwardCommand(
            line=1, col=1,
            total_iters=300, sample_every=100, seed=42,
            narrate_template="Step ${iter} of ${total_iters}.",
        )
        frames = expand_fastforward(cmd)
        assert len(frames) == 3
        for f in frames:
            assert f.narrate_body == "Step ${iter} of ${total_iters}."

    def test_expand_empty_commands(self):
        """All expanded frames have empty command tuples."""
        cmd = FastForwardCommand(
            line=5, col=1,
            total_iters=200, sample_every=100, seed=1,
        )
        frames = expand_fastforward(cmd)
        for f in frames:
            assert f.commands == ()
            assert f.compute == ()

    def test_mixed_manual_and_ff(self):
        """Manual step + fastforward + manual step: contiguous frames."""
        ir = _parse(
            "\\step\n"
            "\\narrate{Initial state.}\n"
            "\\fastforward{10000}{sample_every=500, seed=42}\n"
            "\\step\n"
            "\\narrate{Converged.}\n"
        )
        # 1 manual + 20 ff + 1 manual = 22
        assert len(ir.frames) == 22
        assert ir.frames[0].narrate_body == "Initial state."
        assert ir.frames[-1].narrate_body == "Converged."
        # FF frames in the middle
        assert "Iteration 500 / 10000 (frame 1)." == ir.frames[1].narrate_body
        assert "Iteration 10000 / 10000 (frame 20)." == ir.frames[20].narrate_body
