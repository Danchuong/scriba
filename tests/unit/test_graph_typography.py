"""Phase 6 typography + tint (GEP v2.0 U-03) — RED tests.

Opt-in flags:
- ``split_labels``: parse "X/Y" display labels into a bold primary tspan +
  dim secondary tspan (hierarchy cue for dual-value edges like "cap/flow").
- ``tint_by_source``: pill background takes a light tint derived from the
  source node's state colour instead of the default white fill.

Both default ``False`` so existing SVG output and goldens stay byte-stable.
Dual-value labels arrive through ``set_value`` (dynamic override), matching
how mcmf/dinic-style examples actually compose "capacity/flow" strings.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.graph import Graph


def _make_dual(**extra: object) -> Graph:
    """Graph with a dual-value "5/3" label on edge A→B via set_value."""
    params: dict[str, object] = {
        "nodes": ["A", "B", "C"],
        "edges": [("A", "B", 1.0), ("B", "C", 1.0)],
        "show_weights": True,
        "layout_seed": 1,
    }
    params.update(extra)
    g = Graph("T", params)
    g.set_value(g._edge_key("A", "B"), "5/3")
    return g


@pytest.mark.unit
def test_split_labels_default_off_preserves_bytes() -> None:
    """Default: ``split_labels`` off ⇒ no <tspan> hierarchy emitted."""
    g = _make_dual()
    svg = g.emit_svg()
    assert "<tspan" not in svg, (
        "split_labels=False must not introduce <tspan> elements"
    )
    # Full label still present as plain text.
    assert ">5/3<" in svg


@pytest.mark.unit
def test_split_labels_on_emits_tspan_split() -> None:
    """``split_labels=True`` on an "X/Y" label emits a two-tspan hierarchy."""
    g = _make_dual(split_labels=True)
    svg = g.emit_svg()
    assert svg.count("<tspan") >= 2, (
        "split_labels=True must emit at least two <tspan> children for X/Y"
    )
    assert "font-weight:700" in svg or 'font-weight="700"' in svg, (
        "primary tspan must be bold"
    )
    # Secondary tspan dims via reduced fill opacity (0.55 — distinct from
    # the pill <rect>'s own fill-opacity="0.85" so this assertion cannot
    # false-positive on the rect).
    assert 'fill-opacity:0.55' in svg or 'fill-opacity="0.55"' in svg, (
        "secondary tspan must carry fill-opacity:0.55 for dim effect"
    )


@pytest.mark.unit
def test_split_labels_single_value_no_split() -> None:
    """``split_labels=True`` on a label without "/" renders as single text."""
    g = Graph(
        "Single",
        {
            "nodes": ["A", "B"],
            "edges": [("A", "B", 42)],
            "show_weights": True,
            "split_labels": True,
            "layout_seed": 1,
        },
    )
    svg = g.emit_svg()
    assert "<tspan" not in svg, (
        "single-value label must NOT trigger the tspan hierarchy"
    )
    assert ">42<" in svg, "label content still present"


@pytest.mark.unit
def test_tint_by_source_changes_pill_fill() -> None:
    """``tint_by_source=True`` must replace the default white pill fill."""
    g_default = _make_dual()
    g_tint = _make_dual(tint_by_source=True)
    svg_default = g_default.emit_svg()
    svg_tint = g_tint.emit_svg()
    assert 'fill="white"' in svg_default
    assert svg_tint != svg_default, (
        "tint_by_source=True must alter pill rect output"
    )


@pytest.mark.unit
def test_flags_orthogonal() -> None:
    """Both flags together render without error and produce distinct SVG."""
    g = _make_dual(split_labels=True, tint_by_source=True)
    svg = g.emit_svg()
    assert isinstance(svg, str) and len(svg) > 0
    assert "<tspan" in svg
    # Still carry a rect for each pill.
    assert svg.count("<rect") >= 2
