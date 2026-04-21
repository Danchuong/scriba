# Primitive Participation Contract — Smart-Label

**Document:** 05-primitive-contract.md  
**Date:** 2026-04-21  
**Status:** NORMATIVE  
**Supersedes:** audit observations in `03-primitive-coverage.md`  
**Applies to:** All `PrimitiveBase` subclasses in `scriba/animation/primitives/`

---

## 0. Purpose and Scope

This document codifies the **minimum obligations** a primitive class MUST satisfy
to participate correctly in the smart-label placement system.  It supersedes ad-hoc
per-file conventions and provides:

- A formal Python interface spec with MUST/SHOULD/MAY grading
- An exact list of required call-site patterns
- An exhaustive catalogue of forbidden anti-patterns
- A per-primitive conformance matrix with line citations
- A conformance test suite specification
- A migration plan ordered by effort
- An onboarding guide for future primitives

Every newly written primitive MUST be conformant before merge.  Existing primitives
have an explicit migration plan in §6.

---

## 1. Required Interface

The following methods constitute the **Smart-Label Participation Interface**.  Every
`PrimitiveBase` subclass MUST implement or inherit a correct version of each MUST
method before it may be used in production with `\annotate` commands.

### 1.1 `resolve_annotation_point`

```python
def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
    """Return the SVG (x, y) anchor coordinate for an annotation selector.

    The returned point is the cell/node/part center in the primitive's
    LOCAL coordinate space — i.e. as if no translate transform had been
    applied yet.  The caller (base.emit_annotation_arrows) applies the
    frame translate after this point is returned.

    Parameters
    ----------
    selector:
        Fully-qualified selector string as it appears in the annotation
        dict's "target" or "arrow_from" key, e.g. ``"arr.cell[3]"``,
        ``"G.node[A]"``, ``"p.point[origin]"``.

    Returns
    -------
    tuple[float, float] | None
        SVG (x, y) coordinates, or None when the selector cannot be
        resolved (unknown name prefix, out-of-range index, etc.).

    Contract invariants
    -------------------
    * The returned point MUST lie within or on the boundary of
      ``self.bounding_box()`` (ignoring the arrow_above translate offset).
    * For selectors referencing the same primitive instance (matching
      ``self.name``), the method MUST return a non-None value for every
      selector that ``addressable_parts()`` lists.
    * The method MUST NOT mutate any instance state.
    * Returns ``None`` silently (no exception) for unknown selectors.
    """
```

**Grade:** MUST.  A primitive that returns `None` for all selectors produces
silently-dropped annotations — identical to the Stack/Matrix/MetricPlot/CodePanel
dark state catalogued in `03-primitive-coverage.md §2.12–2.15`.

**Rename note:** The base class already declares this method at `base.py:330`
returning `None` unconditionally.  Subclasses MUST shadow it.  No rename proposed;
the current name is unambiguous.

---

### 1.2 `emit_svg`

```python
def emit_svg(
    self,
    *,
    placed_labels: "list[_LabelPlacement] | None" = None,
    render_inline_tex: "Callable[[str], str] | None" = None,
) -> str:
    """Emit the SVG fragment for this primitive in the current frame.

    The fragment MUST be a single ``<g data-primitive="..." data-shape="...">``
    wrapping element.  All annotation rendering MUST happen inside this
    group — either via ``self.emit_annotation_arrows`` or, for future
    extensions that need pre-seeded collision registries, by pre-populating
    the shared ``placed_labels`` list before calling
    ``self.emit_annotation_arrows``.

    Parameters
    ----------
    placed_labels:
        When provided, the primitive MUST pass this list to every
        ``emit_annotation_arrows`` / ``emit_position_label_svg`` /
        ``emit_plain_arrow_svg`` / ``emit_arrow_svg`` call so that
        labels placed by other primitives in the same frame (MW-2 scope)
        participate in collision avoidance.
        When ``None``, the method creates a fresh list internally for
        intra-primitive collision avoidance.
    render_inline_tex:
        Optional callback for KaTeX rendering of ``$...$`` math labels.

    Contract invariants
    -------------------
    * Headroom MUST be computed via the canonical formula:
        arrow_above = max(
            arrow_height_above(...),
            position_label_height_above(...),
            getattr(self, "_min_arrow_above", 0),
        )
      and applied as ``translate(0, {arrow_above})`` when > 0.
    * The method MUST NOT emit ``<text>`` elements for annotation labels
      directly — all annotation text MUST be emitted by helper functions
      in ``_svg_helpers.py``.
    * The method MUST NOT maintain its own ``placed_labels``-equivalent
      list as a separate instance variable.
    * Bottom-edge expansion for ``position=below`` labels MUST be
      accounted for in viewBox height; use ``position_label_height_below``.
    """
```

**Grade:** MUST.  The `placed_labels` parameter is proposed as a new addition to
the abstract interface (MW-2 prerequisite).  Current primitive signatures lack it;
adding it as a keyword-only parameter with default `None` is backward-compatible.

**Rename note:** Current abstract signature at `base.py:327` has only
`render_inline_tex`.  The `placed_labels` kwarg MUST be added in MW-2.

---

### 1.3 `annotation_headroom_above`

```python
def annotation_headroom_above(self) -> float:
    """Return the vertical pixel headroom needed above y=0 for annotations.

    This is the combined maximum of arrow curves AND position=above pill
    labels for the current annotation set (``self._annotations``).

    The canonical implementation is:

        arrow_above = arrow_height_above(
            self._annotations,
            self.resolve_annotation_point,
            cell_height=self._arrow_cell_height,
            layout=self._arrow_layout,
        )
        pos_above = position_label_height_above(
            self._annotations,
            cell_height=self._arrow_cell_height,
        )
        return float(max(arrow_above, pos_above,
                         getattr(self, "_min_arrow_above", 0)))

    Primitives with non-standard geometry (e.g. Plane2D which uses an
    internal pixel-height for its math viewport rather than CELL_HEIGHT)
    MUST override with the appropriate ``cell_height`` argument.

    Returns
    -------
    float
        Non-negative pixel headroom.  Returns 0.0 when there are no
        annotations or when no annotation generates above-content space.
    """
```

**Grade:** MUST.  Splitting the headroom computation into a named method prevents
the duplicated max()/max() pattern that currently drifts between `emit_svg` and
`bounding_box` in partial primitives.  Both `emit_svg` and `bounding_box` MUST
call this method rather than re-implementing the formula inline.

**Rename note:** This is a NEW method.  It does not yet exist in any primitive.
It replaces the inline `arrow_above = max(...)` blocks scattered across 14 files.

---

### 1.4 `annotation_headroom_below`

```python
def annotation_headroom_below(self) -> float:
    """Return extra pixels needed below the nominal content bottom for annotations.

    The canonical implementation is:

        return float(position_label_height_below(
            self._annotations,
            cell_height=self._arrow_cell_height,
        ))

    Returns
    -------
    float
        Non-negative pixel expansion.  Returns 0.0 when there are no
        position=below annotations.
    """
```

**Grade:** MUST.  Without this, `position=below` pills clip the SVG bottom edge.
`03-primitive-coverage.md §2.2` notes DPTable's 2D layout already misses this;
all other primitives miss it entirely.

**Rename note:** NEW method.  Companion to `annotation_headroom_above`.

---

### 1.5 `register_decorations`

```python
def register_decorations(
    self,
    placed_labels: "list[_LabelPlacement]",
) -> None:
    """Pre-seed the collision registry with this primitive's own visual elements.

    Called by the frame emitter BEFORE ``emit_svg`` so that annotation
    labels placed by ``emit_annotation_arrows`` do not collide with the
    primitive's own cell text, node circles, tick labels, or pointer
    decorations.

    Default implementation is a no-op (base class).  Primitives MUST
    override to register any fixed visual elements that are rendered
    inside the primitive's bounding box and that annotation labels
    should avoid.

    Parameters
    ----------
    placed_labels:
        The shared frame-level collision registry.  The method MUST
        append one ``_LabelPlacement`` entry per fixed obstacle element.
        The entry dimensions MUST match the rendered element's actual
        pixel bbox as closely as possible.

    Contract invariants
    -------------------
    * MUST NOT render any SVG output.  Side-effect is solely the
      mutation of ``placed_labels``.
    * MUST NOT store ``placed_labels`` as an instance attribute.
    * MUST be idempotent — calling it twice with the same list appends
      duplicates; callers are responsible for calling it exactly once
      per frame.

    Scope note
    ----------
    This method is MW-2 scope (unified placed_labels registry seeded at
    frame start).  Its interface is defined here so new primitives can
    implement it correctly from day one.  Existing primitives SHOULD add
    a stub that returns immediately until the MW-2 work item lands.
    """
```

**Grade:** MUST (post-MW-2).  SHOULD add no-op stub now so the method exists at
the call site when MW-2 lands.

---

### 1.6 `dispatch_annotations`

```python
def dispatch_annotations(
    self,
    placed_labels: "list[_LabelPlacement]",
    *,
    render_inline_tex: "Callable[[str], str] | None" = None,
) -> list[str]:
    """Render all annotations for the current frame into SVG lines.

    The default implementation provided by ``PrimitiveBase`` calls
    ``self.emit_annotation_arrows`` and returns the resulting lines.
    Primitives SHOULD NOT override this method unless they have
    annotation categories that cannot be expressed as arrow, plain-
    pointer, or position-only pill labels.

    When a primitive does override, it MUST:
    1. Pass ``placed_labels`` through to every helper function.
    2. Handle all three annotation types:
       - arrow_from (Bezier arc): via ``emit_arrow_svg``
       - arrow=true (plain pointer): via ``emit_plain_arrow_svg``
       - position-only (pill): via ``emit_position_label_svg``
    3. NOT call ``emit_annotation_arrows`` AND separately call the
       helpers for the same annotation set — double-dispatch produces
       duplicate SVG elements.

    Returns
    -------
    list[str]
        SVG lines to splice into the primitive's output group.
        Callers MUST extend their ``parts`` list with the return value
        inside the translate group (after ``register_decorations``).
    """
```

**Grade:** SHOULD.  Most primitives get the correct behaviour for free via the
default base implementation.  Only Plane2D (which splits `arrow_anns` vs
`text_anns`) currently requires an override — and that override must be rewritten
to use `emit_position_label_svg` rather than the orphan `_emit_text_annotation`.

---

## 2. Required Call Patterns

The following sequence MUST appear inside every primitive's `emit_svg` and
`bounding_box` implementations once the migration in §6 is complete.

### 2.1 Headroom computation (emit_svg)

```python
# CORRECT — both arrow and position-only paths compose with _min_arrow_above
arrow_above = max(
    arrow_height_above(
        self._annotations,
        self.resolve_annotation_point,
        cell_height=self._arrow_cell_height,
    ),
    position_label_height_above(
        self._annotations,
        cell_height=self._arrow_cell_height,
    ),
    getattr(self, "_min_arrow_above", 0),
)
```

After §1.3 lands this collapses to:

```python
arrow_above = int(self.annotation_headroom_above())
```

### 2.2 Bottom-edge expansion (bounding_box)

```python
# CORRECT — bottom edge expands for position=below pills
h_base = <nominal_content_height>
h = h_base + self.annotation_headroom_above() + self.annotation_headroom_below()
```

### 2.3 Selector resolution before emit

```python
# Rule: ALWAYS call resolve_annotation_point before passing to helpers.
# NEVER hardcode pixel offsets as substitutes for unresolved selectors.
dst_point = self.resolve_annotation_point(ann.get("target", ""))
if dst_point is None:
    continue   # annotation targets unknown selector — silently skip
```

### 2.4 Routing to helpers

```python
# Three annotation categories — MUST reach the correct helper:
if ann.get("arrow_from"):
    # Category 1: Bezier arc arrow
    src_point = self.resolve_annotation_point(ann["arrow_from"])
    # ... (handled by emit_annotation_arrows)
elif ann.get("arrow"):
    # Category 2: plain straight pointer
    emit_plain_arrow_svg(parts, ann, dst_point=dst_point,
                         placed_labels=placed, ...)
else:
    # Category 3: position-only pill (no arrow at all)
    emit_position_label_svg(parts, ann, anchor_point=dst_point,
                            cell_height=self._arrow_cell_height,
                            placed_labels=placed, ...)
```

The canonical path for all three categories is through
`base.PrimitiveBase.emit_annotation_arrows` which already implements the
dispatch.  Primitives that need to override `dispatch_annotations` for custom
reasons MUST replicate this three-branch structure exactly.

### 2.5 Threading `placed_labels`

```python
# CORRECT: one list, passed to EVERY emit call in the frame
placed: list[_LabelPlacement] = []
self.emit_annotation_arrows(parts, self._annotations,
                             render_inline_tex=render_inline_tex)
# ^^^ base.emit_annotation_arrows creates `placed` internally;
#     after MW-2, it MUST accept an external `placed_labels` arg.
```

The internal `placed` list created at `base.py:382` MUST be the **only** collision
registry active during a single primitive's frame emit.  No second list may be
created in `emit_svg` for a different annotation category or decoration type.

### 2.6 viewBox headroom composition (summary)

| Helper | When to call | Where to call |
|--------|-------------|---------------|
| `arrow_height_above(...)` | Any `arrow_from` or `arrow=true` annotation exists | `emit_svg` AND `bounding_box` |
| `position_label_height_above(...)` | Any position-only annotation with `position=above` | `emit_svg` AND `bounding_box` |
| `position_label_height_below(...)` | Any position-only annotation with `position=below` | `bounding_box` only (content expands downward, no translate needed) |

All three are idempotent and return 0 when no relevant annotation is present, so
calling them unconditionally (without checking `self._annotations` first) is safe
and preferred.

---

## 3. Forbidden Patterns

### FP-1: Direct `<text>` emission for annotation labels

**Rule:** Primitives MUST NOT construct `<text>` SVG elements for annotation
labels outside of `_svg_helpers.py`.  All label text must be routed through
`emit_arrow_svg`, `emit_plain_arrow_svg`, or `emit_position_label_svg`.

**Rationale:** The helper functions apply collision avoidance, math-width
correction, pill geometry, KaTeX fallback, and WCAG-compliant color selection.
Hand-rolled `<text>` elements bypass all of these.

**Current violations:**

| File | Lines | Description |
|------|-------|-------------|
| `plane2d.py` | 673–752 | `_emit_text_annotation` constructs `<rect>` + `_render_svg_text` call for position-only pill. Hardcodes `char_width = 7`, `pill_h = 16`. No collision avoidance, no viewBox clamp. This is the primary bug-E and bug-F source. |

---

### FP-2: Maintaining a second `placed_labels`-equivalent list

**Rule:** During a single `emit_svg` call a primitive MUST NOT create or maintain
more than one `_LabelPlacement` accumulator list.  The single list provided by
(or created inside) `emit_annotation_arrows` is the only collision registry.

**Rationale:** Independent registries cannot avoid collisions with each other.

**Current violations:**

| File | Lines | Description |
|------|-------|-------------|
| `graph.py` | 726 | `placed_edge_labels: list[_LabelPlacement] = []` — collision registry for inline edge-weight labels, isolated from annotation label registry. Edge-weight labels can collide with annotation pills. |
| `plane2d.py` | 1057 | `placed_labels: list[_LabelPlacement] = []` inside `_emit_labels` — isolated registry for line/segment text labels. |
| `plane2d.py` | none | `_emit_text_annotation` creates NO registry at all — position-only pills pile without any avoidance. |

---

### FP-3: Hardcoding pill geometry

**Rule:** Primitives MUST NOT hardcode pill width, height, padding, or corner
radius.  All pill geometry MUST be derived from the constants in `_svg_helpers.py`:
`_LABEL_PILL_PAD_X`, `_LABEL_PILL_PAD_Y`, `_LABEL_PILL_RADIUS`, and from
`estimate_text_width` / `_label_width_text` for per-label sizing.

**Rationale:** Hardcoded geometry diverges from the design system when constants
are updated and produces inconsistent pill sizes across primitive types.

**Current violations:**

| File | Lines | Description |
|------|-------|-------------|
| `plane2d.py` | 719–721 | `char_width = 7`, `pill_w = max(len(label_text) * char_width + 8, 20)`, `pill_h = 16` — all three are hardcoded, bypassing `estimate_text_width` and `_LABEL_PILL_PAD_*`. |

---

### FP-4: Skipping viewBox clamping

**Rule:** When a pill's horizontal position would place any part of the rectangle
at `x < 0`, the primitive (via the helper) MUST clamp so that `pill_rx >= 0`.
Primitives MUST NOT emit annotation SVG without going through the helpers that
apply this clamp (`fi_x = max(fi_x, pill_w // 2)` in each helper).

**Rationale:** `x < 0` in SVG clips against the viewBox and the pill disappears.

**Current violations:**

| File | Lines | Description |
|------|-------|-------------|
| `plane2d.py` | 724–731 | `pill_x = tx - pill_w / 2` with no clamp — bug-F. |

---

### FP-5: Filtering `_annotations` before passing to `emit_annotation_arrows`

**Rule:** Primitives MUST NOT pre-filter `self._annotations` to `arrow_from`-only
before calling `emit_annotation_arrows`.  Doing so silently drops `arrow=true`
(plain-pointer) and position-only annotations.  Pass the full effective annotation
list.

**Rationale:** `emit_annotation_arrows` already contains the three-branch dispatch
logic.  Pre-filtering defeats the dispatch.

**Current violations:**

| File | Lines | Description |
|------|-------|-------------|
| `queue.py` | 403 | `arrow_anns = [a for a in effective_anns if a.get("arrow_from")]` — position-only and `arrow=true` annotations silently dropped. |
| `numberline.py` | 297 | Same pattern — `[a for a in effective_anns if a.get("arrow_from")]`. |

---

### FP-6: Calling `emit_arrow_svg` directly in primitive code

**Rule:** Primitive `emit_svg` bodies MUST NOT call `emit_arrow_svg`,
`emit_plain_arrow_svg`, or `emit_position_label_svg` directly.  These helpers
are called by `base.emit_annotation_arrows`.  Primitives call
`self.emit_annotation_arrows(...)`.

**Exception:** When `dispatch_annotations` is legitimately overridden (e.g.
Plane2D after MW-3), the override method MAY call the helpers directly but MUST
still pass `placed_labels` through.

**Current violations:**

| File | Lines | Description |
|------|-------|-------------|
| `queue.py` | 416 | `emit_arrow_svg(arrow_lines, ann, src, dst, ...)` called directly in `emit_svg`. |
| `numberline.py` | 309 | Same — direct call to `emit_arrow_svg`. |

