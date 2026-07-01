"""VariableWatch primitive — name-value table for displaying variable states.

Renders a two-column table (name | value) that updates as the algorithm
progresses.  Each variable row is independently addressable and state-colorable.

See ``docs/archive/PRIMITIVES-PLAN.md`` §5 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.primitives.base import (
    THEME,
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    _render_svg_text,
    arrow_height_above,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)

from scriba.animation.primitives._protocol import register_primitive as _protocol_register

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_NAME_COL_WIDTH = 100
_MIN_VALUE_COL_WIDTH = 100
_ROW_HEIGHT = 40
_PADDING = 4
_FONT_SIZE = "13"
_NAME_FONT_SIZE = "12"
_NAME_FONT_SIZE_INT = 12

# ---------------------------------------------------------------------------
# Selector regex
# ---------------------------------------------------------------------------

# Leading class mirrors the lexer's identifier grammar
# (``_IDENT_RE = [^\W\d]\w*``, parser/lexer.py): a Unicode letter or
# underscore, never a digit. An ASCII-only ``[A-Za-z_]`` here silently
# dropped non-ASCII-leading names (e.g. ``đáp``) that the lexer accepts.
_VAR_RE = re.compile(r"^var\[(?P<varname>[^\W\d]\w*)\]$")
_ALL_RE = re.compile(r"^all$")

# ---------------------------------------------------------------------------
# VariableWatch primitive
# ---------------------------------------------------------------------------


@register_primitive("VariableWatch")
@_protocol_register
class VariableWatch(PrimitiveBase):
    """Two-column name-value table for algorithm variable inspection.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``vars``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
        Required keys: ``names`` (list of variable name strings).
        Optional keys: ``label``.
    """

    primitive_type = "variablewatch"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "var[{name}]": "variable by name",
        "all": "all variables",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "names",
        "label",
    })

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        raw_names = params.get("names", [])
        if isinstance(raw_names, str):
            # Handle comma-separated string fallback
            raw_names = [n.strip().strip('"').strip("'") for n in raw_names.split(",")]
        self.var_names: list[str] = [str(n) for n in raw_names]
        if not self.var_names:
            import warnings
            warnings.warn(
                f"VariableWatch '{name}' created with empty names list",
                stacklevel=2,
            )
        self.label: str | None = params.get("label")

        # Per-variable values: varname -> display string
        self._values: dict[str, str] = {vn: "----" for vn in self.var_names}

        # Dynamic column widths based on variable names
        if self.var_names:
            self._name_col_width = max(
                _MIN_NAME_COL_WIDTH,
                max(estimate_text_width(vn, _NAME_FONT_SIZE_INT) + 20 for vn in self.var_names),
            )
        else:
            self._name_col_width = _MIN_NAME_COL_WIDTH
        self._value_col_width = _MIN_VALUE_COL_WIDTH
        self._recalc_value_col()
        self._total_width = self._name_col_width + self._value_col_width

    def _recalc_value_col(self) -> None:
        """Recompute value column width from current values.

        Width is monotonic non-shrinking so the stage viewBox (computed
        from the largest historical width) stays consistent across
        frames even when later values are shorter than earlier ones.
        """
        if self._values:
            max_val_w = max(
                (estimate_text_width(str(v), 13) + 16 for v in self._values.values()),
                default=0,
            )
            candidate = max(_MIN_VALUE_COL_WIDTH, max_val_w)
        else:
            candidate = _MIN_VALUE_COL_WIDTH
        self._value_col_width = max(self._value_col_width, candidate)
        self._total_width = self._name_col_width + self._value_col_width

    # ----- apply commands --------------------------------------------------

    def apply_command(self, params: dict[str, Any], *, target_suffix: str | None = None) -> None:
        """Process value-set commands from ``\\apply``.

        When the target is a specific variable (e.g. ``vars.var[i]``),
        *target_suffix* is ``"var[i]"`` and *params* should contain
        ``value``.
        """
        if target_suffix is not None:
            m = _VAR_RE.match(target_suffix)
            if m:
                varname = m.group("varname")
                if varname in self._values and "value" in params:
                    self._values[varname] = str(params["value"])
                    self._recalc_value_col()
                return

        # Bulk apply: iterate params looking for variable names
        changed = False
        for vn in self.var_names:
            if vn in params:
                self._values[vn] = str(params[vn])
                changed = True
        if changed:
            self._recalc_value_col()

    def set_value(self, suffix: str, value: str) -> None:
        """Set a variable's display value (called by emitter)."""
        m = _VAR_RE.match(suffix)
        if m:
            varname = m.group("varname")
            if varname in self._values:
                self._values[varname] = value
                self._recalc_value_col()

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = []
        for vn in self.var_names:
            parts.append(f"var[{vn}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True

        m = _VAR_RE.match(suffix)
        if m:
            return m.group("varname") in self._values

        return False

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Map ``'V.var[name]'`` to the SVG center of that variable row."""
        prefix = f"{self.name}."
        local = selector[len(prefix):] if selector.startswith(prefix) else selector
        m = _VAR_RE.match(local)
        if m:
            varname = m.group("varname")
            if varname in self._values:
                try:
                    row_idx = self.var_names.index(varname)
                except ValueError:
                    return None
                cx = _PADDING + self._total_width / 2
                cy = _PADDING + row_idx * _ROW_HEIGHT + _ROW_HEIGHT / 2
                return (cx, cy)
        return None

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit below the whole table (callout lane),
        clear of the variable rows. Matches the content bottom reserved by
        :meth:`bounding_box`."""
        return float(max(len(self.var_names), 1) * _ROW_HEIGHT + 2 * _PADDING)

    def bounding_box(self) -> BoundingBox:
        row_count = max(len(self.var_names), 1)
        content_w = self._total_width
        h = row_count * _ROW_HEIGHT + 2 * _PADDING
        # Layer A: fold the (wrapped) caption width into the footprint.
        core_w = max(content_w + 2 * _PADDING, self._caption_block_width(content_w))
        h += self._caption_block_height(content_w)

        arrow_above = arrow_height_above(
            self._annotations,
            self.resolve_annotation_point,
            cell_height=_ROW_HEIGHT,
        )
        h += arrow_above

        # Layer C: below-pill callout lane (0 without below pills → byte-stable).
        h += self._below_lane_height()
        # #1: reserve horizontal room for position=left/right pills. Both pads
        # are 0 (int) without left/right pills, so the box stays byte-stable.
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
        effective_anns = self._annotations
        arrow_above = arrow_height_above(
            effective_anns,
            self.resolve_annotation_point,
            cell_height=_ROW_HEIGHT,
        )
        # #1: shift content right for position=left pills (0 when none →
        # "translate(0, …)", byte-identical to the pre-#1 output).
        left_pad, _ = self._h_label_pad()

        parts: list[str] = []
        parts.append(
            f'<g data-primitive="variablewatch" data-shape="{_escape_xml(self.name)}">'
        )

        # Shift content down (arrows) and right (left pills) into valid space.
        if arrow_above > 0 or left_pad > 0:
            parts.append(f'<g transform="translate({left_pad}, {arrow_above})">')

        if not self.var_names:
            # Empty placeholder
            parts.append(
                f'<rect x="{_PADDING}" y="{_PADDING}" '
                f'width="{self._total_width}" height="{_ROW_HEIGHT}" '
                f'fill="{THEME["bg"]}" stroke="{THEME["border"]}" stroke-width="1" '
                f'stroke-dasharray="4 2" rx="4"/>'
            )
            parts.append(
                f'<text x="{_PADDING + self._total_width // 2}" '
                f'y="{_PADDING + _ROW_HEIGHT // 2}" '
                f'text-anchor="middle" dominant-baseline="central" '
                f'fill="{THEME["fg_dim"]}" '
                f'style="font-size:11px">'
                f'no variables</text>'
            )
            if arrow_above > 0 or left_pad > 0:
                parts.append("</g>")
            parts.append("</g>")
            return "".join(parts)

        row_count = len(self.var_names)
        table_h = row_count * _ROW_HEIGHT
        divider_x = _PADDING + self._name_col_width

        # Clip the per-row value-cell fills to the rounded table outline so
        # their square corners never poke past the rx=4 border.  The outer
        # border, column divider and row dividers are drawn AFTER the rows
        # (below), on top of the fills, so the fills can no longer paint over
        # them — previously the idle fill (#f8f9fa) erased the right border and
        # column divider on the value column.
        clip_id = f"vw-clip-{self.name}"
        parts.append(
            f'<clipPath id="{_escape_xml(clip_id)}">'
            f'<rect x="{_PADDING}" y="{_PADDING}" '
            f'width="{self._total_width}" height="{table_h}" rx="4"/>'
            f"</clipPath>"
        )
        parts.append(f'<g clip-path="url(#{_escape_xml(clip_id)})">')

        for row_idx, vn in enumerate(self.var_names):
            suffix = f"var[{vn}]"
            target = f"{self.name}.{suffix}"

            state = self.get_state(suffix)
            # Also check "all" state
            all_state = self.get_state("all")
            if all_state != "idle" and state == "idle":
                state = all_state

            colors = svg_style_attrs(state)

            row_y = _PADDING + row_idx * _ROW_HEIGHT

            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
                f'class="{state_class(state)}">'
            )

            # Value cell background (right column)
            value_x = _PADDING + self._name_col_width
            parts.append(
                f'<rect x="{value_x}" y="{row_y}" '
                f'width="{self._value_col_width}" height="{_ROW_HEIGHT}" '
                f'fill="{colors["fill"]}" stroke="none"/>'
            )

            # Name text (left column, centered, gray) — centered to match the
            # value column so both columns read as centered.
            name_fo_width = self._name_col_width
            name_tx = _PADDING + self._name_col_width // 2
            name_ty = row_y + _ROW_HEIGHT // 2
            parts.append(
                _render_svg_text(
                    vn,
                    name_tx,
                    name_ty,
                    fill=THEME["fg_muted"],
                    font_size=_NAME_FONT_SIZE,
                    text_anchor="middle",
                    dominant_baseline="central",
                    fo_width=name_fo_width,
                    fo_height=_ROW_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )

            # Value text (right column, centered, state-colored)
            value_tx = value_x + self._value_col_width // 2
            value_ty = row_y + _ROW_HEIGHT // 2
            display_value = self._values.get(vn, "----")
            value_fo_width = self._value_col_width - 8
            parts.append(
                _render_svg_text(
                    display_value,
                    value_tx,
                    value_ty,
                    fill=colors["text"],
                    font_size=_FONT_SIZE,
                    text_anchor="middle",
                    dominant_baseline="central",
                    fo_width=value_fo_width,
                    fo_height=_ROW_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )

            parts.append("</g>")

        parts.append("</g>")  # end clipped value-cell fills

        # Borders on top of the fills — crisp 1px outline, column divider and
        # interior row dividers that the value-cell backgrounds can no longer
        # cover.
        parts.append(
            f'<rect x="{_PADDING}" y="{_PADDING}" '
            f'width="{self._total_width}" height="{table_h}" '
            f'fill="none" stroke="{THEME["border"]}" stroke-width="1" rx="4"/>'
        )
        parts.append(
            f'<line x1="{divider_x}" y1="{_PADDING}" '
            f'x2="{divider_x}" y2="{_PADDING + table_h}" '
            f'stroke="{THEME["border"]}" stroke-width="1"/>'
        )
        for _row_idx in range(1, row_count):
            _div_y = _PADDING + _row_idx * _ROW_HEIGHT
            parts.append(
                f'<line x1="{_PADDING}" y1="{_div_y}" '
                f'x2="{_PADDING + self._total_width}" y2="{_div_y}" '
                f'stroke="{THEME["border"]}" stroke-width="0.5"/>'
            )

        # Caption / label
        if self.label is not None:
            content_w = self._total_width
            bbox = self.bounding_box()
            self._emit_caption(
                parts,
                content_width=content_w,
                footprint_width=int(bbox.width),
                top_y=int(bbox.height - self._caption_block_height(content_w)),
                render_inline_tex=render_inline_tex,
            )

        # Arrow annotations
        if effective_anns:
            self.emit_annotation_arrows(parts, effective_anns, render_inline_tex=render_inline_tex)

        # Close the translate group if we opened one
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
