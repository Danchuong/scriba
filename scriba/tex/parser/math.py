"""Math delimiter extraction and KaTeX batch dispatch.

Supports ``$...$`` (inline), ``$$...$$`` and ``$$$...$$$`` (display). The
escaped form ``\\$`` is normalized to a placeholder before scanning so the
literal dollar never enters the math regex.

See ``docs/scriba/02-tex-plugin.md`` §5 for the worker protocol.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from scriba.core.errors import RendererError, ValidationError
from scriba.core.workers import PersistentSubprocessWorker
from scriba.tex.parser.escape import PlaceholderManager

_DOLLAR_LITERAL = "\x00SCRIBA_TEX_DOLLAR\x00"

MAX_MATH_ITEMS = 500
"""Maximum number of math expressions allowed per document."""

# ---------------------------------------------------------------------------
# Module-level compiled patterns for _preprocess_text_command_chars
# ---------------------------------------------------------------------------

_TEXT_CMD_RE = re.compile(
    r"\\(texttt|textbf|textit|textsc|textrm|textsf|text)\{([^}]*)\}"
)
_ESC_UNDERSCORE_RE = re.compile(r"(?<!\\)_")
_ESC_HASH_RE = re.compile(r"(?<!\\)#")
_ESC_PERCENT_RE = re.compile(r"(?<!\\)%")
_ESC_AMP_RE = re.compile(r"(?<!\\)&")


@dataclass(frozen=True)
class _MathItem:
    placeholder: str
    math: str
    display: bool


def _preprocess_text_command_chars(math: str) -> str:
    """Escape ``_ # % &`` inside ``\\text*{}`` for KaTeX compatibility.

    KaTeX does not switch to text mode inside ``\\text``, so a raw ``_`` in
    ``\\text{a_b}`` is parsed as a subscript and fails. Mirrors the upstream
    ``_preprocess_math_for_katex`` helper from ``tex_renderer.py``.
    """
    def _esc(m: re.Match[str]) -> str:
        cmd = m.group(1)
        inner = m.group(2)
        inner = _ESC_UNDERSCORE_RE.sub(r"\\_", inner)
        inner = _ESC_HASH_RE.sub(r"\\#", inner)
        inner = _ESC_PERCENT_RE.sub(r"\\%", inner)
        inner = _ESC_AMP_RE.sub(r"\\&", inner)
        return "\\" + cmd + "{" + inner + "}"

    return _TEXT_CMD_RE.sub(_esc, math)


def extract_math(
    text: str, placeholders: PlaceholderManager
) -> tuple[str, list[_MathItem]]:
    """Replace every math span with a placeholder and collect the items.

    Returns the rewritten text plus the ordered list of math items still
    needing KaTeX rendering.
    """
    items: list[_MathItem] = []

    # Step 0: hide escaped \$ so the regexes never see it.
    text = text.replace("\\$", _DOLLAR_LITERAL)

    def _make_item(math: str, display: bool) -> str:
        cleaned = _preprocess_text_command_chars(math.strip())
        token = placeholders.store("", is_block=display)
        items.append(_MathItem(placeholder=token, math=cleaned, display=display))
        return token

    # Triple-dollar display first (Polygon), then double, then single.
    text = re.sub(
        r"\$\$\$([\s\S]*?)\$\$\$",
        lambda m: _make_item(m.group(1), True),
        text,
    )
    text = re.sub(
        r"\$\$([\s\S]*?)\$\$",
        lambda m: _make_item(m.group(1), True),
        text,
    )
    text = re.sub(
        r"\$([^\$]+?)\$",
        lambda m: _make_item(m.group(1), False),
        text,
    )

    if len(items) > MAX_MATH_ITEMS:
        raise ValidationError(
            f"too many math expressions: {len(items)} > {MAX_MATH_ITEMS}"
        )

    return text, items


def restore_dollar_literals(text: str) -> str:
    """Convert the dollar-literal sentinel back into ``$``."""
    return text.replace(_DOLLAR_LITERAL, "$")


def render_math_batch(
    items: list[_MathItem],
    *,
    worker: PersistentSubprocessWorker,
    macros: dict[str, str] | None,
    strict: bool,
    timeout: float,
) -> dict[str, str]:
    """Render every math item via the KaTeX worker. Returns placeholder→html.

    Wraps display results in ``<div class="scriba-tex-math-display">``
    and inline results in ``<span class="scriba-tex-math-inline">``.
    """
    if not items:
        return {}

    request: dict = {
        "type": "batch",
        "items": [
            {"math": it.math, "displayMode": it.display} for it in items
        ],
    }
    if macros:
        request["macros"] = dict(macros)

    response = worker.send(request, timeout=timeout)
    results = response.get("results") or []
    if len(results) != len(items):
        raise RendererError(
            f"katex worker returned {len(results)} results for {len(items)} items",
            renderer="tex",
        )

    out: dict[str, str] = {}
    for item, res in zip(items, results):
        html = res.get("html")
        error = res.get("error")
        if html is None:
            if strict:
                raise RendererError(
                    f"katex error: {error}", renderer="tex"
                )
            safe_src = (
                item.math.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            html = (
                f'<span class="scriba-tex-math-error" '
                f'title="{safe_src}">{safe_src}</span>'
            )
        if item.display:
            out[item.placeholder] = (
                f'<div class="scriba-tex-math-display">{html}</div>'
            )
        else:
            out[item.placeholder] = (
                f'<span class="scriba-tex-math-inline">{html}</span>'
            )
    return out
