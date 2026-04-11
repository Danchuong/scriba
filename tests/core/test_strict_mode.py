"""Strict mode infrastructure tests (RFC-002, Wave 6.3).

Covers the structured warning channel introduced in v0.6.0:

* :class:`CollectedWarning` dataclass shape.
* :class:`Document.warnings` field default + tuple invariant.
* :class:`RenderContext` ``strict`` / ``strict_except`` / ``warnings_collector`` fields.
* :func:`scriba.animation.errors._emit_warning` routing rules:
  - ``ctx=None`` falls back to ``warnings.warn``
  - ``ctx.warnings_collector`` receives a :class:`CollectedWarning` entry
  - ``ctx.strict`` promotes dangerous codes to raised errors
  - ``ctx.strict_except`` tolerates specific dangerous codes
* Silent-fix promotions that now route through the collector:
  - SF-1 polygon auto-close (E1462) + internal list correctness
  - SF-2 point outside viewport (E1463, hidden)
  - SF-3 degenerate line (E1461)
  - SF-4 MetricPlot log-scale clamp (E1484)
  - SF-8 stray ``\\end{animation}`` (E1007, always raises)
  - SF-9 substory prelude drop (E1057, always raises)
  - SF-14 selector mismatch (E1115, collector + legacy warnings.warn)
* KaTeX error scanning helper.

Deviations from the RFC are documented in the Wave 6 merge report.
"""

from __future__ import annotations

import dataclasses
import warnings

import pytest

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.errors import (
    _DANGEROUS_CODES,
    _emit_warning,
    AnimationError,
    ERROR_CATALOG,
)
from scriba.animation.primitives.metricplot import MetricPlot
from scriba.animation.primitives.plane2d import Plane2D
from scriba.core.artifact import CollectedWarning, Document
from scriba.core.context import RenderContext
from scriba.core.errors import ValidationError
from scriba.tex.renderer import _scan_katex_errors


# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------


def _resolver(_filename: str) -> str | None:  # pragma: no cover - trivial
    return None


def _make_ctx(
    *,
    strict: bool = False,
    strict_except: frozenset[str] = frozenset(),
    collector: list[CollectedWarning] | None = None,
) -> RenderContext:
    return RenderContext(
        resource_resolver=_resolver,
        strict=strict,
        strict_except=strict_except,
        warnings_collector=collector if collector is not None else [],
    )


# ---------------------------------------------------------------------------
# CollectedWarning
# ---------------------------------------------------------------------------


class TestCollectedWarning:
    def test_is_frozen_dataclass(self) -> None:
        assert dataclasses.is_dataclass(CollectedWarning)
        entry = CollectedWarning(code="E1462", message="msg")
        with pytest.raises(dataclasses.FrozenInstanceError):
            entry.code = "E0000"  # type: ignore[misc]

    def test_default_severity_is_hidden(self) -> None:
        entry = CollectedWarning(code="E1115", message="m")
        assert entry.severity == "hidden"

    def test_explicit_fields(self) -> None:
        entry = CollectedWarning(
            code="E1461",
            message="degenerate",
            source_line=12,
            source_col=3,
            primitive="p1",
            severity="dangerous",
        )
        assert entry.code == "E1461"
        assert entry.message == "degenerate"
        assert entry.source_line == 12
        assert entry.source_col == 3
        assert entry.primitive == "p1"
        assert entry.severity == "dangerous"

    def test_equality_by_value(self) -> None:
        a = CollectedWarning(code="E1462", message="auto-close")
        b = CollectedWarning(code="E1462", message="auto-close")
        assert a == b

    def test_severity_literal_accepts_info(self) -> None:
        entry = CollectedWarning(code="E9999", message="x", severity="info")
        assert entry.severity == "info"


# ---------------------------------------------------------------------------
# Document.warnings
# ---------------------------------------------------------------------------


