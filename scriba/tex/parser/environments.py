"""Sectioning, center, basic epigraph, and URL handling.

See ``docs/scriba/02-tex-plugin.md`` §3 for the HTML output contract and
§9 for the XSS hardening rules around ``\\href`` and ``\\url``.
"""

from __future__ import annotations

import re
import unicodedata

from scriba.tex.parser._urls import is_safe_url as _is_safe_url
from scriba.tex.parser.escape import (
    extract_brace_content,
    html_escape_attr,
    html_escape_text,
)


def slugify(text: str) -> str:
    """Slugify heading text per ``02-tex-plugin.md`` §3.1."""
    decoded = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    # Strip any HTML tags that snuck in (e.g. via inline math residue).
    decoded = re.sub(r"<[^>]+>", "", decoded)
    normalized = unicodedata.normalize("NFKD", decoded)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    lowered = stripped.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "section"


def apply_sections(text: str, slug_counts: dict[str, int]) -> str:
    """Convert ``\\section``/``\\subsection``/``\\subsubsection`` to headings.

    ``slug_counts`` is mutated to track per-render duplicate suffixes.
    """

    def _make_replacer(level: int):
        cls = f"scriba-tex-heading scriba-tex-heading-{level}"
        tag = {2: "h2", 3: "h3", 4: "h4"}[level]

        def replacer(m: re.Match[str]) -> str:
            heading = m.group(1)
            base = slugify(heading)
            slug_counts[base] = slug_counts.get(base, 0) + 1
            slug = base if slug_counts[base] == 1 else f"{base}-{slug_counts[base]}"
            return f'<{tag} id="{slug}" class="{cls}">{heading}</{tag}>'

        return replacer

    text = re.sub(r"\\subsubsection\{([^}]*)\}", _make_replacer(4), text)
    text = re.sub(r"\\subsection\{([^}]*)\}", _make_replacer(3), text)
    text = re.sub(r"\\section\{([^}]*)\}", _make_replacer(2), text)
    return text


def apply_center(text: str) -> str:
    """Wrap ``\\begin{center}...\\end{center}`` in ``scriba-tex-center`` div."""
    return re.sub(
        r"\\begin\{center\}([\s\S]*?)\\end\{center\}",
        r'<div class="scriba-tex-center">\1</div>',
        text,
    )


def apply_epigraph(text: str) -> str:
    """Convert ``\\epigraph{quote}{attribution}`` to a blockquote.

    Phase 2c emits a basic version that HTML-escapes the quote and the
    attribution text. Inline LaTeX inside attribution is deferred to 2d.
    """
    out_parts: list[str] = []
    cursor = 0
    needle = "\\epigraph{"
    while True:
        idx = text.find(needle, cursor)
        if idx == -1:
            out_parts.append(text[cursor:])
            break
        out_parts.append(text[cursor:idx])
        # Parse two consecutive {...} bodies.
        body1, after1 = extract_brace_content(text, idx + len("\\epigraph"))
        if after1 == idx + len("\\epigraph"):
            out_parts.append(text[idx:])
            break
        body2, after2 = extract_brace_content(text, after1)
        if after2 == after1:
            out_parts.append(text[idx:])
            break
        quote = html_escape_text(body1).strip()
        attr = html_escape_text(body2).strip()
        out_parts.append(
            '<blockquote class="scriba-tex-epigraph">'
            f'<p class="scriba-tex-epigraph-quote">{quote}</p>'
            f'<footer class="scriba-tex-epigraph-attribution">{attr}</footer>'
            "</blockquote>"
        )
        cursor = after2
    return "".join(out_parts)


def apply_urls(text: str) -> str:
    """Convert ``\\url{}`` and ``\\href{}{}`` to anchor tags or disabled spans."""

    def _url_sub(m: re.Match[str]) -> str:
        raw = m.group(1)
        if not _is_safe_url(raw):
            return f'<span class="scriba-tex-link-disabled">{html_escape_text(raw)}</span>'
        href = html_escape_attr(raw)
        return (
            f'<a class="scriba-tex-link" href="{href}" '
            f'rel="noopener noreferrer">{href}</a>'
        )

    def _href_sub(m: re.Match[str]) -> str:
        raw = m.group(1)
        text_label = m.group(2)
        if not _is_safe_url(raw):
            return f'<span class="scriba-tex-link-disabled">{html_escape_text(text_label)}</span>'
        href = html_escape_attr(raw)
        return (
            f'<a class="scriba-tex-link" href="{href}" '
            f'rel="noopener noreferrer">{html_escape_text(text_label)}</a>'
        )

    text = re.sub(r"\\href\{([^}]*)\}\{([^}]*)\}", _href_sub, text)
    text = re.sub(r"\\url\{([^}]*)\}", _url_sub, text)
    return text