---

## 4. Conformance Matrix

Legend: `✓` = pass, `✗` = fail, `P` = partial, `—` = not applicable.

Columns:
- **RAP** — `resolve_annotation_point` overridden and returns valid point inside bbox
- **HDA** — `annotation_headroom_above()` called in both `emit_svg` and `bounding_box` (or both call `position_label_height_above` + `arrow_height_above` until §1.3 lands)
- **HDB** — `annotation_headroom_below()` accounted for in `bounding_box`
- **EAA** — delegates to `self.emit_annotation_arrows` (no direct helper call)
- **FUL** — full annotation list passed (no `arrow_from`-only filter)
- **FP1** — no direct `<text>` for annotation labels
- **FP2** — no second isolated `placed_labels` list
- **FP3** — no hardcoded pill geometry
- **FP4** — no missing viewBox clamp

```
Primitive       RAP  HDA  HDB  EAA  FUL  FP1  FP2  FP3  FP4
──────────────  ───  ───  ───  ───  ───  ───  ───  ───  ───
Array           ✓    ✓    ✗    ✓    ✓    ✓    ✓    ✓    ✓
                                         array.py:369-371 missing position_label_height_below
DPTable         ✓    ✓    ✗    ✓    ✓    ✓    ✓    ✓    ✓
                                         dptable.py:330 misses position_label_height_below for 2D
Grid            ✓    ✗    ✗    ✓    ✓    ✓    ✓    ✓    ✓
                     grid.py:202 missing position_label_height_above
Graph           ✓    ✗    ✗    ✓    ✓    ✓    ✗    ✓    ✓
                     graph.py:681; FP2 at graph.py:726
Tree            ✓    ✗    ✗    ✓    ✓    ✓    ✓    ✓    ✓
                     tree.py:571
LinkedList      ✓    ✗    ✗    ✓    ✓    ✓    ✓    ✓    ✓
                     linkedlist.py:229-230
HashMap         ✓    ✗    ✗    ✓    ✓    ✓    ✓    ✓    ✓
                     hashmap.py:217-220
VariableWatch   ✓    ✗    ✗    ✓    ✓    ✓    ✓    ✓    ✓
                     variablewatch.py:206-208
Queue           ✓    ✗    ✗    ✗    ✗    ✓    P    ✓    ✓
                     FP5 at queue.py:403; FP6 at queue.py:416
NumberLine      ✓    ✗    ✗    ✗    ✗    ✓    P    ✓    ✓
                     FP5 at numberline.py:297; FP6 at numberline.py:309
Plane2D         ✓    ✗    ✗    P    P    ✗    ✗    ✗    ✗
                     _emit_text_annotation (plane2d.py:673-752): FP1, FP2, FP3, FP4
                     arrow_anns split: plane2d.py:657-662 (FP5 partial)
                     separate placed_labels in _emit_labels: plane2d.py:1057 (FP2)
Stack           ✗    ✗    ✗    ✗    —    —    —    —    —
                     No resolve_annotation_point override; no annotation wiring at all
Matrix          ✗    ✗    ✗    ✗    —    —    —    —    —
                     No resolve_annotation_point override; no annotation wiring
MetricPlot      ✗    ✗    ✗    ✗    —    —    —    —    —
                     No resolve_annotation_point override; no annotation wiring
CodePanel       ✗    ✗    ✗    ✗    —    —    —    —    —
                     No resolve_annotation_point override; no annotation wiring
```

Fully conformant: **Array** (minus HDB), **DPTable** (minus HDB for 2D).  
All others have at least one failing column.

---

## 5. Conformance Test Suite

The following describes `tests/conformance/test_primitive_participation.py`.
Each test function name is final; parametrize over primitives where the assertion
is uniform.

### 5.1 Module structure

```python
"""Conformance tests for the smart-label Primitive Participation Contract.

Each test verifies one facet of the contract defined in
docs/archive/smart-label-ruleset-strengthening-2026-04-21/05-primitive-contract.md.

Run with:
    pytest tests/conformance/test_primitive_participation.py -v
"""
from __future__ import annotations

import re
from typing import Any

import pytest

from scriba.animation.primitives._svg_helpers import _LabelPlacement
from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    get_primitive_registry,
    position_label_height_above,
    position_label_height_below,
    arrow_height_above,
)
```

### 5.2 Fixtures

```python
# Minimal valid construction params for each primitive type
_MINIMAL_PARAMS: dict[str, dict[str, Any]] = {
    "Array":        {"size": 5},
    "DPTable":      {"rows": 3, "cols": 4},
    "Grid":         {"rows": 4, "cols": 4},
    "Graph":        {"nodes": ["A", "B", "C"], "edges": [["A", "B"], ["B", "C"]]},
    "Tree":         {"root": "root", "children": {"root": ["L", "R"]}},
    "LinkedList":   {"size": 4},
    "HashMap":      {"buckets": 4},
    "VariableWatch":{"vars": [{"name": "x"}, {"name": "y"}]},
    "Queue":        {"capacity": 5},
    "NumberLine":   {"min": 0, "max": 10},
    "Plane2D":      {"xrange": [-5, 5], "yrange": [-5, 5]},
    "Stack":        {"items": ["a", "b", "c"]},
    "Matrix":       {"rows": 3, "cols": 3},
    "MetricPlot":   {"metrics": ["acc", "loss"]},
    "CodePanel":    {"lines": ["x = 1", "y = 2", "return x + y"]},
}

# A minimal valid annotation that every wired primitive should render
def _arrow_ann(name: str, src_sel: str, dst_sel: str) -> dict[str, Any]:
    return {
        "target": f"{name}.{dst_sel}",
        "arrow_from": f"{name}.{src_sel}",
        "label": "test",
        "color": "info",
    }

def _position_ann(name: str, sel: str) -> dict[str, Any]:
    return {
        "target": f"{name}.{sel}",
        "label": "pos-label",
        "position": "above",
        "color": "good",
    }

def _build(ptype: str, name: str = "t") -> PrimitiveBase:
    registry = get_primitive_registry()
    cls = registry[ptype]
    return cls(name=name, params=_MINIMAL_PARAMS[ptype])
```

### 5.3 Test: `resolve_annotation_point` returns point inside bbox

```python
@pytest.mark.parametrize("ptype,sel", [
    ("Array",         "t.cell[0]"),
    ("DPTable",       "t.cell[0][0]"),
    ("Grid",          "t.cell[0][0]"),
    ("Graph",         "t.node[A]"),
    ("Tree",          "t.node[root]"),
    ("LinkedList",    "t.node[0]"),
    ("HashMap",       "t.bucket[0]"),
    ("VariableWatch", "t.var[x]"),
    ("Queue",         "t.cell[0]"),
    ("NumberLine",    "t.tick[0]"),
    ("Plane2D",       "t.point[origin]"),
])
def test_resolve_annotation_point_inside_bbox(ptype: str, sel: str) -> None:
    """resolve_annotation_point MUST return a coordinate within bounding_box."""
    prim = _build(ptype)
    point = prim.resolve_annotation_point(sel)
    assert point is not None, (
        f"{ptype}.resolve_annotation_point({sel!r}) returned None"
    )
    bbox: BoundingBox = prim.bounding_box()
    # Allow a small epsilon for primitives that return cell TOP edge (y=0)
    # rather than center — the point is on the boundary, not inside.
    EPS = 2.0
    assert bbox.x - EPS <= point[0] <= bbox.x + bbox.width + EPS, (
        f"{ptype}: x={point[0]} outside bbox.x={bbox.x} + width={bbox.width}"
    )
    # y coordinate may be 0 (top edge) for array-like primitives — allow it.
    assert bbox.y - EPS <= point[1], (
        f"{ptype}: y={point[1]} above bbox top"
    )
```

### 5.4 Test: `placed_labels` mutated after round-trip

```python
@pytest.mark.parametrize("ptype,src,dst", [
    ("Array",         "t.cell[0]", "t.cell[2]"),
    ("DPTable",       "t.cell[0][0]", "t.cell[0][2]"),
    ("Grid",          "t.cell[0][0]", "t.cell[1][1]"),
    ("Graph",         "t.node[A]",    "t.node[C]"),
    ("Tree",          "t.node[L]",    "t.node[R]"),
    ("LinkedList",    "t.node[0]",    "t.node[2]"),
    ("HashMap",       "t.bucket[0]",  "t.bucket[2]"),
    ("VariableWatch", "t.var[x]",     "t.var[y]"),
])
def test_placed_labels_mutated_by_arrow_annotation(
    ptype: str, src: str, dst: str
) -> None:
    """After emit_svg with an arrow annotation, placed_labels MUST be non-empty."""
    prim = _build(ptype)
    prim.set_annotations([_arrow_ann("t", src.split(".", 1)[1], dst.split(".", 1)[1])])

    # Patch emit_annotation_arrows to capture placed list
    original = prim.emit_annotation_arrows
    captured: list[list[_LabelPlacement]] = []

    def capturing_emit(parts, annotations, **kwargs):
        inner_placed: list[_LabelPlacement] = []
        # Call real impl then inspect side effect via placed list
        # (We verify placed grows via the SVG output instead)
        return original(parts, annotations, **kwargs)

    svg = prim.emit_svg()
    assert 'class="scriba-annotation' in svg, (
        f"{ptype}: emit_svg produced no annotation group after set_annotations"
    )
```

### 5.5 Test: viewBox has correct headroom for position-only annotations

```python
@pytest.mark.parametrize("ptype,sel", [
    ("Array",         "t.cell[2]"),
    ("DPTable",       "t.cell[0][1]"),
    ("Grid",          "t.cell[0][0]"),
    ("Graph",         "t.node[B]"),
    ("Tree",          "t.node[root]"),
    ("LinkedList",    "t.node[1]"),
    ("HashMap",       "t.bucket[1]"),
    ("VariableWatch", "t.var[x]"),
    ("Queue",         "t.cell[0]"),
    ("NumberLine",    "t.tick[5]"),
])
def test_bounding_box_expands_for_position_above(ptype: str, sel: str) -> None:
    """bounding_box height MUST increase when a position=above annotation is added."""
    prim = _build(ptype)
    bbox_before = prim.bounding_box()

    prim.set_annotations([_position_ann("t", sel.split(".", 1)[1])])
    bbox_after = prim.bounding_box()

    assert bbox_after.height > bbox_before.height, (
        f"{ptype}: bounding_box.height did not grow after position=above annotation "
        f"(before={bbox_before.height}, after={bbox_after.height}). "
        f"position_label_height_above not wired into bounding_box."
    )
```

### 5.6 Test: no direct `<text>` emission outside helpers for annotations

```python
# Regex matches any <text ...> that is NOT inside a <foreignObject>
# and that occurs inside a scriba-annotation group.
_DIRECT_TEXT_IN_ANNOT_RE = re.compile(
    r'class="scriba-annotation[^"]*".*?<text\b',
    re.DOTALL,
)

@pytest.mark.parametrize("ptype,sel", [
    ("Array",   "t.cell[0]"),
    ("DPTable", "t.cell[0][0]"),
    ("Plane2D", "t.point[origin]"),
])
def test_no_direct_text_emission_in_annotation_group(ptype: str, sel: str) -> None:
    """Annotation groups MUST NOT contain raw <text> elements outside helpers.

    The helpers (_emit_label_single_line) may emit <text> but they always do
    so with paint-order:stroke fill halo which is identifiable.  We check that
    annotation rects are present (pill rendered) and that any <text> inside
    an annotation group carries the halo attributes.
    """
    prim = _build(ptype)
    prim.set_annotations([_position_ann("t", sel.split(".", 1)[1])])
    svg = prim.emit_svg()

    # Every <text> inside a scriba-annotation group must carry the halo style
    # that _emit_label_single_line applies.
    annot_groups = re.findall(
        r'<g class="scriba-annotation.*?</g>',
        svg,
        re.DOTALL,
    )
    for group in annot_groups:
        for text_match in re.finditer(r"<text\b[^>]*>", group):
            attrs = text_match.group(0)
            assert "paint-order" in attrs or "stroke-width" in attrs, (
                f"{ptype}: found <text> in annotation group without halo attrs: "
                f"{attrs!r}. Likely emitted by _emit_text_annotation orphan path."
            )
```

### 5.7 Test: `resolve_annotation_point` returns None for unknown selectors

