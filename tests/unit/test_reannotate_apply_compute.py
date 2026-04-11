"""Tests for ``\\reannotate``, ``\\apply`` and ``\\compute``.

These commands have thin coverage in the existing suite (16-H3/H5).
This module adds focused tests for:

* ``\\reannotate`` — verifies that annotation color/arrow_from is
  actually mutated on a pre-existing annotation.
* ``\\apply`` — primitive-agnostic value/label/extra-param behaviour.
* ``\\compute`` → ``${...}`` interpolation — verifies the bridge between
  compute bindings and selector interpolation.
"""

from __future__ import annotations

from typing import Any

import pytest

from scriba.animation.parser.ast import (
    AnnotateCommand,
    ApplyCommand,
    CellAccessor,
    ComputeCommand,
    FrameIR,
    InterpolationRef,
    ReannotateCommand,
    Selector,
    ShapeCommand,
)
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.scene import SceneState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(src: str):
    return SceneParser().parse(src)


def _shape(name: str, type_name: str = "array") -> ShapeCommand:
    return ShapeCommand(line=0, col=0, name=name, type_name=type_name, params={})


def _sel(target: str) -> Selector:
    return Selector(shape_name=target)


def _annotate(target: str, label: str, color: str = "info") -> AnnotateCommand:
    return AnnotateCommand(
        line=0,
        col=0,
        target=_sel(target),
        label=label,
        color=color,
    )


def _apply(
    target: str,
    value: str | None = None,
    label: str | None = None,
    **extra: Any,
) -> ApplyCommand:
    params: dict[str, Any] = {}
    if value is not None:
        params["value"] = value
    if label is not None:
        params["label"] = label
    params.update(extra)
    return ApplyCommand(line=0, col=0, target=_sel(target), params=params)


def _reannotate(
    target: str, color: str = "good", arrow_from: str | None = None,
) -> ReannotateCommand:
    return ReannotateCommand(
        target=_sel(target),
        color=color,
        arrow_from=arrow_from,
    )


def _frame(*commands: Any, compute: tuple = ()) -> FrameIR:
    return FrameIR(line=0, commands=tuple(commands), compute=compute)


class _MockStarlarkHost:
    """Eval a restricted subset of Python for compute blocks."""

    def eval(
        self,
        globals: dict[str, Any],
        source: str,
        *,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        ns = dict(globals)
        exec(  # noqa: S102 — test-only
            source,
            {"__builtins__": {"len": len, "range": range, "list": list}},
            ns,
        )
        return {k: v for k, v in ns.items() if k not in globals}


# ===========================================================================
# \reannotate
# ===========================================================================


class TestReannotateScene:
    """Scene-level mutation tests for ``\\reannotate``."""

    def test_reannotate_recolors_existing_annotation(self) -> None:
        """Annotate with color=info, then reannotate to color=good."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        state.apply_frame(_frame(_annotate("a.cell[0]", "note", color="info")))
        snap2 = state.apply_frame(
            _frame(_reannotate("a.cell[0]", color="good")),
        )
        assert len(snap2.annotations) == 1
        assert snap2.annotations[0].color == "good"

    def test_reannotate_does_not_touch_other_targets(self) -> None:
        """A targeted reannotate must leave other annotations alone."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        state.apply_frame(
            _frame(
                _annotate("a.cell[0]", "first", color="info"),
                _annotate("a.cell[1]", "second", color="info"),
            ),
        )
        snap = state.apply_frame(
            _frame(_reannotate("a.cell[0]", color="warn")),
        )
        assert len(snap.annotations) == 2
        colors_by_target = {a.target: a.color for a in snap.annotations}
        assert colors_by_target["a.cell[0]"] == "warn"
        assert colors_by_target["a.cell[1]"] == "info"

    def test_reannotate_with_arrow_from_filter(self) -> None:
        """``arrow_from`` narrows matching annotations to those with a source."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        # Create two annotations on the same target, only one with arrow_from.
        state.annotations = [
            # Use the internal structure directly to seed both variants.
        ]
        # Use the parser-produced command flow to get one annotation with arrow_from.
        with_arrow = AnnotateCommand(
            line=0,
            col=0,
            target=_sel("a.cell[0]"),
            label="with",
            color="info",
            arrow_from=_sel("a.cell[5]"),
        )
        without_arrow = _annotate("a.cell[0]", "without", color="info")
        state.apply_frame(_frame(with_arrow, without_arrow))

        # Reannotate only those with arrow_from=a.cell[5].
        snap = state.apply_frame(
            _frame(_reannotate("a.cell[0]", color="good", arrow_from="a.cell[5]")),
        )
        targets = [(a.text, a.color) for a in snap.annotations if a.target == "a.cell[0]"]
        # The one with arrow_from got recolored, the other kept "info".
        colors = {t: c for t, c in targets}
        assert colors["with"] == "good"
        assert colors["without"] == "info"

    def test_reannotate_no_matching_annotation_is_noop(self) -> None:
        """Reannotating a target with no existing annotation does not crash."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))
        snap = state.apply_frame(_frame(_reannotate("a.cell[7]", color="warn")))
        assert len(snap.annotations) == 0


