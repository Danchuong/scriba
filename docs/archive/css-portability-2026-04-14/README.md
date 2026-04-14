# CSS Portability & Deduplication Plan

**Date:** 2026-04-14
**Goal:** Make `render.py` output fully portable (zero CDN, zero external files) while eliminating CSS duplication.
**See also:** [portability-audit.md](portability-audit.md) — full-stack portability audit (network, system, packaging, cross-platform)

---

## Current State

### Problem 1: CSS Duplication

`render.py` `HTML_TEMPLATE` contains ~300 lines of CSS hand-copied from `scriba-scene-primitives.css` with `{{}}` Python escaping. Two copies of:

- CSS custom properties (`--scriba-state-*-fill/stroke/text`)
- State class rules (`.scriba-state-idle`, `.scriba-state-current`, etc.)
- Text halo cascade (`paint-order: stroke fill markers`)
- Dark mode token overrides (`[data-theme="dark"]`)

Only the halo cascade is enforced by `test_css_font_sync.py::TestHaloCascadeParity`. Other rules drift silently.

**Files involved:**
- `render.py` lines 32-501 (inline `<style>` in `HTML_TEMPLATE`)
- `scriba/animation/static/scriba-scene-primitives.css` (769 lines, canonical)

### Problem 2: KaTeX CDN Dependency

`render.py:646` hardcodes:
```
https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/katex.min.css
```

But KaTeX is already **fully vendored** locally:
- `scriba/tex/vendor/katex/katex.min.css` (version 0.16.11)
- `scriba/tex/vendor/katex/fonts/` (20 woff2 files, 296 KiB total)

**Issues:**
- Output HTML requires internet for math rendering
- Version mismatch: vendored 0.16.11 vs CDN 0.16.22
- KaTeX CSS references fonts via relative `url(fonts/...)` — can't inline CSS alone without fonts

### Problem 3: No CSS Inlining Pipeline

The `RenderArtifact` / `Pipeline` system properly declares `css_assets` via filenames, but `render.py` ignores this entirely. It hardcodes CSS in a Python string instead of reading from source `.css` files.

### What Already Works

- All JS: 100% inline (vanilla, no deps)
- All SVG/animation data: 100% inline
- KaTeX JS: vendored, server-side only (Node worker)
- KaTeX fonts: vendored woff2 files
- Pipeline `RendererAssets` protocol: designed for asset collection

---

## Solution Design

### Principle: Single Source, Inline Everything

Output HTML should be **one file, zero external dependencies**. CSS comes from `.css` source files, read at render time and injected into `<style>`.

### Phase 1: Extract render.py CSS into source files

**Goal:** Kill the 300-line duplicated CSS block in `HTML_TEMPLATE`.

**Steps:**

1. **Create `scriba/animation/static/scriba-standalone.css`**
   - Move render.py-only CSS here: widget chrome, controls bar, progress dots, stage layout, narration panel, filmstrip, theme toggle button
   - ~100 lines, no duplication with `scriba-scene-primitives.css`

2. **Modify `render.py` to read CSS from files at render time**
   ```python
   from importlib.resources import files

   def _load_css(*names: str) -> str:
       """Read and concatenate CSS files from scriba packages."""
       parts = []
       for name in names:
           # Resolve from scriba.animation.static or scriba.tex.static
           if name.startswith("scriba-tex"):
               pkg = files("scriba.tex").joinpath("static", name)
           else:
               pkg = files("scriba.animation").joinpath("static", name)
           parts.append(pkg.read_text())
       return "\n".join(parts)
   ```

3. **Update `HTML_TEMPLATE`**
   - Replace 300-line inline CSS with `{css}` placeholder
   - At render time: `css = _load_css("scriba-scene-primitives.css", "scriba-animation.css", "scriba-standalone.css")`
   - No more `{{}}` escaping headache

4. **Delete duplicated CSS from `HTML_TEMPLATE`**
   - Keep only the `{css}` injection point
   - Template shrinks from ~500 lines to ~30 lines

5. **Update `test_css_font_sync.py`**
   - `TestHaloCascadeParity` can be simplified or removed — no more two copies to compare
   - `TestRenderTemplateFontSync` reads from source CSS directly

**Risk:** Low. CSS output identical, just sourced differently.

