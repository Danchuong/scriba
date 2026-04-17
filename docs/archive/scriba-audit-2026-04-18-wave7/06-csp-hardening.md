# Wave 7 Audit — M4: CSP Hardening & Script-Injection Analysis

**Date:** 2026-04-18  
**Rendered input:** `examples/tutorial_en.tex` → `/tmp/tutorial.html` (no-minify)  
**Files audited:** `render.py`, `scriba/animation/emitter.py`, `scriba/animation/primitives/base.py`, `scriba/animation/primitives/graph.py`, `scriba/tex/katex_worker.js`

---

## 1. Violation Inventory

### 1.1 Inline `<script>` block

| # | Severity | Location | Detail |
|---|----------|----------|--------|
| S1 | **HIGH** | `emitter.py:1071` | One `<script>` block per widget, ~60 KB, contains both runtime logic and all frame data (SVG + narration) baked into a `var frames=[...]` literal |

Exact opening tag in rendered HTML:
```html
<script>
(function(){
  var W=document.getElementById('edit-distance-dp');
  var frames=[
    {svg:`<svg ...>`,narration:`...`, substory:``, label:``, tr:null, fs:0},
    ...
  ];
```

CSP violation: any policy without `'unsafe-inline'` or an explicit script hash/nonce blocks this tag entirely.

SHA-256 of the script content (tutorial_en render): `sha256-4Qq2dZB1PQ3ypQikBypzXWxa8SL1BWu1gnKdXKImsKg=`

**Critical insight:** The SHA-256 is stable across identical inputs (verified with two sequential renders). This is because the frame data is embedded directly in the script and is deterministic for a given `.tex` source. However, the hash must be recomputed whenever any frame content changes, making a static `meta` CSP with a hard-coded hash brittle for development workflows.

---

### 1.2 Inline `onclick` event handler

| # | Severity | Location | Detail |
|---|----------|----------|--------|
| S2 | **MEDIUM** | `render.py:42–45` | `<button class="theme-toggle" onclick="...">` in `HTML_TEMPLATE` |

Exact source:
```python
# render.py:42
<button class="theme-toggle" onclick="
  var t = document.documentElement.dataset.theme;
  document.documentElement.dataset.theme = t === 'dark' ? 'light' : 'dark';
">Toggle theme</button>
```

CSP violation: `script-src` without `'unsafe-inline'` blocks inline event handlers unconditionally — hashes and nonces do **not** apply to event handler attributes. This is a hard blocker that SHA-256 cannot solve.

---

### 1.3 Inline `<style>` block

| # | Severity | Location | Detail |
|---|----------|----------|--------|
| S3 | **LOW** | `render.py:37–39` | One large `<style>` block containing bundled CSS + KaTeX CSS (~414 KB); required by the standalone renderer |
| S4 | **LOW** | KaTeX output (375 occurrences) | `style="height:1em;vertical-align:..."` inline `style=` attributes injected by the KaTeX HTML renderer |

`style-src 'unsafe-inline'` is required for both. The KaTeX `style=` attributes alone make eliminating `'unsafe-inline'` for styles impractical without replacing KaTeX's HTML output mode with its MathML output (which would require a separate audit).

---

### 1.4 Summary: strict CSP violations

A policy of `script-src 'self'; style-src 'self'` would produce:

| Violation | Source | Blocker |
|-----------|--------|---------|
| Inline `<script>` | `emitter.py:1071` | Blocked unless hash/nonce present |
| `onclick` attribute | `render.py:42` | Blocked; unhashable |
| Inline `<style>` block | `render.py:37` | Blocked unless hash/nonce or `'unsafe-inline'` |
| 375× `style=` attrs | KaTeX output | Blocked; too many to hash |

---

## 2. Fix Paths

### Option A — Move all inline scripts to external `scriba.js` (recommended)

**Effort: M**

The widget runtime code (everything below `var frames=` through the closing IIFE) is ~11.7 KB and is fully static — it contains no frame data. Frame data is currently embedded in the `frames=[...]` literal inside the script.

**Migration plan:**

1. **Separate data from runtime.** Move the `var frames=[...]` payload into a `data-scriba-frames-json` attribute on the `.scriba-widget` div, encoded with `json.dumps` → `html.escape` (same as the existing `data-scriba-frames` used for substories). This is already working for the substory path (`emitter.py:822`).

2. **Widget self-initialization.** Change the IIFE to be a generic initializer that reads its own widget by scanning for `.scriba-widget[data-scriba-frames-json]` elements, or by reading the closest ancestor:
   ```js
   // scriba.js (static, external)
   (function() {
     document.querySelectorAll('.scriba-widget[data-scriba-frames-json]')
       .forEach(function(W) {
         var frames = JSON.parse(W.getAttribute('data-scriba-frames-json'));
         scribaInit(W, frames);
       });
   })();
   ```
   `scribaInit(W, frames)` contains the current show/animateTransition/snapToFrame logic verbatim.

3. **Multi-widget IPC / state isolation.** Each widget's state (`cur`, `_anims`, `_animState`) lives in the closure of its `scribaInit` call — closures naturally scope per-widget. Multiple widgets on one page each call `scribaInit` independently; their state does not overlap. The `MutationObserver` for theme switching still attaches to `document.documentElement` once globally (guard with a flag).

4. **Event handlers.** All event handlers (`prev.addEventListener`, `next.addEventListener`, `W.addEventListener('keydown')`) are already in the script block as `addEventListener` calls — no `onclick`/`onkeydown` attributes exist inside the widget. No changes needed there.

5. **Reference in HTML.** Replace each `<script>...</script>` block in the emitter with:
   ```html
   <script src="/static/scriba.js"></script>
   ```
   (or a `data:` URI for standalone files — same approach as the existing CSS bundler).

6. **`onclick` on theme toggle** (`render.py:42`). Replace with:
   ```html
   <button class="theme-toggle" id="scriba-theme-toggle">Toggle theme</button>
   ```
   and move the two-line handler into `scriba.js`:
   ```js
   var _tb = document.getElementById('scriba-theme-toggle');
   if (_tb) _tb.addEventListener('click', function() {
     var t = document.documentElement.dataset.theme;
     document.documentElement.dataset.theme = t === 'dark' ? 'light' : 'dark';
   });
   ```

**Result:** Zero inline `<script>` blocks, zero inline event handler attributes. CSP can be:
```
script-src 'self';
style-src 'self' 'unsafe-inline';
```
(`'unsafe-inline'` for styles remains required due to KaTeX `style=` attributes — see Option A+.)

**Mapping of inline blocks to exported functions:**

| Current inline block | Exported function(s) in `scriba.js` |
|----------------------|--------------------------------------|
| `initSub(el)` | `scribaInitSub(el)` — unchanged |
| `_updateControls(i)` | `_updateControls(W, ctr, prev, next, dots, i)` |
| `snapToFrame(i)` | `snapToFrame(stage, narr, subC, frames, i, ...)` |
| `animateTransition(toIdx)` | `animateTransition(...)` |
| `show(i, animate)` | `show(...)` |
| `_applyTransition(rec, parsed, pending)` | `_applyTransition(...)` |
| `_arrowheadAt(path, size)` | `_arrowheadAt(path, size)` — pure, no widget state |
| Theme toggle handler | anonymous in DOMContentLoaded guard |

---

### Option B — CSP nonces

**Effort: N/A — not applicable**

Nonces require a new random value per HTTP response. Scriba renders static `.html` files at build time with no server-side request context. A nonce baked into the file provides no security benefit (it is static and visible to any attacker who reads the file). This option is ruled out.

---

### Option C — SHA-256 hashes in `<meta>` CSP (build-time generated)

**Effort: S for temporary relief; not recommended long-term**

The widget runtime code is ~11.7 KB. The frame data (SVG + narration, ~48.5 KB in the tutorial) is embedded in the same script block, so the hash must cover both. For a given `.tex` source the hash is deterministic, meaning `render.py` can compute and inject it automatically:

```python
import hashlib, base64
digest = base64.b64encode(hashlib.sha256(script_content.encode()).digest()).decode()
csp_meta = f"<meta http-equiv='Content-Security-Policy' content=\"script-src 'sha256-{digest}'; style-src 'unsafe-inline'\">"
```

**Limitations:**
- The hash changes whenever any frame content changes (different `.tex` → different SVG).
- The `onclick` attribute (`render.py:42`) is **not** coverable by a hash; it requires `'unsafe-inline'` or removal. This is an unconditional hard blocker.
- The `<meta>` CSP is weaker than a response-header CSP (cannot restrict `frame-src`, ignored by some parsers).

**Verdict:** Option C unblocks inline scripts for snapshot testing but cannot fix the `onclick` violation. Useful only as a transitional measure before Option A is complete.

---

## 3. Inline `<style>` — Same Rules Apply

`style-src 'unsafe-inline'` is required by:

1. The bundled `<style>` block in `render.py:37` (one block, hashable in principle).
2. KaTeX's 375+ `style=` inline attributes (not hashable without per-attribute effort).

KaTeX's `output: "html"` mode (configured in `katex_worker.js:43`) always emits `style=` attributes for layout. Switching to `output: "mathml"` would eliminate those attributes but requires separate font/rendering audit. The path of least resistance is to accept `'unsafe-inline'` for `style-src` permanently and focus CSP hardening on `script-src`.

---

## 4. XSS / Script Injection Findings

### 4.1 `data-*` attributes — user-controlled strings

| Finding | Severity | Status |
|---------|----------|--------|
| `data-target`, `data-shape`, `data-scriba-scene`, `data-substory-id` | — | **SAFE** — all values pass through `_escape()` (`html.escape(text, quote=True)`) before insertion into HTML attributes. Zero unescaped angle brackets found in 383 `data-*` values audited in the rendered output. |
| `aria-label`, `aria-labelledby` | — | **SAFE** — same `_escape()` wrapper used at `emitter.py:538,767,831,1053` |
| `data-scriba-frames` (substory JSON) | — | **SAFE** — `_json.dumps(json_frames)` → `_escape()` → HTML attribute. Decoded by `JSON.parse(el.getAttribute(...))` which un-entity-decodes before JSON parsing. Verified round-trip. |

### 4.2 KaTeX `trust: false` — confirmed

`katex_worker.js:52`: `trust: false` is set and documented. This blocks `\href`, `\url`, `\htmlId`, `\class`, `\data`, `\includegraphics`. No narration path bypasses this: narration text goes through `ctx.render_inline_tex` → `TexRenderer.render_inline_text()` → the same KaTeX worker with the same options.

The narration `innerHTML` assignment (`emitter.py:1121`, `emitter.py:1296`) receives KaTeX-rendered output (math) interleaved with `html.escape`-ed plain text. User math input cannot inject `<script>` or event handlers because `trust: false` prevents raw HTML output from KaTeX macros.

**Status: SAFE** — no narration bypass path found.

### 4.3 SVG `<title>` — user-controlled edge/annotation labels

Two sites produce SVG `<title>` elements with user-supplied content:

| Location | Escaping used | Status |
|----------|---------------|--------|
| `primitives/graph.py:763` — `<title>{edge_label}</title>` | `html_escape()` (`from html import escape as html_escape`, line 14) applied at construction of `edge_label` (lines 696–697) | **SAFE** |
| `primitives/base.py:1072` — `<title>{ann_desc}</title>` | `_escape_xml()` applied inside `ann_desc` construction at lines 742–744, 1034–1038 | **SAFE** |

`_escape_xml()` (`base.py:432`) escapes `&`, `<`, `>`, `"` — sufficient for XML text content. `html.escape()` in `graph.py` escapes the same set. Both prevent injection of child elements inside `<title>`.

**Minor note:** `edge_label` at `graph.py:759` is also placed in `aria-label="..."` without re-escaping through `_escape()` / `html.escape(quote=True)`. The `html_escape()` call at construction does escape `"` (`html.escape` default: `quote=False`). Inspect:

```python
# graph.py:14
from html import escape as html_escape
# graph.py:696
edge_label = (
    f"Edge from node {html_escape(str(u))} "
    f"to node {html_escape(str(v))}"
)
# graph.py:759
f'role="graphics-symbol" aria-label="{edge_label}">'
```

`html.escape()` with `quote=False` does **not** escape `"`. Node IDs containing a literal `"` would break out of the attribute. In practice, graph node IDs come from Starlark integer or string literals and are unlikely to contain `"`, but this is a latent defect.

| Finding | Severity | File:Line |
|---------|----------|-----------|
| `html_escape` called without `quote=True` on `edge_label` used in `aria-label="..."` attribute | **LOW** | `graph.py:696`, `graph.py:759` |

**Fix (effort S):** Change `html_escape(str(u))` / `html_escape(str(v))` to `html_escape(str(u), quote=True)` / `html_escape(str(v), quote=True)`.

### 4.4 JSON data in backtick template literals

Frame data (SVG, narration, substory HTML) is embedded in the inline script via `_escape_js()` and backtick template literals:

```python
# emitter.py:629
def _escape_js(text: str) -> str:
    return (
        text
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
        .replace("</script>", r"<\/script>")
        .replace("</style>", r"<\/style>")
    )
```

The concern in the Wave 5 audit about `JSON.parse('...')` with single-quote escaping does **not** apply here: the embedding uses backtick template literals, not single-quoted strings. `_escape_js` correctly handles all injection vectors specific to backtick context:

- Backslash: escaped → `\\`
- Backtick: escaped → `` \` ``
- Template expression start `${`: escaped → `\${`
- `</script>`: escaped → `<\/script>` (prevents parser confusion)
- `</style>`: escaped → `<\/style>`

Single quotes need no escaping in backtick strings. **Status: SAFE.**

The `data-scriba-frames` path uses `_json.dumps` → `_escape()` (HTML entity encoding) → attribute → `JSON.parse(el.getAttribute(...))`. The browser automatically un-entity-decodes the attribute value before `getAttribute` returns it, so the JSON round-trip is correct. **Status: SAFE.**

---

## 5. Recommended Action Plan

| Priority | Item | Effort | File(s) |
|----------|------|--------|---------|
| 1 | Move theme-toggle `onclick` to `addEventListener` in `scriba.js` or inline script | S | `render.py:42` |
| 2 | Move widget runtime code to external `scriba.js`; move frame data to `data-scriba-frames-json` attribute | M | `emitter.py:1071–1355`, `render.py:210` |
| 3 | Fix `html_escape(quote=False)` on `edge_label` used in `aria-label` attribute | S | `graph.py:696–697` |
| 4 | Accept `style-src 'unsafe-inline'` permanently until KaTeX MathML migration | — | documentation only |
| 5 | (Optional) Add build-time SHA-256 script hash to `<meta>` CSP as intermediate measure | S | `render.py` |

**Minimum viable CSP after items 1–2:**

```
Content-Security-Policy:
  default-src 'none';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
  font-src 'self' data:;
  frame-src 'none';
  object-src 'none';
  base-uri 'self';
```

This eliminates all `script-src` violations. `style-src 'unsafe-inline'` remains required for KaTeX.
