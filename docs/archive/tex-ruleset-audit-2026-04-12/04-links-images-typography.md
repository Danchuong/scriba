# TeX Ruleset Audit: Links, Images, Typography, Character Escapes

**Date:** 2026-04-12
**Scope:** Sections 2.8, 2.9, 2.11, 2.12, 2.13 of `docs/spec/tex-ruleset.md`
**Auditor model:** Claude Opus 4.6 (1M context)

---

## Summary

| Category | Rules | PASS | PARTIAL | FAIL |
|----------|-------|------|---------|------|
| Links (2.8) | 4 | 3 | 1 | 0 |
| Images (2.9) | 4 | 4 | 0 | 0 |
| Typography (2.11) | 6 | 6 | 0 | 0 |
| Character Escapes (2.12) | 7 | 7 | 0 | 0 |
| Paragraphs (2.13) | 2 | 2 | 0 | 0 |
| **Total** | **23** | **22** | **1** | **0** |

---

## Links (Section 2.8)

### Rule 1 -- `\href{url}{label}` output

**Spec:** `\href{url}{label}` produces `<a class="scriba-tex-link" href="url" rel="noopener noreferrer">label</a>`

**Implementation:** `scriba/tex/parser/environments.py` lines 119-128 (`_href_sub`).
Regex at line 130: `\\href\{([^}]*)\}\{([^}]*)\}`

The href attribute is entity-escaped via `html_escape_attr()`, and the label text via `html_escape_text()`. Class, href, and rel attributes all match the spec.

**Snapshot confirmation:** `tests/tex/snapshots/url_and_href.html` shows:
`<a class="scriba-tex-link" href="https://b.example" rel="noopener noreferrer">B</a>`

**Verdict: PASS**

---

### Rule 2 -- `\url{url}` output

**Spec:** `\url{url}` produces `<a class="scriba-tex-link" href="url" rel="noopener noreferrer">url</a>` where the display text is the URL itself.

**Implementation:** `scriba/tex/parser/environments.py` lines 109-117 (`_url_sub`).
Regex at line 131: `\\url\{([^}]*)\}`

The display text uses `html_escape_attr(raw)` (which escapes both `<>&"'`) rather than `html_escape_text(raw)` (which only escapes `<>&`). For URLs containing literal quote characters, the visible text would display `&quot;` instead of `"`. For all realistic URLs this is a non-issue, but it is technically inconsistent with the spec which shows the display text as the plain URL.

**Snapshot confirmation:** `tests/tex/snapshots/url_and_href.html` shows:
`<a class="scriba-tex-link" href="https://a.example" rel="noopener noreferrer">https://a.example</a>`

**Verdict: PARTIAL** -- Display text uses attribute-level escaping (`html_escape_attr`) instead of text-level escaping (`html_escape_text`). Functionally correct for all normal URLs; quotes in display text would be over-escaped.

**Recommended fix:** In `_url_sub`, change the display text from `{href}` to `{html_escape_text(raw)}` for consistency with `_href_sub` which correctly uses `html_escape_text` for its label.

---

### Rule 3 -- Safe URL schemes

**Spec:** Safe schemes are `http`, `https`, `mailto`, `ftp`, and relative (empty scheme).

**Implementation:** `scriba/tex/parser/_urls.py` lines 10-12.
```python
_SAFE_SCHEMES: frozenset[str] = frozenset(
    {"http", "https", "mailto", "ftp", ""}
)
```

Empty string represents relative URLs. The `is_safe_url` function (lines 20-43) strips control characters, rejects invisible/bidi chars, and parses via `urllib.parse.urlparse`. Scheme comparison is case-insensitive (`.lower()` at line 40).

**Test confirmation:** `tests/tex/test_tex_xss.py` has 5 XSS tests covering `javascript:`, newline smuggling, unicode line separator, tab smuggling, and uppercase `JAVASCRIPT:` -- all correctly rejected.

**Verdict: PASS**

---

### Rule 4 -- Unsafe schemes produce disabled span

**Spec:** Unsafe schemes produce `<span class="scriba-tex-link-disabled">`.

**Implementation:** Both `_url_sub` (line 112) and `_href_sub` (line 123) in `environments.py` emit:
`<span class="scriba-tex-link-disabled">{escaped_text}</span>`

For `\href`, the disabled span shows the label text (not the URL). For `\url`, it shows the URL text. Both are HTML-escaped.

**Test confirmation:** `tests/tex/test_tex_xss.py` lines 18-23 (`test_xss_javascript_url_in_href`) asserts `scriba-tex-link-disabled` is present.

**Verdict: PASS**

---

## Images (Section 2.9)

### Rule 5 -- `\includegraphics` basic output

**Spec:** `\includegraphics[width=8cm]{photo.jpg}` produces `<img>` with CSS width.

