# Scriba Performance Audit — 2026-04-17

**Scope:** `scriba/animation/` and the render path  
`render.py → AnimationRenderer.render_block → _parse → _materialise → emit_animation_html`  
**Date:** 2026-04-17  
**Tooling:** Python `cProfile`, `resource.getrusage`, `time.perf_counter`, `/usr/bin/time -l`

---

## Summary

The render path is fast for real-world usage (3–10 frames, typical primitive counts). The **critical bottleneck is not algorithmic** — it is a fixed-cost tax paid on every render regardless of content:

1. **`_minify_css` on 397 KB of already-minified CSS** — 11 ms per render. KaTeX's CSS (`katex.min.css`, 358 KB, 253 KB of which is base64 font data) is inlined and then re-processed by the regex-heavy `_minify_css` pipeline on every render call. This alone accounts for ~56% of render time for typical inputs.

2. **Full SVG per frame with no diffing** — For N=500 cells, each frame stores 87 KB of SVG, 99.8% of which is structurally identical to adjacent frames. JS stores F copies (template literals), and the print-frame section stores another F copies as static DOM HTML. 6 full SVG copies in a 900 KB file where only 3 bytes differ per adjacent pair.

3. **`_expand_selectors` re-compiles 3 regexes per call** — called twice per frame per primitive on every render, recompiling `range_re`, `all_re`, and `top_re` from scratch each time (Python's `re` module caches compiled patterns internally, but the `re.compile()` call overhead and import still fire every invocation).

4. **`DOMParser().parseFromString(svg)` on every forward step** — the JS animation runtime parses the full next-frame SVG string on every step click even when only a CSS class name changes. For N=500 cells this means parsing 87 KB of XML per navigation.

5. **`inspect.signature` inside a tight loop** — `_emit_frame_svg` calls `inspect.signature(prim.apply_command)` inside the per-target inner loop for any primitive that has `apply_command`. The result is not cached between iterations or frames.

---

## Scaling Table

Measurements taken in-process (no subprocess overhead), 5 runs each, median reported. Platform: macOS 25.1, Apple Silicon M-series, Python 3.10.

| Fixture | N (cells) | Frames | Render time (median) | Output size | Peak RSS |
|---------|-----------|--------|----------------------|-------------|----------|
| Array N=10, 3 frames | 10 | 3 | 3.0 ms | 421 KB | ~54 MB |
| Array N=100, 3 frames | 100 | 3 | 5.8 ms | 508 KB | ~54 MB |
| Array N=500, 3 frames | 500 | 3 | 16.9 ms | 901 KB | ~54 MB |
| Array N=1000, 2 frames | 1000 | 2 | 23.1 ms | 1,065 KB | ~54 MB |
| N=10 cells, 1 frame | 10 | 1 | 2.2 ms | 413 KB | ~54 MB |
| N=10 cells, 10 frames | 10 | 10 | 4.9 ms | 449 KB | ~54 MB |
| foreach 50 iters × 50 cells | 50 | 2 | 5.7 ms | 446 KB | ~54 MB |

**Subprocess (cold process) times** add ~215 ms Python startup overhead flat across all cases.

**Peak RSS** is ~54 MB regardless of input size — dominated by the Python interpreter and imported modules, not by the rendered content. Content contribution is negligible (< 8 MB measured delta between renders).

### Scaling characteristics

- **Array cell count (N):** `emit_svg` scales linearly O(N) — confirmed: 1×/10×/50×/100× cells yields 1×/8×/40×/79× `emit_svg` time. The full `render_file` call scales sub-linearly vs N because the fixed CSS/minify overhead dominates for small N and grows slowly for large N.
- **Frame count (F):** Sub-linear — 10× frames gives only 2.2× total time from 1 frame to 10 frames, because fixed overhead (CSS loading, parsing) is amortized. Frame-proportional work (`emit_svg` × F, differ × F) is cheap.
- **Foreach iterations (I):** Linear — 10→50→100 iterations adds ~0.28/0.81/1.42 ms for parse+expand+apply. `_substitute_body` is O(I × body_size), both small in practice.
- **`_minify_html` input size:** Sub-linear — 421→901→1065 KB inputs cost 16→27→29 ms because the CSS block (constant 397 KB) dominates; the variable SVG/HTML portion adds ~2 ms per 500 KB.

---

## Hot Path Analysis

Profile target: `render_file(array_500.tex)`, 3 frames, N=500 cells.

```
69,370 function calls in 0.024 s (warm, after module import)
```

| Rank | Function | File:line | Self time | Calls | Note |
|------|----------|-----------|-----------|-------|------|
| 1 | `re.Pattern.sub` | `{builtin}` | 10–17 ms cumulative | 22–50 | CSS minification regex passes |
| 2 | `_minify_css` | `emitter.py:1362` | 11 ms | 1 | Runs on full 397 KB CSS block including KaTeX |
| 3 | `ArrayPrimitive.emit_svg` | `array.py:165` | 6 ms (2 calls) | 3 | 1.2 ms/call for N=500 |
| 4 | `_minify_js` | `emitter.py:1380` | 3 ms | 1 | Line-by-line scan of 268 KB JS block |
| 5 | `_render_svg_text` | `base.py:478` | 2 ms | 1,500 | Per-cell text render inside `emit_svg` |
| 6 | `SceneParser.parse` / `tokenize` | `grammar.py:66` / `lexer.py:129` | 2 ms | 1 | Scales O(N) with data array token count |
| 7 | `_inset_rect_attrs` | `base.py:113` | 2 ms | 1,500 | Per-cell rect attribute computation |

Dominant time for N=500: `_minify_css` (11 ms, 56% of total) + `emit_svg` (3.6 ms for 3 frames, 18%) + `_minify_js`+whitespace (3.8 ms, 19%) + parse/state machine (0.8 ms, 4%).

---

## Output Bloat Findings

### Output size composition (N=500 cells, 3 frames — 900 KB total)

| Component | Size | % of output | Notes |
|-----------|------|-------------|-------|
| KaTeX CSS (inline fonts) | 358 KB | 39.8% | `katex.min.css` + 20 woff2 fonts as base64 (253 KB of font bytes) |
| Scene/animation CSS | 36 KB | 4.0% | `scriba-scene-primitives.css`, `scriba-animation.css`, etc. |
| Pygments CSS | 3 KB | 0.3% | Syntax highlighting (loaded unconditionally) |
| JS frame SVGs (template literals) | ~256 KB | 28.5% | 3 frames × 87 KB each, stored as escaped JS strings |
| Print-frame SVGs (DOM HTML) | ~234 KB | 26.0% | 3 frames × 78 KB each, unescaped, in `display:none` div |
| JS animation runtime | ~7 KB | 0.8% | The actual animation controller code |
| HTML scaffolding | ~7 KB | 0.8% | Buttons, narration containers, widget structure |

**KaTeX CSS is 39.8% of every output file** regardless of whether any math appears in the animation.

### SVG duplication: no content diffing

Every frame stores a full independent SVG snapshot. There is no SVG diffing, delta compression, or shared DOM structure between frames.

For N=500, 3 frames:
- **6 full SVG copies** exist in the output: 3 in the JS `frames` array as template literals, 3 in the print-frame section as static DOM HTML.
- Between adjacent frames, **only 1 of 500 cell elements changes** (a single CSS class attribute). The other 499 cells (99.8% of the SVG) are byte-for-byte identical.
- Total SVG bytes: ~490 KB. Unique information: ~3 bytes per frame boundary.
- **The differ (`differ.py`) correctly computes CSS-level transitions** between frames, allowing the JS to perform targeted DOM mutations (`recolor`, `value_change`, etc.) without a full innerHTML swap on forward steps. However, the full SVG strings are still stored and the full SVG is still parsed by `DOMParser` on every animated transition.

### Per-frame SVG sizes

| N cells | SVG size per frame | 3 frames total |
|---------|--------------------|----------------|
| 10 | 1.9 KB | 5.7 KB |
| 100 | 16 KB | 48 KB |
| 500 | 87 KB | 261 KB |
| 1,000 | 172 KB | 344 KB (2 frames) |

---

## Starlark IPC Costs

The Starlark worker runs as a **persistent subprocess** (not re-forked per call). Measurements:

| Scenario | Median latency |
|----------|---------------|
| Single `eval()` call, small bindings (`{"h": [1,2,3]}`) | 0.25 ms |
| Single `eval()` call, 1,000-element list binding | 0.61 ms |
| 10 separate `eval()` calls (10 round-trips) | 1.33 ms total |
| 1 combined `eval()` (same work, 1 round-trip) | 0.34 ms |
| Per-call IPC overhead (amortized across 10 calls) | ~0.10 ms/call |

The IPC transport (Unix socket / pipe JSON) costs ~0.10–0.25 ms per call, not per unit of work. This is negligible for the common case (1–2 `\compute` blocks per animation). If a document has 10 separate `\compute` blocks, batching them into one call saves ~1 ms.

**There is no batching across `\compute` blocks today.** Each `ComputeCommand` in `_instantiate_primitives` and `_run_compute` sends a separate `eval` request. For typical scriba documents this is not a bottleneck, but for documents with many `\compute` blocks (e.g., algorithmic examples with intermediate computations per frame), the overhead accumulates linearly.

---

## Frontend Perf Gotchas

### 1. `DOMParser().parseFromString(svg)` on every animated forward step

`emitter.py`, `animateTransition()` (JS runtime, line ~1296 in emitter output):

```js
var parsed = new DOMParser().parseFromString(frames[toIdx].svg, 'image/svg+xml');
```

This fires on every forward navigation click when transitions exist. For N=500, the browser must parse 87 KB of SVG XML. On a modern desktop this is imperceptible (~0.5 ms), but on mobile or in rapid succession (keyboard arrow spam) it creates jitter. The parsed document is used only to find newly-added elements (`element_add`, `annotation_add` transitions); for `recolor` and `value_change` transitions it could be eliminated entirely with targeted class manipulation on the existing DOM.

### 2. `stage.innerHTML = frames[i].svg` on backward navigation and `fs:1` frames

`snapToFrame(i)` does `stage.innerHTML = frames[i].svg` — a full innerHTML replacement that forces the browser to re-parse and re-layout the entire SVG. For N=500 (87 KB SVG) this replaces 500 DOM nodes. There is no partial update or node reuse.

The `fs:1` (full sync) flag on frames where the SVG changed structurally also triggers `stage.innerHTML` at the end of a transition sequence. This is necessary for correctness (structural mutations like `add_edge`, `add_node`) but fires even for simple recolor changes when `svg_changed` is True (see `emitter.py:1030`).

### 3. Inline KaTeX CSS parsed on every page load

358 KB of CSS including 253 KB of base64-encoded woff2 font data must be parsed by the browser's CSS engine on every page load. There is no CDN link, no `<link>` tag with browser caching, and no preload hint. The CSS is identical across all Scriba pages and cannot be shared across page loads in the browser cache.

### 4. No lazy SVG evaluation — all frames pre-rendered at document load

All frame SVGs are rendered at server build time and embedded in the HTML. The browser receives the full multi-frame payload even if the user never advances past frame 1. For a 10-frame N=500 animation, this would be ~870 KB of SVG data loaded unconditionally.

### 5. First paint delay

The 413–421 KB baseline output (even for a trivial 1-frame animation) must be fully received and parsed before `show(0, false)` runs and injects the first SVG into `stage.innerHTML`. The KaTeX CSS must be parsed before the first paint. On a 10 Mbps connection, 413 KB takes ~330 ms to transfer; on a 1 Mbps connection ~3.3 seconds.

---

## Top 5 Fixes Ranked

### Fix 1: Cache the minified CSS bundle across render calls

**Expected speedup:** 11 ms / render call (56% of hot-path time for N=500)  
**Effort:** Low — add `@functools.lru_cache(maxsize=1)` to `inline_katex_css()` and `load_css()` in `css_bundler.py`, or cache the fully-assembled + minified CSS string at module level.  
**File:line:** `scriba/core/css_bundler.py:14` (`load_css`), `scriba/core/css_bundler.py:33` (`inline_katex_css`)

The KaTeX CSS is read from disk, all font URLs are replaced with base64 data URIs, and then `_minify_css` runs 4 regex passes over the resulting 358 KB string — on every call to `render_file()`. Since the CSS content is immutable (it's vendored), caching the assembled+minified output at module level is safe and removes the largest single cost unconditionally.

```python
import functools

@functools.lru_cache(maxsize=1)
def inline_katex_css() -> str: ...

@functools.lru_cache(maxsize=None)
def load_css(*names: str) -> str: ...
```

Similarly, the assembled final CSS string (`"\n".join(css_parts)`) in `render_file` is identical across all renders of any document; it can be cached at module level.

---

### Fix 2: Eliminate re-minification of already-minified CSS

**Expected speedup:** 11 ms / render call (even without caching, the _minify_css call is wasteful)  
**Effort:** Low — skip `_minify_css` for CSS that is already minified, or do not pass KaTeX CSS through `_minify_html` at all.  
**File:line:** `emitter.py:1412` (`_minify_html`), `render.py:199` (CSS assembly)

`katex.min.css` is already minified (single line, no comments). Running `_minify_css` on it re-processes 358 KB with 4 regex passes for no size reduction (KaTeX CSS is already compact). The fix is either: (a) pass a flag to `_minify_html` indicating the CSS block is pre-minified, or (b) move the CSS into a separate file reference where the browser caches it and it is never minified inline.

Measuring the impact: `_minify_css(397KB)` takes 11 ms median. After Fix 1 caches it, subsequent renders pay 0 ms for the CSS minification. Fix 2 makes the first render cheaper as well.

---

### Fix 3: Move CSS to an external cached file (eliminates first-paint bottleneck)

**Expected speedup:** 330–3,300 ms first-load on slow connections; enables browser caching across page loads  
**Effort:** Medium — requires serving a static CSS file rather than inline embedding, or splitting the HTML into a template + external assets.  
**File:line:** `render.py:191–207` (CSS assembly), `scriba/core/css_bundler.py` (entire module)

The current design inlines all CSS (including 253 KB of base64 fonts) into every HTML output for offline/self-contained use. This prevents browser caching entirely. A two-file output mode (`output.html` + `scriba-bundle.css`) would allow browsers to cache the 397 KB CSS across all Scriba pages. This is a design trade-off: self-contained vs cacheable. Implementing an optional `--external-css` flag would serve both use cases.

---

### Fix 4: Remove `_expand_selectors` regex recompilation

**Expected speedup:** < 1 ms / render (low impact, but clean)  
**Effort:** Very low — move the three `re.compile()` calls outside the function or use a module-level cache keyed on `shape_name`.  
**File:line:** `emitter.py:367–370` (`_expand_selectors`)

```python
# Current: recompiles on every call
range_re = re.compile(rf"^{re.escape(shape_name)}\.range\[(\d+):(\d+)\]$")
all_re   = re.compile(rf"^{re.escape(shape_name)}\.all$")
top_re   = re.compile(rf"^{re.escape(shape_name)}\.top$")
```

Python's `re` module caches compiled patterns by (pattern_string, flags) so repeat calls with the same shape name are free after the first. The `import re` inside the function body also fires on every call (though Python caches module imports). The real fix is to hoist the `import re` to the module top level and use `@functools.lru_cache` on a helper that builds the three compiled patterns for a given shape name.

---

### Fix 5: Cache `inspect.signature` result in `_emit_frame_svg`

**Expected speedup:** < 0.5 ms / render for most primitives; noticeable for Stack/Queue/Graph renders with many apply_params targets  
**Effort:** Very low — cache per primitive class or per instance.  
**File:line:** `emitter.py:508–509`

```python
# Current: called inside per-target inner loop
_accepts_suffix = "target_suffix" in inspect.signature(
    prim.apply_command
).parameters
```

This runs once per primitive per frame (the comment says "Check once"), but it still runs for every frame on every render. `inspect.signature` is not free — it parses the function signature from the AST. Cache it per primitive class:

```python
_SIG_CACHE: dict[type, bool] = {}

def _accepts_target_suffix(prim: Any) -> bool:
    cls = type(prim)
    if cls not in _SIG_CACHE:
        _SIG_CACHE[cls] = "target_suffix" in inspect.signature(
            prim.apply_command
        ).parameters
    return _SIG_CACHE[cls]
```

---

## Methodology Notes

- All timing is in-process using `time.perf_counter()`, 5 runs per fixture, median taken to exclude GC pauses.
- CSS loading times measured on warm import (second+ call) unless noted; first-call times can be 10–50× higher due to `importlib.resources` path resolution.
- Peak RSS measured with `/usr/bin/time -l` (macOS) reporting `maximum resident set size` in bytes.
- Subprocess (cold start) overhead is ~215 ms flat for Python + uv interpreter startup, independent of content.
- Frame count was kept at ≤10 due to the renderer's built-in warning threshold (30 frames) and hard error threshold (100 frames). Benchmarks at higher frame counts would require patching `_FRAME_ERROR_THRESHOLD`.
- Starlark IPC was measured against a warm persistent worker (the worker subprocess stays alive for the duration of a render).