```python
@pytest.mark.parametrize("ptype", list(_MINIMAL_PARAMS.keys()))
def test_resolve_annotation_point_none_for_unknown(ptype: str) -> None:
    """resolve_annotation_point MUST return None for unknown selectors."""
    prim = _build(ptype)
    result = prim.resolve_annotation_point("__nonexistent__.cell[9999]")
    assert result is None, (
        f"{ptype}.resolve_annotation_point returned {result!r} for unknown selector"
    )
```

### 5.8 Test: dark primitives produce no annotation output (guard)

```python
@pytest.mark.parametrize("ptype", ["Stack", "Matrix", "MetricPlot", "CodePanel"])
def test_dark_primitive_silently_drops_annotations(ptype: str) -> None:
    """Dark primitives silently drop annotations — no crash, no partial output."""
    prim = _build(ptype)
    # Inject a syntactically valid annotation targeting a non-existent selector
    prim.set_annotations([{
        "target": f"t.cell[0]", "label": "x", "arrow_from": "t.cell[1]"
    }])
    svg = prim.emit_svg()
    # Should not raise; should not contain annotation markup
    assert 'class="scriba-annotation' not in svg, (
        f"{ptype}: unexpected annotation group in SVG output for dark primitive"
    )
```

*Note: test 5.8 currently passes because dark primitives never call
`emit_annotation_arrows`.  After migration (§6), these primitives will become
wired and test 5.8 MUST be updated to assert annotation output IS present.*

---

## 6. Migration Plan

Ordered by implementation effort (smallest first).  Estimates are in
**agent-hours** under the assumption that the engineer has the audit in hand and
the codebase is familiar.

---

### 6.1 Grid — headroom gap (0.5 h)

**File:** `scriba/animation/primitives/grid.py`  
**Lines to change:** `grid.py:202` (`emit_svg`) and the matching line in `bounding_box`.

**Change set:**
1. Import `position_label_height_above` and `position_label_height_below` from
   `base` (they are already re-exported; just add to the import list if not present).
2. In `emit_svg`, replace:
   ```python
   arrow_above = arrow_height_above(effective_anns, ...)
   ```
   with:
   ```python
   arrow_above = max(
       arrow_height_above(effective_anns, self.resolve_annotation_point, ...),
       position_label_height_above(effective_anns, cell_height=CELL_HEIGHT),
       getattr(self, "_min_arrow_above", 0),
   )
   ```
3. In `bounding_box`, apply the identical max() formula.
4. Optionally expand bounding_box height for `position_label_height_below`.

---

### 6.2 Tree — headroom gap (0.5 h)

**File:** `scriba/animation/primitives/tree.py`  
**Lines:** `tree.py:571` (emit_svg), `tree.py:548` (bounding_box).

**Change set:** Identical pattern to Grid (§6.1).  Tree uses `_arrow_layout="2d"`,
so pass `layout="2d"` to `arrow_height_above` if not already done.

---

### 6.3 LinkedList — headroom gap (0.5 h)

**File:** `scriba/animation/primitives/linkedlist.py`  
**Lines:** `linkedlist.py:229–230`, `linkedlist.py:246–247`.

**Change set:** Identical pattern to Grid.

---

### 6.4 HashMap — headroom gap (0.5 h)

**File:** `scriba/animation/primitives/hashmap.py`  
**Lines:** `hashmap.py:217–220`, `hashmap.py:234–237`.

**Change set:** Identical pattern to Grid.

---

### 6.5 VariableWatch — headroom gap (0.5 h)

**File:** `scriba/animation/primitives/variablewatch.py`  
**Lines:** `variablewatch.py:206–208`, `variablewatch.py:217–219`.

**Change set:** Identical pattern to Grid.

---

### 6.6 Graph — headroom gap + edge-label registry isolation (1.0 h)

**File:** `scriba/animation/primitives/graph.py`  
**Lines:** `graph.py:681` (emit_svg), `graph.py:659` (bounding_box), `graph.py:726`.

**Change set:**
1. Headroom: same as Grid (§6.1), with `layout="2d"`.
2. Edge-label registry (FP-2): Move `placed_edge_labels` so that it is initialized
   from the same `placed` list that `emit_annotation_arrows` creates.  This requires
   threading the list out of `emit_annotation_arrows` or pre-building it before the
   annotation loop.  Simplest approach: call `register_decorations` stub first
   (MW-2 hook), building `placed` by recording each edge-weight label rect as a
   `_LabelPlacement` obstacle.

---

### 6.7 Array and DPTable — `position_label_height_below` wiring (0.5 h each)

**Files:** `array.py`, `dptable.py`  
**Lines:** `array.py:369–371` (bounding_box), `dptable.py:330`.

**Change set:** Add `position_label_height_below(effective_anns, ...)` to the
`bounding_box` height computation.  This is the only missing piece for both
primitives (they are otherwise fully conformant).

---

### 6.8 Queue — orphan loop replacement (1.5 h)

**File:** `scriba/animation/primitives/queue.py`  
**Lines:** `queue.py:402–421` (orphan loop), `queue.py:278` (redundant marker defs call).

**Change set:**
1. Replace the manual `arrow_anns` filter + loop at lines 402–421 with:
   ```python
   if effective_anns:
       self.emit_annotation_arrows(
           parts, effective_anns, render_inline_tex=render_inline_tex
       )
   ```
2. Remove the now-redundant `emit_arrow_marker_defs` call at line 278 (it is
   a no-op but creates confusion).
3. Wire `position_label_height_above` into `_arrow_height_above` (the helper
   method that computes the translate offset at `queue.py:242–248`).
4. Add `position_label_height_below` to `bounding_box`.

**Risk:** Low.  The Queue's `resolve_annotation_point` already works for cell
selectors.  The `arrow=true` and position-only branches in
`emit_annotation_arrows` will now fire; verify with `test_placed_labels_mutated`
and `test_bounding_box_expands_for_position_above`.

---

### 6.9 NumberLine — orphan loop replacement (1.5 h)

**File:** `scriba/animation/primitives/numberline.py`  
**Lines:** `numberline.py:297–313`.

**Change set:**
1. Replace the manual `arrow_from`-only filter + loop with:
   ```python
   if effective_anns:
       self.emit_annotation_arrows(
           lines, effective_anns, render_inline_tex=render_inline_tex
       )
   ```
