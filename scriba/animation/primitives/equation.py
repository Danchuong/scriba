"""Equation primitive — math as an evolving object.

A first-class shape whose native accessors are ``term[<id>]`` (tagged
sub-expressions declared via the scriba-owned ``\\term{id}{body}`` macro) and
``line[<i>]`` (aligned rows of a multi-line derivation). Unlike a ``$...$``
atom on someone else's cell, an ``Equation``'s sub-terms and aligned lines are
independently addressable — so a teacher can tint one term, reveal a derivation
line-by-line, or swap a whole line, all riding the existing motion kinds
(``recolor`` / ``value_change`` / ``annotation_*``).

See ``investigations/design-math.md`` (Approach C) for the full rationale, the
KaTeX ``\\htmlClass`` selective-trust verification, and the security proof.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives._text_metrics import measure_value_text
from scriba.animation.primitives._text_render import (
    _escape_xml,
    _render_mixed_html,
    strip_math_markup,
)
from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    register_primitive,
    state_class,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register

# ---------------------------------------------------------------------------
# Layout constants (display-equation scale). foreignObjects paint
# overflow:visible so a tall \frac/\sum never clips; these size the reserved
# envelope (viewBox) which is frame-invariant (R-32).
# ---------------------------------------------------------------------------
_EQ_FONT_PX: int = 20          # display-equation font size
_EQ_LINE_H: int = 46           # per-line row height (clears fractions/limits)
_EQ_PAD_X: int = 12            # horizontal breathing room around the content
_EQ_CAPTION_GAP: int = 8       # gap between the last line and the caption

# A ``\term`` id is an ASCII identifier (no leading digit) so the rewritten
# ``scriba-term-<id>`` is a safe CSS class AND the selector ``E.term[<id>]``
# can address it (the selector index parser reads a bare identifier).
_TERM_ID_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Match the KaTeX span carrying a scriba-term class (emitted by \htmlClass
# under selective trust) so we can graft on the primitive's data-target +
# state class. Only OUR term spans carry ``scriba-term-<id>``; KaTeX's own
# classes (katex/base/mord/…) never do, and the source-echo in the MathML
# ``<annotation>`` is ``\htmlClass{…}`` text (no ``class="``), so it is not
# matched. Deterministic — scriba emitted the class.
_TERM_SPAN_RE = re.compile(
    r'class="(?P<cls>[^"]*\bscriba-term-(?P<id>[A-Za-z0-9_]+)\b[^"]*)"'
)

_TERM_MACRO = "\\term{"


def _scan_and_rewrite(text: str) -> tuple[str, str, list[str], "tuple[str, str] | None"]:
    """Rewrite ``\\term{id}{body}`` → ``\\htmlClass{scriba-term-<id>}{body}``.

    Returns ``(katex_form, display_form, ids, error)``:

    * ``katex_form`` — the string sent to KaTeX (``\\term`` → ``\\htmlClass``).
    * ``display_form`` — ``\\term`` unwrapped to just ``body`` (no tagging), for
      deterministic width measurement.
    * ``ids`` — the declared term ids, in source order.
    * ``error`` — the FIRST ``(code, detail)`` encountered, or ``None``:
        - ``E1531`` duplicate ``\\term`` id within this line, or
        - ``E1532`` malformed ``\\term`` (non-identifier id, or missing body).

    Callers preprocess strictly at declaration time (raise on ``error``) and
    leniently at emit time for value overrides (ignore ``error``).
    """
    out_katex: list[str] = []
    out_disp: list[str] = []
    ids: list[str] = []
    error: "tuple[str, str] | None" = None
    i = 0
    n = len(text)
    while i < n:
        j = text.find(_TERM_MACRO, i)
        if j == -1:
            out_katex.append(text[i:])
            out_disp.append(text[i:])
            break
        out_katex.append(text[i:j])
        out_disp.append(text[i:j])

        # -- id, up to the first '}' --
        k = j + len(_TERM_MACRO)
        end_id = text.find("}", k)
        if end_id == -1:
            error = error or ("E1532", "\\term is missing its closing id brace")
            out_katex.append(text[j:])
            out_disp.append(text[j:])
            break
        tid = text[k:end_id]
        if not _TERM_ID_RE.fullmatch(tid):
            error = error or (
                "E1532",
                f"\\term id {tid!r} is not an identifier "
                "([A-Za-z_][A-Za-z0-9_]*)",
            )
            out_katex.append(text[j : end_id + 1])
            out_disp.append(text[j : end_id + 1])
            i = end_id + 1
            continue

        # -- body: a brace-balanced group immediately after the id --
        if end_id + 1 >= n or text[end_id + 1] != "{":
            error = error or ("E1532", f"\\term{{{tid}}} is missing its {{body}}")
            out_katex.append(text[j : end_id + 1])
            out_disp.append(text[j : end_id + 1])
            i = end_id + 1
            continue
        depth = 0
        b = end_id + 1
        body_start = end_id + 2
        while b < n:
            c = text[b]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            b += 1
        if b >= n or depth != 0:
            error = error or ("E1532", f"\\term{{{tid}}} has an unterminated body")
            out_katex.append(text[j:])
            out_disp.append(text[j:])
            break
        body = text[body_start:b]

        if tid in ids:
            error = error or ("E1531", f"duplicate \\term id {tid!r} in one line")
        ids.append(tid)
        out_katex.append(f"\\htmlClass{{scriba-term-{tid}}}{{{body}}}")
        out_disp.append(body)
        i = b + 1

    return "".join(out_katex), "".join(out_disp), ids, error


def _split_align(line: str) -> tuple[str, str]:
    """Split a line at its FIRST unescaped ``&`` (the alignment anchor).

    Returns ``(lhs, rhs)``; a line with no ``&`` is all ``lhs`` (``rhs=""``).
    ``\\&`` (literal ampersand) is not a split point.
    """
    m = re.search(r"(?<!\\)&", line)
    if m is None:
        return line, ""
    return line[: m.start()], line[m.end():]


@register_primitive("Equation")
@_protocol_register
class Equation(PrimitiveBase):
    """Math as an evolving object — addressable terms and aligned lines.

    Parameters (``\\shape{E}{Equation}{...}``):

    * ``tex`` — a single equation, e.g.
      ``tex="T(n)=2\\term{rec}{T(n/2)}+\\term{work}{cn}"``.
    * ``lines`` — a multi-line aligned derivation (rows aligned on the first
      ``&``), e.g. ``lines=["T(n) &= 2\\term{rec}{T(n/2)}+\\term{work}{cn}",
      "&= 4\\term{rec}{T(n/4)}+2\\term{work}{cn}"]``.
    * ``label`` — optional caption below the equation.

    Accessors: ``E.line[i]`` (i-th aligned row, 0-based), ``E.term[id]`` (a
    tagged sub-expression), ``E.all`` (every line). The same ``\\term`` id may
    repeat across lines (that is how "the same term" is tracked down a
    derivation); within ONE line an id must be unique (E1531).
    """

    primitive_type = "equation"
    # \apply re-typeset verbs (per-line value= handled generically).
    APPLY_KEYS: ClassVar[frozenset[str]] = frozenset({"lines", "tex"})

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "line[{i}]": "aligned row by index",
        "term[{id}]": "tagged sub-expression",
        "all": "all lines",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({"tex", "lines", "label"})

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)

        tex = self.params.get("tex")
        lines = self.params.get("lines")
        if tex is not None and lines is not None:
            # Contradictory declaration — ``lines`` used to silently win and
            # ``tex`` vanished (hunt-authoring-traps-026.md F5). The docs
            # (§7.21) promise "exactly one of tex/lines"; enforce it.
            raise _animation_error(
                "E1530",
                detail="Equation accepts exactly one of 'tex' or 'lines', not both",
                hint=(
                    'give just one, e.g. tex="T(n)=2T(n/2)+cn" OR '
                    'lines=["a &= b", "&= c"]'
                ),
            )
        if lines is not None:
            if not isinstance(lines, (list, tuple)) or not lines:
                raise _animation_error(
                    "E1530",
                    detail="Equation 'lines' must be a non-empty list of strings",
                    hint='example: \\shape{D}{Equation}{lines=["a &= b", "&= c"]}',
                )
            raw_lines = [str(x) for x in lines]
        elif tex is not None:
            raw_lines = [str(tex)]
        else:
            raise _animation_error(
                "E1530",
                detail="Equation requires a 'tex' or 'lines' parameter",
                hint='example: \\shape{E}{Equation}{tex="T(n)=2T(n/2)+cn"}',
            )

        self.label: str | None = self.params.get("label")

        # Preprocess (strict): rewrite \term, collect the declared id set,
        # raising E1531 (dup within a line) / E1532 (malformed) at the shape
        # declaration boundary.
        self._raw_lines: tuple[str, ...] = tuple(raw_lines)
        rendered: list[str] = []
        term_ids: list[str] = []
        for line in raw_lines:
            katex_form, _disp, ids, error = _scan_and_rewrite(line)
            if error is not None:
                raise _animation_error(
                    error[0],
                    detail=error[1],
                    hint="\\term{id}{body}: id is an identifier, body is braced",
                )
            rendered.append(katex_form)
            for tid in ids:
                if tid not in term_ids:
                    term_ids.append(tid)
        self._rendered_lines: list[str] = rendered
        self._term_ids: tuple[str, ...] = tuple(term_ids)

    # -- structural apply (whole-equation re-typeset; bare-shape convenience) --

    def apply_command(
        self, params: dict[str, Any], *, target_suffix: str | None = None
    ) -> None:
        """``\\apply{E}{tex=...}`` / ``\\apply{E}{lines=[...]}`` re-typesets the
        whole equation.

        The value_change-riding swap of a single line is
        ``\\apply{E.line[i]}{value="new tex"}`` (mirrors ``Bar``'s
        ``\\apply{h.bar[i]}{value=X}``): a ``value=`` on the ``line[i]`` PART
        flows through ``set_value`` and the differ emits ``value_change``. A
        bare-shape ``tex=``/``lines=`` re-typeset routes here instead (the
        frame renderer skips ``set_value`` for a bare shape).
        """
        new: list[str] | None = None
        if "lines" in params and isinstance(params["lines"], (list, tuple)):
            new = [str(x) for x in params["lines"]]
        elif "tex" in params:
            new = [str(params["tex"])]
        if not new:
            return
        rendered: list[str] = []
        term_ids: list[str] = list(self._term_ids)
        for line in new:
            katex_form, _disp, ids, _error = _scan_and_rewrite(line)  # lenient
            rendered.append(katex_form)
            for tid in ids:
                if tid not in term_ids:
                    term_ids.append(tid)
        self._raw_lines = tuple(new)
        self._rendered_lines = rendered
        self._term_ids = tuple(term_ids)

    # -- PrimitiveBase interface --------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts = [f"line[{i}]" for i in range(len(self._rendered_lines))]
        parts.extend(f"term[{tid}]" for tid in self._term_ids)
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True
        m = re.fullmatch(r"line\[(\d+)\]", suffix)
        if m:
            return 0 <= int(m.group(1)) < len(self._rendered_lines)
        m = re.fullmatch(r"term\[([A-Za-z0-9_]+)\]", suffix)
        if m:
            return m.group(1) in self._term_ids
        return False

    def _effective_line_katex(self, i: int) -> str:
        """The KaTeX-form tex for line ``i``, honouring a ``\\apply`` value
        override (``\\apply{E.line[i]}{value=...}`` → ``set_value``)."""
        override = self.get_value(f"line[{i}]")
        if override is not None:
            katex_form, _disp, _ids, _error = _scan_and_rewrite(str(override))
            return katex_form
        return self._rendered_lines[i]

    def _line_display(self, i: int) -> str:
        override = self.get_value(f"line[{i}]")
        source = str(override) if override is not None else self._raw_lines[i]
        _katex, disp, _ids, _error = _scan_and_rewrite(source)
        return disp

    @staticmethod
    def _frag_width(disp_frag: str) -> int:
        """Deterministic width estimate for a display fragment (KaTeX-aware
        via ``measure_value_text`` on the ``$...$`` form)."""
        if not disp_frag.strip():
            return 0
        return measure_value_text(f"${disp_frag}$", _EQ_FONT_PX)

    def _column_x(self) -> int:
        """The shared ``&``-anchor x: the widest pre-``&`` (lhs) width across
        all lines. Every line's rhs starts here, so the anchor column is
        identical for every row (aligned)."""
        widest = 0
        for i in range(len(self._rendered_lines)):
            lhs, _rhs = _split_align(self._line_display(i))
            widest = max(widest, self._frag_width(lhs))
        return widest + _EQ_PAD_X

    def _content_width(self) -> int:
        col = self._column_x()
        widest_rhs = 0
        for i in range(len(self._rendered_lines)):
            _lhs, rhs = _split_align(self._line_display(i))
            widest_rhs = max(widest_rhs, self._frag_width(rhs))
        return col + widest_rhs + _EQ_PAD_X

    def _content_height(self) -> int:
        return len(self._rendered_lines) * _EQ_LINE_H

    def _fo(
        self,
        frag_katex: str,
        x: int,
        y: int,
        w: int,
        css_class: str,
        align: str,
        render_inline_tex: "Callable[[str], str] | None",
    ) -> str:
        """One ``<foreignObject>`` wrapping a rendered KaTeX fragment (with
        term data-targets grafted on), or a plain-text fallback when no KaTeX
        callback is available."""
        if not frag_katex.strip():
            return ""
        if render_inline_tex is not None:
            inner = _render_mixed_html(f"${frag_katex}$", render_inline_tex)
            inner = self._inject_term_targets(inner)
        else:
            inner = _escape_xml(strip_math_markup(f"${frag_katex}$"))
        style = (
            f"width:{w}px;height:{_EQ_LINE_H}px;line-height:{_EQ_LINE_H}px;"
            f"text-align:{align};white-space:nowrap;font-size:{_EQ_FONT_PX}px;"
            "font-family:var(--scriba-fo-font-family, 'Scriba Sans', sans-serif)"
        )
        return (
            f'<foreignObject class="{css_class}" x="{x}" y="{y}" '
            f'width="{w}" height="{_EQ_LINE_H}" overflow="visible">'
            f'<div xmlns="http://www.w3.org/1999/xhtml" style="{style}">'
            f"{inner}</div></foreignObject>"
        )

    def _inject_term_targets(self, html: str) -> str:
        """Graft ``data-target`` + the resolved state class onto every KaTeX
        term span (deterministic — scriba emitted the ``scriba-term-<id>``
        class). The term inherits ``.scriba-term.scriba-state-*`` colour, so
        ``\\recolor{E.term[id]}{state=...}`` tints exactly that sub-expression
        while its siblings keep their ink."""
        def repl(m: re.Match[str]) -> str:
            cls = m.group("cls")
            tid = m.group("id")
            state = self.resolve_effective_state(f"term[{tid}]")
            return (
                f'class="{cls} scriba-term {state_class(state)}" '
                f'data-target="{self.name}.term[{tid}]"'
            )

        return _TERM_SPAN_RE.sub(repl, html)

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        arrow_above = self._reserved_arrow_above()
        col_x = self._column_x()

        lines: list[str] = [
            f'<g data-primitive="equation" data-shape="{self.name}">'
        ]
        if arrow_above > 0:
            lines.append(f'  <g transform="translate(0, {arrow_above})">')

        for i in range(len(self._rendered_lines)):
            suffix = f"line[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.resolve_effective_state(suffix)
            y = i * _EQ_LINE_H

            katex = self._effective_line_katex(i)
            disp = self._line_display(i)
            lhs_katex, rhs_katex = _split_align(katex)
            lhs_disp, rhs_disp = _split_align(disp)
            lhs_w = self._frag_width(lhs_disp)
            rhs_w = self._frag_width(rhs_disp)

            # Every line + term is emitted on EVERY frame (hidden lines carry
            # scriba-state-hidden = display:none, space still reserved) so the
            # bounding box is frame-invariant across a reveal (R-32).
            lines.append(f'  <g data-target="{target}" class="{state_class(state)}">')
            lhs_fo = self._fo(
                lhs_katex, col_x - lhs_w, y, max(lhs_w, 1),
                "scriba-eqn-lhs", "right", render_inline_tex,
            )
            if lhs_fo:
                lines.append(f"    {lhs_fo}")
            rhs_fo = self._fo(
                rhs_katex, col_x, y, max(rhs_w, 1),
                "scriba-eqn-rhs", "left", render_inline_tex,
            )
            if rhs_fo:
                lines.append(f"    {rhs_fo}")
            lines.append("  </g>")

        # Caption (optional) — below the last line, centered on the content.
        if self._caption_lines(self._content_width()):
            caption_top = self._content_height() + _EQ_CAPTION_GAP
            self._emit_caption(
                lines,
                content_width=self._content_width(),
                footprint_width=self._content_width(),
                top_y=caption_top,
                render_inline_tex=render_inline_tex,
            )

        if self._annotations:
            self.emit_annotation_arrows(
                lines,
                self._annotations,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
            )

        if arrow_above > 0:
            lines.append("  </g>")
        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> BoundingBox:
        """Frame-invariant footprint: every line and term is reserved on every
        frame regardless of reveal state (R-32)."""
        w = self._content_width()
        h = self._reserved_arrow_above() + self._content_height()
        cap_h = self._caption_block_height(self._content_width())
        if cap_h:
            h += _EQ_CAPTION_GAP + cap_h
        return BoundingBox(x=0, y=0, width=int(w), height=int(h))

    # -- annotation anchors --------------------------------------------------

    def _line_index_of(self, suffix: str) -> int | None:
        m = re.fullmatch(r"line\[(\d+)\]", suffix)
        if m and 0 <= int(m.group(1)) < len(self._rendered_lines):
            return int(m.group(1))
        m = re.fullmatch(r"term\[([A-Za-z0-9_]+)\]", suffix)
        if m and m.group(1) in self._term_ids:
            tid = m.group(1)
            for i, line in enumerate(self._raw_lines):
                if f"\\term{{{tid}}}" in line:
                    return i
            return 0
        return None

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Arrow anchor for ``E.line[i]`` / ``E.term[id]`` — the row's top
        centre (arrows curve above). A term resolves to the row that declares
        it (line-level precision; KaTeX glyph geometry is not modelled in v1)."""
        prefix = self.name + "."
        if not selector.startswith(prefix):
            return None
        i = self._line_index_of(selector[len(prefix):])
        if i is None:
            return None
        return (float(self._content_width() // 2), float(i * _EQ_LINE_H))

    def resolve_label_anchor(self, selector: str) -> tuple[float, float] | None:
        pt = self.resolve_annotation_point(selector)
        if pt is None:
            return None
        return (pt[0], pt[1] + _EQ_LINE_H / 2)

    # -- obstacle protocol stubs --------------------------------------------

    def resolve_obstacle_boxes(self) -> list:
        return []

    def resolve_obstacle_segments(self) -> list:
        return []
