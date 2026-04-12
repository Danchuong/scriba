"""tabular environment handling.

See ``docs/scriba/02-tex-plugin.md`` §3 (tabular HTML contract).

Cell content is processed through inline TeX via the ``cell_renderer``
callback, which applies math, text commands, and other inline formatting.
The wrapper structure (table/row/cell tags) is emitted here; the callback
handles recursive inline expansion within each cell.
"""

from __future__ import annotations

import html as _html
import re
from typing import Callable

from scriba.tex.parser.escape import PlaceholderManager

CellRenderer = Callable[[str], str]

_TABULAR_RE = re.compile(
    r"\\begin\{tabular\}\{([^}]*)\}([\s\S]*?)\\end\{tabular\}"
)
_MULTICOLUMN_RE = re.compile(
    r"^\\multicolumn\{(\d+)\}\{([^}]*)\}\{([\s\S]*)\}$"
)
_MULTIROW_RE = re.compile(
    r"^\\multirow\{(\d+)\}\{[^}]*\}\{([\s\S]*)\}$"
)
_CLINE_RE = re.compile(r"\\cline\{(\d+)-(\d+)\}")


def _parse_col_spec(col_spec: str) -> tuple[list[str], list[bool], bool]:
    """Return ``(alignments, right_borders, has_left_border)``.

    ``alignments[i]`` is one of ``"left" | "center" | "right"``.
    ``right_borders[i]`` is True when a ``|`` follows that column.
    ``has_left_border`` is True when the spec starts with ``|``.
    """
    spec = col_spec.replace(" ", "")
    align_map = {"l": "left", "c": "center", "r": "right"}

    alignments: list[str] = []
    right_borders: list[bool] = []
    has_left_border = spec.startswith("|")

    i = 0
    while i < len(spec):
        ch = spec[i]
        if ch in "lcr":
            alignments.append(align_map[ch])
            has_right = i + 1 < len(spec) and spec[i + 1] == "|"
            right_borders.append(has_right)
            i += 2 if has_right else 1
        else:
            i += 1
    return alignments, right_borders, has_left_border


def _border_classes(*, top: bool, bottom: bool, left: bool, right: bool) -> list[str]:
    """Return border classes in stable order: top, bottom, left, right."""
    classes: list[str] = []
    if top:
        classes.append("scriba-tex-border-top")
    if bottom:
        classes.append("scriba-tex-border-bottom")
    if left:
        classes.append("scriba-tex-border-left")
    if right:
        classes.append("scriba-tex-border-right")
    return classes


def _split_rows(body: str) -> list[str]:
    """Split tabular body on ``\\\\`` row separators."""
    return re.split(r"\\\\", body)


def _split_cells(row: str) -> list[str]:
    """Split a row on unescaped ``&``. ``\\&`` is a literal ampersand."""
    return re.split(r"(?<!\\)&", row)


def _render_cell_content(raw: str, cell_renderer: CellRenderer | None) -> str:
    """Render cell content. When ``cell_renderer`` is provided, the cell's
    raw TeX is processed for inline math, text commands, dashes, etc., via
    that callback (which must return safe HTML). Otherwise the cell is
    HTML-escaped only — used as a safe fallback for callers that don't
    plumb a renderer."""
    if cell_renderer is not None:
        return cell_renderer(raw.strip())
    text = raw.replace("\\&", "&")
    return _html.escape(text.strip(), quote=False)


def apply_tabular(
    text: str,
    placeholders: PlaceholderManager,
    *,
    cell_renderer: CellRenderer | None = None,
) -> str:
    """Replace every ``tabular`` environment with a block placeholder.

    ``cell_renderer`` (optional) is called with each cell's raw TeX and
    must return safe HTML. When omitted, cells are HTML-escaped only and
    inline TeX features inside cells will not be rendered.
    """

    def _sub(match: re.Match[str]) -> str:
        col_spec = match.group(1)
        body = match.group(2)
        html = _render_table(col_spec, body, cell_renderer)
        return placeholders.store(html, is_block=True)

    return _TABULAR_RE.sub(_sub, text)


