"""Shared arrow annotation SVG rendering infrastructure for animation primitives.

Extracted from base.py (Wave C1 split). Re-exported from base.py for
backward compatibility — all existing imports from base.py continue to work.

placed_labels contract
----------------------
Callers MUST initialize one ``placed_labels: list[_LabelPlacement] = []``
before all annotation loops for a given frame and pass the **same list** to
every call of both ``emit_plain_arrow_svg`` and ``emit_arrow_svg`` within
that frame.  Sharing the list is what lets the collision-avoidance nudge
account for labels placed by both helper functions.  Using a fresh list per
call defeats overlap detection across annotation types.
"""

from __future__ import annotations

import math
import os
import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterator

from scriba.animation.primitives._text_render import _escape_xml, estimate_text_width
from scriba.animation.primitives._types import CELL_HEIGHT

# Match inline math delimited by single `$`. Non-greedy; rejects empty bodies.
_MATH_DELIM_RE = re.compile(r"\$[^$]+?\$")

# Gate debug annotation comments behind an env var so they never leak into
# production HTML.  Set SCRIBA_DEBUG_LABELS=1 to enable.
_DEBUG_LABELS: bool = os.getenv("SCRIBA_DEBUG_LABELS") == "1"

if TYPE_CHECKING:  # pragma: no cover - type checking only
    pass


__all__ = [
    # Label placement
    "_LABEL_MAX_WIDTH_CHARS",
    "_LABEL_PILL_PAD_X",
    "_LABEL_PILL_PAD_Y",
    "_LABEL_PILL_RADIUS",
    "_LABEL_BG_OPACITY",
    "_LABEL_HEADROOM",
    "_PLAIN_ARROW_STEM",
    "_LEADER_DISPLACEMENT_THRESHOLD",
    "_LabelPlacement",
    "_nudge_candidates",
    "_wrap_label_lines",
    "_place_pill",
    # Arrow styles and rendering
    "ARROW_STYLES",
    "emit_plain_arrow_svg",
    "emit_arrow_svg",
    "emit_position_label_svg",
    "arrow_height_above",
    "position_label_height_above",
    "position_label_height_below",
    "emit_arrow_marker_defs",
]


# ---------------------------------------------------------------------------
# Smart label placement constants & helpers
# ---------------------------------------------------------------------------

_LABEL_MAX_WIDTH_CHARS = 24
_LABEL_PILL_PAD_X = 6
_LABEL_PILL_PAD_Y = 3
_LABEL_PILL_RADIUS = 4
_LABEL_BG_OPACITY = 0.92
_LABEL_HEADROOM = 24
# Length of the straight stem for plain arrow=true annotations (no source arc).
_PLAIN_ARROW_STEM = 18
# R-07: Leader-line displacement threshold — scale-relative minimum.
# A leader is emitted when the label is nudged more than this many pixels from
# its natural anchor.  The threshold is computed per-call as max(pill_h, 20) so
# it scales with pill height rather than being a fixed constant.  The constant
# below is kept for backward compatibility with any callers that reference it
# directly; the per-call formula supersedes it in emit_arrow_svg.
_LEADER_DISPLACEMENT_THRESHOLD: float = 20.0


@dataclass(slots=True)
class _LabelPlacement:
    """Tracks the bounding box of a placed annotation label for collision avoidance."""

    x: float
    y: float
    width: float
    height: float

    def overlaps(self, other: "_LabelPlacement") -> bool:
        """Return True if this placement overlaps *other*."""
        return not (
            self.x + self.width / 2 < other.x - other.width / 2
            or self.x - self.width / 2 > other.x + other.width / 2
            or self.y + self.height / 2 < other.y - other.height / 2
            or self.y - self.height / 2 > other.y + other.height / 2
        )


def _label_has_math(text: str) -> bool:
    """True if *text* contains at least one ``$...$`` inline math fragment."""
    return bool(text) and bool(_MATH_DELIM_RE.search(text))


# Ordered 8-direction compass list used by _nudge_candidates.
# Tie-break priority: N, S, E, W, NE, NW, SE, SW.
# Each entry is (dx_sign, dy_sign) where values are -1, 0, or +1.
_COMPASS_8 = (
    (0, -1),    # 0: N
    (0, +1),    # 1: S
    (+1, 0),    # 2: E
    (-1, 0),    # 3: W
    (+1, -1),   # 4: NE
    (-1, -1),   # 5: NW
    (+1, +1),   # 6: SE
    (-1, +1),   # 7: SW
)

# Half-plane preferred direction indices for side hints.
# Only strictly-preferred half-plane directions (not neutral E/W or N/S) are
# listed here so that test_side_hint_above_upper_first can assert all first-4
# candidates have dy < 0.  Neutral directions (E/W for above/below, N/S for
# left/right) are included in the "other" group that comes second.
_SIDE_HINT_PREFERRED: dict[str, tuple[int, ...]] = {
    "above": (0, 4, 5),   # N, NE, NW  (all dy < 0)
    "below": (1, 6, 7),   # S, SE, SW  (all dy > 0)
    "left":  (3, 5, 7),   # W, NW, SW  (all dx < 0)
    "right": (2, 4, 6),   # E, NE, SE  (all dx > 0)
}


def _nudge_candidates(
    pill_w: float,
    pill_h: float,
    side_hint: str | None = None,
) -> Iterator[tuple[float, float]]:
    """Yield (dx, dy) nudge offsets in Manhattan-distance order for collision resolution.

    Generates 32 candidates = 8 compass directions x 4 step sizes.

    Step sizes are fractions of *pill_h*: 0.25, 0.5, 1.0, 1.5.
    Both horizontal and vertical steps use *pill_h*-based sizing so the grid
    is square in pixel space.

    Within the same Manhattan distance, candidates follow the fixed priority:
    N, S, E, W, NE, NW, SE, SW.

    When *side_hint* is one of ``"above"``, ``"below"``, ``"left"``, ``"right"``,
    the strictly-preferred half-plane candidates (e.g. N, NE, NW for "above")
    are emitted first across all step sizes (sorted by Manhattan distance),
    followed by the remaining candidates in Manhattan-distance order.

    When *side_hint* is ``None`` or unknown, all 32 candidates are sorted by
    Manhattan distance (smallest first) with the fixed tie-break direction
    priority.

    Parameters
    ----------
    pill_w:
        Pill width in pixels (unused for step sizing; retained for API
        symmetry in case callers want aspect-aware steps in the future).
    pill_h:
        Pill height in pixels.  Steps are multiples of this value.
    side_hint:
        Optional placement preference: ``"above"``, ``"below"``, ``"left"``,
        or ``"right"``.  When provided, candidates in the preferred half-plane
        are emitted before the rest.

    Yields
    ------
    tuple[float, float]
        ``(dx, dy)`` offset tuples, smallest Manhattan distance first.
        Within equal distance, order follows N, S, E, W, NE, NW, SE, SW.
    """
    steps = (pill_h * 0.25, pill_h * 0.5, pill_h * 1.0, pill_h * 1.5)

    # Build all 32 (dx, dy, priority_index) tuples.
    all_candidates: list[tuple[float, float, int]] = []
    for step in steps:
        for priority, (dx_sign, dy_sign) in enumerate(_COMPASS_8):
            dx = dx_sign * step
            dy = dy_sign * step
            all_candidates.append((dx, dy, priority))

    def _manhattan(c: tuple[float, float, int]) -> float:
        return abs(c[0]) + abs(c[1])

    hint_key = side_hint if side_hint in _SIDE_HINT_PREFERRED else None

    if hint_key is None:
        # No side hint: sort all 32 by (manhattan_distance, priority_index).
        sorted_candidates = sorted(all_candidates, key=lambda c: (_manhattan(c), c[2]))
        for dx, dy, _ in sorted_candidates:
            yield (dx, dy)
    else:
        preferred_set = set(_SIDE_HINT_PREFERRED[hint_key])

        preferred = [c for c in all_candidates if c[2] in preferred_set]
        other = [c for c in all_candidates if c[2] not in preferred_set]

        sorted_preferred = sorted(preferred, key=lambda c: (_manhattan(c), c[2]))
        sorted_other = sorted(other, key=lambda c: (_manhattan(c), c[2]))

        for dx, dy, _ in sorted_preferred:
            yield (dx, dy)
        for dx, dy, _ in sorted_other:
            yield (dx, dy)