**Implementation:** `scriba/tex/parser/images.py` lines 79-113 (`apply_includegraphics`).
Regex at line 16: `\\includegraphics(?:\[([^\]]*)\])?\{([^}]+)\}`

Output format (lines 107-110):
`<img src="{safe_url}" alt="{safe_name}" class="scriba-tex-image"{style_attr} />`

Note: The spec does not mention the `alt` attribute or the `scriba-tex-image` class name, but these are reasonable additions. The CSS width conversion is correct.

**Snapshot confirmation:** `tests/tex/snapshots/includegraphics_with_width_cm.html`:
`<img src="/resources/fig.png" alt="fig.png" class="scriba-tex-image" style="width: 189px" />`

5cm * 37.8 px/cm = 189px -- correct.

**Verdict: PASS**

---

### Rule 6 -- Options: width, height, scale

**Spec:** `width=Nunit`, `height=Nunit`, `scale=N`

**Implementation:** `scriba/tex/parser/images.py` lines 30-76 (`_parse_options`).

- `scale=N` -> `transform: scale(N)` plus `transform-origin: top left` (lines 47-51)
- `width=Nunit` -> `width: Npx` (lines 53-66)
- `height=Nunit` -> `height: Npx` (lines 53-66)

The spec says `scale=N` maps to `CSS transform: scale(N)` -- matches. Width and height produce pixel values -- matches.

**Snapshot confirmation:** `tests/tex/snapshots/includegraphics_with_scale.html`:
`style="transform: scale(0.5); transform-origin: top left"` -- correct.

**Verdict: PASS**

---

### Rule 7 -- Recognized units: cm, mm, in, pt, px

**Spec:** `cm`, `mm`, `in`, `pt`, `px`

**Implementation:** `scriba/tex/parser/images.py` lines 21-27 (`_UNIT_TO_PX`):
```python
_UNIT_TO_PX: dict[str, float] = {
    "cm": 37.8,
    "mm": 3.78,
    "in": 96.0,
    "pt": 1.333,
    "px": 1.0,
}
```

All five units present. Conversion factors are standard CSS reference values.

**Verdict: PASS**

---

### Rule 8 -- Missing images fallback

**Spec:** Missing images render as `[missing image: filename]`.

**Implementation:** `scriba/tex/parser/images.py` lines 92-100. When `resource_resolver` returns `None` or the URL is unsafe:
```python
html = (
    f'<span class="scriba-tex-image-missing" '
    f'data-filename="{safe_name}">[missing image: {safe_name}]</span>'
)
```

The visible text `[missing image: filename]` matches the spec.

**Snapshot confirmation:** `tests/tex/snapshots/includegraphics_missing_resource.html`:
`<span class="scriba-tex-image-missing" data-filename="gone.png">[missing image: gone.png]</span>`

**Verdict: PASS**

---

## Typography (Section 2.11)

All typography rules are implemented in `scriba/tex/parser/dashes_quotes.py` (`apply_typography`, lines 11-33).

### Rule 9 -- `---` produces em dash (U+2014)

**Implementation:** Line 27: `text = text.replace("---", "\u2014")`
Triple-dash is replaced before double-dash (correct ordering).

**Snapshot:** `tests/tex/snapshots/dashes_and_quotes.html` contains the em dash character.

**Verdict: PASS**

---

### Rule 10 -- `--` produces en dash (U+2013)

**Implementation:** Line 28: `text = text.replace("--", "\u2013")`
Runs after `---` replacement, so `---` is not double-matched.

**Snapshot:** Confirmed in `dashes_and_quotes.html`.

**Verdict: PASS**

---

### Rule 11 -- ``` ``text'' ``` produces curly double quotes

**Implementation:** Line 23: `re.sub(r"``((?:[^']|'(?!'))*?)''", "\u201c\\1\u201d", text)`
Matches opening double-backtick and closing double-apostrophe, replacing with U+201C and U+201D.

**Snapshot:** `dashes_and_quotes.html` shows `\u201cthis\u201d` (curly double quotes around "this").

**Verdict: PASS**

---

### Rule 12 -- `` `text' `` produces curly single quotes

