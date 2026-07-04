r"""``\ref{selector}{text}`` macro — a narration word that points at a cell.

Inside a ``\narrate{...}`` body, ``\ref{a.cell[2]}{pivot}`` colours the word
*pivot* to match ``a.cell[2]``'s **current-frame** visual state, so naming a
cell also points at it.  The ink follows the R-36 annotation-state palette
(``--scriba-annotation-state-*``) — the narration word sits on the page
background, not a coloured pill, so those WCAG-AA text inks are the correct
tokens, not the pill fills.

Resolution is honest about "no signal":

* ``state ∈ {current, done, dim, good, error, path}`` → tinted
  ``<span class="scriba-ref scriba-ref-state-{state}">``.
* a valid target with no signalling state (idle / highlight / hidden, or an
  unstated / range target) → bare ``<span class="scriba-ref">`` (inherits the
  body colour — an element with no state is not falsely coloured).
* an **undeclared shape** → soft **E1322**: the reference degrades to plain
  text (a narration typo must never blank a render).

This is a *renderer-level* macro pass co-located with ``process_hl_macros``
(the narrate body is a raw string with no grammar token stream), sharing the
same ``\x00``-placeholder stash so both macros' spans survive the downstream
KaTeX/escape pass.  ``\ref`` emphasis is tint-only in v1 (see
``investigations/anim-narrate-focus.md`` §2c): a baked ring is deferred
because ``scriba-highlighted`` is latent no-op paint on already-coloured cells.
"""

from __future__ import annotations

import re
from typing import Callable

from scriba.animation.constants import VALID_ANNOTATION_STATE_COLORS
from scriba.animation.extensions.hl_macro import (
    _escape_html,
    _extract_braced,
)

# Matches the start of \ref{ — balanced-brace extraction follows.
_REF_START_RE = re.compile(r"\\ref\{")


def process_ref_macros(
    narration: str,
    *,
    state_of: Callable[[str], str | None],
    render_inline_tex: Callable[[str], str] | None = None,
    escape_plain_text: bool = True,
    span_wrapper: Callable[[str], str] | None = None,
    warn: Callable[[str, str], None] | None = None,
) -> tuple[str, set[str]]:
    r"""Replace ``\ref{selector}{text}`` macros with state-tinted ``<span>``\s.

    Parameters
    ----------
    narration:
        Raw narration string potentially containing ``\ref`` macros.
    state_of:
        Resolver ``selector -> state | None``.  Returns the target's
        current-frame state string when the target's **shape** is declared
        (``"idle"`` for a valid-but-unstated / range target), or ``None``
        when the shape is undeclared (→ soft E1322, plain-text degrade).
    render_inline_tex:
        Optional callback converting the ``text`` argument (which may carry
        ``$math$``) to HTML.  When *None* the text is HTML-escaped instead.
    escape_plain_text:
        When ``True`` (default) plain-text segments between macros are
        HTML-escaped.  ``_render_narration`` passes ``False`` because it
        defers a single escape/render pass over the whole string (see the
        ``process_hl_macros`` contract for why pre-escaping breaks ``$math$``).
    span_wrapper:
        Optional callback applied to each generated span (and to the plain
        degrade output) before it is appended — used to stash the HTML behind
        a placeholder so the downstream escape pass does not clobber it.
    warn:
        Optional ``(code, message)`` sink for the soft **E1322** warning
        raised when a ``\ref`` names an undeclared shape.

    Returns
    -------
    tuple[str, set[str]]
        The rewritten narration and the set of resolved ``\ref`` targets
        (valid selectors), for a potential emphasis merge by the caller.
    """
    escape_fn = _escape_html if escape_plain_text else (lambda s: s)

    def _emit(html: str) -> str:
        return span_wrapper(html) if span_wrapper else html

    parts: list[str] = []
    ref_targets: set[str] = set()
    pos = 0

    for m in _REF_START_RE.finditer(narration):
        brace_start = m.end() - 1  # points at the '{' captured by the regex
        sel_result = _extract_braced(narration, brace_start)
        if sel_result is None:
            continue
        selector, after_sel = sel_result
        selector = selector.strip()
        if not selector:
            continue

        # The text body must follow immediately in another braced group.
        if after_sel >= len(narration) or narration[after_sel] != "{":
            continue
        text_result = _extract_braced(narration, after_sel)
        if text_result is None:
            continue
        text_body, after_text = text_result

        # Render the text body (math-aware via callback, else escape).
        if render_inline_tex is not None:
            rendered = render_inline_tex(text_body)
        else:
            rendered = _escape_html(text_body)

        state = state_of(selector)
        if state is None:
            # Undeclared shape → soft degrade to plain text + warning.
            if warn is not None:
                warn(
                    "E1322",
                    f"\\ref references an unknown or undeclared target "
                    f"{selector!r}; degraded to plain text",
                )
            piece = rendered
        elif state in VALID_ANNOTATION_STATE_COLORS:
            piece = (
                f'<span class="scriba-ref scriba-ref-state-{state}">'
                f"{rendered}</span>"
            )
            ref_targets.add(selector)
        else:
            # Valid target, no signalling state (idle/highlight/hidden/range).
            piece = f'<span class="scriba-ref">{rendered}</span>'
            ref_targets.add(selector)

        parts.append(escape_fn(narration[pos : m.start()]))
        parts.append(_emit(piece))
        pos = after_text

    parts.append(escape_fn(narration[pos:]))
    return "".join(parts), ref_targets
