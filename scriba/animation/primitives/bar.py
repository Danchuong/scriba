"""Bar primitive — variable-height columns over an index axis (histogram).

Each datum is a column whose pixel height is proportional to its value,
sharing a common baseline; the x-axis is the element index. This is the
"height = value" channel that MetricPlot (cumulative polyline) and the
cell primitives (text / brick towers) do not provide — the shape the
histogram family of problems needs (largest-rectangle-in-histogram,
monotonic-stack-on-heights, trapping-rain-water, skyline, sorting-as-bars).

A column's height is a pure function of its stored value, recomputed at
emit time, so ``\\apply{h.bar[i]}{value=X}`` rides the existing
``value_change`` transition (the differ sees the value channel change; the
runtime stamps the destination frame's SVG so the column snaps to its new
height and pulses the value label) — no new motion kind, no differ/scene/
runtime changes. This mirrors Array's value-change semantics.

The height envelope (``_envelope_max``) grows monotonically as values are
set, so the value-prescan (``_prescan_value_widths``) drives it to the
timeline maximum before the first frame renders. The bounding box is a
fixed function of the column count and the layout constants — never of the
values — so the stage viewBox is invariant across frames (spec R-32).

See ``docs/primitives/bar.md`` for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives.base import (
    _CAPTION_CLEAR_GAP,
    INDEX_FONT_PX,
    LABEL_FONT_PX,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    _render_svg_text,
    register_primitive,
    state_class,
)

from scriba.animation.primitives._protocol import register_primitive as _protocol_register

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BAR_WIDTH = 36          # default column width (px)
_BAR_GAP = 8             # gap between columns (px)
_PLOT_HEIGHT = 140       # pixel height of a column whose value == the ceiling
_PADDING = 8             # outer padding (px)
_INDEX_LABEL_BAND = 16   # vertical band below the baseline for index labels
_INDEX_LABEL_DY = 11     # baseline -> index-label center offset
_VALUE_LABEL_BAND = 15   # headroom reserved above the plot for value labels
_VALUE_LABEL_GAP = 4     # column top -> value-label baseline gap
_INDEX_FONT_PX = INDEX_FONT_PX   # canonical _types.INDEX_FONT_PX (index labels)
_VALUE_FONT_PX = LABEL_FONT_PX   # canonical _svg_helpers.LABEL_FONT_PX (value labels)
_FLOAT_EPS = 1e-9

# ---------------------------------------------------------------------------
# Selector regex
# ---------------------------------------------------------------------------

_BAR_RE = re.compile(r"^bar\[(?P<idx>\d+)\]$")
_ALL_RE = re.compile(r"^all$")


def _fmt_value(v: float) -> str:
    """Render a bar value: integers without a trailing ``.0``, else 2 dp."""
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# Bar primitive
# ---------------------------------------------------------------------------


@register_primitive("Bar")
@_protocol_register
class Bar(PrimitiveBase):
    """Variable-height columns over an index axis (histogram).

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``h``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
        Required key: ``data`` (a non-empty list of numbers).
        Optional keys: ``max`` (full-scale ceiling; defaults to
        ``max(data)``), ``label`` (caption), ``bar_width`` / ``width``
        (per-column width), ``show_values`` (print each value above its
        column).
    """

    primitive_type = "bar"
    # apply_command only reads the generic value= (routed via set_value); no
    # structural \apply keys of its own.
    APPLY_KEYS: ClassVar[frozenset[str]] = frozenset()

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "bar[{i}]": "column by index",
        "all": "all columns",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "data",
        "max",
        "label",
        "bar_width",
        "width",
        "show_values",
    })

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        self.values: list[float] = self._parse_data(params.get("data"))
        self.label: str | None = params.get("label")
        self.show_values: bool = bool(params.get("show_values", False))

        # bar_width wins over the width alias; clamp to a sane minimum.
        raw_w = params.get("bar_width", params.get("width", _BAR_WIDTH))
        try:
            self.bar_width: int = max(4, int(float(raw_w)))
        except (TypeError, ValueError):
            self.bar_width = _BAR_WIDTH

        # Full-scale ceiling. A user-supplied ``max`` sets the reference a
        # column of that value would fill the plot; a ``max`` smaller than the
        # data is grown so no column ever clips (kept honest by _envelope_max).
        data_max = max(self.values) if self.values else 1.0
        ceiling = data_max
        raw_max = params.get("max")
        if raw_max is not None:
            try:
                cand = float(raw_max)
                if cand > 0:
                    ceiling = cand
            except (TypeError, ValueError):
                ceiling = data_max
        # R-32 envelope: the scaling ceiling only ever grows, so the value
        # prescan lifts it to the timeline maximum before frame 0 renders.
        self._envelope_max: float = max(ceiling, data_max, _FLOAT_EPS)

    # ----- construction validation -----------------------------------------

    @staticmethod
    def _parse_data(raw: Any) -> list[float]:
        """Validate and coerce the ``data`` parameter to a list of floats."""
        if raw is None:
            raise _animation_error(
                "E1488",
                "Bar requires a non-empty numeric 'data' list; "
                "hint: Bar{name}{data=[3, 1, 4, 1, 5]}.",
            )
        if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple)):
            raise _animation_error(
                "E1489",
                f"Bar 'data' must be a list of numbers, got {type(raw).__name__}; "
                "hint: data=[3, 1, 4, 1, 5].",
            )
        if len(raw) == 0:
            raise _animation_error(
                "E1488",
                "Bar 'data' is empty; supply at least one value, "
                "e.g. data=[3, 1, 4, 1, 5].",
            )
        values: list[float] = []
        for entry in raw:
            if isinstance(entry, bool) or not isinstance(entry, (int, float)):
                raise _animation_error(
                    "E1490",
                    f"Bar 'data' contains a non-numeric entry {entry!r}; "
                    "every value must be an int or float.",
                )
            values.append(float(entry))
        return values

    # ----- internal: geometry ----------------------------------------------

    def _bar_px_height(self, value: float) -> float:
        """Pixel height for *value*, clamped to ``[0, _PLOT_HEIGHT]``.

        The clamp is a safety net: after the value prescan the ceiling is the
        timeline maximum, so no column exceeds the plot — but a value set past
        the ceiling in a prescan-free path (e.g. a direct unit test) still
        cannot poke outside the (fixed) bounding box.
        """
        if self._envelope_max <= 0:
            return 0.0
        h = (value / self._envelope_max) * _PLOT_HEIGHT
        if h < 0.0:
            return 0.0
        if h > _PLOT_HEIGHT:
            return float(_PLOT_HEIGHT)
        return h

    def _value_band(self) -> int:
        return _VALUE_LABEL_BAND if self.show_values else 0

    def _plot_top(self) -> int:
        return _PADDING + self._value_band()

    def _baseline_y(self) -> int:
        return self._plot_top() + _PLOT_HEIGHT

    def _content_width(self) -> int:
        n = len(self.values)
        return n * (self.bar_width + _BAR_GAP) - _BAR_GAP

    def _bar_x(self, i: int) -> int:
        return _PADDING + i * (self.bar_width + _BAR_GAP)

    # ----- value updates (rides value_change) ------------------------------

    def set_value(self, suffix: str, value: str) -> None:
        """Update one column's value (called by the emitter + value prescan).

        Overrides the base string-store: the value drives the rendered height,
        and growing ``_envelope_max`` keeps the R-32 envelope at the timeline
        maximum. An out-of-range or non-numeric value is dropped silently
        (mirrors the soft-drop selector contract).
        """
        m = _BAR_RE.match(suffix)
        if not m:
            return
        i = int(m.group("idx"))
        if not (0 <= i < len(self.values)):
            return
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        self.values[i] = v
        if v > self._envelope_max:
            self._envelope_max = v

    def value_must_be_numeric(self, suffix: str) -> bool:
        """A column height is intrinsically numeric — ``value=`` must parse as a
        number. A non-numeric override cannot become a height (it soft-drops in
        :meth:`set_value`); the pre-differ pass rejects it with ``E1107``."""
        return bool(_BAR_RE.match(suffix))

    def apply_command(
        self, params: dict[str, Any], *, target_suffix: str | None = None
    ) -> None:
        """Process ``\\apply`` payloads. A targeted ``value=X`` updates the
        column height (the pipeline routes value through :meth:`set_value`;
        this covers a direct ``apply_command`` call)."""
        if target_suffix is not None and "value" in params:
            self.set_value(target_suffix, params["value"])

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts = [f"bar[{i}]" for i in range(len(self.values))]
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True
        m = _BAR_RE.match(suffix)
        if m:
            return 0 <= int(m.group("idx")) < len(self.values)
        return False

    def _effective_state(self, suffix: str) -> str:
        """Combine the per-column state with the ``all`` sweep and highlight."""
        state = self.get_state(suffix)
        all_state = self.get_state("all")
        if state == "idle" and all_state != "idle":
            state = all_state
        if state == "idle" and self._is_highlighted(suffix):
            state = "highlight"
        return state

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Arrow anchor for ``h.bar[i]``: the column's top-center, so arrows
        curve above the column (mirrors Array's cell-top anchor)."""
        prefix = f"{self.name}."
        local = selector[len(prefix):] if selector.startswith(prefix) else selector
        m = _BAR_RE.match(local)
        if not m:
            return None
        i = int(m.group("idx"))
        if not (0 <= i < len(self.values)):
            return None
        x = self._bar_x(i) + self.bar_width / 2.0
        y_top = self._baseline_y() - self._bar_px_height(self.values[i])
        return (float(x), float(y_top))

    def resolve_label_anchor(self, selector: str) -> tuple[float, float] | None:
        """Pill anchor for ``h.bar[i]``: the column's visual center."""
        prefix = f"{self.name}."
        local = selector[len(prefix):] if selector.startswith(prefix) else selector
        m = _BAR_RE.match(local)
        if not m:
            return None
        i = int(m.group("idx"))
        if not (0 <= i < len(self.values)):
            return None
        x = self._bar_x(i) + self.bar_width / 2.0
        h = self._bar_px_height(self.values[i])
        return (float(x), float(self._baseline_y() - h / 2.0))

    def resolve_annotation_box(self, selector: str):
        """Bounding box of the annotated column, so a pill never parks on top
        of the column it labels (spec R-02)."""
        prefix = f"{self.name}."
        local = selector[len(prefix):] if selector.startswith(prefix) else selector
        m = _BAR_RE.match(local)
        if not m:
            return None
        i = int(m.group("idx"))
        if not (0 <= i < len(self.values)):
            return None
        h = self._bar_px_height(self.values[i])
        return BoundingBox(
            x=float(self._bar_x(i)),
            y=float(self._baseline_y() - h),
            width=float(self.bar_width),
            height=float(h),
        )

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit below the columns + index labels."""
        return float(self._baseline_y() + _INDEX_LABEL_BAND)

    def bounding_box(self) -> BoundingBox:
        content_w = self._content_width()
        full_w = content_w + 2 * _PADDING
        # Height is a pure function of the column count and layout constants —
        # never of the values — so the box is invariant across frames (R-32).
        h = _PADDING + self._value_band() + _PLOT_HEIGHT + _INDEX_LABEL_BAND

        # Layer A: fold the (wrapped) caption width/height into the footprint.
        core_w = max(full_w, self._caption_block_width(content_w))
        h += self._caption_block_height(content_w)
        if self.label is not None:
            h += _CAPTION_CLEAR_GAP

        # Layer B/C: reserve the annotation arrow lane + below-pill callout
        # lane. Both are 0 without annotations, so the box stays byte-stable.
        h += self._reserved_arrow_above()
        h += self._below_lane_height()

        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(core_w, right_reach)
        return BoundingBox(x=0, y=0, width=w, height=h)

    def emit_svg(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        parts: list[str] = []
        parts.append(
            f'<g data-primitive="bar" data-shape="{_escape_xml(self.name)}">'
        )

        arrow_above = self._reserved_arrow_above()
        left_pad, _ = self._h_label_pad()
        if arrow_above > 0 or left_pad > 0:
            parts.append(f'<g transform="translate({left_pad}, {arrow_above})">')

        baseline_y = self._baseline_y()
        content_w = self._content_width()

        for i, value in enumerate(self.values):
            suffix = f"bar[{i}]"
            target = f"{self.name}.{suffix}"
            state = self._effective_state(suffix)

            h = self._bar_px_height(value)
            x = self._bar_x(i)
            y = baseline_y - h

            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
                f'class="{state_class(state)}">'
            )
            # Direct-child <rect> is filled by the CSS state class (recolor
            # swaps the class); exact height keeps height strictly proportional
            # to value, so no stroke inset is applied to the column.
            parts.append(
                f'<rect x="{x}" y="{y:.2f}" '
                f'width="{self.bar_width}" height="{h:.2f}"/>'
            )
            if self.show_values:
                # Value label above the column top — the first <text> in the
                # group, so value_change's pulse/stamp lands on it.
                parts.append(
                    _render_svg_text(
                        _fmt_value(value),
                        x + self.bar_width // 2,
                        int(y - _VALUE_LABEL_GAP - _VALUE_FONT_PX // 2),
                        fill=THEME["fg_muted"],
                        font_size=str(_VALUE_FONT_PX),
                        text_anchor="middle",
                        dominant_baseline="central",
                        fo_width=self.bar_width + _BAR_GAP,
                        fo_height=_VALUE_LABEL_BAND,
                        render_inline_tex=render_inline_tex,
                    )
                )
            parts.append("</g>")

            # Index label below the baseline (outside the addressable group).
            parts.append(
                f'<text x="{x + self.bar_width // 2}" '
                f'y="{baseline_y + _INDEX_LABEL_DY}" '
                f'text-anchor="middle" dominant-baseline="central" '
                f'fill="{THEME["fg_muted"]}" '
                f'style="font-size:{_INDEX_FONT_PX}px">'
                f"{i}</text>"
            )

        # Baseline rule under the columns.
        parts.append(
            f'<line x1="{_PADDING}" y1="{baseline_y}" '
            f'x2="{_PADDING + content_w}" y2="{baseline_y}" '
            f'stroke="{THEME["border"]}" stroke-width="1"/>'
        )

        # Caption.
        if self.label is not None:
            bbox = self.bounding_box()
            self._emit_caption(
                parts,
                content_width=content_w,
                footprint_width=int(bbox.width),
                top_y=int(
                    bbox.height
                    - self._caption_block_height(content_w)
                    - self._reserved_arrow_above()
                ),
                render_inline_tex=render_inline_tex,
            )

        # Annotations (arrows + position pills) via the shared engine.
        if self._annotations:
            self.emit_annotation_arrows(
                parts,
                self._annotations,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
            )

        if arrow_above > 0 or left_pad > 0:
            parts.append("</g>")
        parts.append("</g>")
        return "".join(parts)

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []
