"""NumberLine primitive — a horizontal axis with evenly spaced tick marks.

See ``docs/06-primitives.md`` §8 for the authoritative specification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from scriba.animation.errors import E1103, animation_error
from scriba.animation.primitives.base import (
    DEFAULT_STATE,
    STATE_COLORS,
    _escape_xml,
    _render_svg_text,
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
# Factory
# ---------------------------------------------------------------------------


class NumberLinePrimitive:
    """Factory that creates :class:`NumberLineInstance` from ``\\shape`` params."""

    name: str = "NumberLine"

    def declare(
        self, shape_name: str, params: dict[str, Any]
    ) -> NumberLineInstance:
        """Validate params and build a :class:`NumberLineInstance`."""
        domain = params.get("domain")
        if domain is None:
            raise animation_error(
                E1103,
                detail="NumberLine requires 'domain' parameter",
            )
        if not isinstance(domain, (list, tuple)) or len(domain) != 2:
            raise animation_error(
                E1103,
                detail="NumberLine 'domain' must be a [min, max] list",
            )

        domain_min = float(domain[0])
        domain_max = float(domain[1])

        ticks: int | None = params.get("ticks")
        if ticks is not None:
            ticks = int(ticks)
            if ticks > 1_000:
                raise animation_error(
                    E1103,
                    detail=f"[E1103] NumberLine ticks {ticks} exceeds maximum of 1,000",
                )
        else:
            # Default: max-min+1 if integer range, else 11
            if domain_min == int(domain_min) and domain_max == int(domain_max):
                ticks = int(domain_max - domain_min) + 1
            else:
                ticks = 11

        labels: list[str] | str | None = params.get("labels")
        tick_labels = _resolve_labels(labels, ticks, domain_min, domain_max)

        label: str | None = params.get("label")

        return NumberLineInstance(
            shape_name=shape_name,
            domain_min=domain_min,
            domain_max=domain_max,
            tick_count=ticks,
            tick_labels=tick_labels,
            label=label,
        )


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

_TICK_RE = re.compile(r"^(?P<name>\w+)\.tick\[(?P<idx>\d+)\]$")
_RANGE_RE = re.compile(r"^(?P<name>\w+)\.range\[(?P<lo>\d+):(?P<hi>\d+)\]$")
_AXIS_RE = re.compile(r"^(?P<name>\w+)\.axis$")
_ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")


# ---------------------------------------------------------------------------
# Instance
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NumberLineInstance:
    """A declared NumberLine instance with layout pre-computed."""

    shape_name: str
    domain_min: float
    domain_max: float
    tick_count: int
    tick_labels: list[str] = field(default_factory=list)
    label: str | None = None
    primitive_type: str = "numberline"

    # -- protocol -----------------------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Return all valid selector targets."""
        parts: list[str] = []
        parts.append(f"{self.shape_name}.axis")
        for i in range(self.tick_count):
            parts.append(f"{self.shape_name}.tick[{i}]")
        parts.append(f"{self.shape_name}.all")
        return parts

    def validate_selector(self, selector_str: str) -> bool:
        """Check whether *selector_str* is valid for this instance."""
        m = _TICK_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            return 0 <= int(m.group("idx")) < self.tick_count

        m = _RANGE_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            return 0 <= lo <= hi < self.tick_count

        m = _AXIS_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            return True

        m = _ALL_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            return True

        return False

    def emit_svg(
        self,
        state: dict[str, dict[str, Any]],
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
            f'x2="{NL_WIDTH - NL_PADDING}" y2="{NL_AXIS_Y}" '
            f'stroke="{idle_colors["stroke"]}" stroke-width="2"/>'
        )
        lines.append("  </g>")

        # Ticks
        usable_width = NL_WIDTH - 2 * NL_PADDING
        for i in range(self.tick_count):
            target = f"{self.shape_name}.tick[{i}]"
            tick_state = state.get(target, {})
            state_name = tick_state.get("state", DEFAULT_STATE)
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
            text_color = "#212529" if state_name != "dim" else "#adb5bd"
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
            if tick_state.get("highlighted"):
                lines.append(
                    f'    <circle cx="{x}" cy="{NL_AXIS_Y}" r="8" '
                    f'fill="none" stroke="#F0E442" stroke-width="3" '
                    f'stroke-dasharray="4 2"/>'
                )
            lines.append("  </g>")

        # Caption label
        if self.label is not None:
            center_x = int(NL_WIDTH // 2)
            label_y = NL_HEIGHT
            lines.append(
                "  "
                + _render_svg_text(
                    self.label,
                    center_x,
                    label_y,
                    fill="#6c757d",
                    css_class="scriba-primitive-label",
                    fo_width=NL_WIDTH,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
            )

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> tuple[float, float, float, float]:
        """Return ``(x, y, width, height)``."""
        h = NL_HEIGHT
        if self.label:
            h += 16  # extra space for caption
        return (0.0, 0.0, float(NL_WIDTH), float(h))


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