def _render_table(
    col_spec: str, body: str, cell_renderer: CellRenderer | None
) -> str:
    alignments, right_borders, has_left_border = _parse_col_spec(col_spec)

    # Pre-pass: split body into row-info dicts. ``\hline`` and ``\cline`` may
    # appear at the start of a segment to indicate a top border on the row
    # they precede, or alone in a trailing segment to indicate a bottom
    # border on the previous row.
    raw_segments = _split_rows(body)
    rows: list[dict] = []
    pending_top_hline = False
    pending_top_clines: list[tuple[int, int]] = []

    for segment in raw_segments:
        seg = segment.strip()
        # Strip and remember any leading \hline / \cline markers.
        consumed_hline = False
        consumed_clines: list[tuple[int, int]] = []
        while True:
            if seg.startswith("\\hline"):
                consumed_hline = True
                seg = seg[len("\\hline") :].strip()
                continue
            cline = _CLINE_RE.match(seg)
            if cline:
                consumed_clines.append((int(cline.group(1)), int(cline.group(2))))
                seg = seg[cline.end() :].strip()
                continue
            break

        if not seg:
            # Trailing markers belong to the PREVIOUS row as bottom borders.
            if rows:
                if consumed_hline:
                    rows[-1]["bottom_hline"] = True
                for span in consumed_clines:
                    rows[-1]["bottom_clines"].append(span)
            else:
                # Markers before any row → defer to next row's top border.
                if consumed_hline:
                    pending_top_hline = True
                pending_top_clines.extend(consumed_clines)
            continue

        rows.append(
            {
                "raw": seg,
                "top_hline": consumed_hline or pending_top_hline,
                "top_clines": list(consumed_clines) + list(pending_top_clines),
                "bottom_hline": False,
                "bottom_clines": [],
            }
        )
        pending_top_hline = False
        pending_top_clines = []

    parts = ['<table class="scriba-tex-table">']
    # Per-column remaining-row counter for active \multirow cells. When
    # >0 the column position is occupied by an earlier multirow; the
    # LaTeX user still writes a (typically empty) cell at that position,
    # which we consume but do not emit.
    active_rowspans: dict[int, int] = {}
    for row in rows:
        parts.append('<tr class="scriba-tex-table-row">')
        cell_strings = _split_cells(row["raw"])
        col_idx = 0  # 0-based logical column position
        for cell_raw in cell_strings:
            # If this column is held by a multirow from a previous row,
            # consume the (placeholder) raw cell and advance without
            # emitting a <td>. A placeholder may itself be a
            # ``\multicolumn{N}{...}{...}`` standing in for N occupied
            # columns — skip N positions in that case.
            if active_rowspans.get(col_idx, 0) > 0:
                placeholder_mc = _MULTICOLUMN_RE.match(cell_raw.strip())
                placeholder_span = (
                    int(placeholder_mc.group(1)) if placeholder_mc else 1
                )
                for off in range(placeholder_span):
                    if active_rowspans.get(col_idx + off, 0) > 0:
                        active_rowspans[col_idx + off] -= 1
                col_idx += placeholder_span
                continue
            cell = cell_raw.strip()

            # Default per column-spec.
            colspan = 1
            rowspan = 1
            cell_align = (
                alignments[col_idx] if col_idx < len(alignments) else "left"
            )
            cell_content = cell

            mc = _MULTICOLUMN_RE.match(cell)
            mr_outer = _MULTIROW_RE.match(cell)
            if mc:
                colspan = int(mc.group(1))
                spec = mc.group(2).replace(" ", "")
                for ch in spec:
                    if ch == "l":
                        cell_align = "left"
                        break
                    if ch == "c":
                        cell_align = "center"
                        break
                    if ch == "r":
                        cell_align = "right"
                        break
                cell_content = mc.group(3)
                # \multicolumn body may itself be a \multirow.
                inner_mr = _MULTIROW_RE.match(cell_content.strip())
                if inner_mr:
                    rowspan = int(inner_mr.group(1))
                    cell_content = inner_mr.group(2)
                # Multicolumn spec controls its own borders.
                mc_left = spec.startswith("|")
                mc_right = spec.endswith("|")
            elif mr_outer:
                rowspan = int(mr_outer.group(1))
                cell_content = mr_outer.group(2)
                mc_left = has_left_border and col_idx == 0
                last_col = col_idx + colspan - 1
                mc_right = (
                    last_col < len(right_borders) and right_borders[last_col]
                )
            else:
                mc_left = has_left_border and col_idx == 0
                last_col = col_idx + colspan - 1
                mc_right = (
                    last_col < len(right_borders) and right_borders[last_col]
                )

            top = row["top_hline"] or any(
                a <= col_idx + 1 <= b for a, b in row["top_clines"]
            )
            bottom = row["bottom_hline"] or any(
                a <= col_idx + 1 <= b for a, b in row["bottom_clines"]
            )

            classes = ["scriba-tex-table-cell", f"scriba-tex-align-{cell_align}"]
            classes.extend(
                _border_classes(top=top, bottom=bottom, left=mc_left, right=mc_right)
            )

            attrs = f' class="{" ".join(classes)}"'
            if colspan > 1:
                attrs += f' colspan="{colspan}"'
            if rowspan > 1:
                attrs += f' rowspan="{rowspan}"'

            parts.append(
                f"<td{attrs}>{_render_cell_content(cell_content, cell_renderer)}</td>"
            )

            if rowspan > 1:
                # Block these column positions in the next (rowspan-1) rows.
                for off in range(colspan):
                    active_rowspans[col_idx + off] = rowspan - 1
            col_idx += colspan


        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)