**Implementation:** Line 24: `re.sub(r"`([^']*?)'", "\u2018\\1\u2019", text)`
Runs after double-quote substitution to avoid interference.

**Verdict: PASS**

---

### Rule 13 -- `~` produces `&nbsp;`

**Implementation:** Line 32: `text = text.replace("~", "&nbsp;")`

**Verdict: PASS**

---

### Rule 14 -- `\\` produces `<br />`

**Implementation:** Line 31: `text = re.sub(r"\\\\", "<br />", text)`

Note: This runs during `apply_typography` which is called in step 7 of the main pipeline (line 465 of `renderer.py`). The `\\` regex matches two literal backslashes.

**Verdict: PASS**

---

## Character Escapes (Section 2.12)

Character escapes are handled in two places:
1. **Main pipeline** (`renderer.py` lines 433-446, step 3b): handles `\&`, `\%`, `\#`, `\_`, `\{`, `\}`
2. **Math extraction** (`math.py` line 66 + line 99-101): handles `\$` via sentinel

### Rule 15 -- `\$` produces `$`

**Implementation:** `scriba/tex/parser/math.py` line 66 replaces `\$` with `_DOLLAR_LITERAL` sentinel before math extraction. Line 101 (`restore_dollar_literals`) restores the sentinel to literal `$` after HTML escaping (called at `renderer.py` line 435).

**Snapshot:** `tests/tex/snapshots/escaped_dollar_is_literal.html`: `The price is $5.` -- correct.

**Verdict: PASS**

---

### Rule 16 -- `\&` produces `&`

**Implementation:** `renderer.py` line 440: `text.replace("\\&amp;", "&amp;")`
After `html.escape`, `\&` becomes `\&amp;`. The replacement produces `&amp;`, which renders as `&` in the browser.

**Verdict: PASS**

---

### Rule 17 -- `\%` produces `%`

**Implementation:** `renderer.py` line 441: `.replace("\\%", "%")`
The `%` character is not affected by `html.escape`, so the replacement is straightforward.

**Verdict: PASS**

---

### Rule 18 -- `\#` produces `#`

**Implementation:** `renderer.py` line 442: `.replace("\\#", "#")`

**Verdict: PASS**

---

### Rule 19 -- `\_` produces `_`

**Implementation:** `renderer.py` line 443: `.replace("\\_", "_")`

**Verdict: PASS**

---

### Rule 20 -- `\{` produces `{`

**Implementation:** `renderer.py` line 444: `.replace("\\{", "{")`

**Verdict: PASS**

---

### Rule 21 -- `\}` produces `}`

**Implementation:** `renderer.py` line 445: `.replace("\\}", "}")`

**Verdict: PASS**

---

## Paragraphs (Section 2.13)

### Rule 22 -- Blank lines create `<p class="scriba-tex-paragraph">`

**Implementation:** `renderer.py` lines 517-525 (step 10). Text is split on `\n\n+` into paragraphs (line 518). Each non-block paragraph is wrapped at line 540:
```python
f'<p class="scriba-tex-paragraph">{placeholders.restore_blocks(text)}</p>'
```

**Snapshot confirmation:** Multiple snapshots (e.g., `escaped_dollar_is_literal.html`, `url_and_href.html`) confirm the `scriba-tex-paragraph` class.

**Verdict: PASS**

---

### Rule 23 -- Block-level elements never wrapped in `<p>`

**Implementation:** `renderer.py` lines 527-539 (`_wrap_paragraph`).

Block detection uses two mechanisms:
1. **Block placeholders** (line 536): `if text in placeholders.block_tokens` -- code blocks and tables stored as block placeholders are emitted directly.
2. **HTML tag prefix** (line 538): `_BLOCK_PREFIX_RE` matches opening tags `h2|h3|h4|ul|ol|div|blockquote|table|pre|figure` -- these are emitted without `<p>` wrapping.

Additionally, lines 503-516 insert blank lines around block-level elements (headings, lists, blockquotes, tables, figures, and block placeholders) so they become their own paragraph slots.

**Verdict: PASS**

---

## Findings Summary

### PARTIAL (1)

| # | Rule | Issue | Severity | File | Lines |
|---|------|-------|----------|------|-------|
| 2 | `\url{}` display text | Display text uses `html_escape_attr` (escapes quotes) instead of `html_escape_text`. Over-escapes `"` and `'` in display text of URLs containing quotes. | LOW | `scriba/tex/parser/environments.py` | 116 |

### All other rules (22): PASS

No FAIL findings. The implementation faithfully follows the spec across links, images, typography, character escapes, and paragraph handling.

---

## Files Examined

| File | Relevant Lines | Purpose |
|------|---------------|---------|
| `scriba/tex/parser/environments.py` | 106-132 | `apply_urls` -- `\href` and `\url` |
| `scriba/tex/parser/_urls.py` | 1-43 | `is_safe_url` -- URL scheme validation |
| `scriba/tex/parser/images.py` | 1-113 | `apply_includegraphics` -- image parsing |
| `scriba/tex/parser/dashes_quotes.py` | 1-33 | `apply_typography` -- dashes, quotes, ties, breaks |
| `scriba/tex/parser/escape.py` | 1-128 | `PlaceholderManager`, HTML escaping primitives |
| `scriba/tex/parser/math.py` | 19, 66, 99-101 | `\$` sentinel handling |
| `scriba/tex/renderer.py` | 401-541 | Main pipeline, character escapes, paragraph wrapping |
| `tests/tex/test_tex_snapshots.py` | 169-199 | Snapshot tests for images, links, dashes |
| `tests/tex/test_tex_xss.py` | 1-98 | XSS hardening tests |
| `tests/tex/snapshots/*.html` | -- | Snapshot golden files |
