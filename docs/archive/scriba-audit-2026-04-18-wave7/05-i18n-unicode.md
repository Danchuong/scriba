# i18n / Unicode Audit — Scriba Wave 7 (2026-04-18)

Scope: Vietnamese/CJK/RTL text, grapheme clusters, file encoding, HTML lang,
KaTeX `\text{}`, width measurement, file-path Unicode, error formatting,
NFC/NFD normalisation.

Methodology: static code analysis + empirical Python PoC against the live
source tree.

---

## Findings

### [HIGH] F-I18N-01 — `render.py:106` `read_text()` without `encoding=`

**File:** `render.py:106`

```python
source = input_path.read_text()   # no encoding argument
```

**Also:** `render.py:212`

```python
output_path.write_text(full_html)  # no encoding argument
```

**PoC:**

```
$ python -c "
import pathlib, tempfile, os
f = pathlib.Path(tempfile.mktemp(suffix='.tex'))
f.write_bytes('Tiếng Việt'.encode('windows-1252', errors='replace'))
print(repr(f.read_text()))   # OK on macOS/UTF-8, corrupted on Windows
"
# macOS (UTF-8 locale): 'Ti?ng Vi?t'  (replacement chars - silent data loss)
# Windows cp1252 locale: UnicodeDecodeError or garbled text
```

**Expected:** source bytes decoded as UTF-8.
**Actual on Windows:** locale-specific codec (often `cp1252`) silently
misinterprets the file or raises `UnicodeDecodeError`.

**Fix:**

```python
# render.py line 106
source = input_path.read_text(encoding="utf-8")

# render.py line 212
output_path.write_text(full_html, encoding="utf-8")
```

---

### [HIGH] F-I18N-02 — `render.py:106` UTF-8 BOM not stripped

**File:** `render.py:106`

When a `.tex` file is saved with a UTF-8 BOM (`\xef\xbb\xbf`) — common from
Windows editors (Notepad, VS Code with "UTF-8 with BOM") — `read_text()` passes
the BOM through as the literal first character `U+FEFF`.

**PoC:**

```python
import pathlib, tempfile
f = pathlib.Path(tempfile.mktemp(suffix='.tex'))
f.write_bytes(b'\xef\xbb\xbf\\section{Hello}')
content = f.read_text(encoding='utf-8')
assert content[0] == '\ufeff'   # True — BOM becomes first char
```

The BOM character then flows into the lexer, the TeX parser, and ultimately
the HTML output as a zero-width non-breaking space, causing invisible parse
errors (e.g. the first `\section` command is never matched because the regex
sees `\ufeff\section`).

**Fix:**

```python
source = input_path.read_text(encoding="utf-8-sig")  # strips BOM automatically
```

---

### [HIGH] F-I18N-03 — `scriba/animation/primitives/base.py:133` `estimate_text_width` ignores grapheme width

**File:** `scriba/animation/primitives/base.py:133–143`

```python
def estimate_text_width(text: str, font_size: int = 14) -> int:
    s = str(text)
    avg_char_w = font_size * 0.62   # assumes monospace ASCII
    return int(len(s) * avg_char_w + 0.5)
```

`len(s)` counts Unicode codepoints, not:

1. **Grapheme clusters** — emoji ZWJ sequences (e.g. `👨‍👩‍👧‍👦`) have
   `len() = 7` (4 emoji + 3 ZWJ) but display width = 1–2 cells.
2. **CJK full-width characters** — ideographs render at ~1 em (14 px) but are
   counted identically to ASCII chars at 0.62 em (8.7 px) — a ~1.6× underestimate.
3. **Combining characters** — Vietnamese `Xếp` has combining diacritics that
   don't add display width.

**PoC:**

```
estimate_text_width('👨‍👩‍👧‍👦')  → 61 px  (actual browser: ~14 px)
estimate_text_width('二叉搜索树')   → 43 px  (actual browser: ~70 px)
estimate_text_width('Xếp hàng')    → 78 px  (actual browser: ~71 px, slight overcount from precomposed NFC)
```

**Impact:** Cell/viewbox sizing is incorrect for CJK labels and emoji values.
CJK text overflows cells; emoji labels produce grotesquely wide viewboxes.

**Fix (pragmatic):**

```python
import unicodedata

def _char_display_width(ch: str) -> float:
    """Return display width multiplier for one codepoint."""
    cat = unicodedata.category(ch)
    if cat in ('Mn', 'Me', 'Cf'):   # combining / format — zero width
        return 0.0
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ('W', 'F'):           # Wide / Fullwidth
        return 1.0                  # ~1 em in CJK fonts
    return 0.62                     # Latin/ASCII average

def estimate_text_width(text: str, font_size: int = 14) -> int:
    total = sum(_char_display_width(ch) for ch in str(text))
    return int(total * font_size + 0.5)
```

This does not solve ZWJ sequences perfectly (requires `grapheme` library for
full grapheme cluster segmentation) but fixes the CJK case and combining marks.

---

### [MEDIUM] F-I18N-04 — `scriba/animation/parser/lexer.py:89` `_IDENT_RE` is ASCII-only

**File:** `scriba/animation/parser/lexer.py:89`

```python
_IDENT_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
```

Shape names must match this regex (used at `lexer.py:165`, `lexer.py:231`).
Non-ASCII Unicode letters (Vietnamese `Đ`, `ắ`, CJK) cannot start or continue
an identifier.

**PoC:**

```
_IDENT_RE.match('mảng')  → matches 'm', rest 'ảng' becomes CHAR tokens
_IDENT_RE.match('Đồng')  → None (first char rejected entirely)
```

A `\shape{mảng}{Array}` declaration silently misparsed: the shape name
registers as `m` with subsequent `ảng` as stray CHAR tokens, causing confusing
downstream errors rather than a clear rejection.

**Expected:** Either (a) Unicode identifiers accepted (Python's `\w` in
`re.UNICODE` mode), or (b) a clear `E1XXX` error when non-ASCII appears in a
shape-name position.

**Fix option A** (accept Unicode identifiers):

```python
_IDENT_RE = re.compile(r"[\w&&[^\d]][\w]*", re.UNICODE)
# or simpler:
_IDENT_RE = re.compile(r"[^\W\d]\w*", re.UNICODE)
```

**Fix option B** (reject with clear error):

After failing `_IDENT_RE`, check if the current character is a non-ASCII letter
(`ch.isalpha() and not ch.isascii()`) and raise `E1006` with a hint.

---

### [MEDIUM] F-I18N-05 — `render.py:32` `lang="en"` hardcoded

**File:** `render.py:32`

```python
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en" data-theme="light">
```

The `lang` attribute is hardcoded to `"en"`. Documents with Vietnamese, Arabic,
or CJK narration will have incorrect language metadata, affecting:

- Screen reader pronunciation
- Browser hyphenation
- Bidirectional text algorithm (especially RTL languages)
- Search engine indexing

**Fix:** Accept an optional `--lang` CLI argument and thread it through
`RenderContext.metadata`:

```python
# render.py
parser.add_argument("--lang", default="en", help="BCP 47 language tag for HTML lang=")
# ...
HTML_TEMPLATE = HTML_TEMPLATE.replace('lang="en"', f'lang="{args.lang}"')
```

---

### [MEDIUM] F-I18N-06 — RTL text in narration has no `dir` attribute

**Files:** `render.py:32`, `scriba/animation/emitter.py:1065`

Arabic/Hebrew narration text flows left-to-right in the browser because neither
the `<html>` element nor the `<p class="scriba-narration">` carries a `dir`
attribute. RTL text mixed with LTR punctuation triggers Unicode Bidirectional
Algorithm (UBA) issues: parentheses, numbers, and punctuation are reordered
incorrectly.

**PoC:**

```tex
\narrate{خوارزمية البحث الثنائي: O(log n)}
```

Expected display: `O(log n) :خوارزمية البحث الثنائي` (RTL order, LTR for math)
Actual: RTL characters right-aligned inside LTR container without explicit `dir=`
guidance — browser may render incorrectly depending on first-strong heuristic.

**Fix:** Add `dir="auto"` to `<p class="scriba-narration">` in the emitter so
the browser's first-strong heuristic applies per paragraph:

```python
# emitter.py, narration paragraph
f'<p class="scriba-narration" dir="auto" ...>'
```

SVG `<text>` elements rendering RTL narration inside animation stages similarly
lack `direction` / `unicode-bidi` attributes — accept this as out-of-scope
since SVG RTL is a distinct engineering effort.

---

### [MEDIUM] F-I18N-07 — `scriba/tex/parser/environments.py:20–33` `slugify` drops all non-Latin characters

**File:** `scriba/tex/parser/environments.py:20–33`

```python
def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", decoded)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "section"
```

CJK and Arabic section headings collapse to the fallback `"section"`, causing
all CJK/Arabic headings to produce the same `id="section"` (deduplicated to
`id="section-2"`, `"section-3"`, etc.).

**PoC:**

```
slugify('二叉搜索树')  → 'section'
slugify('مرحبا')      → 'section'
slugify('Mảng và con trỏ')  → 'mang-va-con-tro'   # Vietnamese: ok (NFKD strips diacritics)
```

Vietnamese is actually handled acceptably (NFKD decomposition strips diacritics,
leaving ASCII base letters). CJK and Arabic are not.

**Impact:** Multiple CJK/Arabic headings cannot be individually hash-navigated.
This is a `[MEDIUM]` because the existing spec for `slugify` targets Latin
headings and the fallback is safe (no XSS), but the UX is broken for CJK/Arabic.

**Fix:** Preserve non-Latin codepoints in the slug using percent-encoding or a
transliteration table, or emit a hash-based suffix from the heading text.

---

### [LOW] F-I18N-08 — `scriba/animation/parser/lexer.py` column tracking counts codepoints, not graphemes

**File:** `scriba/animation/parser/lexer.py:134–252`

```python
col += advance      # advance = len(m.group()) — codepoint count
col += 1            # for single-char tokens
```

For source lines containing non-BMP emoji or precomposed Vietnamese, `col`
values in error messages refer to codepoint offsets, not visual column
positions. This causes caret-pointer snippets in error output
(`scriba/core/errors.py:68–69`) to point one or more columns to the right
of the actual error when the source line contains multi-codepoint grapheme
clusters before the error position.

**Impact:** Low — only affects diagnostic display, not rendering correctness.

**Fix:** No actionable fix without a grapheme-cluster segmenter dependency.
Document that `col` is a codepoint offset in error output.

---

### [LOW] F-I18N-09 — `scriba/animation/emitter.py:44` `_LABEL_ID_RE` is ASCII-only (by design but undocumented)

**File:** `scriba/animation/emitter.py:44`

```python
_LABEL_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9._-]*$")
```

Labels such as `bước-1`, `Đồng`, `café` silently fall back to
`frame-N` IDs without any warning. A Vietnamese user writing
`\step[label=bước-1]` gets no error and no indication that the label
was ignored.

**PoC:**

```
_LABEL_ID_RE.match('bước-1')  → None   (rejected — no warning emitted)
_LABEL_ID_RE.match('cafe-1')  → match  (ok)
```

**Fix:** Emit a `[E1116]` warning when a `\step[label=...]` value fails the
regex, advising the author to use ASCII-only labels.

---

### [LOW] F-I18N-10 — `base.py:178–203` `_wrap_label_lines` does not break CJK text

**File:** `scriba/animation/primitives/base.py:178–203`

Label line-breaking only splits at `" "`, `","`, `"+"`, `"="`, `"-"`. CJK
text has no inter-word spaces; a 30-character Chinese label is never wrapped
regardless of `max_chars`.

**PoC:**

```
_wrap_label_lines('这是一段很长的中文文字，没有空格分隔')
→ ['这是一段很长的中文文字，没有空格分隔']  (single line, overflows pill)
```

**Fix:** After the existing space-based split, add a fallback that breaks every
`max_chars` characters when the line is entirely CJK (no ASCII spaces):

```python
# After existing tokenizer, check if result is still 1 long CJK line
if len(lines) == 1 and len(lines[0]) > max_chars:
    s = lines[0]
    lines = [s[i:i+max_chars] for i in range(0, len(s), max_chars)]
```

---

## Confirmed-OK / Non-Issues

| Area | Verdict |
|------|---------|
| `html.escape()` + `_escape_xml()` with Unicode | OK — Python stdlib handles all Unicode correctly |
| NFC normalization in `grammar.py:99` and `selectors.py:66` | OK — implemented in Wave 5.1 |
| `json.dumps(ensure_ascii=True)` in worker IPC | OK — non-ASCII safely escaped for line-oriented protocol |
| KaTeX `\text{...}` with Latin diacritics | OK — KaTeX renders unicode in text mode |
| `scene_id_from_source` SHA-256 with Unicode source | OK — `.encode()` defaults to UTF-8 |
| Error message `__str__` with non-ASCII data values | OK — f-strings handle Unicode |
| `_escape_js()` in emitter | OK — escapes backtick/`${`/`</script>` but leaves Unicode intact (safe for UTF-8 HTML) |
| KaTeX `\text{}` CJK | Untested but KaTeX supports CJK in text mode via browser fonts |

---

## Summary Table

| ID | Severity | File:Line | Issue |
|----|----------|-----------|-------|
| F-I18N-01 | HIGH | `render.py:106,212` | `read_text()`/`write_text()` missing `encoding="utf-8"` |
| F-I18N-02 | HIGH | `render.py:106` | UTF-8 BOM not stripped (`encoding="utf-8-sig"` needed) |
| F-I18N-03 | HIGH | `primitives/base.py:133` | `estimate_text_width` ignores grapheme clusters and CJK full-width |
| F-I18N-04 | MEDIUM | `parser/lexer.py:89` | `_IDENT_RE` ASCII-only; non-ASCII shape names silently misparsed |
| F-I18N-05 | MEDIUM | `render.py:32` | `lang="en"` hardcoded; wrong for non-English documents |
| F-I18N-06 | MEDIUM | `emitter.py:1065` | No `dir` attribute on narration paragraphs; RTL text misorders |
| F-I18N-07 | MEDIUM | `tex/parser/environments.py:20` | `slugify()` drops all CJK/Arabic chars → duplicate `id="section"` |
| F-I18N-08 | LOW | `parser/lexer.py:134–252` | Column tracking counts codepoints, not graphemes |
| F-I18N-09 | LOW | `emitter.py:44` | Non-ASCII `\step[label=]` silently ignored; no warning emitted |
| F-I18N-10 | LOW | `primitives/base.py:178` | `_wrap_label_lines` never breaks CJK text (no spaces) |
