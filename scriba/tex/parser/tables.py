"""tabular environment handling.

See ``docs/scriba/02-tex-plugin.md`` §3 (tabular HTML contract).

Cells in Phase 2d are treated as opaque text and HTML-escaped. Inline math
and text commands inside cells are out of scope for the initial port —
the legacy renderer's recursive cell processing can be added incrementally
without changing the wrapper structure emitted here.
"""

from __future__ import annotations

import html as _html
import re

from scriba.tex.parser.escape import PlaceholderManager

_TABULAR_RE = re.compile(
    r"\\begin\{tabular\}\{([^}]*)\}([\s\S]*?)\\end\{tabular\}"
)
_MULTICOLUMN_RE = re.compile(
    r"^\\multicolumn\{(\d+)\}\{([^}]*)\}\{([\s\S]*)\}$"
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


def _render_cell_content(raw: str) -> str:
    """HTML-escape cell content. ``\\&`` collapses to a literal ``&``."""
    text = raw.replace("\\&", "&")
    return _html.escape(text.strip(), quote=False)


def apply_tabular(
    text: str,
    placeholders: PlaceholderManager,
) -> str:
    """Replace every ``tabular`` environment with a block placeholder."""

    def _sub(match: re.Match[str]) -> str:
        col_spec = match.group(1)
        body = match.group(2)
        html = _render_table(col_spec, body)
        return placeholders.store(html, is_block=True)

    return _TABULAR_RE.sub(_sub, text)


def _render_table(col_spec: str, body: str) -> str:
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
    for row in rows:
        parts.append('<tr class="scriba-tex-table-row">')
        cell_strings = _split_cells(row["raw"])
        col_idx = 0  # 0-based logical column position
        for cell_raw in cell_strings:
            cell = cell_raw.strip()

            # Default per column-spec.
            colspan = 1
            cell_align = (
                alignments[col_idx] if col_idx < len(alignments) else "left"
            )
            cell_content = cell

            mc = _MULTICOLUMN_RE.match(cell)
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
                # Multicolumn spec controls its own borders.
                mc_left = spec.startswith("|")
                mc_right = spec.endswith("|")
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

            parts.append(
                f"<td{attrs}>{_render_cell_content(cell_content)}</td>"
            )
            col_idx += colspan

        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)
