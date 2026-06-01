"""\\hl{step-id}{tex} macro — highlight a LaTeX term synced to filmstrip frames.

The macro produces a ``<span class="scriba-hl">`` wrapper whose
``data-hl-step`` attribute ties it to a specific animation step.  When the
browser navigates to ``#scene-frame-N``, a pure-CSS ``:target`` rule lights
up the matching spans — zero JavaScript required.
"""

from __future__ import annotations

import html
import re
from typing import Callable

from scriba.animation.errors import _animation_error, _suggest_closest

# Matches the start of \hl{ — balanced-brace extraction follows.
_HL_START_RE = re.compile(r"\\hl\{")


def _escape_attr(value: str) -> str:
    """HTML-escape a value for safe embedding inside an attribute."""
    return html.escape(value, quote=True)


def _escape_html(value: str) -> str:
    """HTML-escape content for safe embedding inside element bodies."""
    return html.escape(value, quote=False)


def _extract_braced(text: str, start: int) -> tuple[str, int] | None:
    """Extract content between balanced braces starting at *start*.

    *start* must point at the opening ``{``.  Returns ``(content, end)``
    where *end* is the index just past the closing ``}``, or *None* if
    braces are unbalanced.
    """
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
        i += 1
    return None


def process_hl_macros(
    narration: str,
    scene_id: str,
    render_inline_tex: Callable[[str], str] | None = None,
    escape_plain_text: bool = True,
    span_wrapper: Callable[[str], str] | None = None,
    valid_step_ids: frozenset[str] | None = None,
) -> str:
    r"""Replace ``\hl{step-id}{tex}`` macros with highlighted ``<span>`` elements.

    Parameters
    ----------
    narration:
        Raw narration string potentially containing ``\hl`` macros.
    scene_id:
        Identifier of the enclosing scene (reserved for future scoping).
    render_inline_tex:
        Optional callback that converts a TeX string to HTML (e.g. KaTeX).
        When *None*, the tex body is HTML-escaped instead.
    escape_plain_text:
        When ``True`` (default), plain-text segments between ``\hl``
        macros are HTML-escaped for safe embedding.  When ``False``, the
        caller is responsible for downstream escaping — used by
        ``_render_narration`` which passes the result through the TeX
        renderer immediately afterwards.  The TeX renderer does its own
        math-aware escape (extract ``$...$`` first, then escape free
        text), so pre-escaping here would double-process the ``<`` inside
        math delimiters and break KaTeX parsing (e.g. ``$\min_{j<1}$``
        becomes ``$\min_{j&lt;1}$`` which KaTeX rejects).
    span_wrapper:
        Optional callback applied to each generated ``<span>`` before it
        is appended.  ``_render_narration`` uses this to swap the span for
        a placeholder token so the downstream TeX renderer (which escapes
        ``<``/``>`` in free text) does not clobber the span HTML; the real
        span is restored after TeX rendering.  When *None* the span HTML
        is emitted directly.
    valid_step_ids:
        Optional set of step-ids that ``\hl`` may legitimately reference
        — the union of declared ``\step[label=...]`` labels and the
        implicit ``step{N}`` ids (``N = 1..frame_count``).  When supplied,
        any ``\hl`` whose step-id is not in the set raises **E1321** so a
        typo'd cross-reference fails loud instead of emitting a dead span.
        When *None* (default) no validation is performed — preserving the
        legacy contract for callers that do not know the valid set.

    Returns
    -------
    str
        The narration with all ``\hl`` macros replaced by ``<span>`` tags.
    """
    escape_fn = _escape_html if escape_plain_text else (lambda s: s)
    parts: list[str] = []
    pos = 0

    for m in _HL_START_RE.finditer(narration):
        # Extract step-id (first braced group — already consumed by the regex).
        brace_start = m.end() - 1  # points at the '{' captured by the regex
        step_result = _extract_braced(narration, brace_start)
        if step_result is None:
            continue
        step_id, after_step = step_result

        # step-id must be non-empty
        if not step_id:
            continue

        # Validate the step-id against the known label/step{N} set (E1321).
        # Only enforced when the caller threads the valid set through; a
        # typo'd id otherwise produces a dead cross-reference with no signal.
        if valid_step_ids is not None and step_id not in valid_step_ids:
            suggestion = _suggest_closest(step_id, valid_step_ids)
            hint = (
                f"did you mean '{suggestion}'?"
                if suggestion is not None
                else (
                    "reference a \\step[label=...] declared in this "
                    "animation, or the implicit id step{N} (N = frame number)"
                )
            )
            raise _animation_error(
                "E1321",
                f"\\hl references unknown step-id {step_id!r}",
                hint=hint,
            )

        # The tex body must follow immediately in another braced group.
        if after_step >= len(narration) or narration[after_step] != "{":
            continue
        tex_result = _extract_braced(narration, after_step)
        if tex_result is None:
            continue
        tex_body, after_tex = tex_result

        # Render the tex body.
        if render_inline_tex is not None:
            rendered = render_inline_tex(tex_body)
        else:
            rendered = _escape_html(tex_body)

        # Assemble output. Plain-text escape is conditional — see
        # ``escape_plain_text`` doc above.
        parts.append(escape_fn(narration[pos : m.start()]))
        span_html = (
            f'<span class="scriba-hl" '
            f'data-hl-step="{_escape_attr(step_id)}">'
            f"{rendered}</span>"
        )
        parts.append(span_wrapper(span_html) if span_wrapper else span_html)
        pos = after_tex

    # Trailing plain text after the last macro — same conditional escape.
    parts.append(escape_fn(narration[pos:]))
    return "".join(parts)