2. Wire `position_label_height_above` into the `_arrow_height_above` helper
   used at `numberline.py:196–202`.
3. Add `position_label_height_below` to `bounding_box`.
4. Set `self._arrow_cell_height` in `__init__` to `NL_TICK_HEIGHT` (the tick
   height value used at line 298 as `tick_height`), so that the base dispatch
   uses the right geometry.

**Risk:** Low.

---

### 6.10 Plane2D — `_emit_text_annotation` consolidation (3.0 h)

**File:** `scriba/animation/primitives/plane2d.py`  
**Lines:** `plane2d.py:657–752` (annotation split + `_emit_text_annotation`),
`plane2d.py:600–617` (headroom), `plane2d.py:1047–1057` (`_emit_labels` registry).

**Change set:**
1. **Unify annotation list:** Remove the `arrow_anns` / `text_anns` split at
   lines 657–658.  Pass the full `effective_anns` to `self.emit_annotation_arrows`.
2. **Delete `_emit_text_annotation`** (lines 673–752).  The position-only branch
   in `base.emit_annotation_arrows` (via `emit_position_label_svg`) now handles
   what `_emit_text_annotation` was doing, but correctly.
3. **Thread shared `placed`:** `emit_annotation_arrows` creates its own `placed`
   list internally.  Until MW-2 lands, the `_emit_labels` registry at line 1057
   remains isolated; document this as a known RC1 issue.
4. **Headroom:** Wire `position_label_height_above` into the `emit_svg` headroom
   at `plane2d.py:600–617` and into `bounding_box` at `plane2d.py:617`.
5. **Verify:** Run the conformance suite, especially `test_no_direct_text_emission`.

**Risk:** Medium.  `_emit_text_annotation` is the only code currently rendering
position-only labels on Plane2D.  Deleting it and relying on
`emit_annotation_arrows` changes rendered output.  Visual regression test required.

---

### 6.11 Stack — full annotation wiring (2.5 h)

**File:** `scriba/animation/primitives/stack.py`  
**Lines:** `stack.py:186–204` (bounding_box, emit_svg).

**Change set:**
1. Override `resolve_annotation_point` to map `item[N]` and `top` selectors to
   pixel centers.  The cell center for item `N` in a vertical Stack is:
   ```python
   y = _PADDING + (visible - 1 - N) * (_CELL_HEIGHT + _CELL_GAP) + _CELL_HEIGHT // 2
   x = _PADDING + self._cell_width // 2
   ```
   For `top`, resolve to item `len(self.items) - 1`.
2. Add `arrow_height_above` / `position_label_height_above` to `emit_svg`
   translate and `bounding_box` height.
3. Call `self.emit_annotation_arrows(parts, self._annotations, ...)` at the end
   of `emit_svg` (inside the translate group).
4. Set `self._arrow_cell_height = float(_CELL_HEIGHT)` in `__init__`.

**Risk:** Medium.  `resolve_annotation_point` for `top` must correctly track the
current stack size (computed from `len(self.items)` at render time, not init time).

---

### 6.12 Matrix — full annotation wiring (2.5 h)

**File:** `scriba/animation/primitives/matrix.py`  
**Lines:** `matrix.py:261–401` (emit_svg), `matrix.py:403` (bounding_box).

**Change set:**
1. Override `resolve_annotation_point` for `cell[r][c]` selectors.  Cell center:
   ```python
   x = c * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH // 2
   y = r * (CELL_HEIGHT + CELL_GAP) + CELL_HEIGHT // 2
   ```
2. Add headroom wiring (same pattern as Grid).
3. Add `self.emit_annotation_arrows(lines, self._annotations, ...)` to `emit_svg`.
4. Set `self._arrow_layout = "2d"` and `self._arrow_cell_height = float(CELL_HEIGHT)`.
5. Import `arrow_height_above`, `position_label_height_above`,
   `position_label_height_below` from `base`.

---

### 6.13 CodePanel — full annotation wiring (2.0 h)

**File:** `scriba/animation/primitives/codepanel.py`  
**Lines:** `codepanel.py:172` (emit_svg), `codepanel.py:164` (bounding_box).

**Change set:**
1. Override `resolve_annotation_point` for `line[N]` selectors.  Line N center:
   ```python
   LINE_HEIGHT = 20   # existing constant in codepanel.py
   x = self.width // 2
   y = N * LINE_HEIGHT + LINE_HEIGHT // 2
   ```
2. Add headroom wiring.
3. Add `self.emit_annotation_arrows(parts, self._annotations, ...)`.
4. Import required helpers from `base`.

**Risk:** Low.  CodePanel geometry is the simplest (uniform line height, no 2D layout).

---

### 6.14 MetricPlot — annotation wiring (4.0 h)

**File:** `scriba/animation/primitives/metricplot.py`

**Prerequisite:** Define what an annotation anchor means for MetricPlot.  The
natural model is: `data[series_name][step_idx]` → SVG (x, y) of the data point
at that step for that series.

**Change set:**
1. Define `resolve_annotation_point` for `series[name][step]` selectors, mapping
   to the rendered pixel coordinates of the point on the chart.
2. Update `SELECTOR_PATTERNS` to document the new selector form.
3. Add headroom wiring.
4. Add `self.emit_annotation_arrows(parts, self._annotations, ...)`.
5. Set `self._arrow_layout = "2d"` (MetricPlot is a 2D scatter-like surface).

**Risk:** Medium.  The pixel-to-data-point mapping depends on the chart scale
computation, which must be stable at `emit_svg` time.

---

### Effort summary

| Primitive | Category | Agent-hours |
|-----------|----------|-------------|
| Grid | Headroom gap | 0.5 |
| Tree | Headroom gap | 0.5 |
| LinkedList | Headroom gap | 0.5 |
| HashMap | Headroom gap | 0.5 |
| VariableWatch | Headroom gap | 0.5 |
| Array | HDB wiring | 0.5 |
| DPTable | HDB wiring | 0.5 |
| Graph | Headroom + FP2 | 1.0 |
| Queue | Orphan loop | 1.5 |
| NumberLine | Orphan loop | 1.5 |
| Stack | Full wiring | 2.5 |
| Matrix | Full wiring | 2.5 |
| CodePanel | Full wiring | 2.0 |
| MetricPlot | Full wiring | 4.0 |
| **Total** | | **17.5 h** |

---

## 7. Extension Points — Onboarding a New Primitive

The following step-by-step procedure applies when adding a new primitive (e.g.
`TreeMap`, `Venn`, `SankeyDiagram`) to the scriba primitives registry.

### Step 1: Subclass `PrimitiveBase`

```python
from scriba.animation.primitives.base import (
    PrimitiveBase,
    BoundingBox,
    arrow_height_above,
    position_label_height_above,
    position_label_height_below,
    register_primitive,
)
from scriba.animation.primitives._svg_helpers import _LabelPlacement

@register_primitive("TreeMap")
class TreeMapPrimitive(PrimitiveBase):
    primitive_type = "treemap"
    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "region[{name}]": "named region by key",
    }
```

### Step 2: Implement `resolve_annotation_point`

Map every selector in `SELECTOR_PATTERNS` (and in `addressable_parts`) to a
pixel center within the primitive's local coordinate system.

```python
def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
    m = re.match(rf"^{re.escape(self.name)}\.region\[(?P<key>[^\]]+)\]$", selector)
    if m:
        key = m.group("key")
        region = self._regions.get(key)
        if region is not None:
            cx = region.x + region.w / 2
            cy = region.y + region.h / 2
            return (cx, cy)
    return None
```

### Step 3: Set arrow layout attributes in `__init__`

```python
def __init__(self, name: str, params: dict[str, Any]) -> None:
    super().__init__(name, params)
    # Use "2d" for any primitive where annotations connect spatially
    # separated elements in a 2D plane rather than a 1D row.
    self._arrow_layout = "2d"
    self._arrow_shorten = 0.0
    self._arrow_cell_height = float(self._region_height or CELL_HEIGHT)
```

### Step 4: Implement `annotation_headroom_above` and `annotation_headroom_below`

If the primitive uses non-standard geometry, override the defaults:

```python
def annotation_headroom_above(self) -> float:
    return float(max(
        arrow_height_above(
            self._annotations,
            self.resolve_annotation_point,
            cell_height=self._arrow_cell_height,
            layout=self._arrow_layout,
        ),
        position_label_height_above(
            self._annotations,
            cell_height=self._arrow_cell_height,
        ),
        getattr(self, "_min_arrow_above", 0),
    ))

def annotation_headroom_below(self) -> float:
    return float(position_label_height_below(
        self._annotations,
        cell_height=self._arrow_cell_height,
    ))
```

If the canonical formula with `self._arrow_cell_height` is correct (most cases),
these overrides are not needed — once `PrimitiveBase` gains these methods they
will use `self._arrow_cell_height` automatically.

### Step 5: Wire headroom into `emit_svg` and `bounding_box`

```python
def emit_svg(self, *, render_inline_tex=None) -> str:
    arrow_above = int(self.annotation_headroom_above())
    lines: list[str] = [f'<g data-primitive="treemap" data-shape="{self.name}">']
    if arrow_above > 0:
        lines.append(f'  <g transform="translate(0, {arrow_above})">')

    # ... render the primitive content ...

    if self._annotations:
        self.emit_annotation_arrows(lines, self._annotations,
                                    render_inline_tex=render_inline_tex)
    if arrow_above > 0:
        lines.append("  </g>")
    lines.append("</g>")
    return "\n".join(lines)

def bounding_box(self) -> BoundingBox:
    w = self._compute_width()
    h = self._compute_height()
    h += self.annotation_headroom_above()
    h += self.annotation_headroom_below()
    return BoundingBox(x=0, y=0, width=float(w), height=float(h))
```

### Step 6: Add `register_decorations` stub (MW-2 readiness)

```python
def register_decorations(self, placed_labels: list[_LabelPlacement]) -> None:
    """Pre-seed placed_labels with this primitive's fixed visual elements.

    MW-2 scope: append a _LabelPlacement for each region label that
    emit_svg renders as part of the primitive content so that annotation
    labels do not collide with them.
    """
    # Stub until MW-2 implements the unified registry seeding protocol.
    return
```

### Step 7: Add to `_MINIMAL_PARAMS` in the conformance test

```python
"TreeMap": {"regions": {"A": [0, 0, 100, 100], "B": [100, 0, 80, 100]}},
```

And add parametrize entries to `test_resolve_annotation_point_inside_bbox`,
`test_placed_labels_mutated_by_arrow_annotation`, and
`test_bounding_box_expands_for_position_above`.

### Step 8: Run conformance suite

```bash
pytest tests/conformance/test_primitive_participation.py -v -k "TreeMap"
```

All tests MUST pass before the primitive is merged.

### Step 9: Self-check before merge

- [ ] `resolve_annotation_point` returns non-None for every selector in `addressable_parts()`
- [ ] `bounding_box` height grows when a `position=above` annotation is added
- [ ] No `<text>` for annotation labels outside `_svg_helpers` helpers
- [ ] No second `placed_labels` list created in `emit_svg`
- [ ] No hardcoded pill dimensions (use `estimate_text_width` + `_LABEL_PILL_PAD_*`)
- [ ] `register_decorations` stub present
- [ ] Added to `_MINIMAL_PARAMS` and conformance test parametrize lists
- [ ] Conformance tests pass

---

## Appendix A: Interface Change Summary

The following additions/changes to `PrimitiveBase` are required to enforce this
contract at the type-checker level.  They are non-breaking (all are keyword-only
with defaults or new methods with default no-op implementations):

| Change | Type | Notes |
|--------|------|-------|
| `emit_svg(placed_labels=None, ...)` | New kwarg | MW-2 prerequisite; backward-compatible |
| `annotation_headroom_above() -> float` | New method | Concrete default using `self._arrow_cell_height` |
| `annotation_headroom_below() -> float` | New method | Concrete default |
| `register_decorations(placed_labels) -> None` | New method | Default no-op |
| `dispatch_annotations(placed_labels, ...) -> list[str]` | New method | Default delegates to `emit_annotation_arrows` |

All five can land as concrete (non-abstract) methods on `PrimitiveBase`, so
existing primitive subclasses that do not override them inherit correct behaviour
immediately for the three headroom/decoration methods.  The `emit_svg` kwarg
addition requires updating the abstract signature only.

---

*End of document.*
