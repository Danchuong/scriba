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

    Returns
    -------
    str
        The narration with all ``\hl`` macros replaced by ``<span>`` tags.
    """
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

        # Assemble output.
        parts.append(narration[pos : m.start()])
        parts.append(
            f'<span class="scriba-hl" '
            f'data-hl-step="{_escape_attr(step_id)}">'
            f"{rendered}</span>"
        )
        pos = after_tex

    parts.append(narration[pos:])
    return "".join(parts)