# Regex to match LaTeX command tokens like \frac, \sum, \alpha, etc.
_LATEX_CMD_RE = re.compile(r"\\[a-zA-Z]+")


def _label_width_text(text: str) -> str:
    r"""Return a width-estimation string derived from *text*.

    For plain text: returned unchanged.
    For math labels (containing ``$...$``):

    1. Strip ``$`` delimiters.
    2. Strip ``\\command`` tokens (``\\frac``, ``\\sum``, ``\\alpha``, etc.).
    3. Strip brace characters ``{`` and ``}``.
    4. Repeat the remaining characters by 1.15× (by appending a scaled
       suffix) so that ``estimate_text_width`` accounts for the structural
       overhead of rendered math, which KaTeX renders ~15 % wider than a
       naive character count suggests.

    The 1.15× factor is applied by returning a string whose estimated
    width, when passed to ``estimate_text_width``, equals the corrected
    estimate.  Because ``estimate_text_width`` is linear in character count
    for ASCII, repeating characters achieves the scale accurately.
    """
    if not text:
        return ""
    has_math = _label_has_math(text)
    # Strip $ delimiters from math spans.
    result = _MATH_DELIM_RE.sub(lambda m: m.group(0)[1:-1], text)
    if has_math:
        # Strip LaTeX command tokens and braces.
        result = _LATEX_CMD_RE.sub("", result)
        result = result.replace("{", "").replace("}", "")
        # Apply 1.15x scale by appending 15% extra characters.
        # We append a scaled copy of the stripped string so that
        # estimate_text_width(result_scaled) ≈ estimate_text_width(result) * 1.15.
        extra_len = max(1, int(len(result) * 0.15))
        result = result + result[:extra_len]
    return result


def _emit_label_single_line(
    *,
    label_text: str,
    fi_x: int,
    fi_y: int,
    pill_rx: int,
    pill_ry: int,
    pill_w: int,
    pill_h: int,
    l_fill: str,
    l_weight: str,
    l_size: str,
    render_inline_tex: "Callable[[str], str] | None",
) -> str:
    """Emit an annotation label as either ``<text>`` or KaTeX foreignObject.

    When *label_text* contains ``$...$`` math and a ``render_inline_tex``
    callback is available, the label is emitted as an SVG
    ``<foreignObject>`` hosting the KaTeX-rendered HTML centered inside the
    pill rectangle.  Falls back to plain SVG ``<text>`` otherwise.
    """
    if render_inline_tex is not None and _label_has_math(label_text):
        try:
            html = render_inline_tex(label_text)
        except Exception:
            html = None
        if html:
            weight_css = f"font-weight:{l_weight};" if l_weight else ""
            size_css = f"font-size:{l_size};" if l_size else ""
            return (
                f'    <foreignObject x="{pill_rx}" y="{pill_ry}"'
                f' width="{pill_w}" height="{pill_h}"'
                f' class="scriba-annot-fobj">'
                f'<div xmlns="http://www.w3.org/1999/xhtml"'
                f' class="scriba-annot-label"'
                f' style="width:100%;height:100%;display:flex;'
                f'align-items:center;justify-content:center;'
                f'text-align:center;line-height:1;'
                f'white-space:pre-wrap;gap:0.25em;'
                f'color:{l_fill};{weight_css}{size_css}'
                f'text-shadow:0 0 2px #fff,0 0 2px #fff;">'
                f'{html}</div></foreignObject>'
            )

    # Fallback: plain SVG <text> with halo.
    style_parts: list[str] = []
    if l_weight:
        style_parts.append(f"font-weight:{l_weight}")
    if l_size:
        style_parts.append(f"font-size:{l_size}")
    style_parts.append("text-anchor:middle")
    style_parts.append("dominant-baseline:auto")
    style_str = ";".join(style_parts)
    text_attrs = (
        f'x="{fi_x}" y="{fi_y}" fill="{l_fill}"'
        f' stroke="white" stroke-width="3"'
        f' stroke-linejoin="round" paint-order="stroke fill"'
    )
    return (
        f'    <text {text_attrs} style="{style_str}">'
        f'{_escape_xml(label_text)}</text>'
    )


def _wrap_label_lines(text: str, max_chars: int = _LABEL_MAX_WIDTH_CHARS) -> list[str]:
    """Split label text into lines at natural break points if it exceeds *max_chars*.

    Split characters: space, comma, ``+``, ``=``.  The ``-`` character is
    intentionally excluded from splitting to avoid breaking LaTeX math
    expressions like ``$f(x)=-4$`` across lines.  Inside ``$...$`` delimiters
    no splitting occurs at all (``in_math`` guard).
    """
    if len(text) <= max_chars:
        return [text]
    # Split at spaces, operators, commas — but NOT inside $...$ math regions.
    tokens: list[str] = []
    current = ""
    in_math = False
    for ch in text:
        if ch == "$":
            in_math = not in_math
        current += ch
        if not in_math and ch in (" ", ",", "+", "="):
            tokens.append(current)
            current = ""
    if current:
        tokens.append(current)

    lines: list[str] = []
    line = ""
    for tok in tokens:
        if line and len(line) + len(tok) > max_chars:
            lines.append(line.rstrip())
            line = tok
        else:
            line += tok
    if line:
        lines.append(line.rstrip())
    return lines if lines else [text]


# ---------------------------------------------------------------------------
# Shared arrow annotation infrastructure
# ---------------------------------------------------------------------------

# Annotation pill labels (ARROW_STYLES "label_fill") are rendered on a white
# semi-opaque pill background (fill="white" fill-opacity="0.92").  All label_fill
# values below have been verified ≥ 4.5:1 against white (WCAG AA, 2026-04-17):
#   good  #027a55 → 5.36:1   info   #506882 → 5.76:1
#   warn  #92600a → 5.38:1   error  #c6282d → 5.61:1
#   muted #526070 → 6.43:1   path   #2563eb → 5.17:1
ARROW_STYLES: dict[str, dict[str, str]] = {
    "good": {
        "stroke": "#027a55",      # darkened from #059669 (3.77:1 ✗) → 5.36:1 ✓
        "stroke_width": "2.2",
        "opacity": "1.0",
        "label_fill": "#027a55",
        "label_weight": "700",
        "label_size": "12px",
    },
    "info": {
        "stroke": "#506882",      # darkened from #94a3b8 (2.56:1 ✗) → 5.76:1 ✓
        "stroke_width": "1.5",
        "opacity": "0.45",
        "label_fill": "#506882",
        "label_weight": "500",
        "label_size": "11px",
    },
    "warn": {
        "stroke": "#92600a",      # darkened from #d97706 (3.19:1 ✗) → 5.38:1 ✓
        "stroke_width": "2.0",
        "opacity": "0.8",
        "label_fill": "#92600a",
        "label_weight": "600",
        "label_size": "11px",
    },
    "error": {
        "stroke": "#c6282d",      # darkened from #dc2626 (4.83:1 ✗) → 5.61:1 ✓
        "stroke_width": "2.0",
        "opacity": "0.8",
        "label_fill": "#c6282d",
        "label_weight": "600",
        "label_size": "11px",
    },
    "muted": {
        "stroke": "#526070",      # darkened from #cbd5e1 (1.48:1 ✗) → 6.43:1 ✓
        "stroke_width": "1.2",
        "opacity": "0.3",
        "label_fill": "#526070",
        "label_weight": "500",
        "label_size": "11px",
    },
    "path": {
        "stroke": "#2563eb",      # unchanged — 5.17:1 ✓ on white
        "stroke_width": "2.5",
        "opacity": "1.0",
        "label_fill": "#2563eb",
        "label_weight": "700",
        "label_size": "12px",
    },
}


