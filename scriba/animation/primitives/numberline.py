"""NumberLine primitive — a horizontal axis with evenly spaced tick marks.

See ``docs/spec/primitives.md`` §8 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import E1103, _animation_error
from scriba.animation.primitives._text_metrics import measure_value_text
from scriba.animation.primitives.base import (
    _CAPTION_CLEAR_GAP,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _render_svg_text,
    position_below_lane_height,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)


from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._types import (
    ALL_RE,
    RANGE_RE,
    SUFFIX_RANGE_RE,
    SUFFIX_TICK_RE,
)

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

NL_WIDTH = 400
NL_HEIGHT = 56
NL_PADDING = 20
NL_AXIS_Y = 20
NL_TICK_TOP = 12
NL_TICK_BOTTOM = 28
NL_LABEL_Y = 42


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

# Tick/axis selectors are numberline-specific; range/all are canonical.
_TICK_RE = re.compile(r"^(?P<name>\w+)\.tick\[(?P<idx>\d+)\]$")
_RANGE_RE = RANGE_RE
_AXIS_RE = re.compile(r"^(?P<name>\w+)\.axis$")
_ALL_RE = ALL_RE

# Suffix-only regexes (no shape name prefix) — canonical from ._types.
_SUFFIX_TICK_RE = SUFFIX_TICK_RE
_SUFFIX_RANGE_RE = SUFFIX_RANGE_RE


# ---------------------------------------------------------------------------
# NumberLinePrimitive
# ---------------------------------------------------------------------------


@register_primitive("NumberLine")
@_protocol_register
class NumberLinePrimitive(PrimitiveBase):
    """A horizontal axis with evenly spaced tick marks.

    Extends :class:`PrimitiveBase` with self-managed state.
    """

    primitive_type = "numberline"
    supports_trace = True

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "tick[{i}]": "tick mark by index",
        "range[{lo}:{hi}]": "contiguous range of ticks",
        "axis": "the axis line",
        "all": "all ticks and axis",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "domain",
        "ticks",
        "labels",
        "label",
    })

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)
        domain = self.params.get("domain")
        if domain is None:
            raise _animation_error(
                "E1452",
                detail="NumberLine requires 'domain' parameter",
                hint="example: NumberLine{n}{domain=[0, 10]}",
            )
        if not isinstance(domain, (list, tuple)) or len(domain) != 2:
            raise _animation_error(
                "E1453",
                detail=(
                    "NumberLine 'domain' must be a two-element "
                    f"[min, max] list, got {domain!r}"
                ),
            )

        try:
            domain_min = float(domain[0])
            domain_max = float(domain[1])
        except (TypeError, ValueError):
            # Fail loud, not a raw ValueError traceback (sweep3-content:
            # same wrong-TYPE leak class as the Matrix data= guard).
            raise _animation_error(
                "E1453",
                detail=(
                    "NumberLine 'domain' endpoints must be numbers, "
                    f"got {domain!r}"
                ),
            ) from None

        ticks: int | None = self.params.get("ticks")
        if ticks is not None:
            if isinstance(ticks, bool) or not isinstance(ticks, (int, float)):
                raise _animation_error(
                    "E1455",
                    detail=(
                        f"NumberLine 'ticks' must be an integer, got {ticks!r}"
                    ),
                    hint="example: ticks=11",
                )
            ticks = int(ticks)
            if ticks < 1:
                raise _animation_error(
                    E1103,
                    detail=(
                        f"NumberLine ticks {ticks} is out of range; "
                        "must be a positive integer (1..1000)"
                    ),
                )
            if ticks > 1_000:
                raise _animation_error(
                    "E1454",
                    detail=(
                        f"NumberLine ticks {ticks} exceeds maximum; "
                        "valid: 1..1000"
                    ),
                )
        else:
            # Default: max-min+1 if integer range, else 11
            if domain_min == int(domain_min) and domain_max == int(domain_max):
                ticks = int(domain_max - domain_min) + 1
            else:
                ticks = 11

        labels: list[str] | str | None = self.params.get("labels")
        tick_labels = _resolve_labels(labels, ticks, domain_min, domain_max)

        label: str | None = self.params.get("label")

        # Dynamic width: ensure enough room for ticks and their labels
        min_tick_spacing = 40  # minimum pixels between ticks for readability
        # Ensure tick spacing can accommodate the widest label
        if tick_labels:
            max_label_w = max(measure_value_text(str(tl), 10, mono=True) for tl in tick_labels)
            min_tick_spacing = max(min_tick_spacing, max_label_w + 8)
        width = max(NL_WIDTH, ticks * min_tick_spacing + 2 * NL_PADDING)

        self.domain_min: float = domain_min
        self.domain_max: float = domain_max
        self.tick_count: int = ticks
        self.tick_labels: list[str] = tick_labels
        self.label: str | None = label
        self.width: int = width
        # Tick band height — the "cell height" the shared annotation engine uses
        # to offset position pills from the tick anchor (Layer B/C pill path).
        self._arrow_cell_height = float(NL_TICK_BOTTOM - NL_TICK_TOP)

    # -- internal: tick position ---------------------------------------------

    def _tick_x(self, i: int) -> int:
        """Return the x coordinate for tick index *i*."""
        usable_width = self.width - 2 * NL_PADDING
        if self.tick_count > 1:
            return int(NL_PADDING + i * usable_width / (self.tick_count - 1))
        return int(NL_PADDING + usable_width // 2)

    # -- PrimitiveBase interface --------------------------------------------

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Map ``'N.tick[3]'`` or ``'N.range[1:3]'`` to its SVG anchor.

        Layer B — a ``range[lo:hi]`` target validated true but had no anchor, so
        the annotation was silently dropped. The range anchor is the midpoint
        between its end ticks (top edge, arrows curve above).
        """
        prefix = f"{self.name}."
        local = selector[len(prefix):] if selector.startswith(prefix) else selector
        m = _SUFFIX_TICK_RE.match(local)
        if m:
            idx = int(m.group("idx"))
            if 0 <= idx < self.tick_count:
                x = float(self._tick_x(idx))
                y = float(NL_TICK_TOP)  # top of tick — arrows curve above
                return (x, y)
        m = _SUFFIX_RANGE_RE.match(local)
        if m:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            if 0 <= lo <= hi < self.tick_count:
                x = (self._tick_x(lo) + self._tick_x(hi)) / 2.0
                return (float(x), float(NL_TICK_TOP))
        return None

    def addressable_parts(self) -> list[str]:
        """Return all valid selector suffixes."""
        parts: list[str] = ["axis"]
        for i in range(self.tick_count):
            parts.append(f"tick[{i}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        """Check whether *suffix* is a valid addressable part."""
        m = _SUFFIX_TICK_RE.match(suffix)
        if m:
            return 0 <= int(m.group("idx")) < self.tick_count

        m = _SUFFIX_RANGE_RE.match(suffix)
        if m:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            return 0 <= lo <= hi < self.tick_count

        return suffix in ("axis", "all")

    def renders_value(self, suffix: str) -> bool:
        """NumberLine ticks are axis coordinates, not a per-tick value slot.

        A tick's label is its coordinate, set by ``domain=``/``ticks=``/
        ``labels=`` (§7.6); there is no per-tick ``value=`` op. A ``value=``
        would vanish from the render (flip-back), so reject it.
        """
        return False

    def _arrow_height_above(self, annotations: "list[dict]") -> int:
        """Compute arrow height above, locked to cross-frame max to prevent jitter."""
        return self._reserved_arrow_above()

    def resolve_trace_point(self, selector: str) -> "tuple[float, float] | None":
        # trace threads tick CENTERS; the annotation anchor is the tick TOP
        pt = self.resolve_annotation_point(selector)
        if pt is None:
            return None
        return (pt[0], pt[1] + _TICK_HALF_H if "_TICK_HALF_H" in globals() else pt[1])

    def _trace_cell_suffix(self, cell) -> str:
        return f"tick[{int(cell)}]"

    def _cursor_cell_suffix(self, index) -> str:
        # R-38: NumberLine cells are ticks; the caret binds a tick center.
        return f"tick[{int(index)}]"

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        """Emit SVG ``<g>`` for the number line."""

        effective_anns = self._annotations
        arrow_above = self._arrow_height_above(effective_anns)
        # #1: shift content right for position=left pills (0 when none).
        left_pad, _right = self._h_label_pad()

        lines: list[str] = [
            f'<g data-primitive="numberline" data-shape="{self.name}">'
        ]

        # Shift content down (arrows) and right (left pills) into valid space.
        if arrow_above > 0 or left_pad > 0:
            lines.append(f'  <g transform="translate({left_pad}, {arrow_above})">')


        # Axis line — honours \recolor{nl.axis}{state=...}
        axis_state = self.resolve_effective_state("axis")
        axis_css = state_class(axis_state)
        axis_colors = svg_style_attrs(axis_state)
        lines.append(
            f'  <g data-target="{self.name}.axis" class="{axis_css}">'
        )
        lines.append(
            f'    <line x1="{NL_PADDING}" y1="{NL_AXIS_Y}" '
            f'x2="{self.width - NL_PADDING}" y2="{NL_AXIS_Y}" '
            f'stroke="{axis_colors["stroke"]}" stroke-width="2"/>'
        )
        lines.append("  </g>")

        # Ticks
        for i in range(self.tick_count):
            target = f"{self.name}.tick[{i}]"
            suffix = f"tick[{i}]"

            effective_state = self.resolve_effective_state(suffix)

            css = state_class(effective_state)
            colors = svg_style_attrs(effective_state)

            x = self._tick_x(i)

            tick_label = self.tick_labels[i] if i < len(self.tick_labels) else str(i)

            lines.append(
                f'  <g data-target="{target}" class="{css}">'
            )
            # Tick line uses state color, but thicker when active
            sw = "2.5" if effective_state not in ("idle", "dim") else "1.5"
            lines.append(
                f'    <line x1="{x}" y1="{NL_TICK_TOP}" '
                f'x2="{x}" y2="{NL_TICK_BOTTOM}" '
                f'stroke="{colors["fill"]}" stroke-width="{sw}"/>'
            )
            # Text always uses dark color (no background rect to contrast against)
            text_color = THEME["fg"] if effective_state != "dim" else THEME["fg_dim"]
            lines.append(
                "    "
                + _render_svg_text(
                    tick_label,
                    x,
                    NL_LABEL_Y,
                    fill=text_color,
                    font_size="10",
                    fo_width=40,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
            )
            lines.append("  </g>")

        # Caption label — below the below-pill lane (lane is 0 when there are no
        # below pills, so the caption stays at NL_HEIGHT in the common case).
        if self.label is not None:
            below_lane = self._below_lane_height()
            self._emit_caption(
                lines,
                content_width=self.width,
                # Core width (not the left/right-padded bbox width): the caption
                # is inside the left_pad-shifted group, so it centers on content.
                footprint_width=int(
                    max(float(self.width), float(self._caption_block_width(self.width)))
                ),
                top_y=int(NL_HEIGHT + below_lane + _CAPTION_CLEAR_GAP),
                render_inline_tex=render_inline_tex,
            )

        # All annotation kinds route through the shared dispatcher (FP-6):
        # it splits arrow_from / arrow=true / position-only internally, emits
        # marker defs itself, shares one placement registry, and is exactly
        # what _measure_emit replays — so measured == painted by construction
        # (the bespoke arrow loop measured with prior-stroke avoidance the
        # paint path didn't have).
        # R-37 traces: above the cell bodies (a filled cell would
        # swallow an under-stroke) but below pills/arrows; digits
        # stay legible via the global paint-order halo
        self.emit_traces_under(lines)
        # R-38 binding carets ride the same decoration band as traces.
        self.emit_cursors_under(lines)

        if effective_anns:
            self.emit_annotation_arrows(
                lines,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
            )

        # Close translate group if opened for arrow/left-pad space
        if arrow_above > 0 or left_pad > 0:
            lines.append("  </g>")

        lines.append("</g>")
        return "\n".join(lines)

    def resolve_below_baseline(self) -> float | None:
        """Y where ``position=below`` pills start — below the tick labels, so a
        below pill clears the axis labels (lane mode) instead of landing in the
        label band. The caption is then placed beneath the below-pill lane.
        """
        return float(NL_HEIGHT)

    def bounding_box(self) -> BoundingBox:
        """Return ``(x, y, width, height)``."""
        h = float(NL_HEIGHT)
        # Layer A: fold the (wrapped) caption width into the footprint.
        w = max(float(self.width), float(self._caption_block_width(self.width)))
        # Below-pill lane first, then the caption beneath it (mirrors Array's
        # content -> lane -> caption order). No below pills -> lane is 0 and the
        # caption stays at NL_HEIGHT, so the box is byte-stable.
        below_lane = self._below_lane_height()
        h += below_lane + self._caption_block_height(self.width)
        if self.label is not None:
            h += _CAPTION_CLEAR_GAP

        # R-38: keep a below-tick binding caret inside the box (0 when none).
        h = max(h, self._cursor_extent_below())

        arrow_above = self._arrow_height_above(self._annotations)
        h += arrow_above

        # #1: reserve horizontal room for position=left/right pills (0 without
        # them, so the box is byte-stable in the common case).
        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(w, float(right_reach))

        return BoundingBox(x=0.0, y=0.0, width=w, height=float(h))

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []


# ---------------------------------------------------------------------------
# Backward-compatible alias
# ---------------------------------------------------------------------------

NumberLineInstance = NumberLinePrimitive


# ---------------------------------------------------------------------------
# Label resolution
# ---------------------------------------------------------------------------


def _resolve_labels(
    labels: list[str] | str | None,
    tick_count: int,
    domain_min: float,
    domain_max: float,
) -> list[str]:
    """Resolve tick labels from params or generate defaults."""
    if labels is None:
        # Generate default labels from domain values
        if tick_count == 1:
            return [str(int(domain_min)) if domain_min == int(domain_min) else str(domain_min)]
        result: list[str] = []
        for i in range(tick_count):
            val = domain_min + i * (domain_max - domain_min) / (tick_count - 1)
            if val == int(val):
                result.append(str(int(val)))
            else:
                result.append(f"{val:.1f}")
        return result

    if isinstance(labels, list):
        return [str(lb) for lb in labels]

    if isinstance(labels, str):
        return _parse_label_string(labels, tick_count)

    return [str(i) for i in range(tick_count)]


def _parse_label_string(fmt: str, tick_count: int) -> list[str]:
    """Parse label format strings like ``"0..10"``."""
    m = re.match(r"^(\d+)\.\.(\d+)$", fmt)
    if m:
        start = int(m.group(1))
        return [str(i) for i in range(start, start + tick_count)]

    # Fallback: plain indices
    return [str(i) for i in range(tick_count)]