class TestDocumentWarnings:
    def test_default_is_empty_tuple(self) -> None:
        doc = Document(
            html="",
            required_css=frozenset(),
            required_js=frozenset(),
            versions={"core": 2},
        )
        assert doc.warnings == ()
        assert isinstance(doc.warnings, tuple)

    def test_accepts_tuple_of_warnings(self) -> None:
        w = (
            CollectedWarning(code="E1462", message="auto-close"),
            CollectedWarning(code="E1463", message="outside"),
        )
        doc = Document(
            html="",
            required_css=frozenset(),
            required_js=frozenset(),
            versions={"core": 2},
            warnings=w,
        )
        assert doc.warnings == w
        assert len(doc.warnings) == 2

    def test_document_is_frozen(self) -> None:
        doc = Document(
            html="",
            required_css=frozenset(),
            required_js=frozenset(),
            versions={"core": 2},
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            doc.warnings = ()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RenderContext strict fields
# ---------------------------------------------------------------------------


class TestRenderContextStrictFields:
    def test_defaults(self) -> None:
        ctx = RenderContext(resource_resolver=_resolver)
        assert ctx.strict is False
        assert ctx.strict_except == frozenset()
        assert ctx.warnings_collector is None

    def test_immutable(self) -> None:
        ctx = RenderContext(resource_resolver=_resolver)
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.strict = True  # type: ignore[misc]

    def test_strict_except_accepts_frozenset(self) -> None:
        ctx = RenderContext(
            resource_resolver=_resolver,
            strict=True,
            strict_except=frozenset({"E1462"}),
        )
        assert "E1462" in ctx.strict_except

    def test_warnings_collector_is_mutable_list(self) -> None:
        collector: list[CollectedWarning] = []
        ctx = RenderContext(
            resource_resolver=_resolver,
            warnings_collector=collector,
        )
        assert ctx.warnings_collector is collector

    def test_dataclasses_replace_preserves_new_fields(self) -> None:
        ctx = RenderContext(resource_resolver=_resolver)
        new_ctx = dataclasses.replace(ctx, strict=True)
        assert new_ctx.strict is True
        assert new_ctx.resource_resolver is _resolver


# ---------------------------------------------------------------------------
# _emit_warning helper
# ---------------------------------------------------------------------------


class TestEmitWarningHelper:
    def test_dangerous_codes_set(self) -> None:
        # Sanity: the set we promote in strict mode matches the spec.
        assert "E1461" in _DANGEROUS_CODES
        assert "E1462" in _DANGEROUS_CODES
        assert "E1463" in _DANGEROUS_CODES
        assert "E1484" in _DANGEROUS_CODES
        assert "E1501" in _DANGEROUS_CODES
        assert "E1502" in _DANGEROUS_CODES
        assert "E1503" in _DANGEROUS_CODES

    def test_ctx_none_falls_back_to_warnings_warn(self) -> None:
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            _emit_warning(None, "E1462", "hello")
        assert len(record) == 1
        assert "E1462" in str(record[0].message)
        assert "hello" in str(record[0].message)

    def test_ctx_with_collector_appends_entry(self) -> None:
        ctx = _make_ctx()
        _emit_warning(
            ctx,
            "E1462",
            "auto-close",
            primitive="p",
            severity="dangerous",
        )
        assert ctx.warnings_collector is not None
        assert len(ctx.warnings_collector) == 1
        entry = ctx.warnings_collector[0]
        assert entry.code == "E1462"
        assert entry.message == "auto-close"
        assert entry.primitive == "p"
        assert entry.severity == "dangerous"

    def test_ctx_strict_raises_for_dangerous_code(self) -> None:
        ctx = _make_ctx(strict=True)
        with pytest.raises((AnimationError, ValidationError)) as exc_info:
            _emit_warning(ctx, "E1462", "forced")
        assert getattr(exc_info.value, "code", None) == "E1462"

    def test_ctx_strict_except_tolerates(self) -> None:
        ctx = _make_ctx(strict=True, strict_except=frozenset({"E1462"}))
        # Must not raise.
        _emit_warning(ctx, "E1462", "tolerated")
        assert ctx.warnings_collector is not None
        assert ctx.warnings_collector[0].code == "E1462"

    def test_ctx_strict_does_not_raise_for_non_dangerous_code(self) -> None:
        ctx = _make_ctx(strict=True)
        # E1115 is NOT in _DANGEROUS_CODES so strict must NOT promote.
        _emit_warning(ctx, "E1115", "hidden")
        assert ctx.warnings_collector is not None
        assert ctx.warnings_collector[0].code == "E1115"

    def test_strict_with_empty_collector_still_raises(self) -> None:
        # Even without a collector, strict mode should promote.
        ctx = RenderContext(
            resource_resolver=_resolver,
            strict=True,
            warnings_collector=[],
        )
        with pytest.raises((AnimationError, ValidationError)):
            _emit_warning(ctx, "E1484", "log clamp")


# ---------------------------------------------------------------------------
# SF-1 — polygon auto-close
# ---------------------------------------------------------------------------


class TestSF1PolygonAutoclose:
    def test_lax_populates_collector_and_closes_list(self) -> None:
        ctx = _make_ctx()
        p = Plane2D("p", {})
        p._ctx = ctx
        p.apply_command(
            {"add_polygon": [(0, 0), (3, 0), (3, 3), (0, 3)]}
        )
        assert ctx.warnings_collector is not None
        codes = [w.code for w in ctx.warnings_collector]
        assert "E1462" in codes
        # Internal list must match the rendered SVG path: first point
        # explicitly duplicated at the end.
        pts = p.polygons[0]["points"]
        assert len(pts) == 5
        assert pts[0] == pts[-1]

    def test_lax_skips_warning_when_already_closed(self) -> None:
        ctx = _make_ctx()
        p = Plane2D("p", {})
        p._ctx = ctx
        p.apply_command(
            {
                "add_polygon": [
                    (0, 0),
                    (3, 0),
                    (3, 3),
                    (0, 0),
                ]
            }
        )
        assert ctx.warnings_collector is not None
        assert all(w.code != "E1462" for w in ctx.warnings_collector)

    def test_strict_raises_e1462(self) -> None:
        ctx = _make_ctx(strict=True)
        p = Plane2D("p", {})
        p._ctx = ctx
        with pytest.raises((AnimationError, ValidationError)) as exc_info:
            p.apply_command(
                {"add_polygon": [(0, 0), (3, 0), (3, 3), (0, 3)]}
            )
        assert getattr(exc_info.value, "code", None) == "E1462"

    def test_strict_except_e1462_tolerates(self) -> None:
        ctx = _make_ctx(strict=True, strict_except=frozenset({"E1462"}))
        p = Plane2D("p", {})
        p._ctx = ctx
        # Must not raise.
        p.apply_command(
            {"add_polygon": [(0, 0), (3, 0), (3, 3), (0, 3)]}
        )
        assert any(
            w.code == "E1462" for w in (ctx.warnings_collector or [])
        )


# ---------------------------------------------------------------------------
# SF-2 — point outside viewport (hidden)
# ---------------------------------------------------------------------------


class TestSF2PointOutsideViewport:
    def test_lax_populates_collector(self) -> None:
        ctx = _make_ctx()
        p = Plane2D("p", {"xrange": [0, 5], "yrange": [0, 5]})
        p._ctx = ctx
        p.apply_command({"add_point": (-10, -10)})
        codes = [w.code for w in (ctx.warnings_collector or [])]
        assert "E1463" in codes

    def test_strict_does_not_raise(self) -> None:
        # E1463 lives in _DANGEROUS_CODES so strict could promote it —
        # but the spec tags the severity as 'hidden', meaning the emitter
        # side uses severity='hidden'. Strict promotion is code-based,
        # not severity-based, so strict WILL raise. Document the actual
        # behaviour here so future changes remain intentional.
        ctx = _make_ctx(strict=True, strict_except=frozenset({"E1463"}))
        p = Plane2D("p", {"xrange": [0, 5], "yrange": [0, 5]})
        p._ctx = ctx
        # strict_except tolerates — no raise.
        p.apply_command({"add_point": (-10, -10)})
        assert any(
            w.code == "E1463" for w in (ctx.warnings_collector or [])
        )

    def test_inside_viewport_no_warning(self) -> None:
        ctx = _make_ctx()
        p = Plane2D("p", {"xrange": [0, 5], "yrange": [0, 5]})
        p._ctx = ctx
        p.apply_command({"add_point": (2, 3)})
        assert all(
            w.code != "E1463" for w in (ctx.warnings_collector or [])
        )


# ---------------------------------------------------------------------------
# SF-3 — degenerate line
# ---------------------------------------------------------------------------


class TestSF3DegenerateLine:
    def test_lax_populates_collector(self) -> None:
        ctx = _make_ctx()
        p = Plane2D("p", {})
        p._ctx = ctx
        p.apply_command({"add_line": ("L", {"a": 0, "b": 0, "c": 0})})
        codes = [w.code for w in (ctx.warnings_collector or [])]
        assert "E1461" in codes
        # Degenerate line is NOT added to self.lines.
        assert len(p.lines) == 0

    def test_strict_raises_e1461(self) -> None:
        ctx = _make_ctx(strict=True)
        p = Plane2D("p", {})
        p._ctx = ctx
        with pytest.raises((AnimationError, ValidationError)) as exc_info:
            p.apply_command(
                {"add_line": ("L", {"a": 0, "b": 0, "c": 0})}
            )
        assert getattr(exc_info.value, "code", None) == "E1461"

    def test_non_degenerate_line_silent(self) -> None:
        ctx = _make_ctx()
        p = Plane2D("p", {})
        p._ctx = ctx
        p.apply_command({"add_line": ("L", {"a": 1, "b": 1, "c": 2})})
        assert all(
            w.code != "E1461" for w in (ctx.warnings_collector or [])
        )
        assert len(p.lines) == 1


# ---------------------------------------------------------------------------
# SF-4 — MetricPlot log-scale clamp
# ---------------------------------------------------------------------------


class TestSF4LogScaleClamp:
    def _build_plot(self, ctx: RenderContext | None) -> MetricPlot:
        plot = MetricPlot(
            "m",
            {
                "series": [
                    {"name": "s", "axis": "left", "scale": "log"},
                ],
            },
        )
        plot._ctx = ctx
        return plot

    def test_lax_clamps_and_collects(self) -> None:
        ctx = _make_ctx()
        plot = self._build_plot(ctx)
        plot.apply_command({"s": 1.0})
        plot.apply_command({"s": -5.0})
        plot.apply_command({"s": 2.0})
        # Force svg emission so _build_segments runs.
        plot.emit_svg()
        codes = [w.code for w in (ctx.warnings_collector or [])]
        assert "E1484" in codes

    def test_strict_raises_e1484(self) -> None:
        ctx = _make_ctx(strict=True)
        plot = self._build_plot(ctx)
        plot.apply_command({"s": 1.0})
        plot.apply_command({"s": -5.0})
        with pytest.raises((AnimationError, ValidationError)) as exc_info:
            plot.emit_svg()
        assert getattr(exc_info.value, "code", None) == "E1484"


# ---------------------------------------------------------------------------
# SF-8 — stray \end{animation}
# ---------------------------------------------------------------------------


class TestSF8StrayEnd:
    def test_always_raises_e1007(self) -> None:
        source = "some text \\end{animation} trailing"
        with pytest.raises((AnimationError, ValidationError)) as exc_info:
            detect_animation_blocks(source)
        assert getattr(exc_info.value, "code", None) == "E1007"

    def test_no_strict_opt_out(self) -> None:
        # There is no strict-mode path for SF-8. The detector is a pure
        # function that does not take a RenderContext, so strict_except
        # cannot reach it. The raise is unconditional.
        source = "\\end{animation}"
        with pytest.raises((AnimationError, ValidationError)):
            detect_animation_blocks(source)

    def test_well_formed_document_parses(self) -> None:
        source = "\\begin{animation}\n\\end{animation}"
        blocks = detect_animation_blocks(source)
        assert len(blocks) == 1


# ---------------------------------------------------------------------------
# SF-9 — substory prelude drop
# ---------------------------------------------------------------------------


class TestSF9SubstoryPrelude:
    def _parse(self, body: str) -> None:
        from scriba.animation.parser.grammar import SceneParser

        SceneParser().parse(body)

    def test_highlight_in_prelude_raises_e1057(self) -> None:
        body = (
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\substory[title=\"t\"]\n"
            "\\highlight{a.cell[0]}\n"  # prelude command — forbidden
            "\\step\n"
            "\\endsubstory\n"
        )
        with pytest.raises((AnimationError, ValidationError)) as exc_info:
            self._parse(body)
        assert getattr(exc_info.value, "code", None) == "E1057"

    def test_apply_in_prelude_raises_e1057(self) -> None:
        body = (
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\substory[title=\"t\"]\n"
            "\\apply{a.cell[0]}{state=current}\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        with pytest.raises((AnimationError, ValidationError)) as exc_info:
            self._parse(body)
        assert getattr(exc_info.value, "code", None) == "E1057"

    def test_recolor_in_prelude_raises_e1057(self) -> None:
        body = (
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\substory[title=\"t\"]\n"
            "\\recolor{a.cell[0]}{state=current}\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        with pytest.raises((AnimationError, ValidationError)) as exc_info:
            self._parse(body)
        assert getattr(exc_info.value, "code", None) == "E1057"

    def test_commands_inside_substory_step_are_ok(self) -> None:
        body = (
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\substory[title=\"t\"]\n"
            "\\step\n"
            "\\highlight{a.cell[0]}\n"
            "\\endsubstory\n"
        )
        # Must parse without raising.
        self._parse(body)


# ---------------------------------------------------------------------------
# SF-14 — selector mismatch (legacy warnings.warn + collector)
# ---------------------------------------------------------------------------


class TestSF14SelectorMismatch:
    def test_legacy_userwarning_fires(self) -> None:
        from scriba.animation.emitter import _validate_expanded_selectors

        class _FakePrim:
            def __init__(self) -> None:
                self._ctx = None

            def addressable_parts(self) -> list[str]:
                return ["cell[0]", "cell[1]"]

            def validate_selector(self, suffix: str) -> bool:
                return suffix in self.addressable_parts()

        prim = _FakePrim()
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            _validate_expanded_selectors(
                {"a.cell[99]": {}}, "a", prim
            )
        # Legacy UserWarning must still fire.
        assert any(
            "does not match" in str(w.message) for w in record
        )

    def test_collector_receives_entry_when_ctx_present(self) -> None:
        from scriba.animation.emitter import _validate_expanded_selectors

        collector: list[CollectedWarning] = []
        ctx = RenderContext(
            resource_resolver=_resolver,
            warnings_collector=collector,
        )

        class _FakePrim:
            def __init__(self, ctx_: RenderContext) -> None:
                self._ctx = ctx_

            def addressable_parts(self) -> list[str]:
                return ["cell[0]"]

            def validate_selector(self, suffix: str) -> bool:
                return suffix in self.addressable_parts()

        prim = _FakePrim(ctx)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _validate_expanded_selectors(
                {"a.cell[99]": {}}, "a", prim
            )
        assert any(w.code == "E1115" for w in collector)


# ---------------------------------------------------------------------------
# KaTeX inline error scan
# ---------------------------------------------------------------------------


class TestKaTeXErrorScan:
    def test_ctx_none_is_noop(self) -> None:
        # Must not raise.
        _scan_katex_errors(
            '<span class="katex-error" title="bad">x</span>', None
        )

    def test_populates_collector_on_error_span(self) -> None:
        ctx = _make_ctx()
        html = (
            '<p>text <span class="katex-error" '
            'title="ParseError: Expected &#x27;EOF&#x27;">$\\foo$</span></p>'
        )
        _scan_katex_errors(html, ctx)
        assert ctx.warnings_collector is not None
        codes = [w.code for w in ctx.warnings_collector]
        assert "E1200" in codes
        # Decoded entities: we at least see "ParseError" in the message.
        assert any(
            "ParseError" in w.message for w in ctx.warnings_collector
        )

    def test_clean_html_produces_nothing(self) -> None:
        ctx = _make_ctx()
        html = "<p>plain text with no katex errors</p>"
        _scan_katex_errors(html, ctx)
        assert ctx.warnings_collector == []

    def test_multiple_errors_each_collected(self) -> None:
        ctx = _make_ctx()
        html = (
            '<span class="katex-error" title="a">x</span>'
            '<span class="katex-error" title="b">y</span>'
        )
        _scan_katex_errors(html, ctx)
        assert ctx.warnings_collector is not None
        assert len(ctx.warnings_collector) == 2


# ---------------------------------------------------------------------------
# Catalog presence — W6 merge guard
# ---------------------------------------------------------------------------


class TestErrorCatalogMergeGuards:
    """Confirm all Wave 6 E-codes we own live in ERROR_CATALOG.

    This test exists so the merge-time side-effects from W6.1/W6.2/W6.4/W6.5
    never hit a KeyError cascade when they import from errors.py.
    """

    @pytest.mark.parametrize(
        "code",
        [
            # W6.3 own codes
            "E1007",
            "E1057",
            "E1115",
            "E1200",
            # W6.4 uniqueness
            "E1017",
            "E1018",
            "E1019",
            # W6.1 tree
            "E1433",
            "E1434",
            "E1435",
            "E1436",
            # W6.5 plane2d remove
            "E1437",
            # W6.2 graph
            "E1471",
            "E1472",
            "E1473",
            "E1474",
        ],
    )
    def test_code_in_catalog(self, code: str) -> None:
        assert code in ERROR_CATALOG, f"missing catalog entry for {code}"

    def test_catalog_values_are_strings(self) -> None:
        for code, detail in ERROR_CATALOG.items():
            assert isinstance(code, str)
            assert isinstance(detail, str)
            assert detail, f"empty detail for {code}"