class TestReannotateParser:
    """Parser-level tests for ``\\reannotate``."""

    def test_reannotate_parses_with_color(self) -> None:
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\annotate{a.cell[0]}{label=x}\n"
            "\\reannotate{a.cell[0]}{color=good}\n"
        )
        cmd = ir.frames[0].commands[1]
        assert isinstance(cmd, ReannotateCommand)
        assert cmd.color == "good"


# ===========================================================================
# \apply (primitive-agnostic)
# ===========================================================================


class TestApplyGeneric:
    """Primitive-agnostic tests for ``\\apply``."""

    def test_apply_value_on_matrix(self) -> None:
        """Value stored on a Matrix cell persists across frames."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("m", "matrix"),))

        snap = state.apply_frame(_frame(_apply("m.cell[1][2]", value="42")))
        assert snap.shape_states["m"]["m.cell[1][2]"].value == "42"

    def test_apply_value_on_dptable(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(_shape("dp", "dptable"),))

        snap = state.apply_frame(_frame(_apply("dp.cell[3][4]", value="7")))
        assert snap.shape_states["dp"]["dp.cell[3][4]"].value == "7"

    def test_apply_extra_params_accumulated(self) -> None:
        """Extra params beyond value/label are accumulated in ``apply_params``."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("q", "queue"),))

        snap = state.apply_frame(
            _frame(
                _apply("q", enqueue="1"),
                _apply("q", enqueue="2"),
            ),
        )
        # Both enqueue calls are preserved.
        extras = snap.shape_states["q"]["q"].apply_params
        assert extras is not None
        assert len(extras) == 2


# ===========================================================================
# \compute ↔ interpolation bridge
# ===========================================================================


class TestComputeInterpolationBridge:
    """``\\compute`` produces bindings that selectors can interpolate."""

    def test_compute_prelude_binding_used_by_foreach_selector(self) -> None:
        """A prelude compute binding is resolved when a ``\\foreach`` expands its body.

        The interpolation bridge lives at the ``\\foreach`` expansion step:
        ``${i}`` in a cell selector picks up the iteration variable, which
        in turn derives from ``xs`` (a compute binding).
        """
        from scriba.animation.parser.ast import ForeachCommand, RecolorCommand

        host = _MockStarlarkHost()
        state = SceneState()

        state.apply_prelude(
            shapes=(_shape("a"),),
            prelude_compute=(
                ComputeCommand(line=0, col=0, source="xs = [1, 2, 3]"),
            ),
            starlark_host=host,
        )

        # \foreach{i}{${xs}} recolor{a.cell[${i}]}{state=done} \endforeach
        body = (
            RecolorCommand(
                line=0,
                col=0,
                target=Selector(
                    shape_name="a",
                    accessor=CellAccessor(
                        indices=(InterpolationRef(name="i"),),
                    ),
                ),
                state="done",
            ),
        )
        foreach_cmd = ForeachCommand(
            variable="i",
            iterable_raw="${xs}",
            body=body,
        )
        snap = state.apply_frame(
            FrameIR(line=0, commands=(foreach_cmd,)),
            starlark_host=host,
        )
        # Each xs value (1, 2, 3) should have been applied as an index.
        for i in (1, 2, 3):
            assert snap.shape_states["a"][f"a.cell[{i}]"].state == "done"

    def test_frame_compute_scopes_to_frame(self) -> None:
        """A frame-scoped compute is visible in the same frame but not the next."""
        host = _MockStarlarkHost()
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),), starlark_host=host)

        frame = FrameIR(
            line=0,
            commands=(),
            compute=(ComputeCommand(line=0, col=0, source="k = 5"),),
        )
        snap = state.apply_frame(frame, starlark_host=host)
        assert snap.bindings.get("k") == 5

        # Next frame does not see ``k``.
        snap2 = state.apply_frame(FrameIR(line=0, commands=()), starlark_host=host)
        assert "k" not in snap2.bindings

    def test_compute_list_indexing_bindings(self) -> None:
        """A compute-emitted list binding can be referenced in later compute."""
        host = _MockStarlarkHost()
        state = SceneState()
        state.apply_prelude(
            shapes=(_shape("a"),),
            prelude_compute=(
                ComputeCommand(line=0, col=0, source="xs = list(range(5))"),
            ),
            starlark_host=host,
        )
        # ``xs`` is visible to a later frame compute.
        frame = FrameIR(
            line=0,
            commands=(),
            compute=(ComputeCommand(line=0, col=0, source="n = len(xs)"),),
        )
        snap = state.apply_frame(frame, starlark_host=host)
        assert snap.bindings.get("n") == 5
