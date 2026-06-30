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
    target: str,
    color: str = "good",
    arrow_from: str | None = None,
    label: str | None = None,
) -> ReannotateCommand:
    return ReannotateCommand(
        target=_sel(target),
        color=color,
        arrow_from=arrow_from,
        label=label,
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

    def test_reannotate_arrow_from_replaces_arc_source(self) -> None:
        """``arrow_from`` re-points the arc source (§5.9), not a filter."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        with_arrow = AnnotateCommand(
            line=0,
            col=0,
            target=_sel("a.cell[0]"),
            label="note",
            color="info",
            arrow_from=_sel("a.cell[5]"),
        )
        state.apply_frame(_frame(with_arrow))

        snap = state.apply_frame(
            _frame(_reannotate("a.cell[0]", color="good", arrow_from="a.cell[3]")),
        )
        ann = next(a for a in snap.annotations if a.target == "a.cell[0]")
        assert ann.color == "good"
        assert ann.arrow_from == "a.cell[3]"  # re-pointed, not the original a.cell[5]

    def test_reannotate_label_replaces_text(self) -> None:
        """``label`` replaces the annotation text (§5.9)."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        state.apply_frame(_frame(_annotate("a.cell[0]", "orig", color="info")))
        snap = state.apply_frame(
            _frame(_reannotate("a.cell[0]", color="good", label="updated")),
        )
        ann = next(a for a in snap.annotations if a.target == "a.cell[0]")
        assert ann.text == "updated"
        assert ann.color == "good"

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


# ===========================================================================
# \narrate ${...} interpolation
# ===========================================================================


class TestNarrationInterpolation:
    """``${name}`` in ``\\narrate`` resolves against ``\\compute`` bindings."""

    def test_narration_resolves_compute_binding(self) -> None:
        """A computed value is interpolated into the narration text."""
        host = _MockStarlarkHost()
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),), starlark_host=host)

        frame = FrameIR(
            line=0,
            commands=(),
            compute=(ComputeCommand(line=0, col=0, source="even = [i for i in range(8) if i % 2 == 0]"),),
            narrate_body="Got ${even}.",
        )
        snap = state.apply_frame(frame, starlark_host=host)
        assert snap.narration == "Got [0, 2, 4, 6]."

    def test_narration_unknown_name_stays_literal(self) -> None:
        """An unbound ``${name}`` is left verbatim — narration never errors."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        frame = FrameIR(line=0, commands=(), narrate_body="Price is ${total} dollars.")
        snap = state.apply_frame(frame)
        assert snap.narration == "Price is ${total} dollars."

    def test_narration_mixes_bound_and_unbound(self) -> None:
        """Only known bindings substitute; unknown names pass through."""
        host = _MockStarlarkHost()
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),), starlark_host=host)

        frame = FrameIR(
            line=0,
            commands=(),
            compute=(ComputeCommand(line=0, col=0, source="x = 42"),),
            narrate_body="Answer ${x}, but ${missing} stays.",
        )
        snap = state.apply_frame(frame, starlark_host=host)
        assert snap.narration == "Answer 42, but ${missing} stays."

    def test_frame_local_binding_not_visible_to_later_narration(self) -> None:
        """A binding made inside a step is frame-local; a later narration keeps the literal."""
        host = _MockStarlarkHost()
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),), starlark_host=host)

        state.apply_frame(
            FrameIR(
                line=0,
                commands=(),
                compute=(ComputeCommand(line=0, col=0, source="k = 5"),),
            ),
            starlark_host=host,
        )
        snap2 = state.apply_frame(
            FrameIR(line=0, commands=(), narrate_body="k is ${k}."),
            starlark_host=host,
        )
        assert snap2.narration == "k is ${k}."


# ===========================================================================
# remove_edge purges persistent edge decorations (E1115 noise fix)
# ===========================================================================


class TestRemoveEdgePurgesDecoration:
    """Removing an edge drops any persistent recolor/state keyed on it, so a
    later frame does not warn E1115 for a now-deleted (but once-valid) edge."""

    def test_remove_edge_clears_persistent_recolor(self) -> None:
        ir = _parse(
            '\\shape{G}{Graph}{nodes=["A","B","C"], edges=[("A","B"),("A","C")]}\n'
            "\\step\n"
            "\\recolor{G.edge[(A,B)]}{state=current}\n"
            "\\step\n"
            '\\apply{G}{remove_edge={from="A", to="B"}}\n'
        )
        state = SceneState()
        state.apply_prelude(shapes=ir.shapes)

        snap1 = state.apply_frame(ir.frames[0])
        # Recolor is active while the edge exists.
        assert "G.edge[(A,B)]" in snap1.shape_states["G"]

        snap2 = state.apply_frame(ir.frames[1])
        # After remove_edge the decoration is gone — no stale selector to warn on.
        assert "G.edge[(A,B)]" not in snap2.shape_states["G"]

    def test_remove_edge_undirected_either_order(self) -> None:
        ir = _parse(
            '\\shape{G}{Graph}{nodes=["A","B"], edges=[("A","B")]}\n'
            "\\step\n"
            "\\recolor{G.edge[(A,B)]}{state=current}\n"
            "\\step\n"
            '\\apply{G}{remove_edge={from="B", to="A"}}\n'  # reverse order
        )
        state = SceneState()
        state.apply_prelude(shapes=ir.shapes)
        state.apply_frame(ir.frames[0])
        snap2 = state.apply_frame(ir.frames[1])
        assert "G.edge[(A,B)]" not in snap2.shape_states["G"]
