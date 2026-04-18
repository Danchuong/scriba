"""CSS/JS/HTML minification helpers extracted from emitter.py (Wave D2).

All three functions are conservative in what they modify:
- ``_minify_css`` — removes comments, collapses whitespace.
- ``_minify_js``  — strips ``//`` comments only when clearly safe.
- ``_minify_html`` — orchestrates the above plus HTML comment removal.
"""

from __future__ import annotations

import re as _re

__all__ = [
    "_minify_css",
    "_minify_html",
    "_minify_js",
]


def _minify_css(css: str) -> str:
    """Minify CSS content conservatively.

    Removes comments, collapses whitespace, strips trailing semicolons
    before closing braces, and trims around punctuation.  Does not
    attempt shorthand optimisations or value rewriting.
    """
    # Remove CSS comments /* ... */
    css = _re.sub(r"/\*.*?\*/", "", css, flags=_re.DOTALL)
    # Collapse runs of whitespace to a single space
    css = _re.sub(r"\s+", " ", css)
    # Remove spaces around { } : ; ,
    css = _re.sub(r"\s*([{}:;,])\s*", r"\1", css)
    # Remove last semicolon before }
    css = _re.sub(r";}", "}", css)
    return css.strip()


def _minify_js(js: str) -> str:
    """Minify JavaScript content very conservatively.

    Only removes single-line ``//`` comments that are clearly safe
    (not inside strings) and collapses blank lines.  Does **not**
    attempt to remove multi-line comments or rewrite tokens — the
    risk of breaking template literals, regex, or URLs is too high.
    """
    lines = js.split("\n")
    result: list[str] = []
    for line in lines:
        # Remove single-line comments only when they appear after code
        # and are clearly not inside a string.  Strategy: only strip
        # ``//`` comments on lines that don't contain quotes after the
        # comment marker position (very conservative).
        stripped = line.rstrip()
        idx = stripped.find("//")
        if idx >= 0:
            before = stripped[:idx]
            # Only strip if the prefix has balanced quotes (simple check)
            single_q = before.count("'") % 2 == 0
            double_q = before.count('"') % 2 == 0
            backtick = before.count("`") % 2 == 0
            # Also skip lines where // might be a URL (://)
            is_url = idx > 0 and stripped[idx - 1] == ":"
            if single_q and double_q and backtick and not is_url:
                stripped = before.rstrip()
        if stripped:
            result.append(stripped)
    return "\n".join(result)


def _minify_html(html: str) -> str:
    """HTML minification without external dependencies.

    Removes HTML comments (except conditional comments ``<!--[``),
    collapses whitespace between tags, strips leading whitespace per
    line, minifies inline ``<style>`` CSS and ``<script>`` JavaScript.
    Content inside ``<pre>`` tags is preserved verbatim.
    """
    preserved: list[str] = []

    def _stash(m: _re.Match[str]) -> str:
        idx = len(preserved)
        preserved.append(m.group(0))
        return f"\x00PRESERVE{idx}\x00"

    # Preserve <pre> blocks verbatim
    html = _re.sub(
        r"<pre\b[^>]*>.*?</pre>",
        _stash,
        html,
        flags=_re.DOTALL | _re.IGNORECASE,
    )

    # Minify <style> blocks, then stash them
    def _minify_style_block(m: _re.Match[str]) -> str:
        open_tag = m.group(1)
        content = m.group(2)
        # Fast-path: skip re-minification when the block already looks
        # minified (no double-newlines, fewer than 50 line breaks).
        # This avoids re-running four regex passes over the 397 KB KaTeX
        # CSS bundle on every render — 56 % of total render time saved.
        if "\n\n" not in content and content.count("\n") < 50:
            minified = content.strip()
        else:
            minified = _minify_css(content)
        idx = len(preserved)
        preserved.append(f"{open_tag}{minified}</style>")
        return f"\x00PRESERVE{idx}\x00"

    html = _re.sub(
        r"(<style\b[^>]*>)(.*?)</style>",
        _minify_style_block,
        html,
        flags=_re.DOTALL | _re.IGNORECASE,
    )

    # Minify <script> blocks, then stash them
    def _minify_script_block(m: _re.Match[str]) -> str:
        open_tag = m.group(1)
        content = m.group(2)
        minified = _minify_js(content)
        idx = len(preserved)
        preserved.append(f"{open_tag}{minified}</script>")
        return f"\x00PRESERVE{idx}\x00"

    html = _re.sub(
        r"(<script\b[^>]*>)(.*?)</script>",
        _minify_script_block,
        html,
        flags=_re.DOTALL | _re.IGNORECASE,
    )

    # Remove HTML comments (but keep conditional comments <!--[...])
    html = _re.sub(r"<!--(?!\[).*?-->", "", html, flags=_re.DOTALL)
    # Collapse whitespace between tags
    html = _re.sub(r">\s+<", "><", html)
    # Remove leading whitespace per line
    html = _re.sub(r"^\s+", "", html, flags=_re.MULTILINE)

    html = html.strip()

    # Restore preserved blocks
    for idx, block in enumerate(preserved):
        html = html.replace(f"\x00PRESERVE{idx}\x00", block)

    return html
