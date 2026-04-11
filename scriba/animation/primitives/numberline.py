"""NumberLine primitive — a horizontal axis with evenly spaced tick marks.

See ``docs/spec/primitives.md`` §8 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import E1103, animation_error
from scriba.animation.primitives.base import (
    STATE_COLORS,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _render_svg_text,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
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

_TICK_RE = re.compile(r"^(?P<name>\w+)\.tick\[(?P<idx>\d+)\]$")
_RANGE_RE = re.compile(r"^(?P<name>\w+)\.range\[(?P<lo>\d+):(?P<hi>\d+)\]$")
_AXIS_RE = re.compile(r"^(?P<name>\w+)\.axis$")
_ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")

# Suffix-only regexes (no shape name prefix)
_SUFFIX_TICK_RE = re.compile(r"^tick\[(?P<idx>\d+)\]$")
_SUFFIX_RANGE_RE = re.compile(r"^range\[(?P<lo>\d+):(?P<hi>\d+)\]$")


# ---------------------------------------------------------------------------
# NumberLinePrimitive
# ---------------------------------------------------------------------------


@register_primitive("NumberLine")
class NumberLinePrimitive(PrimitiveBase):
    """A horizontal axis with evenly spaced tick marks.

    Extends :class:`PrimitiveBase` with self-managed state.
    """

    primitive_type: str = "numberline"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "tick[{i}]": "tick mark by index",
        "range[{lo}:{hi}]": "contiguous range of ticks",
        "axis": "the axis line",
        "all": "all ticks and axis",
    }

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)
        domain = self.params.get("domain")
        if domain is None:
            raise animation_error(
                "E1452",
                detail="NumberLine requires 'domain' parameter",
                hint="example: NumberLine{n}{domain=[0, 10]}",
            )
        if not isinstance(domain, (list, tuple)) or len(domain) != 2:
            raise animation_error(
                "E1453",
                detail=(
                    "NumberLine 'domain' must be a two-element "
                    f"[min, max] list, got {domain!r}"
                ),
            )

        domain_min = float(domain[0])
        domain_max = float(domain[1])

        ticks: int | None = self.params.get("ticks")
        if ticks is not None:
            ticks = int(ticks)
            if ticks > 1_000:
                raise animation_error(
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
            max_label_w = max(estimate_text_width(str(tl), 10) for tl in tick_labels)
            min_tick_spacing = max(min_tick_spacing, max_label_w + 8)
        width = max(NL_WIDTH, ticks * min_tick_spacing + 2 * NL_PADDING)

        self.shape_name: str = name
        self.domain_min: float = domain_min
        self.domain_max: float = domain_max
        self.tick_count: int = ticks
        self.tick_labels: list[str] = tick_labels
        self.label: str | None = label
        self.width: int = width

    # -- PrimitiveBase interface --------------------------------------------

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

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> str:
        """Emit SVG ``<g>`` for the number line."""

        lines: list[str] = [
            f'<g data-primitive="numberline" data-shape="{self.shape_name}">'
        ]

        # Axis line — always idle color
        idle_colors = STATE_COLORS["idle"]
        lines.append(
            f'  <g data-target="{self.shape_name}.axis">'
        )
        lines.append(
            f'    <line x1="{NL_PADDING}" y1="{NL_AXIS_Y}" '
            f'x2="{self.width - NL_PADDING}" y2="{NL_AXIS_Y}" '
            f'stroke="{idle_colors["stroke"]}" stroke-width="2"/>'
        )
        lines.append("  </g>")

        # Ticks
        usable_width = self.width - 2 * NL_PADDING
        for i in range(self.tick_count):
            target = f"{self.shape_name}.tick[{i}]"
            suffix = f"tick[{i}]"

            state_name = self.get_state(suffix)
            highlighted = suffix in self._highlighted

            css = state_class(state_name)
            colors = svg_style_attrs(state_name)

            if self.tick_count > 1:
                x = int(NL_PADDING + i * usable_width / (self.tick_count - 1))
            else:
                x = int(NL_PADDING + usable_width // 2)

            tick_label = self.tick_labels[i] if i < len(self.tick_labels) else str(i)

            lines.append(
                f'  <g data-target="{target}" class="{css}">'
            )
            # Tick line uses state color, but thicker when active
            sw = "2.5" if state_name not in ("idle", "dim") else "1.5"
            lines.append(
                f'    <line x1="{x}" y1="{NL_TICK_TOP}" '
                f'x2="{x}" y2="{NL_TICK_BOTTOM}" '
                f'stroke="{colors["fill"]}" stroke-width="{sw}"/>'
            )
            # Text always uses dark color (no background rect to contrast against)
            text_color = THEME["fg"] if state_name != "dim" else THEME["fg_dim"]
            lines.append(
                "    "
                + _render_svg_text(
                    tick_label,
                    x,
                    NL_LABEL_Y,
                    fill=text_color,
                    fo_width=40,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
            )
            # Highlight overlay (additive — gold circle around tick)
            if highlighted:
                lines.append(
                    f'    <circle cx="{x}" cy="{NL_AXIS_Y}" r="8" '
                    f'fill="none" stroke="#F0E442" stroke-width="3" '
                    f'stroke-dasharray="4 2"/>'
                )
            lines.append("  </g>")

        # Caption label
        if self.label is not None:
            center_x = int(self.width // 2)
            label_y = NL_HEIGHT
            lines.append(
                "  "
                + _render_svg_text(
                    self.label,
                    center_x,
                    label_y,
                    fill=THEME["fg_muted"],
                    css_class="scriba-primitive-label",
                    fo_width=self.width,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
            )

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> BoundingBox:
        """Return ``(x, y, width, height)``."""
        h = NL_HEIGHT
        if self.label:
            h += 16  # extra space for caption
        return BoundingBox(x=0.0, y=0.0, width=float(self.width), height=float(h))


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
        start, end = int(m.group(1)), int(m.group(2))
        return [str(i) for i in range(start, start + tick_count)]

    # Fallback: plain indices
    return [str(i) for i in range(tick_count)]
