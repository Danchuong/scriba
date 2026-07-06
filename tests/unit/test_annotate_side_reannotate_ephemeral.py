r"""End-to-end wiring for two formerly parsed-but-inert decoration keys.

Both keys were *accepted but dropped* — the E1123 param-guard let them through
(``investigations/hunt-param-guard.md`` ⚠️2) yet no handler threaded them, so
author intent was silently discarded one layer down. This module pins the real
behavior they now drive:

* ``\annotate{...}{side=above|below|left|right}`` — a smart-label half-plane
  preference (§5.8). Threaded onto ``AnnotateCommand`` → ``AnnotationEntry`` →
  the emit dict ``ann["side"]`` that ``_svg_helpers`` already consumes
  (``ann.get("side") or ann.get("position")``). An unknown value raises the
  annotation-placement enum error **E1112** (shared with ``position``); the
  honored set is exactly the four half-planes the scorer acts on — note it
  *excludes* ``inside`` (a valid ``position`` but a no-op side).
* ``\reannotate{...}{ephemeral=true}`` — a one-frame recolor that reverts to
  the prior colour at the next ``\step`` (§5.9), mirroring annotation ephemeral
  clearing. Absent, ``\reannotate`` persists exactly as before.

Note on the behavioral pin: ``side`` is a *soft* smart-label hint consumed only
under collision (``_svg_helpers._emit_label_and_pill``'s ``if placed_labels is
not None`` scorer). Plain annotations place by the hard ``position`` path and
never read ``side``; on the corpus arrow annotation the scorer's argmin does not
flip in the open board — so ``side`` produces no observable pixel delta in any
reachable config. The genuine wiring — "``ann.get("side")`` now returns the
author's value instead of ``None``" — is therefore pinned at the emit-dict
consumer seam it reaches, plus the parser/scene fields it threads through.
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.ast import AnnotateCommand, ReannotateCommand
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.renderer import AnimationRenderer
from scriba.animation.scene import SceneState
from scriba.core.context import RenderContext
from scriba.core.errors import ValidationError


# --------------------------------------------------------------------------- #
# Harness
# --------------------------------------------------------------------------- #


def _ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        metadata={"output_mode": "interactive"},
        warnings_collector=None,
    )


def _render(body: str) -> str:
    renderer = AnimationRenderer()
    source = '\\begin{animation}[id="wire"]\n' + body + "\n\\end{animation}"
    blocks = renderer.detect(source)
    assert len(blocks) == 1
    return renderer.render_block(blocks[0], _ctx()).html


def _drive(source: str) -> list:
    """Parse a full animation and return one snapshot per ``\\step`` frame."""
    ir = SceneParser().parse(source)
    state = SceneState()
    state.apply_prelude(
        shapes=ir.shapes,
        prelude_commands=ir.prelude_commands,
        prelude_compute=ir.prelude_compute,
    )
    return [state.apply_frame(f) for f in ir.frames]


# The corpus §5.8 demo: an arrow annotation whose pill routes through the smart-
# label emitter that reads ``ann.get("side")``.
_SIDE_ARROW_BODY = (
    "\\shape{dp}{DPTable}{rows=3, cols=3}\n\\step\n"
    '\\annotate{dp.cell[1][2]}{label="+5", arrow_from="dp.cell[1][0]", '
    'color=good, side=below}\n\\narrate{x}\n'
)


# --------------------------------------------------------------------------- #
# FEATURE 1 — \annotate side= : threaded onto the command
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestAnnotateSideThreaded:
    def test_side_parsed_onto_command(self) -> None:
        ir = SceneParser().parse(
            "\\shape{dp}{DPTable}{rows=3, cols=3}\n\\step\n"
            '\\annotate{dp.cell[1][1]}{label="x", side=below}\n'
        )
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, AnnotateCommand)
        assert getattr(cmd, "side", None) == "below"

    def test_side_survives_onto_scene_entry(self) -> None:
        (snap,) = _drive(
            "\\shape{dp}{DPTable}{rows=3, cols=3}\n\\step\n"
            '\\annotate{dp.cell[1][1]}{label="x", side=below}\n'
        )
        assert snap.annotations[0].side == "below"

    def test_side_reaches_emit_dict_consumer(self, monkeypatch) -> None:
        """The exact anti-swallow guarantee: ``ann.get("side")`` in the smart-
        label emitter now returns the author's value instead of ``None`` (it was
        dropped at the parser before). Pixels may not move — the hint is soft —
        but the value provably reaches its one consumer."""
        import scriba.animation.primitives._svg_helpers as helpers

        seen: list[dict] = []
        orig = helpers._emit_label_and_pill

        def _spy(*args, **kwargs):
            for candidate in (*args, *kwargs.values()):
                if isinstance(candidate, dict) and "target" in candidate:
                    seen.append(dict(candidate))
                    break
            return orig(*args, **kwargs)

        monkeypatch.setattr(helpers, "_emit_label_and_pill", _spy)
        _render(_SIDE_ARROW_BODY)

        assert seen, "arrow annotation did not reach the smart-label emitter"
        assert all(d.get("side") == "below" for d in seen)


# --------------------------------------------------------------------------- #
# FEATURE 1 — \annotate side= : enum validation (E1112, honored 4 only)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestAnnotateSideValidation:
    def test_unknown_side_raises_e1112_with_hint(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _render(
                "\\shape{dp}{DPTable}{rows=3, cols=3}\n\\step\n"
                '\\annotate{dp.cell[1][1]}{label="x", side=belw}\n'
            )
        assert exc.value.code == "E1112"
        msg = str(exc.value)
        assert "did you mean" in msg.lower()
        assert "below" in msg  # fuzzy-closest honored half-plane

    def test_unknown_side_with_no_close_match_still_raises(self) -> None:
        # A value with no fuzzy neighbour still raises (just without a hint).
        with pytest.raises(ValidationError) as exc:
            _render(
                "\\shape{dp}{DPTable}{rows=3, cols=3}\n\\step\n"
                '\\annotate{dp.cell[1][1]}{label="x", side=diagonal}\n'
            )
        assert exc.value.code == "E1112"

    def test_inside_is_a_valid_position_but_not_a_valid_side(self) -> None:
        """``inside`` is honored for ``position`` but the scorer ignores it as a
        side; ``side=inside`` must be rejected, not silently inert."""
        # position=inside is accepted...
        assert _render(
            "\\shape{dp}{DPTable}{rows=3, cols=3}\n\\step\n"
            '\\annotate{dp.cell[1][1]}{label="x", position=inside}\n\\narrate{x}\n'
        )
        # ...but side=inside is not one of the four honored half-planes.
        with pytest.raises(ValidationError) as exc:
            _render(
                "\\shape{dp}{DPTable}{rows=3, cols=3}\n\\step\n"
                '\\annotate{dp.cell[1][1]}{label="x", side=inside}\n'
            )
        assert exc.value.code == "E1112"

    @pytest.mark.parametrize("side", ["above", "below", "left", "right"])
    def test_all_four_honored_sides_render(self, side: str) -> None:
        assert _render(
            "\\shape{dp}{DPTable}{rows=3, cols=3}\n\\step\n"
            f'\\annotate{{dp.cell[1][1]}}{{label="x", side={side}}}\n\\narrate{{x}}\n'
        )


# --------------------------------------------------------------------------- #
# FEATURE 2 — \reannotate ephemeral= : one-frame recolor that reverts
# --------------------------------------------------------------------------- #

_EPHEMERAL_SRC = (
    "\\shape{dp}{DPTable}{rows=3, cols=3}\n"
    "\\step\n"
    '\\annotate{dp.cell[1][1]}{label="orig", color=info}\n'
    "\\step\n"
    "\\reannotate{dp.cell[1][1]}{color=warn, ephemeral=true}\n"
    "\\step\n"
    "\\narrate{next}\n"
)

_PERSIST_SRC = (
    "\\shape{dp}{DPTable}{rows=3, cols=3}\n"
    "\\step\n"
    '\\annotate{dp.cell[1][1]}{label="orig", color=info}\n'
    "\\step\n"
    "\\reannotate{dp.cell[1][1]}{color=warn}\n"
    "\\step\n"
    "\\narrate{next}\n"
)


@pytest.mark.unit
class TestReannotateEphemeral:
    def test_ephemeral_parsed_onto_command(self) -> None:
        ir = SceneParser().parse(
            "\\shape{a}{Array}{values=[1,2,3]}\n\\step\n"
            '\\annotate{a.cell[0]}{label=x}\n'
            "\\reannotate{a.cell[0]}{color=warn, ephemeral=true}\n"
        )
        cmd = ir.frames[0].commands[1]
        assert isinstance(cmd, ReannotateCommand)
        assert getattr(cmd, "ephemeral", False) is True

    def test_ephemeral_recolor_reverts_next_step(self) -> None:
        s1, s2, s3 = _drive(_EPHEMERAL_SRC)
        assert s1.annotations[0].color == "info"          # original
        assert s2.annotations[0].color == "warn"          # recolored THIS frame
        # reverts NEXT frame — the annotation itself survives (not removed).
        assert len(s3.annotations) == 1
        assert s3.annotations[0].color == "info"

    def test_non_ephemeral_reannotate_persists(self) -> None:
        """Regression guard: without ``ephemeral`` the recolor sticks (today's
        behavior, byte-identical)."""
        s1, s2, s3 = _drive(_PERSIST_SRC)
        assert s1.annotations[0].color == "info"
        assert s2.annotations[0].color == "warn"
        assert s3.annotations[0].color == "warn"          # persists
