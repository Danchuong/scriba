"""CodePanel primitive — source code display with line-by-line highlighting.

Renders a monospace code panel with line numbers and per-line state
coloring. Useful for showing which line of an algorithm is executing
at each animation step.

See ``docs/archive/PRIMITIVES-PLAN.md`` §4 for the design.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.primitives._text_metrics import measure_label_line
from scriba.animation.primitives.base import (
    _label_width_text,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    _label_has_math,
    _render_svg_text,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)

from scriba.animation.primitives._protocol import register_primitive as _protocol_register

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LINE_HEIGHT = 24
_HEADER_HEIGHT = 26  # title bar above the code, IDE-tab style
_HEADER_FONT_PX = 12  # title-bar label font (IDE-tab style)
_PADDING_X = 12
_PADDING_Y = 8
_CHAR_WIDTH = 8.4  # approximate monospace character width at 14px (Menlo/Monaco/Consolas)
_FONT_SIZE = 14
_BORDER_RADIUS = 6
_CODE_TEXT_COLOR = THEME["fg"]
_LINE_NUM_COLOR = THEME["fg_muted"]
_PANEL_BG = THEME["bg"]
_PANEL_BORDER = THEME["border"]

# ---------------------------------------------------------------------------
# Selector regex
# ---------------------------------------------------------------------------

_LINE_RE = re.compile(r"^line\[(?P<idx>\d+)\]$")
_ALL_RE = re.compile(r"^all$")

# ---------------------------------------------------------------------------
# CodePanel primitive
# ---------------------------------------------------------------------------


@register_primitive("CodePanel")
@_protocol_register
class CodePanel(PrimitiveBase):
    """Source code display with line numbers and per-line state highlighting.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``code``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
        Accepts ``source`` (newline-separated string) or ``lines``
        (list of strings). Optional: ``label``.
    """

    primitive_type = "codepanel"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "line[{i}]": "line by number (1-based)",
        "all": "all lines",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "source",
        "lines",
        "label",
    })

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        # Parse source lines from either 'source' or 'lines' param
        raw_source = params.get("source")
        raw_lines = params.get("lines")

        if raw_lines is not None:
            if isinstance(raw_lines, list):
                self.lines: list[str] = [str(line) for line in raw_lines]
            else:
                self.lines = [str(raw_lines)]
        elif raw_source is not None:
            text = str(raw_source)
            # Strip a single leading/trailing newline (from multiline source=)
            if text.startswith("\n"):
                text = text[1:]
            if text.endswith("\n"):
                text = text[:-1]
            self.lines = text.split("\n")
        else:
            self.lines = []

        self.label: str | None = params.get("label")

        # Pre-compute dynamic gutter width based on line count
        self._gutter_width: int = self._line_num_gutter_width()
        # Annotation geometry (Layer B/C): a line is the "cell"; pills/arrows
        # offset from a line anchor by the line height.
        self._arrow_layout = "1d"
        self._arrow_cell_height = float(_LINE_HEIGHT)

    # ----- helpers ---------------------------------------------------------

    def _line_num_gutter_width(self) -> int:
        """Compute gutter width dynamically based on number of lines."""
        max_line = len(self.lines)
        digit_count = len(str(max_line)) if max_line > 0 else 1
        return max(30, digit_count * 10 + 8)  # 10px per digit + padding

    def _longest_line_chars(self) -> int:
        """Return the character count of the longest source line."""
        if not self.lines:
            return 0
        return max(len(line) for line in self.lines)

    def _panel_width(self) -> int:
        """Compute total panel width from longest line."""
        code_width = max(int(self._longest_line_chars() * _CHAR_WIDTH), 100)
        return _PADDING_X + self._gutter_width + _PADDING_X + code_width + _PADDING_X

    def _panel_height(self) -> int:
        """Compute total panel height from line count."""
        n = max(len(self.lines), 1)
        height = _PADDING_Y + n * _LINE_HEIGHT + _PADDING_Y
        if self.label:
            height += _HEADER_HEIGHT  # reserved for the top title bar
        return height

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = []
        for i in range(len(self.lines)):
            parts.append(f"line[{i + 1}]")  # 1-based
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        """Validate a selector suffix (e.g. ``line[3]`` or ``all``).

        CodePanel uses **1-based** line numbering: ``line[1]`` refers
        to the first line. ``line[0]`` is explicitly rejected as
        invalid. Valid indices satisfy ``1 <= idx <= len(lines)``.
        """
        if suffix == "all":
            return True

        m = _LINE_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            # Reject 0-based indexing explicitly; CodePanel is 1-based.
            if idx < 1:
                return False
            return idx <= len(self.lines)

        return False

    def _line_anchor_y(self, line_num: int) -> float:
        """Vertical center of 1-based ``line_num`` in the content frame."""
        header_h = _HEADER_HEIGHT if self.label is not None else 0
        return header_h + _PADDING_Y + (line_num - 1) * _LINE_HEIGHT + _LINE_HEIGHT / 2

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Center anchor for a 1-based ``line[k]`` selector, so annotations
        track a code line. CodePanel previously had no resolver, so any line
        annotation was silently dropped.
        """
        prefix = f"{self.name}."
        local = selector[len(prefix):] if selector.startswith(prefix) else selector
        m = _LINE_RE.match(local)
        if m:
            line_num = int(m.group("idx"))
            if 1 <= line_num <= len(self.lines):
                return (
                    float(self._panel_width() // 2),
                    self._line_anchor_y(line_num),
                )
        return None

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit below the whole panel (callout lane),
        clear of the code lines. The panel bottom is the full panel height
        (header + code rows), matching :meth:`_panel_height`."""
        return float(self._panel_height())

    def bounding_box(self) -> BoundingBox:
        core_w = self._panel_width()
        h = self._panel_height()
        # Layer B/C: reserve space for annotation arrows + position pills.
        # No annotations -> all terms are 0, so the box is byte-stable.
        arrow_above = self._reserved_arrow_above()
        h += arrow_above
        # Layer C: below-pill callout lane sits below the panel.
        h += self._below_lane_height()
        # #1: reserve horizontal room for position=left/right pills. Both pads
        # are 0 (int) without left/right pills, so the box stays byte-stable.
        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(core_w, right_reach)
        return BoundingBox(x=0, y=0, width=w, height=h)

    def _header_label(self) -> str:
        """The title-bar label, ellipsized to fit the header width.

        The header is a single-line, left-aligned IDE-tab title — unlike the
        centered captions on the data primitives, a long title truncates with
        ``…`` rather than overflowing the panel (the panel width is driven by
        the code, not the title). Math titles are left intact (the
        foreignObject path renders them; truncating the source would corrupt
        the markup)."""
        if self.label is None:
            return ""
        text = str(self.label)
        if not text or _label_has_math(text):
            return text
        # Left pad + right pad inset inside the full-width header.
        avail = self._panel_width() - 2 * _PADDING_X
        if estimate_text_width(text, _HEADER_FONT_PX) <= avail:
            return text
        ellipsis = "…"
        clipped = text
        while clipped and estimate_text_width(
            clipped + ellipsis, _HEADER_FONT_PX
        ) > avail:
            clipped = clipped[:-1]
        return clipped + ellipsis if clipped else ellipsis

    def emit_svg(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        parts: list[str] = []
        panel_w = self._panel_width()
        panel_h = self._panel_height()

        parts.append(
            f'<g data-primitive="codepanel" '
            f'data-shape="{_escape_xml(self.name)}">'
        )

        # Reserve space above the panel for annotation arrows/pills and shift
        # the panel down. No annotations -> arrow_above is 0 and no group opens
        # (byte-stable). Empty panels carry no line annotations, so the early
        # return below never sits inside an open group.
        effective_anns = self._annotations
        arrow_above = self._reserved_arrow_above()
        # #1: shift content right to make room for position=left pills (0 when
        # none → "translate(0, …)", byte-identical to the pre-#1 output). Empty
        # panels resolve no anchors, so left_pad stays 0 and the early return
        # below never sits inside an open group.
        left_pad, _right = self._h_label_pad()
        if arrow_above > 0 or left_pad > 0:
            parts.append(f'  <g transform="translate({left_pad}, {arrow_above})">')

        # Panel background border
        parts.append(
            f'<rect x="0" y="0" width="{panel_w}" height="{panel_h}" '
            f'rx="{_BORDER_RADIUS}" fill="{_PANEL_BG}" '
            f'stroke="{_PANEL_BORDER}" stroke-width="1"/>'
        )

        if not self.lines:
            parts.append(
                f'<text x="{panel_w // 2}" y="{panel_h // 2}" '
                f'style="font-family:monospace;'
                f"font-size:11px;"
                f"font-weight:400;"
                f"text-anchor:middle;"
                f'dominant-baseline:central" '
                f'fill="{THEME["fg_dim"]}">no code</text>'
            )
            parts.append("</g>")
            return "".join(parts)

        # Code lines start below the title bar when a label is present.
        header_h = _HEADER_HEIGHT if self.label is not None else 0

        # Resolve "all" state — applies to every line unless overridden
        all_state = self.get_state("all")

        for i, line_text in enumerate(self.lines):
            line_num = i + 1  # 1-based
            suffix = f"line[{line_num}]"
            target = f"{self.name}.{suffix}"

            # Per-line state: specific line state overrides "all" state
            line_state = self.get_state(suffix)
            if line_state == "idle" and all_state != "idle":
                line_state = all_state

            colors = svg_style_attrs(line_state)

            # Vertical position for this line (offset by the title bar)
            line_y = header_h + _PADDING_Y + i * _LINE_HEIGHT
            text_y = line_y + _LINE_HEIGHT // 2

            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
                f'class="{state_class(line_state)}">'
            )

            # Background rect for the line (colored when state != idle)
            if line_state != "idle":
                parts.append(
                    f'<rect x="0" y="{line_y}" '
                    f'width="{panel_w}" height="{_LINE_HEIGHT}" '
                    f'fill="{colors["fill"]}"/>'
                )

            # Line number — right-aligned in the gutter
            # Use inline style to prevent global CSS from overriding
            # monospace font and text-anchor.
            line_num_x = _PADDING_X + self._gutter_width - 4
            line_num_fill = (
                colors["text"] if line_state != "idle" else _LINE_NUM_COLOR
            )
            parts.append(
                f'<text x="{line_num_x}" y="{text_y}" '
                f'style="font-family:monospace;'
                f"font-size:{_FONT_SIZE - 1}px;"
                f"font-weight:400;"
                f"text-anchor:end;"
                f'dominant-baseline:central" '
                f'fill="{line_num_fill}">'
                f"{line_num}</text>"
            )

            # Code text — left-aligned after gutter, preserve indentation
            # Use inline style so global CSS cannot override monospace font.
            code_x = _PADDING_X + self._gutter_width + _PADDING_X
            text_fill = colors["text"] if line_state != "idle" else _CODE_TEXT_COLOR
            escaped_text = _escape_xml(line_text)

            parts.append(
                f'<text x="{code_x}" y="{text_y}" '
                f'style="font-family:monospace;'
                f"font-size:{_FONT_SIZE}px;"
                f"font-weight:400;"
                f"text-anchor:start;"
                f'dominant-baseline:central" '
                f'fill="{text_fill}" '
                f'xml:space="preserve">{escaped_text}</text>'
            )

            parts.append("</g>")

        # Title bar — IDE-tab style header across the top of the panel.
        if self.label is not None:
            r = _BORDER_RADIUS
            # Header fill with rounded top corners that match the panel.
            parts.append(
                f'<path d="M 0 {_HEADER_HEIGHT} L 0 {r} '
                f'Q 0 0 {r} 0 L {panel_w - r} 0 '
                f'Q {panel_w} 0 {panel_w} {r} '
                f'L {panel_w} {_HEADER_HEIGHT} Z" '
                f'fill="{THEME["bg_alt"]}"/>'
            )
            # Divider between the header and the code area.
            parts.append(
                f'<line x1="0" y1="{_HEADER_HEIGHT}" '
                f'x2="{panel_w}" y2="{_HEADER_HEIGHT}" '
                f'stroke="{_PANEL_BORDER}" stroke-width="1"/>'
            )
            parts.append(
                _render_svg_text(
                    self._header_label(),
                    _PADDING_X,
                    _HEADER_HEIGHT // 2,
                    fill=THEME["fg_muted"],
                    font_size=str(_HEADER_FONT_PX),
                    text_anchor="start",
                    dominant_baseline="central",
                    css_class="scriba-primitive-label",
                    fo_width=measure_label_line(
                        str(self._header_label()), _HEADER_FONT_PX
                    ) + 12,
                    fo_height=_HEADER_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )

        # Annotations (arrows + position pills) via the shared engine, inside
        # the translate group so anchors share the content frame (Layer B/C).
        if effective_anns:
            self.emit_annotation_arrows(
                parts,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
            )

        if arrow_above > 0 or left_pad > 0:
            parts.append("  </g>")
        parts.append("</g>")
        return "".join(parts)

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []
