"""CodePanel primitive — source code display with line-by-line highlighting.

Renders a monospace code panel with line numbers and per-line state
coloring. Useful for showing which line of an algorithm is executing
at each animation step.

See ``docs/archive/PRIMITIVES-PLAN.md`` §4 for the design.
"""

from __future__ import annotations

import re
from html import escape as html_escape
from typing import Any, Callable

from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    svg_style_attrs,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LINE_HEIGHT = 24
_PADDING_X = 12
_PADDING_Y = 8
_CHAR_WIDTH = 8.4  # approximate monospace character width at 14px (Menlo/Monaco/Consolas)
_FONT_SIZE = 14
_BORDER_RADIUS = 6
_CODE_TEXT_COLOR = "#212529"
_LINE_NUM_COLOR = "#8b949e"
_PANEL_BG = "#f6f8fa"
_PANEL_BORDER = "#d0d7de"

# ---------------------------------------------------------------------------
# Selector regex
# ---------------------------------------------------------------------------

_LINE_RE = re.compile(r"^line\[(?P<idx>\d+)\]$")
_ALL_RE = re.compile(r"^all$")

# ---------------------------------------------------------------------------
# CodePanel primitive
# ---------------------------------------------------------------------------


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

        self.label_text: str | None = params.get("label")
        self.primitive_type: str = "codepanel"

        # Pre-compute dynamic gutter width based on line count
        self._gutter_width: int = self._line_num_gutter_width()

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
        if self.label_text:
            height += 20
        return height

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = []
        for i in range(len(self.lines)):
            parts.append(f"line[{i + 1}]")  # 1-based
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True

        m = _LINE_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return 1 <= idx <= len(self.lines)

        return False

    def bounding_box(self) -> BoundingBox:
        return BoundingBox(
            x=0,
            y=0,
            width=self._panel_width(),
            height=self._panel_height(),
        )

    def emit_svg(
        self, *, render_inline_tex: Callable[[str], str] | None = None
    ) -> str:
        parts: list[str] = []
        panel_w = self._panel_width()
        panel_h = self._panel_height()

        parts.append(
            f'<g data-primitive="codepanel" '
            f'data-shape="{html_escape(self.name)}">'
        )

        # Panel background border
        parts.append(
            f'<rect x="0" y="0" width="{panel_w}" height="{panel_h}" '
            f'rx="{_BORDER_RADIUS}" fill="{_PANEL_BG}" '
            f'stroke="{_PANEL_BORDER}" stroke-width="1"/>'
        )

        if not self.lines:
            parts.append(
                f'<text x="{panel_w // 2}" y="{panel_h // 2}" '
                f'style="font-family:monospace;font-size:11px;'
                f"font-weight:400;"
                f"text-anchor:middle;"
                f'dominant-baseline:central" '
                f'fill="#adb5bd">no code</text>'
            )
            parts.append("</g>")
            return "".join(parts)

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

            # Vertical position for this line
            line_y = _PADDING_Y + i * _LINE_HEIGHT
            text_y = line_y + _LINE_HEIGHT // 2

            parts.append(
                f'<g data-target="{html_escape(target)}" '
                f'class="scriba-state-{line_state}">'
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
                f'style="font-family:monospace;font-size:{_FONT_SIZE - 1}px;'
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
                f'style="font-family:monospace;font-size:{_FONT_SIZE}px;'
                f"font-weight:400;"
                f"text-anchor:start;"
                f'dominant-baseline:central" '
                f'fill="{text_fill}" '
                f'xml:space="preserve">{escaped_text}</text>'
            )

            parts.append("</g>")

        # Caption / label
        if self.label_text is not None:
            label_y = panel_h - 4
            label_x = panel_w // 2
            parts.append(
                f'<text x="{label_x}" y="{label_y}" '
                f'text-anchor="middle" fill="#6c757d" '
                f'class="scriba-primitive-label" '
                f'font-size="12">{_escape_xml(self.label_text)}</text>'
            )

        parts.append("</g>")
        return "".join(parts)