### Phase 2: Inline KaTeX CSS with embedded fonts

**Goal:** Zero CDN dependency for math rendering.

**Steps:**

1. **Create build script `scripts/bundle_katex_css.py`**
   - Read `scriba/tex/vendor/katex/katex.min.css`
   - Find all `url(fonts/KaTeX_*.woff2)` references
   - Replace each with `url(data:font/woff2;base64,<base64-encoded-font>)`
   - Write output to `scriba/tex/vendor/katex/katex-inline.css`
   - Run once after KaTeX version upgrades

2. **Alternative: Inline at render time (simpler, slower)**
   ```python
   def _inline_katex_css() -> str:
       katex_dir = files("scriba.tex.vendor.katex")
       css = (katex_dir / "katex.min.css").read_text()
       fonts_dir = katex_dir / "fonts"
       
       def replace_font_url(match):
           font_file = match.group(1)
           font_path = fonts_dir / font_file
           b64 = base64.b64encode(font_path.read_bytes()).decode()
           return f"url(data:font/woff2;base64,{b64})"
       
       return re.sub(r'url\(fonts/(KaTeX_[^)]+\.woff2)\)', replace_font_url, css)
   ```

3. **Update `render.py`**
   - Replace CDN `<link>` with `<style>{katex_inline_css}</style>`
   - Use vendored version (0.16.11) — fixes version mismatch too

4. **Size impact**
   - KaTeX CSS: ~25 KiB
   - 20 fonts base64'd: ~395 KiB (296 KiB * 1.33 base64 overhead)
   - Total added to each HTML: ~420 KiB
   - Acceptable for standalone educational HTML files

**Risk:** Medium. Font rendering must match CDN version. Test with math-heavy .tex files.

**Alternative if 420 KiB too large:** Subset fonts — KaTeX uses only ~8 of 20 fonts for typical math. Can analyze actual usage and embed only needed fonts. Deferred unless size is a complaint.

### Phase 3: Conditional CSS loading (optional, future)

**Goal:** Support both portable (inline) and lightweight (external link) modes.

**Steps:**

1. Add `--portable` flag to `render.py` (default: True)
   - `--portable`: inline all CSS + fonts (current plan)
   - `--no-portable`: use `<link>` tags pointing to relative paths, copy assets alongside HTML

2. Add `--assets-dir` flag
   - When `--no-portable`: copy CSS/font files to specified directory
   - Generate `<link>` tags with relative paths

**Deferred.** Phase 1 + 2 solve the immediate problem. Phase 3 only needed if file size becomes an issue.

---

## File Changes Summary

| File | Action |
|------|--------|
| `scriba/animation/static/scriba-standalone.css` | **Create** — render.py-only widget chrome CSS (~100 lines) |
| `render.py` | **Edit** — replace inline CSS with file reads, replace KaTeX CDN with inline |
| `scripts/bundle_katex_css.py` | **Create** — one-time KaTeX CSS+font bundler (if pre-build approach chosen) |
| `tests/unit/test_css_font_sync.py` | **Edit** — simplify parity tests, add portable output tests |

## Validation Plan

1. Render existing examples (`dinic.tex`, `mcmf.tex`, `maxflow.tex`) with new code
2. Diff HTML output — CSS rules should be identical, just sourced from files
3. Open output HTML **offline** (airplane mode) — math fonts must render
4. Run `test_css_font_sync.py` — all tests pass
5. Check HTML file size delta — should be ~420 KiB larger due to inlined fonts
6. Visual regression: screenshot before/after comparison of rendered examples

## Migration Notes

- No breaking changes to `.tex` input format
- No breaking changes to Pipeline/cookbook path (untouched)
- `render.py` CLI interface unchanged
- Output HTML format unchanged (just CSS source changes)
- Existing rendered `.html` files in examples/ should be re-rendered after migration

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Inline at render time, not pre-build | Simpler, no build step. ~50ms overhead acceptable for CLI tool |
| Base64 fonts in CSS | Data-URI is the only way to make one-file HTML with custom fonts |
| Keep all 20 KaTeX fonts | Subsetting requires usage analysis per document — complexity not worth it yet |
| Default to portable | Primary user is offline-first educational content |
| Phase 3 deferred | YAGNI until file size is actually a problem |