def emit_plain_arrow_svg(
    lines: list[str],
    ann: dict[str, Any],
    dst_point: tuple[float, float],
    render_inline_tex: "Callable[[str], str] | None" = None,
    placed_labels: "list[_LabelPlacement] | None" = None,
    _debug_capture: "dict[str, Any] | None" = None,
) -> None:
    """Emit a short straight pointer arrow for ``arrow=true`` annotations.

    ``arrow=true`` means "draw an arrowhead pointing at the target with no
    source arc".  A short vertical stem originates from
    ``_PLAIN_ARROW_STEM`` pixels above the target cell top edge, and an
    inline arrowhead polygon points downward into the target.

    Parameters
    ----------
    lines:
        Output buffer — SVG markup is appended in-place.
    ann:
        Annotation dict with keys ``target``, optional ``color``, and
        optional ``label``.
    dst_point:
        ``(x, y)`` SVG coordinates of the target cell center (top edge).
    render_inline_tex:
        Optional callback for rendering ``$...$`` math in labels.
    placed_labels:
        Shared mutable list of already-placed label bounding boxes used for
        collision avoidance.  Callers MUST pass the **same** list to every
        ``emit_plain_arrow_svg`` and ``emit_arrow_svg`` call within a single
        frame so that cross-annotation overlap detection works correctly.
        When provided, the final placement is appended to this list.
    """
    color = ann.get("color", "info")
    label_text = ann.get("label", "")
    target = ann.get("target", "")

    x2, y2 = float(dst_point[0]), float(dst_point[1])
    x1, y1 = x2, y2 - _PLAIN_ARROW_STEM

    # Resolve inline style for this color
    style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
    s_stroke = style["stroke"]
    s_width = style["stroke_width"]
    s_opacity = style["opacity"]

    ann_desc = f"Pointer to {_escape_xml(str(target))}"
    if label_text:
        ann_desc += f": {_escape_xml(label_text)}"

    # Inline arrowhead polygon pointing straight down into the target.
    arrow_size = 10
    # Direction: straight down (unit vector = (0, 1))
    aux, auy = 0.0, 1.0
    apx, apy = -auy, aux  # perpendicular = (-1, 0)
    hw = arrow_size * 0.5
    ix2, iy2 = int(x2), int(y2)
    p1x, p1y = float(ix2), float(iy2)
    p2x = p1x - aux * arrow_size + apx * hw
    p2y = p1y - auy * arrow_size + apy * hw
    p3x = p1x - aux * arrow_size - apx * hw
    p3y = p1y - auy * arrow_size - apy * hw
    arrow_points = (
        f"{p1x:.1f},{p1y:.1f} {p2x:.1f},{p2y:.1f} {p3x:.1f},{p3y:.1f}"
    )

    ix1, iy1 = int(x1), int(y1)

    ann_key = f"{target}-plain-arrow"
    lines.append(
        f'  <g class="scriba-annotation scriba-annotation-{color}"'
        f' data-annotation="{_escape_xml(ann_key)}"'
        f' opacity="{s_opacity}"'
        f' role="graphics-symbol" aria-label="{ann_desc}">'
    )
    lines.append(
        f'    <line x1="{ix1}" y1="{iy1}" x2="{ix2}" y2="{iy2}"'
        f' stroke="{s_stroke}" stroke-width="{s_width}"/>'
    )
    lines.append(
        f'    <polygon points="{arrow_points}" fill="{s_stroke}"/>'
    )

    if label_text:
        l_fill = style["label_fill"]
        l_weight = style["label_weight"]
        l_size = style["label_size"]
        l_font_px = int(l_size.replace("px", "")) if l_size.endswith("px") else 11

        # Do not wrap when math is present — would split inside $...$.
        if _label_has_math(label_text):
            label_lines = [label_text]
        else:
            label_lines = _wrap_label_lines(label_text)
        line_height = l_font_px + 2
        num_lines = len(label_lines)

        max_line_w = max(
            estimate_text_width(_label_width_text(ln), l_font_px)
            for ln in label_lines
        )
        pill_w = max_line_w + _LABEL_PILL_PAD_X * 2
        pill_h = num_lines * line_height + _LABEL_PILL_PAD_Y * 2

        # Label sits above the stem start
        natural_x = float(ix1)
        natural_y = float(iy1) - pill_h / 2 - 2
        final_x = natural_x
        final_y = natural_y

        # Populate debug capture dict for testing (zero overhead when None).
        if _debug_capture is not None:
            _debug_capture["final_y"] = final_y
            _debug_capture["l_font_px"] = l_font_px
            _debug_capture["pill_w"] = pill_w
            _debug_capture["pill_h"] = pill_h

        # MW-1: Extract side hint from annotation for half-plane preference.
        anchor_side = ann.get("side") or ann.get("position") or None

        collision_unresolved = False
        if placed_labels is not None:
            # HIGH #2: initial candidate uses center-corrected y so overlap
            # geometry during nudge matches the registered placement geometry.
            candidate_y = final_y - l_font_px * 0.3
            candidate = _LabelPlacement(
                x=final_x, y=candidate_y, width=float(pill_w), height=float(pill_h),
            )
            if not any(candidate.overlaps(p) for p in placed_labels):
                pass  # natural position is free — no nudge needed
            else:
                # MW-1: 8-direction grid search at 4 step sizes (32 candidates).
                resolved = False
                for ndx, ndy in _nudge_candidates(float(pill_w), float(pill_h), side_hint=anchor_side):
                    test = _LabelPlacement(
                        x=final_x + ndx,
                        y=candidate_y + ndy,
                        width=float(pill_w),
                        height=float(pill_h),
                    )
                    if not any(test.overlaps(p) for p in placed_labels):
                        candidate = test
                        resolved = True
                        break
                if not resolved:
                    # QW-2: all 32 candidates exhausted — keep last position.
                    collision_unresolved = True
            final_x = candidate.x
            # Reconstruct render y from candidate y (which carries the -0.3 correction).
            final_y = candidate.y + l_font_px * 0.3
            # QW-3: register the clamped x so collision avoidance for
            # subsequent labels uses the same coordinate as rendering.
            clamped_x = max(final_x, pill_w / 2)
            # QW-1: register y = candidate.y (already = final_y - l_font_px*0.3).
            placed_labels.append(_LabelPlacement(
                x=clamped_x,
                y=candidate.y,
                width=float(pill_w),
                height=float(pill_h),
            ))

        fi_x = int(final_x)
        fi_y = int(final_y)

        # QW-2: emit collision debug comment when all directions were exhausted.
        # HIGH #1: gated behind _DEBUG_LABELS so it never leaks into production.
        if collision_unresolved and _DEBUG_LABELS:
            target_id = ann.get("target", "unknown")
            lines.append(f"  <!-- scriba:label-collision id={target_id} -->")

        # R-19: unconditional stderr warning when placement is degraded.
        if collision_unresolved:
            _target_id = ann.get("target", "unknown")
            _disp = math.sqrt((float(fi_x) - natural_x) ** 2 + (float(fi_y) - natural_y) ** 2)
            sys.stderr.write(
                f"scriba:label-placement-degraded annotation={_target_id}"
                f" displacement={_disp:.1f}px\n"
            )

        pill_rx = max(0, int(fi_x - pill_w / 2))
        pill_ry = int(fi_y - pill_h / 2 - l_font_px * 0.3)
        fi_x = max(fi_x, pill_w // 2)
        lines.append(
            f'    <rect x="{pill_rx}" y="{pill_ry}"'
            f' width="{pill_w}" height="{pill_h}"'
            f' rx="{_LABEL_PILL_RADIUS}" ry="{_LABEL_PILL_RADIUS}"'
            f' fill="white" fill-opacity="{_LABEL_BG_OPACITY}"'
            f' stroke="{s_stroke}" stroke-width="0.5" stroke-opacity="0.3"/>'
        )

        if num_lines == 1:
            lines.append(
                _emit_label_single_line(
                    label_text=label_text,
                    fi_x=fi_x,
                    fi_y=fi_y,
                    pill_rx=pill_rx,
                    pill_ry=pill_ry,
                    pill_w=int(pill_w),
                    pill_h=int(pill_h),
                    l_fill=l_fill,
                    l_weight=l_weight,
                    l_size=l_size,
                    render_inline_tex=render_inline_tex,
                )
            )
        else:
            text_attrs = (
                f'x="{fi_x}" y="{fi_y}" fill="{l_fill}"'
                f' stroke="white" stroke-width="3"'
                f' stroke-linejoin="round" paint-order="stroke fill"'
            )
            style_parts = []
            if l_weight:
                style_parts.append(f"font-weight:{l_weight}")
            if l_size:
                style_parts.append(f"font-size:{l_size}")
            style_parts.append("text-anchor:middle")
            style_parts.append("dominant-baseline:auto")
            style_str = ";".join(style_parts)
            tspans = ""
            for li, ln_text in enumerate(label_lines):
                dy_val = f"{line_height}" if li > 0 else "0"
                tspans += (
                    f'<tspan x="{fi_x}" dy="{dy_val}">'
                    f"{_escape_xml(ln_text)}</tspan>"
                )
            lines.append(
                f'    <text {text_attrs} style="{style_str}">{tspans}</text>'
            )

    lines.append("  </g>")


def emit_arrow_svg(
    lines: list[str],
    ann: dict[str, Any],
    src_point: tuple[float, float],
    dst_point: tuple[float, float],
    arrow_index: int,
    cell_height: float,
    render_inline_tex: "Callable[[str], str] | None" = None,
    layout: str = "horizontal",
    shorten_src: float = 0.0,
    shorten_dst: float = 0.0,
    placed_labels: "list[_LabelPlacement] | None" = None,
    _debug_capture: "dict[str, Any] | None" = None,
) -> None:
    """Emit a cubic Bezier arrow annotation into *lines*.

    This is the shared arrow rendering used by Array, DPTable, and any
    future primitive that supports annotation arrows.  Each primitive is
    responsible for resolving selectors to SVG coordinates (via its own
    ``_cell_center`` / ``resolve_annotation_point``) and passing the
    results here.

    Parameters
    ----------
    lines:
        Output buffer -- SVG markup is appended in-place.
    ann:
        Annotation dict with keys ``target``, ``arrow_from``, and
        optional ``color`` and ``label``.
    src_point:
        ``(x, y)`` SVG coordinates of the arrow source.
    dst_point:
        ``(x, y)`` SVG coordinates of the arrow destination.
    arrow_index:
        Stagger index for multiple arrows targeting the same cell.
    cell_height:
        Cell height used for curve offset calculation.
    render_inline_tex:
        Optional callback for rendering ``$...$`` math in labels.
    layout:
        ``"horizontal"`` (default) curves upward for Array/DPTable etc.
        ``"2d"`` curves perpendicular to the source-destination line,
        suitable for Graph, Tree, Grid, and Plane2D.
    shorten_src:
        Pull the path start point toward the destination by this many
        pixels.  Useful for circular nodes so the arrow starts at the
        circle edge rather than the center.
    shorten_dst:
        Pull the path end point toward the source by this many pixels.
        Useful for circular nodes so the arrowhead stops at the circle
        edge rather than piercing into the node.
    placed_labels:
        Shared mutable list of already-placed label bounding boxes used for
        collision avoidance.  Callers MUST pass the **same** list to every
        ``emit_plain_arrow_svg`` and ``emit_arrow_svg`` call within a single
        frame so that cross-annotation overlap detection works correctly.
        When provided, the final placement is appended to this list.
    """
    color = ann.get("color", "info")
    label_text = ann.get("label", "")
    target = ann.get("target", "")
    arrow_from = ann.get("arrow_from", "")

    x1, y1 = float(src_point[0]), float(src_point[1])
    x2, y2 = float(dst_point[0]), float(dst_point[1])

    # Shorten endpoints toward each other (for circle-edge arrows)
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx * dx + dy * dy) or 1.0

    if shorten_src > 0 and dist > 0:
        x1 = x1 + (dx / dist) * shorten_src
        y1 = y1 + (dy / dist) * shorten_src
    if shorten_dst > 0 and dist > 0:
        x2 = x2 - (dx / dist) * shorten_dst
        y2 = y2 - (dy / dist) * shorten_dst

    # Recompute after shortening
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx * dx + dy * dy) or 1.0

    # Control points: sqrt-scaled curve height capped at 1.2x cell height,
    # with compact stagger for multiple arrows targeting the same cell.
    h_dist = abs(x2 - x1) + abs(y2 - y1)
    base_offset = min(cell_height * 1.2, max(cell_height * 0.5, math.sqrt(h_dist) * 2.5))
    stagger = cell_height * 0.3
    total_offset = base_offset + arrow_index * stagger

    if layout == "2d":
        # Perpendicular Bezier: curve away from the connecting line
        perp_x = -dy / dist
        perp_y = dx / dist

        mid_x_f = (x1 + x2) / 2
        mid_y_f = (y1 + y2) / 2

        cx1 = int((x1 + mid_x_f) / 2 + perp_x * total_offset)
        cy1 = int((y1 + mid_y_f) / 2 + perp_y * total_offset)
        cx2 = int((x2 + mid_x_f) / 2 + perp_x * total_offset)
        cy2 = int((y2 + mid_y_f) / 2 + perp_y * total_offset)

        label_ref_x = int(mid_x_f + perp_x * (total_offset + 8))
        label_ref_y = int(mid_y_f + perp_y * (total_offset + 8))
    else:
        # Horizontal layout: curve upward (original formula)
        mid_x_f = (x1 + x2) / 2
        mid_y_val = int(min(y1, y2) - total_offset)

        # When source and target are nearly vertically aligned (same column
        # in a 2D DPTable), the default control points collapse to a vertical
        # line.  Offset them horizontally to produce a visible arc.
        h_span = abs(x2 - x1)
        if h_span < 4:
            h_nudge = total_offset * 0.6
            cx1 = max(0, int(mid_x_f - h_nudge))
            cy1 = mid_y_val
            cx2 = max(0, int(mid_x_f - h_nudge))
            cy2 = mid_y_val
            # Clamp label X so pill doesn't go negative.
            # Estimate pill half-width from label text.
            _est_pill_hw = (
                estimate_text_width(label_text, 11) // 2 + _LABEL_PILL_PAD_X
                if label_text else 20
            )
            raw_lx = int(mid_x_f - h_nudge - 8)
            label_ref_x = max(raw_lx, _est_pill_hw)
            label_ref_y = mid_y_val - 4
        else:
            cx1 = int((x1 + mid_x_f) / 2)
            cy1 = mid_y_val
            cx2 = int((x2 + mid_x_f) / 2)
            cy2 = mid_y_val
            label_ref_x = int(mid_x_f)
            label_ref_y = mid_y_val - 4  # slightly above the curve peak

    # Curve midpoint B(0.5) for leader anchoring — evaluated from the actual
    # control points so the anchor dot sits ON the rendered curve, not on the
    # control-point plateau (which is ~25% above the true midpoint for cubic
    # Bézier when both controls share the same coordinate).
    curve_mid_x = int(0.125 * x1 + 0.375 * cx1 + 0.375 * cx2 + 0.125 * x2)
    curve_mid_y = int(0.125 * y1 + 0.375 * cy1 + 0.375 * cy2 + 0.125 * y2)

    ix1, iy1 = int(x1), int(y1)
    ix2, iy2 = int(x2), int(y2)

    # Resolve inline style for this color
    style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
    s_stroke = style["stroke"]
    s_width = style["stroke_width"]
    s_opacity = style["opacity"]

    ann_desc = (
        f"Arrow from {_escape_xml(str(arrow_from))} "
        f"to {_escape_xml(str(target))}"
    )
    if label_text:
        ann_desc += f": {_escape_xml(label_text)}"

    # Compute inline arrowhead polygon at the path endpoint.
    # This replaces SVG <marker> defs which have cross-browser issues
    # (Safari file://, innerHTML replacement, etc.).
    arrow_size = 10
    # Direction vector at the curve tip: approximate via last control
    # point → endpoint.
    adx = float(ix2 - cx2)
    ady = float(iy2 - cy2)
    ad = math.sqrt(adx * adx + ady * ady) or 1.0
    aux, auy = adx / ad, ady / ad       # unit vector toward tip
    apx, apy = -auy, aux                 # perpendicular
    hw = arrow_size * 0.5
    # Three vertices: tip, and two base corners
    p1x, p1y = ix2, iy2
    p2x = p1x - aux * arrow_size + apx * hw
    p2y = p1y - auy * arrow_size + apy * hw
    p3x = p1x - aux * arrow_size - apx * hw
    p3y = p1y - auy * arrow_size - apy * hw
    arrow_points = (
        f"{p1x:.1f},{p1y:.1f} {p2x:.1f},{p2y:.1f} {p3x:.1f},{p3y:.1f}"
    )

    ann_key = f"{target}-{arrow_from}" if arrow_from else f"{target}-solo"
    lines.append(
        f'  <g class="scriba-annotation scriba-annotation-{color}"'
        f' data-annotation="{_escape_xml(ann_key)}"'
        f' opacity="{s_opacity}"'
        f' role="graphics-symbol" aria-label="{ann_desc}">'
    )
    lines.append(
        f'    <path d="M{ix1},{iy1} C{cx1},{cy1} {cx2},{cy2} {ix2},{iy2}" '
        f'stroke="{s_stroke}" stroke-width="{s_width}" fill="none">'
        f'<title>{ann_desc}</title>'
        f'</path>'
    )
    lines.append(
        f'    <polygon points="{arrow_points}" fill="{s_stroke}"/>'
    )
    if label_text:
        l_fill = style["label_fill"]
        l_weight = style["label_weight"]
        l_size = style["label_size"]
        l_font_px = int(l_size.replace("px", "")) if l_size.endswith("px") else 11

        # Multi-line wrap (skip when math is present — would split inside $...$).
        if _label_has_math(label_text):
            label_lines = [label_text]
        else:
            label_lines = _wrap_label_lines(label_text)
        line_height = l_font_px + 2
        num_lines = len(label_lines)

        # Measure pill dimensions (strip $ delimiters for math labels)
        max_line_w = max(
            estimate_text_width(_label_width_text(ln), l_font_px)
            for ln in label_lines
        )
        pill_w = max_line_w + _LABEL_PILL_PAD_X * 2
        pill_h = num_lines * line_height + _LABEL_PILL_PAD_Y * 2

        # Natural label position
        natural_x = float(label_ref_x)
        natural_y = float(label_ref_y)
        final_x = natural_x
        final_y = natural_y

        # Populate debug capture dict for testing (zero overhead when None).
        if _debug_capture is not None:
            _debug_capture["final_y"] = final_y
            _debug_capture["l_font_px"] = l_font_px
            _debug_capture["pill_w"] = pill_w
            _debug_capture["pill_h"] = pill_h

        # MW-1: Extract side hint from annotation for half-plane preference.
        anchor_side = ann.get("side") or ann.get("position") or None

        # Collision avoidance
        collision_unresolved = False
        if placed_labels is not None:
            # HIGH #2: initial candidate uses center-corrected y so overlap
            # geometry during nudge matches the registered placement geometry.
            candidate_y = final_y - l_font_px * 0.3
            candidate = _LabelPlacement(
                x=final_x, y=candidate_y, width=float(pill_w), height=float(pill_h),
            )
            if not any(candidate.overlaps(p) for p in placed_labels):
                pass  # natural position is free — no nudge needed
            else:
                # MW-1: 8-direction grid search at 4 step sizes (32 candidates).
                resolved = False
                for ndx, ndy in _nudge_candidates(float(pill_w), float(pill_h), side_hint=anchor_side):
                    test = _LabelPlacement(
                        x=final_x + ndx,
                        y=candidate_y + ndy,
                        width=float(pill_w),
                        height=float(pill_h),
                    )
                    if not any(test.overlaps(p) for p in placed_labels):
                        candidate = test
                        resolved = True
                        break
                if not resolved:
                    # QW-2: all 32 candidates exhausted — keep last position.
                    collision_unresolved = True

            final_x = candidate.x
            # Reconstruct render y from candidate y (which carries the -0.3 correction).
            final_y = candidate.y + l_font_px * 0.3
            # QW-3: register clamped x so subsequent labels check the right coord.
            clamped_x = max(final_x, pill_w / 2)
            # QW-1: register y = candidate.y (already = final_y - l_font_px*0.3).
            placed_labels.append(_LabelPlacement(
                x=clamped_x,
                y=candidate.y,
                width=float(pill_w),
                height=float(pill_h),
            ))

        fi_x = int(final_x)
        fi_y = int(final_y)

        # QW-2: emit collision debug comment when all directions were exhausted.
        # HIGH #1: gated behind _DEBUG_LABELS so it never leaks into production.
        if collision_unresolved and _DEBUG_LABELS:
            target_id = ann.get("target", "unknown")
            lines.append(f"  <!-- scriba:label-collision id={target_id} -->")

        # R-19: unconditional stderr warning when placement is degraded.
        if collision_unresolved:
            _target_id = ann.get("target", "unknown")
            _disp = math.sqrt((float(fi_x) - natural_x) ** 2 + (float(fi_y) - natural_y) ** 2)
            sys.stderr.write(
                f"scriba:label-placement-degraded annotation={_target_id}"
                f" displacement={_disp:.1f}px\n"
            )

        # Background pill: white rect with rounded corners, before text
        # Clamp so pill doesn't extend outside the viewBox (x/y >= 0).
        pill_rx = max(0, int(fi_x - pill_w / 2))
        pill_ry = int(fi_y - pill_h / 2 - l_font_px * 0.3)
        # If pill was clamped, shift label text to stay centered in pill
        fi_x = max(fi_x, pill_w // 2)
        lines.append(
            f'    <rect x="{pill_rx}" y="{pill_ry}"'
            f' width="{pill_w}" height="{pill_h}"'
            f' rx="{_LABEL_PILL_RADIUS}" ry="{_LABEL_PILL_RADIUS}"'
            f' fill="white" fill-opacity="{_LABEL_BG_OPACITY}"'
            f' stroke="{s_stroke}" stroke-width="0.5" stroke-opacity="0.3"/>'
        )

        # Leader line: if label was nudged far from its natural position.
        # A-5 non-colour cue: warn token uses a dashed leader (stroke-dasharray
        # "3,2") to remain distinguishable from error (solid) under deuteranopia
        # (CIEDE2000 warn/error pairwise distance 2.8 under deuteranopia).
        # R-07: threshold is scale-relative — max(pill_h, _LEADER_DISPLACEMENT_THRESHOLD).
        displacement = math.sqrt(
            (final_x - natural_x) ** 2 + (final_y - natural_y) ** 2
        )
        _leader_threshold = max(float(pill_h), _LEADER_DISPLACEMENT_THRESHOLD)
        if displacement > _leader_threshold:
            leader_dasharray = ' stroke-dasharray="3,2"' if color == "warn" else ""
            lines.append(
                f'    <circle cx="{curve_mid_x}" cy="{curve_mid_y}" r="2"'
                f' fill="{s_stroke}" opacity="0.6"/>'
            )
            lines.append(
                f'    <polyline points="{curve_mid_x},{curve_mid_y}'
                f' {fi_x},{fi_y}"'
                f' fill="none" stroke="{s_stroke}"'
                f' stroke-width="0.75"{leader_dasharray}'
                f' opacity="0.6"/>'
            )

        # Render label text with paint-order halo (single-line dispatches
        # to KaTeX foreignObject when math is present).
        if num_lines == 1:
            lines.append(
                _emit_label_single_line(
                    label_text=label_text,
                    fi_x=fi_x,
                    fi_y=fi_y,
                    pill_rx=pill_rx,
                    pill_ry=pill_ry,
                    pill_w=int(pill_w),
                    pill_h=int(pill_h),
                    l_fill=l_fill,
                    l_weight=l_weight,
                    l_size=l_size,
                    render_inline_tex=render_inline_tex,
                )
            )
        else:
            # Multi-line — use tspan elements
            text_attrs = (
                f'x="{fi_x}" y="{fi_y}" fill="{l_fill}"'
                f' stroke="white" stroke-width="3"'
                f' stroke-linejoin="round" paint-order="stroke fill"'
            )
            style_parts = []
            if l_weight:
                style_parts.append(f"font-weight:{l_weight}")
            if l_size:
                style_parts.append(f"font-size:{l_size}")
            style_parts.append("text-anchor:middle")
            style_parts.append("dominant-baseline:auto")
            style_str = ";".join(style_parts)
            tspans = ""
            for li, ln_text in enumerate(label_lines):
                dy_val = f'{line_height}' if li > 0 else "0"
                tspans += (
                    f'<tspan x="{fi_x}" dy="{dy_val}">'
                    f'{_escape_xml(ln_text)}</tspan>'
                )
            lines.append(
                f'    <text {text_attrs} style="{style_str}">{tspans}</text>'
            )

    lines.append("  </g>")


def arrow_height_above(
    annotations: list[dict[str, Any]],
    cell_center_resolver: "Callable[[str], tuple[float, float] | None]",
    cell_height: float = CELL_HEIGHT,
    layout: str = "horizontal",
) -> int:
    """Compute the max vertical extent above y=0 that arrows need.

    Parameters
    ----------
    annotations:
        Full list of annotations for the primitive.
    cell_center_resolver:
        Callable that maps a selector string (e.g. ``"arr.cell[3]"``)
        to ``(x, y)`` SVG coordinates, or ``None`` if unresolvable.
    cell_height:
        Cell height used for curve offset calculation.
    layout:
        ``"horizontal"`` (default) assumes upward-curving arrows.
        ``"2d"`` computes based on perpendicular offset from the
        source-destination line.
    """
    if not annotations:
        return 0
    # Include both arc-style (arrow_from) and pointer-style (arrow=True) annotations
    arrow_anns = [a for a in annotations if a.get("arrow_from")]
    plain_anns = [a for a in annotations if a.get("arrow") and not a.get("arrow_from")]
    if not arrow_anns and not plain_anns:
        return 0

    # Plain arrow=true annotations need a fixed height above the target for the
    # short pointer stem (stem length + label headroom).
    plain_height = 0
    if plain_anns:
        plain_height = _PLAIN_ARROW_STEM + (
            _LABEL_HEADROOM if any(a.get("label") for a in plain_anns) else 0
        )

    if not arrow_anns:
        return plain_height

    has_label = any(a.get("label") for a in arrow_anns)
    max_height = 0
    for idx, ann in enumerate(arrow_anns):
        src = cell_center_resolver(ann.get("arrow_from", ""))
        dst = cell_center_resolver(ann.get("target", ""))
        if src is None or dst is None:
            continue
        x1, y1 = src
        x2, y2 = dst
        # Count arrows targeting same cell before this one
        target = ann.get("target", "")
        arrow_index = sum(
            1
            for j, a in enumerate(arrow_anns)
            if a.get("target") == target
            and j < idx
        )
        h_dist = abs(x2 - x1) + abs(y2 - y1)
        base_offset = min(cell_height * 1.2, max(cell_height * 0.5, math.sqrt(h_dist) * 2.5))
        stagger = cell_height * 0.3
        total_offset = base_offset + arrow_index * stagger

        if layout == "2d":
            # For 2D layouts the curve bows perpendicular to the line
            # between source and destination.  The vertical component
            # above the topmost endpoint depends on the perpendicular
            # direction.
            dx = x2 - x1
            dy = y2 - y1
            dist = math.sqrt(dx * dx + dy * dy) or 1.0
            perp_y = dx / dist  # perpendicular y-component
            # The control points sit at roughly mid_y + perp_y * offset.
            # The worst-case vertical extent above the topmost point is
            # how far above min(y1, y2) the curve can reach.
            mid_y = (y1 + y2) / 2
            ctrl_y = mid_y + perp_y * total_offset
            extent_above = max(0, min(y1, y2) - ctrl_y)
            max_height = max(max_height, int(extent_above))
        else:
            # Horizontal: the curve peaks at min(y1, y2) - total_offset
            max_height = max(max_height, int(total_offset))

    if has_label:
        # QW-7: use 32 px headroom when any arrow label contains math
        # (fractions, large operators overflow the 24 px default).
        has_math = any(_label_has_math(a.get("label", "")) for a in arrow_anns)
        headroom_extra = 32 if has_math else _LABEL_HEADROOM
        max_height += headroom_extra

    return max(max_height, plain_height)


def _position_only_anns(annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to annotations that go through emit_position_label_svg.

    These are annotations with a ``label`` and (optionally) a ``position`` key
    but with neither ``arrow_from`` nor ``arrow=true``.
    """
    return [
        a for a in annotations
        if a.get("label")
        and not a.get("arrow_from")
        and not a.get("arrow")
    ]


def position_label_height_above(
    annotations: list[dict[str, Any]],
    *,
    l_font_px: int = 11,
    cell_height: float = CELL_HEIGHT,
) -> int:
    """Compute the max vertical headroom needed above y=0 for position=above labels.

    Parameters
    ----------
    annotations:
        Full annotation list for the primitive (any entries without
        ``arrow_from`` / ``arrow=true`` that have a ``label`` are considered).
    l_font_px:
        Label font size in pixels used to compute pill height.
    cell_height:
        Cell height used to match the offset calculation in
        ``emit_position_label_svg``.

    Returns
    -------
    int
        Pixel headroom required above the cell top-edge (y=0) to fit all
        ``position=above`` pill labels, or 0 when there are none.
    """
    pos_anns = [
        a for a in _position_only_anns(annotations)
        if a.get("position", "above") == "above"
    ]
    if not pos_anns:
        return 0

    line_height = l_font_px + 2
    pill_h_base = line_height + _LABEL_PILL_PAD_Y * 2  # single-line pill height
    gap = max(4.0, cell_height * 0.1)

    # The label center sits at:
    #   final_y = ay - cell_height/2 - pill_h/2 - gap
    # where ay = 0 (cell center-y for the top row, which is the closest to y=0).
    # The topmost pixel of the pill rect is at:
    #   pill_ry = final_y - pill_h/2 - l_font_px*0.3
    # Headroom = max(0, -pill_ry) so the translate shifts content down enough.
    has_math = any(_label_has_math(a.get("label", "")) for a in pos_anns)
    headroom_extra = 32 if has_math else _LABEL_HEADROOM

    # Worst-case pill_h is pill_h_base (single line); multi-line makes it taller
    # but also pushes its center further — here we use pill_h_base as the
    # conservative minimum (taller pills need more room, but we match the
    # same conservative estimate used for arrow_height_above).
    pill_h = pill_h_base
    final_y = -cell_height / 2 - pill_h / 2 - gap
    pill_ry = final_y - pill_h / 2 - l_font_px * 0.3
    # headroom = how much above y=0 the pill extends, plus label readability buffer
    raw_headroom = int(math.ceil(-pill_ry)) + headroom_extra
    return max(0, raw_headroom)


def position_label_height_below(
    annotations: list[dict[str, Any]],
    *,
    l_font_px: int = 11,
    cell_height: float = CELL_HEIGHT,
) -> int:
    """Compute extra height needed BELOW the cell bottom for position=below labels.

    Parameters
    ----------
    annotations:
        Full annotation list for the primitive.
    l_font_px:
        Label font size in pixels.
    cell_height:
        Cell height used to match offset calculation in
        ``emit_position_label_svg``.

    Returns
    -------
    int
        Extra pixels needed below the nominal cell bottom, or 0 when none.
    """
    pos_anns = [
        a for a in _position_only_anns(annotations)
        if a.get("position") == "below"
    ]
    if not pos_anns:
        return 0

    line_height = l_font_px + 2
    pill_h = line_height + _LABEL_PILL_PAD_Y * 2
    gap = max(4.0, cell_height * 0.1)

    # AC-6: mirror the math-headroom branch from position_label_height_above.
    # When any below-label contains $…$, add 8 px extra (32 − 24 delta).
    has_math = any(_label_has_math(a.get("label", "")) for a in pos_anns)
    math_extra = 8 if has_math else 0  # _LABEL_MATH_HEADROOM_EXTRA

    # final_y for below = ay + cell_height/2 + pill_h/2 + gap
    # pill bottom = final_y + pill_h/2 + l_font_px*0.3
    # extra = pill_bottom - cell_height
    pill_bottom = cell_height / 2 + pill_h + gap + l_font_px * 0.3 + math_extra
    return max(0, int(math.ceil(pill_bottom - cell_height)))


def _place_pill(
    *,
    natural_x: float,
    natural_y: float,
    pill_w: float,
    pill_h: float,
    placed_labels: "list[_LabelPlacement]",
    viewbox_w: float,
    viewbox_h: float,
    side_hint: "str | None" = None,
    overlap_pad: float = 0.0,
    _debug_capture: "dict[str, Any] | None" = None,
) -> "tuple[_LabelPlacement, bool]":
    """Place a pill label using per-candidate clamp + collision avoidance.

    Sole placement primitive for MW-3. Closes ISSUE-A3 (clamp-race) by
    clamping each candidate to the viewport *before* the collision check,
    so a candidate that would collide only after clamping is rejected.

    Parameters
    ----------
    natural_x, natural_y:
        Natural pill center (cx, cy) before any nudge.  The caller is
        responsible for supplying the geometry-rule-derived center
        (e.g. arc mid-point, stem tip, or position-offset anchor).
    pill_w, pill_h:
        Pill dimensions in SVG user units.  MUST be > 0.
    placed_labels:
        Registry of already-placed pills in this frame.  The returned
        placement is NOT appended — the caller does that to maintain C-3
        (append-only registry).
    viewbox_w, viewbox_h:
        Declared viewBox dimensions for clamping (G-3).
    side_hint:
        Half-plane preference passed to ``_nudge_candidates`` (C-5).
    overlap_pad:
        Extra separation margin for ``_LabelPlacement.overlaps`` calls.
        Defaults to 0.0 (strict AABB non-intersection per §2.3).
    _debug_capture:
        When provided, receives diagnostic keys ``natural_x``,
        ``natural_y``, ``final_x``, ``final_y``, ``collision_unresolved``,
        ``candidates_tried``.  Enabled by ``SCRIBA_DEBUG_LABELS=1``.

    Returns
    -------
    tuple[_LabelPlacement, bool]
        ``(placement, fits_cleanly)`` where *fits_cleanly* is ``True``
        when the returned placement does not overlap any existing entry.
        When all 32 candidates are exhausted the last candidate (clamped)
        is returned with ``fits_cleanly=False`` (E-1).

    Tie-breakers
    ------------
    G-5: below > above > right > left — encoded in the ``_nudge_candidates``
    iterator (S, N, E, W, … priority in ``_COMPASS_8``).  When
    ``side_hint`` is provided, the preferred half-plane comes first (C-5).

    Invariants enforced
    -------------------
    - AC-3 (clamp pre-collision): every candidate is clamped before the
      collision check, preventing post-selection drift.
    - G-3 (pill inside viewport): clamp guarantees
      ``0 <= pill_rx`` and ``pill_rx + pill_w <= viewbox_w`` etc.
    - G-4 (clamp preserves dimensions): only the center translates.
    - C-4 (non-overlap): checked after clamp against ``placed_labels``.
    """
    half_w = pill_w / 2.0
    half_h = pill_h / 2.0

    def _clamp(cx: float, cy: float) -> tuple[float, float]:
        """Translate center so the AABB stays within [0, viewbox_w] × [0, viewbox_h]."""
        cx = max(half_w, min(cx, viewbox_w - half_w))
        cy = max(half_h, min(cy, viewbox_h - half_h))
        return cx, cy

    # Natural position — clamp first (G-3).
    clamped_x, clamped_y = _clamp(natural_x, natural_y)
    natural_placement = _LabelPlacement(
        x=clamped_x, y=clamped_y, width=pill_w, height=pill_h
    )

    # Check whether the natural (clamped) position is collision-free.
    if not any(natural_placement.overlaps(p) for p in placed_labels):
        if _debug_capture is not None:
            _debug_capture.update({
                "natural_x": natural_x, "natural_y": natural_y,
                "final_x": clamped_x, "final_y": clamped_y,
                "collision_unresolved": False, "candidates_tried": 0,
            })
        return natural_placement, True

    # Nudge loop — clamp each candidate BEFORE collision check (AC-3).
    last_placement = natural_placement
    candidates_tried = 0
    for ndx, ndy in _nudge_candidates(pill_w, pill_h, side_hint=side_hint):
        cx = natural_x + ndx
        cy = natural_y + ndy
        cx, cy = _clamp(cx, cy)
        candidate = _LabelPlacement(x=cx, y=cy, width=pill_w, height=pill_h)
        last_placement = candidate
        candidates_tried += 1
        if not any(candidate.overlaps(p) for p in placed_labels):
            if _debug_capture is not None:
                _debug_capture.update({
                    "natural_x": natural_x, "natural_y": natural_y,
                    "final_x": cx, "final_y": cy,
                    "collision_unresolved": False,
                    "candidates_tried": candidates_tried,
                })
            return candidate, True

    # All 32 candidates exhausted — emit last candidate per E-1.
    if _DEBUG_LABELS:
        pass  # callers emit the debug comment using their target id
    if _debug_capture is not None:
        _debug_capture.update({
            "natural_x": natural_x, "natural_y": natural_y,
            "final_x": last_placement.x, "final_y": last_placement.y,
            "collision_unresolved": True,
            "candidates_tried": candidates_tried,
        })
    return last_placement, False


def emit_position_label_svg(
    lines: list[str],
    ann: dict[str, Any],
    anchor_point: tuple[float, float],
    cell_height: float = CELL_HEIGHT,
    render_inline_tex: "Callable[[str], str] | None" = None,
    placed_labels: "list[_LabelPlacement] | None" = None,
) -> None:
    """Emit a pill-only label for position-only annotations (no arrow, no arc).

    Called when an annotation has a ``label`` and a ``position`` key but
    neither ``arrow_from`` nor ``arrow=true``.  Emits just the rounded pill
    rectangle and the label text, offset from *anchor_point* according to
    *position* (``"above"``, ``"below"``, ``"left"``, ``"right"``).

    Parameters
    ----------
    lines:
        Output buffer — SVG markup is appended in-place.
    ann:
        Annotation dict.  Keys ``label``, ``color``, ``position``,
        ``target`` are consulted.
    anchor_point:
        ``(x, y)`` SVG coordinates of the annotated cell center.
    cell_height:
        Cell height used to compute the vertical offset from the anchor.
    render_inline_tex:
        Optional callback for rendering ``$...$`` math in labels.
    placed_labels:
        Shared mutable list of already-placed label bounding boxes.
        Callers MUST pass the **same** list to every label-emitting call
        within a single frame so that cross-annotation overlap detection
        works correctly.
    """
    label_text = ann.get("label", "")
    if not label_text:
        return

    color = ann.get("color", "info")
    target = ann.get("target", "")
    position = ann.get("position", "above")

    style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
    s_stroke = style["stroke"]
    s_opacity = style["opacity"]
    l_fill = style["label_fill"]
    l_weight = style["label_weight"]
    l_size = style["label_size"]
    l_font_px = int(l_size.replace("px", "")) if l_size.endswith("px") else 11

    if _label_has_math(label_text):
        label_lines = [label_text]
    else:
        label_lines = _wrap_label_lines(label_text)
    line_height = l_font_px + 2
    num_lines = len(label_lines)

    max_line_w = max(
        estimate_text_width(_label_width_text(ln), l_font_px)
        for ln in label_lines
    )
    pill_w = max_line_w + _LABEL_PILL_PAD_X * 2
    pill_h = num_lines * line_height + _LABEL_PILL_PAD_Y * 2

    ax, ay = float(anchor_point[0]), float(anchor_point[1])
    gap = max(4.0, cell_height * 0.1)

    if position == "above":
        final_x = ax
        final_y = ay - cell_height / 2 - pill_h / 2 - gap
    elif position == "below":
        final_x = ax
        final_y = ay + cell_height / 2 + pill_h / 2 + gap
    elif position == "left":
        final_x = ax - pill_w / 2 - gap
        final_y = ay
    elif position == "right":
        final_x = ax + pill_w / 2 + gap
        final_y = ay
    else:
        # Default: above
        final_x = ax
        final_y = ay - cell_height / 2 - pill_h / 2 - gap

    if placed_labels is not None:
        # HIGH #2: initial candidate uses center-corrected y so overlap
        # geometry during nudge matches the registered placement geometry.
        candidate_y = final_y - l_font_px * 0.3
        candidate = _LabelPlacement(
            x=final_x, y=candidate_y, width=float(pill_w), height=float(pill_h),
        )
        nudge_step = pill_h + 2
        nudge_dirs = [
            (0, -nudge_step),
            (-nudge_step, 0),
            (nudge_step, 0),
            (0, nudge_step),
        ]
        collision_unresolved = False
        for _ in range(4):
            if not any(candidate.overlaps(p) for p in placed_labels):
                break
            resolved = False
            for ndx, ndy in nudge_dirs:
                test = _LabelPlacement(
                    x=candidate.x + ndx,
                    y=candidate.y + ndy,
                    width=candidate.width,
                    height=candidate.height,
                )
                if not any(test.overlaps(p) for p in placed_labels):
                    candidate = test
                    resolved = True
                    break
            if not resolved:
                collision_unresolved = True
                break
        final_x = candidate.x
        # Reconstruct render y from candidate y (which carries the -0.3 correction).
        final_y = candidate.y + l_font_px * 0.3
        clamped_x = max(final_x, pill_w / 2)
        # QW-1: register y = candidate.y (already = final_y - l_font_px*0.3).
        placed_labels.append(_LabelPlacement(
            x=clamped_x,
            y=candidate.y,
            width=float(pill_w),
            height=float(pill_h),
        ))
        # HIGH #1: gated behind _DEBUG_LABELS so it never leaks into production.
        if collision_unresolved and _DEBUG_LABELS:
            lines.append(f"  <!-- scriba:label-collision id={target} -->")

    fi_x = int(final_x)
    fi_y = int(final_y)

    pill_rx = max(0, int(fi_x - pill_w / 2))
    pill_ry = int(fi_y - pill_h / 2 - l_font_px * 0.3)
    fi_x = max(fi_x, pill_w // 2)

    ann_desc = _escape_xml(label_text)
    ann_key = f"{target}-position-{position}"
    lines.append(
        f'  <g class="scriba-annotation scriba-annotation-{color}"'
        f' data-annotation="{_escape_xml(ann_key)}"'
        f' opacity="{s_opacity}"'
        f' role="graphics-symbol" aria-label="{ann_desc}">'
    )
    lines.append(
        f'    <rect x="{pill_rx}" y="{pill_ry}"'
        f' width="{pill_w}" height="{pill_h}"'
        f' rx="{_LABEL_PILL_RADIUS}" ry="{_LABEL_PILL_RADIUS}"'
        f' fill="white" fill-opacity="{_LABEL_BG_OPACITY}"'
        f' stroke="{s_stroke}" stroke-width="0.5" stroke-opacity="0.3"/>'
    )
    if num_lines == 1:
        lines.append(
            _emit_label_single_line(
                label_text=label_text,
                fi_x=fi_x,
                fi_y=fi_y,
                pill_rx=pill_rx,
                pill_ry=pill_ry,
                pill_w=int(pill_w),
                pill_h=int(pill_h),
                l_fill=l_fill,
                l_weight=l_weight,
                l_size=l_size,
                render_inline_tex=render_inline_tex,
            )
        )
    else:
        text_attrs = (
            f'x="{fi_x}" y="{fi_y}" fill="{l_fill}"'
            f' stroke="white" stroke-width="3"'
            f' stroke-linejoin="round" paint-order="stroke fill"'
        )
        style_parts: list[str] = []
        if l_weight:
            style_parts.append(f"font-weight:{l_weight}")
        if l_size:
            style_parts.append(f"font-size:{l_size}")
        style_parts.append("text-anchor:middle")
        style_parts.append("dominant-baseline:auto")
        style_str = ";".join(style_parts)
        tspans = ""
        for li, ln_text in enumerate(label_lines):
            dy_val = f"{line_height}" if li > 0 else "0"
            tspans += (
                f'<tspan x="{fi_x}" dy="{dy_val}">'
                f"{_escape_xml(ln_text)}</tspan>"
            )
        lines.append(
            f'    <text {text_attrs} style="{style_str}">{tspans}</text>'
        )
    lines.append("  </g>")


def emit_arrow_marker_defs(
    lines: list[str],
    annotations: list[dict[str, Any]],
) -> None:
    """Emit ``<defs>`` with ``<marker>`` elements for arrow colors.

    Only emits markers for colors actually used in *annotations*.
    Does nothing when no arrow annotations are present.

    Parameters
    ----------
    lines:
        Output buffer -- SVG markup is appended in-place.
    annotations:
        Full list of annotations; only those with ``arrow_from`` are
        considered.
    """
    # Arrowheads are now rendered as inline <polygon> elements inside
    # each annotation group by emit_arrow_svg().  No <marker> <defs>
    # needed.  This function is kept as a no-op for call-site compat.
    pass
